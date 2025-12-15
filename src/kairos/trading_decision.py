"""量化交易决策脚本 - 综合技术面和宏观面生成交易建议"""
import json
import os
from datetime import datetime
from kairos.futures.config import CONTRACTS
from kairos.futures.display import get_daily_output_dir


def load_json(path: str) -> dict | None:
    """加载 JSON 文件"""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def score_technical(indicators: dict) -> dict:
    """技术面评分（0-100）"""
    score, signals = 50, []  # 基准分

    trend = indicators.get("trend", "sideways")
    if trend == "bullish":
        score += 15
        signals.append("均线多头排列 +15")
    elif trend == "bearish":
        score -= 15
        signals.append("均线空头排列 -15")

    macd = indicators.get("macd", {})
    macd_signal = macd.get("signal", "")
    if macd_signal == "golden_cross":
        score += 10
        signals.append("MACD金叉 +10")
    elif macd_signal == "death_cross":
        score -= 10
        signals.append("MACD死叉 -10")
    elif macd_signal == "bullish":
        score += 5
        signals.append("MACD多头 +5")
    elif macd_signal == "bearish":
        score -= 5
        signals.append("MACD空头 -5")

    kdj = indicators.get("kdj", {})
    kdj_zone = kdj.get("zone", "")
    if kdj_zone == "oversold":
        score += 10
        signals.append("KDJ超卖 +10")
    elif kdj_zone == "overbought":
        score -= 10
        signals.append("KDJ超买 -10")

    rsi = indicators.get("rsi", {})
    rsi_zone = rsi.get("zone", "")
    if rsi_zone == "oversold":
        score += 10
        signals.append("RSI超卖 +10")
    elif rsi_zone == "overbought":
        score -= 10
        signals.append("RSI超买 -10")

    boll = indicators.get("boll", {})
    boll_pos = boll.get("position", "")
    if boll_pos == "below_lower":
        score += 5
        signals.append("价格破布林下轨 +5")
    elif boll_pos == "above_upper":
        score -= 5
        signals.append("价格破布林上轨 -5")

    return {"score": max(0, min(100, score)), "signals": signals}


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
    macd, kdj, rsi, boll, ma = ind.get("macd", {}), ind.get("kdj", {}), ind.get("rsi", {}), ind.get("boll", {}), ind.get("ma", {})
    price = tech.get("latest", {}).get("price", 0)
    return {
        "macd": {"dif": macd.get("dif", 0), "dea": macd.get("dea", 0), "macd": macd.get("macd", 0)},
        "kdj": {"k": kdj.get("k", 0), "d": kdj.get("d", 0), "j": kdj.get("j", 0)},
        "rsi": {"value": rsi.get("rsi", 0)},
        "boll": {"upper": boll.get("upper", 0), "mid": boll.get("mid", 0), "lower": boll.get("lower", 0),
                 "current_price": price, "position": boll.get("position", "")},
        "ma": {"ma5": ma.get("ma5", 0), "ma10": ma.get("ma10", 0), "ma20": ma.get("ma20", 0)},
        "divergence": tech.get("divergence", {"type": "无背离", "confidence": "低", "indicator": "", "description": ""}),
    }


def make_decision(contract_id: str) -> dict:
    """生成交易决策"""
    output_dir = get_daily_output_dir()
    config = CONTRACTS.get(contract_id, {})
    tech = load_json(os.path.join(output_dir, f"{contract_id}_technical.json"))
    macro = load_json(os.path.join(output_dir, f"{contract_id}_macro.json"))
    if not tech:
        return {"error": f"未找到技术分析数据，请先运行分析"}

    tech_result = score_technical(tech.get("indicators", {}))
    tech_score, signals = tech_result["score"], tech_result["signals"]
    macro_score = macro.get("macro_score", 50) if macro else 50
    total_score = int(tech_score * 0.6 + macro_score * 0.4)

    direction = "做多" if total_score >= 60 else "做空" if total_score <= 40 else "观望"
    levels = calc_entry_stop_target(tech, macro, direction)

    divergence = tech.get("divergence", {})
    if divergence and divergence.get("type") != "无背离":
        div_type, div_ind = divergence.get("type", ""), divergence.get("indicator", "")
        adj = -10 if div_type == "顶背离" else 10 if div_type == "底背离" else 0
        signals.append(f"检测到{div_type}({div_ind}) {adj:+d}")

    conf_score = total_score if direction == "做多" else (100 - total_score) if direction == "做空" else 0
    main = config.get("main_contract", contract_id)
    display = main if main and not main.endswith("0") else contract_id

    return {
        "contract": contract_id, "display_contract": display, "name": config.get("name", contract_id),
        "timestamp": datetime.now().isoformat(), "current_price": tech.get("latest", {}).get("price", 0),
        "scores": {"technical": tech_score, "macro": macro_score, "total": total_score},
        "technical_indicators": extract_indicators(tech), "technical_signals": signals,
        "decision": {"direction": direction, "entry_range": levels["entry_range"],
                     "target": levels["target"], "stop_loss": levels["stop_loss"], "confidence": decide_confidence(conf_score)},
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

