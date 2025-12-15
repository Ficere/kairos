"""自动化交易决策流程 - 支持移仓换月双合约分析"""
import json
import os
from datetime import datetime
from kairos.futures.config import CONTRACTS, load_contracts
from kairos.futures.display import get_daily_output_dir
from kairos.futures.data_fetcher import get_historical_data
from kairos.futures.indicators import calc_all_indicators
from kairos.futures.divergence import detect_divergence
from kairos.trading_decision import score_technical, calc_entry_stop_target, decide_confidence, extract_indicators
from kairos.contracts import update_contracts as update_contracts_impl, is_in_switch_period, get_switch_varieties, load_config


def run_step(step: int, total: int, name: str):
    """打印步骤信息"""
    print(f"\n[{step}/{total}] {name}")
    print("-" * 50)


def analyze_technical_single(contract_id: str) -> dict | None:
    """分析单个品种的技术面"""
    config = CONTRACTS.get(contract_id)
    if not config:
        return None

    hist = get_historical_data(contract_id, days=60)
    if hist.empty or len(hist) < 20:
        return None

    recent = hist.tail(20)
    indicators = calc_all_indicators(recent)
    if not indicators:
        return None

    divergence = detect_divergence(hist.tail(30), lookback=30) if len(hist) >= 30 else None

    return {
        "contract": contract_id,
        "name": config["name"],
        "exchange": config["exchange"],
        "timestamp": datetime.now().isoformat(),
        "indicators": indicators,
        "divergence": divergence,
        "latest": {
            "price": float(recent['close'].iloc[-1]),
            "high_20d": float(recent['high'].max()),
            "low_20d": float(recent['low'].min()),
        },
    }


def analyze_macro_single(contract_id: str, tech: dict) -> dict:
    """分析单个品种的宏观面（无LLM时返回占位数据）"""
    price = tech["latest"]["price"] if tech else 0
    return {"contract": contract_id, "name": CONTRACTS.get(contract_id, {}).get("name", contract_id),
            "timestamp": datetime.now().isoformat(), "macro_score": 50,
            "value_range": {"low": price * 0.9, "high": price * 1.1, "fair": price}}


def get_display_contract(contract_id: str, config: dict) -> str:
    """获取用于显示的合约代码"""
    main = config.get("main_contract", contract_id)
    return main if main and not main.endswith("0") else contract_id


def make_decision_single(contract_id: str, tech: dict, macro: dict, contract_status: str = "稳定") -> dict:
    """生成单个品种的交易决策"""
    config = CONTRACTS.get(contract_id, {})
    tech_result = score_technical(tech.get("indicators", {}))
    tech_score, signals = tech_result["score"], tech_result["signals"]
    macro_score = macro.get("macro_score", 50)
    total_score = int(tech_score * 0.6 + macro_score * 0.4)
    direction = "做多" if total_score >= 60 else "做空" if total_score <= 40 else "观望"
    levels = calc_entry_stop_target(tech, macro, direction)

    divergence = tech.get("divergence", {})
    if divergence and divergence.get("type") != "无背离":
        adj = -10 if divergence.get("type") == "顶背离" else 10 if divergence.get("type") == "底背离" else 0
        signals.append(f"检测到{divergence.get('type')}({divergence.get('indicator', '')}) {adj:+d}")

    conf_score = total_score if direction == "做多" else (100 - total_score) if direction == "做空" else 0
    display = get_display_contract(contract_id, config)

    return {
        "contract": contract_id, "display_contract": display, "name": config.get("name", contract_id),
        "contract_status": contract_status,  # 新增：合约状态
        "timestamp": datetime.now().isoformat(), "current_price": tech.get("latest", {}).get("price", 0),
        "scores": {"technical": tech_score, "macro": macro_score, "total": total_score},
        "technical_indicators": extract_indicators(tech), "technical_signals": signals,
        "decision": {"direction": direction, "entry_range": levels["entry_range"], "target": levels["target"],
                     "stop_loss": levels["stop_loss"], "confidence": decide_confidence(conf_score)},
    }


