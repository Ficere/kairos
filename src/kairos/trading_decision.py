"""量化交易决策脚本 - 综合技术面和宏观面生成交易建议"""
import json
import os
from datetime import datetime
from kairos.futures.config import CONTRACTS
from kairos.futures.display import get_daily_output_dir
from kairos.scoring.engine import score_technical_v2, calc_signal_consistency, score_divergence
from kairos.scoring.config import get_market_regime
from kairos.scoring.adaptive import score_with_adaptive_weights


def load_json(path: str) -> dict | None:
    """加载 JSON 文件"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def score_technical(indicators: dict) -> dict:
    """技术面评分（0-100）- 使用自适应权重评分引擎"""
    return score_with_adaptive_weights(indicators)


def calc_entry_stop_target(tech: dict, macro: dict, direction: str) -> dict:
    """计算入场、止损、目标价"""
    price = tech.get("latest", {}).get("price", 0)
    boll = tech.get("indicators", {}).get("boll", {})
    atr = tech.get("indicators", {}).get("atr", price * 0.02)
    vr = macro.get("value_range", {}) if macro else {}

    if direction == "做多":
        el, eh = max(boll.get("lower", price*0.98), vr.get("low", price*0.95)), boll.get("mid", price)
        return {"entry_range": f"{el:.2f} - {eh:.2f}", "stop_loss": round(el - atr*1.5, 2),
                "target": round(min(boll.get("upper", price*1.05), vr.get("high", price*1.1)), 2)}
    elif direction == "做空":
        el, eh = boll.get("mid", price), min(boll.get("upper", price*1.02), vr.get("high", price*1.05))
        return {"entry_range": f"{el:.2f} - {eh:.2f}", "stop_loss": round(eh + atr*1.5, 2),
                "target": round(max(boll.get("lower", price*0.95), vr.get("low", price*0.9)), 2)}
    return {"entry_range": "-", "stop_loss": "-", "target": "-"}


def decide_confidence(score: int) -> str:
    """根据综合评分计算确定性等级"""
    if score >= 80: return "高确定性(30-50%)"
    if score >= 60: return "中确定性(20-30%)"
    if score >= 50: return "低确定性(10-20%)"
    return "观望(0%)"


def extract_indicators(tech: dict) -> dict:
    """提取详细技术指标数值"""
    ind = tech.get("indicators", {})
    macd = ind.get("macd", {})
    kdj = ind.get("kdj", {})
    rsi = ind.get("rsi", {})
    boll = ind.get("boll", {})
    ma = ind.get("ma", {})
    adx = ind.get("adx", {})
    obv = ind.get("obv", {})
    price = tech.get("latest", {}).get("price", 0)

    result = {
        "macd": {"dif": macd.get("dif", 0), "dea": macd.get("dea", 0), "macd": macd.get("macd", 0)},
        "kdj": {"k": kdj.get("k", 0), "d": kdj.get("d", 0), "j": kdj.get("j", 0)},
        "rsi": {"value": rsi.get("rsi", 0)},
        "boll": {"upper": boll.get("upper", 0), "mid": boll.get("mid", 0), "lower": boll.get("lower", 0),
                 "current_price": price, "position": boll.get("position", "")},
        "ma": {"ma5": ma.get("ma5", 0), "ma10": ma.get("ma10", 0), "ma20": ma.get("ma20", 0)},
        "adx": {"adx": adx.get("adx", 0), "plus_di": adx.get("plus_di", 0),
                "minus_di": adx.get("minus_di", 0), "strength": adx.get("strength", "weak")},
        "divergence": tech.get("divergence", {"type": "无背离", "confidence": "低", "indicator": "", "description": ""}),
    }

    # 添加 OBV（如果存在）
    if obv:
        result["obv"] = {"obv": obv.get("obv", 0), "signal": obv.get("signal", "")}

    # 添加信号一致性分析
    consistency = calc_signal_consistency(ind)
    result["signal_consistency"] = consistency

    # 添加市场状态
    result["market_regime"] = get_market_regime(ind)

    return result


def make_decision(contract_id: str) -> dict:
    """生成交易决策 - 使用自适应评分和增强置信度"""
    output_dir = get_daily_output_dir()
    config = CONTRACTS.get(contract_id, {})
    tech = load_json(os.path.join(output_dir, f"{contract_id}_technical.json"))
    macro = load_json(os.path.join(output_dir, f"{contract_id}_macro.json"))
    if not tech:
        return {"error": f"未找到技术分析数据，请先运行分析"}

    # 使用自适应评分（包含置信度和量价确认）
    tech_result = score_technical(tech.get("indicators", {}))
    tech_score = tech_result["score"]
    signals = tech_result["signals"]
    confidence = tech_result.get("confidence", {})

    macro_score = macro.get("macro_score", 50) if macro else 50
    total_score = int(tech_score * 0.6 + macro_score * 0.4)

    direction = "做多" if total_score >= 60 else "做空" if total_score <= 40 else "观望"
    levels = calc_entry_stop_target(tech, macro, direction)

    # 使用分级背离评分
    divergence = tech.get("divergence", {})
    div_score, div_signal = score_divergence(divergence)
    if div_signal:
        tech_score += div_score
        signals.append(div_signal)

    # 使用增强置信度
    conf_level = confidence.get("level", "观望") + f"({confidence.get('position_pct', '0%')})"

    main = config.get("main_contract", contract_id)
    display = main if main and not main.endswith("0") else contract_id

    return {
        "contract": contract_id, "display_contract": display, "name": config.get("name", contract_id),
        "timestamp": datetime.now().isoformat(), "current_price": tech.get("latest", {}).get("price", 0),
        "scores": {"technical": tech_score, "macro": macro_score, "total": total_score},
        "technical_indicators": extract_indicators(tech), "technical_signals": signals,
        "decision": {"direction": direction, "entry_range": levels["entry_range"],
                     "target": levels["target"], "stop_loss": levels["stop_loss"], "confidence": conf_level},
        "confidence_details": confidence,  # 新增：详细置信度信息
        "market_regime": tech_result.get("market_regime", "neutral"),  # 新增：市场状态
        "macro_factors": macro.get("key_factors", []) if macro else [],
        "risk_warning": macro.get("risk_warning", "") if macro else "",
    }


def print_decision(d: dict):
    """打印决策结果"""
    dec, scores = d["decision"], d["scores"]
    display = d.get("display_contract", d["contract"])
    icon = "🟢" if dec["direction"] == "做多" else "🔴" if dec["direction"] == "做空" else "⚪"
    print(f"\n{'='*60}\n📊 {display} ({d['name']}) | 价格:{d['current_price']}")
    print(f"📈 评分: 技术{scores['technical']} + 宏观{scores['macro']} = 综合{scores['total']}")
    print(f"🎯 {icon} {dec['direction']} | 开仓:{dec['entry_range']} | 目标:{dec['target']} | 止损:{dec['stop_loss']}")

