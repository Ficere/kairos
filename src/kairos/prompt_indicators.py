"""技术指标说明和表格格式化"""

# 精简版指标说明
INDICATOR_DOCS = """
## 📊 评分说明

**基准50分** | 趋势±15 | MACD金叉/死叉±10,多头/空头±5 | 动量组(KDJ+RSI)±8~12 | ADX±4~8 | OBV±5~8 | 背离±10

> MA多头排列(+15) | MACD金叉(+10) | RSI<30超卖(+8),>70超买(-8) | ADX>30强趋势 | OBV确认量价

---
"""


def format_compact_row(d: dict) -> str:
    """生成紧凑的单行指标摘要"""
    ti = d.get("technical_indicators", {})
    macd = ti.get("macd", {})
    kdj = ti.get("kdj", {})
    rsi = ti.get("rsi", {}).get("value", 50)
    boll = ti.get("boll", {})
    adx = ti.get("adx", {})
    obv = ti.get("obv", {})
    div = ti.get("divergence", {}).get("type", "")
    cons = ti.get("signal_consistency", {})

    # 构建紧凑字符串
    parts = []
    # MACD 状态
    macd_sig = "MACD↑" if macd.get('dif', 0) > macd.get('dea', 0) else "MACD↓"
    parts.append(macd_sig)
    # RSI
    if rsi > 70:
        parts.append(f"RSI超买({rsi:.0f})")
    elif rsi < 30:
        parts.append(f"RSI超卖({rsi:.0f})")
    else:
        parts.append(f"RSI:{rsi:.0f}")
    # KDJ
    k = kdj.get('k', 50)
    if k > 80:
        parts.append("K超买")
    elif k < 20:
        parts.append("K超卖")
    # ADX
    adx_val = adx.get("adx", 0)
    if adx_val > 30:
        parts.append(f"ADX强({adx_val:.0f})")
    # OBV
    obv_sig = obv.get("signal", "")
    if obv_sig and obv_sig != "N/A":
        parts.append(f"OBV{obv_sig[:2]}")
    # 背离
    if div and div != "无背离":
        parts.append(div)
    # 一致性
    cons_val = cons.get("consistency", 0)
    if cons_val >= 0.8:
        parts.append(f"一致{cons_val:.0%}")

    return " | ".join(parts)


def format_variety_compact(d: dict) -> str:
    """格式化单个品种的紧凑信息"""
    contract = d.get("display_contract", d.get("contract", ""))
    name = d.get("name", "")
    price = d.get("current_price", "N/A")
    scores = d.get("scores", {})
    boll = d.get("technical_indicators", {}).get("boll", {})

    # 布林带关键位
    upper = boll.get('upper', 0)
    lower = boll.get('lower', 0)

    return f"- **{name}**({contract}) 价格:{price} 评分:{scores.get('total','-')} 布林[{lower:.0f}-{upper:.0f}] | {format_compact_row(d)}"