def save_json(path: str, data: dict):
    """保存 JSON 文件"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def analyze_single_contract(cid: str, output_dir: str, status: str = "稳定", suffix: str = "") -> dict | None:
    """分析单个合约，返回决策或 None"""
    tech = analyze_technical_single(cid)
    if not tech:
        return None
    macro = analyze_macro_single(cid, tech)
    decision = make_decision_single(cid, tech, macro, status)
    file_suffix = f"_{suffix}" if suffix else ""
    save_json(os.path.join(output_dir, f"{cid}_technical{file_suffix}.json"), tech)
    save_json(os.path.join(output_dir, f"{cid}_decision{file_suffix}.json"), decision)
    return decision


def run_full_analysis(contract_ids: list[str]) -> dict:
    """运行完整分析流程，支持移仓期双合约分析"""
    output_dir = get_daily_output_dir()
    results = {"success": [], "failed": [], "decisions": [], "switches": []}
    total = len(contract_ids)

    run_step(1, 4, "更新主力合约配置")
    update_contracts_impl(contract_ids)
    load_contracts()
    config = load_config()

    # 获取移仓中的品种
    switch_map = {s["variety"]: s for s in get_switch_varieties(config)}
    results["switches"] = list(switch_map.values())

    run_step(2, 4, f"技术面分析 ({total} 个品种)")
    run_step(3, 4, f"宏观面分析 (使用默认评分)")
    run_step(4, 4, f"生成交易决策")

    for i, cid in enumerate(contract_ids, 1):
        variety = cid.replace("0", "").upper()
        print(f"  [{i}/{total}] {cid}...", end=" ")

        # 判断合约状态
        in_switch = variety in switch_map
        status = "主力" if in_switch else "稳定"
        decision = analyze_single_contract(cid, output_dir, status)

        if not decision:
            print("❌ 数据不足")
            results["failed"].append(cid)
            continue

        results["success"].append(cid)
        results["decisions"].append(decision)
        d = decision["decision"]
        icon = "🟢" if d["direction"] == "做多" else "🔴" if d["direction"] == "做空" else "⚪"
        status_icon = "🔥" if in_switch else ""
        print(f"✅ {status_icon}{icon} {d['direction']} | 评分:{decision['scores']['total']}")

        # 移仓期间同时分析旧合约
        if in_switch:
            prev = switch_map[variety]["previous_contract"]
            print(f"      ↳ 分析移仓合约 {prev}...", end=" ")
            prev_decision = analyze_single_contract(cid, output_dir, "移仓中", "previous")
            if prev_decision:
                prev_decision["display_contract"] = prev
                results["decisions"].append(prev_decision)
                print(f"✅ 📦")
            else:
                print("❌")

    return results


def print_summary(results: dict, output_dir: str):
    """打印汇总报告"""
    decisions = results["decisions"]
    switches = results.get("switches", [])
    longs = [d for d in decisions if d["decision"]["direction"] == "做多"]
    shorts = [d for d in decisions if d["decision"]["direction"] == "做空"]
    print(f"\n{'='*60}\n📊 分析结果汇总\n{'='*60}")
    print(f"✅ 成功: {len(results['success'])}/{len(results['success'])+len(results['failed'])}")
    if results["failed"]:
        print(f"❌ 失败: {', '.join(results['failed'][:10])}")
    if switches:
        print(f"\n⚠️ 移仓提示 ({len(switches)}个):")
        for s in switches:
            print(f"   {s['name']}: {s['previous_contract']} → {s['main_contract']}")
    for label, data, key in [("🟢 做多", longs, -1), ("🔴 做空", shorts, 1)]:
        if data:
            print(f"\n{label} ({len(data)}个):")
            for d in sorted(data, key=lambda x: key * x["scores"]["total"])[:10]:
                status = d.get("contract_status", "")
                icon = "🔥" if status == "主力" else "📦" if status == "移仓中" else ""
                print(f"   {icon}{d.get('display_contract', d['contract']):8} 评分:{d['scores']['total']:3}")
    date_str = datetime.now().strftime("%Y-%m-%d")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    os.makedirs("plans", exist_ok=True)
    save_json(os.path.join("plans", f"summary_{date_str}.json"), {"timestamp": datetime.now().isoformat(),
        "generated_at": generated_at, "success": len(results["success"]), "failed": results["failed"],
        "switches": switches, "long_signals": [d["contract"] for d in longs],
        "short_signals": [d["contract"] for d in shorts]})

    # 生成 Deep Research 提示词
    from kairos.prompt_generator import generate_deep_research_prompt
    generate_deep_research_prompt(results, output_dir)

