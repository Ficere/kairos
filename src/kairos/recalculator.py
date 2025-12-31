"""技术面重算模块 - 基于缓存数据重新计算技术指标和评分"""
import json
import os
from datetime import datetime
from pathlib import Path

from kairos.futures.config import CONTRACTS, load_contracts
from kairos.futures.data_cache import (
    load_historical_data, load_multi_timeframe_data, 
    list_cached_contracts, has_cached_data
)
from kairos.futures.indicators import calc_all_indicators
from kairos.futures.indicators_mtf import calc_multi_timeframe_indicators, get_timeframe_alignment
from kairos.futures.divergence import detect_divergence
from kairos.trading_decision import score_technical, calc_entry_stop_target, decide_confidence, extract_indicators_summary
from kairos.scoring.engine import score_multi_timeframe, score_divergence


def recalc_technical_single(contract_id: str, date_str: str) -> dict | None:
    """从缓存数据重新计算单个品种的技术面
    
    Args:
        contract_id: 合约ID
        date_str: 日期字符串 (YYYY-MM-DD)
    
    Returns:
        技术分析结果字典或 None
    """
    config = CONTRACTS.get(contract_id)
    if not config:
        return None
    
    # 加载缓存的日线数据
    hist = load_historical_data(contract_id, date_str)
    if hist is None or hist.empty or len(hist) < 30:
        return None

    # ADX 需要至少 2*14+1=29 个数据点，取 30 条确保有效计算
    recent = hist.tail(30)
    indicators = calc_all_indicators(recent)
    if not indicators:
        return None
    
    divergence = detect_divergence(hist.tail(30), lookback=30) if len(hist) >= 30 else None
    
    result = {
        "contract": contract_id,
        "name": config["name"],
        "exchange": config["exchange"],
        "timestamp": datetime.now().isoformat(),
        "recalculated": True,
        "source_date": date_str,
        "indicators": indicators,
        "divergence": divergence,
        "latest": {
            "price": float(recent['close'].iloc[-1]),
            "high_20d": float(recent['high'].max()),
            "low_20d": float(recent['low'].min()),
        },
    }
    
    # 尝试加载多周期数据
    mtf_data = load_multi_timeframe_data(contract_id, date_str)
    if mtf_data:
        mtf_indicators = calc_multi_timeframe_indicators(mtf_data)
        if mtf_indicators:
            mtf_score = score_multi_timeframe(mtf_indicators)
            alignment = get_timeframe_alignment(mtf_indicators)
            result["mtf"] = {
                "indicators": mtf_indicators,
                "score": mtf_score,
                "alignment": alignment,
                "timeframes": list(mtf_data.keys())
            }
    
    return result


def recalc_decision_single(contract_id: str, date_str: str,
                           contract_status: str = "稳定") -> dict | None:
    """从缓存数据重新计算单个品种的交易决策"""
    tech = recalc_technical_single(contract_id, date_str)
    if not tech:
        return None

    config = CONTRACTS.get(contract_id, {})
    mtf_data = tech.get("mtf")

    # 评分：优先使用多周期，否则回退单周期（传入合约配置用于移仓敏感期检测）
    if mtf_data and mtf_data.get("score"):
        tech_score = mtf_data["score"]["score"]
        signals = mtf_data["score"].get("signals", [])[:5]
    else:
        r = score_technical(tech.get("indicators", {}), contract_config=config)
        tech_score, signals = r["score"], r["signals"]

    # 背离评分
    div_score, div_signal = score_divergence(tech.get("divergence", {}))
    if div_signal:
        tech_score += div_score
        signals.append(div_signal)

    # 计算总分和方向
    price = tech.get("latest", {}).get("price", 0)
    macro = {"macro_score": 50, "value_range": {"low": price * 0.9, "high": price * 1.1, "fair": price}}
    total_score = int(tech_score * 0.6 + 50 * 0.4)
    direction = "做多" if total_score >= 60 else "做空" if total_score <= 40 else "观望"
    levels = calc_entry_stop_target(tech, macro, direction)
    conf_score = total_score if direction == "做多" else (100 - total_score) if direction == "做空" else 0

    main = config.get("main_contract", contract_id)
    display = main if main and not main.endswith("0") else contract_id

    return {
        "contract": contract_id, "display_contract": display, "name": config.get("name", contract_id),
        "variety": config.get("variety", contract_id.replace("0", "").upper()),
        "contract_status": contract_status, "recalculated": True, "source_date": date_str,
        "timestamp": datetime.now().isoformat(), "current_price": price,
        "scores": {"technical": tech_score, "macro": 50, "total": total_score},
        "technical_indicators": extract_indicators_summary(tech), "technical_signals": signals,
        "decision": {"direction": direction, "entry_range": levels["entry_range"],
                     "target": levels["target"], "stop_loss": levels["stop_loss"],
                     "confidence": decide_confidence(conf_score)},
    }


def recalc_all_decisions(date_str: str) -> dict:
    """重新计算指定日期所有缓存品种的技术面和决策

    Args:
        date_str: 日期字符串

    Returns:
        包含 decisions, success, failed 的结果字典
    """
    load_contracts()  # 刷新合约配置
    cached_contracts = list_cached_contracts(date_str)

    if not cached_contracts:
        return {"decisions": [], "success": [], "failed": [], "error": "无缓存数据"}

    results = {"decisions": [], "success": [], "failed": []}
    total = len(cached_contracts)

    print(f"📦 从缓存重算技术面 ({total} 个品种)")
    print("-" * 50)

    for i, cid in enumerate(cached_contracts, 1):
        print(f"  [{i}/{total}] {cid}...", end=" ")

        decision = recalc_decision_single(cid, date_str)
        if decision:
            results["success"].append(cid)
            results["decisions"].append(decision)
            d = decision["decision"]
            icon = "🟢" if d["direction"] == "做多" else "🔴" if d["direction"] == "做空" else "⚪"
            print(f"✅ {icon} {d['direction']} | 评分:{decision['scores']['total']}")
        else:
            results["failed"].append(cid)
            print("❌ 计算失败")

    return results


def save_recalculated_decisions(date_str: str, decisions: list) -> Path:
    """保存重算后的决策文件

    Args:
        date_str: 日期字符串
        decisions: 决策列表

    Returns:
        输出目录路径
    """
    output_dir = Path("plans") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)

    for decision in decisions:
        cid = decision["contract"]
        file_path = output_dir / f"{cid}_decision.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(decision, f, ensure_ascii=False, indent=2)

    print(f"✅ 已保存 {len(decisions)} 个决策文件到 {output_dir}")
    return output_dir

