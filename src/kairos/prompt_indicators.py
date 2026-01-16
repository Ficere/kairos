"""技术指标说明和表格格式化"""


def _water_position(val: float) -> str:
    """判断MACD指标的水上/水下位置"""
    return "水上" if val >= 0 else "水下"


def format_indicator_detail(d: dict) -> str:
    """格式化技术指标详情（完整版，用于详细分析）"""
    ti = d.get("technical_indicators", {})
    lines = []

    # MACD 详细信息
    macd = ti.get("macd", {})
    if macd:
        dif = macd.get("dif", 0)
        dea = macd.get("dea", 0)
        macd_bar = (dif - dea) * 2
        direction = "多头(DIF>DEA)" if dif > dea else "空头(DIF<DEA)"
        lines.append(f"  MACD: {direction} DIF:{dif:.2f}({_water_position(dif)}) "
                     f"DEA:{dea:.2f}({_water_position(dea)}) 柱状线:{macd_bar:.2f}({_water_position(macd_bar)})")

    # RSI 详细信息
    rsi = ti.get("rsi", {})
    if rsi:
        val = rsi.get("value", rsi.get("rsi", 50))
        if val > 80:
            zone = "极度超买(>80)"
        elif val > 70:
            zone = "超买区间(70-80)"
        elif val < 20:
            zone = "极度超卖(<20)"
        elif val < 30:
            zone = "超卖区间(20-30)"
        elif val > 50:
            zone = "偏多区间(50-70)"
        else:
            zone = "偏空区间(30-50)"
        lines.append(f"  RSI: {val:.1f} {zone}")

    # KDJ 详细信息
    kdj = ti.get("kdj", {})
    if kdj:
        k, d_val, j = kdj.get("k", 50), kdj.get("d", 50), kdj.get("j", 50)
        signal = kdj.get("signal", "")
        signal_text = "金叉" if signal == "golden_cross" else "死叉" if signal == "death_cross" else "多头" if k > d_val else "空头"
        zone = kdj.get("zone", "neutral")
        zone_text = "超买" if zone == "overbought" else "超卖" if zone == "oversold" else "中性"
        lines.append(f"  KDJ: K:{k:.1f} D:{d_val:.1f} J:{j:.1f} {signal_text} ({zone_text})")

    # 布林带详细信息
    boll = ti.get("boll", {})
    if boll:
        upper, mid, lower = boll.get("upper", 0), boll.get("mid", 0), boll.get("lower", 0)
        pos = boll.get("position", "middle")
        pos_map = {"above_upper": "突破上轨(超买)", "upper_half": "上轨与中轨之间",
                   "lower_half": "中轨与下轨之间", "below_lower": "跌破下轨(超卖)"}
        bandwidth = boll.get("bandwidth", 0)
        lines.append(f"  布林带: 上轨:{upper:.0f} 中轨:{mid:.0f} 下轨:{lower:.0f} "
                     f"位置:{pos_map.get(pos, '中轨附近')} 带宽:{bandwidth:.1f}%")

    # ADX 详细信息
    adx = ti.get("adx", {})
    if adx:
        adx_val = adx.get("adx", 0)
        plus_di = adx.get("plus_di", 0)
        minus_di = adx.get("minus_di", 0)
        trend = "强趋势" if adx_val > 30 else "中等趋势" if adx_val > 20 else "弱趋势/震荡"
        di_direction = "+DI>-DI(多头)" if plus_di > minus_di else "-DI>+DI(空头)"
        lines.append(f"  ADX: {adx_val:.1f}({trend}) +DI:{plus_di:.1f} -DI:{minus_di:.1f} {di_direction}")

    # 背离详细信息
    div = ti.get("divergence", {})
    if div and div.get("type") != "无背离":
        div_type = div.get("type", "")
        indicator = div.get("indicator", "")
        conf = div.get("confidence", "中")
        desc = div.get("description", "")
        lines.append(f"  背离: {div_type}({indicator}) 置信度:{conf} - {desc}")

    # OBV 详细信息
    obv = ti.get("obv", {})
    if obv:
        signal = obv.get("signal", "")
        momentum = obv.get("momentum", 0)
        signal_text = "多头" if signal == "bullish" else "空头" if signal == "bearish" else "中性"
        if momentum != 0:
            lines.append(f"  OBV: {signal_text} 动量:{momentum:+.1f}%")
        else:
            lines.append(f"  OBV: {signal_text}")

    return "\n".join(lines) if lines else "  无详细指标数据"


def format_variety_compact(d: dict) -> str:
    """格式化单个品种的详细技术信息（多行，增强版）"""
    contract = d.get("display_contract", d.get("contract", ""))
    name = d.get("name", "")
    price = d.get("current_price", "N/A")
    scores = d.get("scores", {})
    ti = d.get("technical_indicators", {})
    signals = d.get("technical_signals", [])

    # 基础信息行
    total = scores.get('total', '-')
    tech_score = scores.get('technical', '-')
    lines = [f"### {name}({contract}) 价格:{price} 综合评分:{total} 技术评分:{tech_score}"]

    # 详细技术指标
    lines.append(format_indicator_detail(d))

    # 信号一致性行
    cons = ti.get("signal_consistency", {})
    if cons:
        cons_val = cons.get("consistency", 0)
        count = cons.get("count", 0)
        direction = cons.get("direction", "neutral")
        dir_icon = "🟢多" if direction == "bullish" else "🔴空" if direction == "bearish" else "⚪中性"
        lines.append(f"  信号一致性: {cons_val:.0%} ({count}个指标同向) {dir_icon}")

    # 技术信号摘要
    if signals:
        sig_text = " | ".join(signals[:5])
        lines.append(f"  信号摘要: {sig_text}")

    return "\n".join(lines)

