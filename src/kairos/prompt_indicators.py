"""技术指标说明和表格格式化"""

# 精简版指标说明（已优化权重）
INDICATOR_DOCS = """
## 📊 评分说明

**基准50分** | 趋势±12 | MACD±8(金叉/死叉)±4(方向) | 动量±6~10 | ADX±4~6 | OBV±3~6 | 背离±5~12

> MA排列(±12) | MACD金叉按周期(1m:2→1d:15) | RSI超卖<30(+6)超买>70(-6) | ADX>30强趋势

### 📉 量价关系与背离分析

**量价配合评分**：
| 类型 | 条件 | 评分调整 | 信号含义 |
|------|------|---------|---------|
| 价涨量增 | 价格上涨+成交量放大>1.5倍 | +5 | 健康上涨，趋势确认 |
| 价涨量缩 | 价格上涨+成交量萎缩<0.7倍 | -3 | 上涨乏力，警惕回调 |
| 价跌量增 | 价格下跌+成交量放大>1.5倍 | -5 | 恐慌抛售，趋势延续 |
| 价跌量缩 | 价格下跌+成交量萎缩<0.7倍 | +3 | 抛压减轻，企稳迹象 |

**背离分级**：
| 背离类型 | 识别标准 | 评分权重 | 置信度系数 |
|---------|---------|---------|-----------|
| 常规背离 | 单一指标(MACD/RSI)背离 | ±8 | 高1.0/中0.7/低0.4 |
| 强背离 | 多指标(MACD+RSI)共振背离 | ±12 | 高1.0/中0.8/低0.5 |
| 隐藏背离 | 趋势中继确认信号 | ±5 | 固定0.7 |

### 🔄 双日反包分析（关键反转形态）

| 形态 | 条件 | 评分调整 | 信号含义 |
|------|------|---------|---------|
| 量价双包 | 当日量>前日量 且 当日振幅包前日 | +10/-10 | 强反转确认信号 |
| 量包价不包 | 当日量>前日量×1.5 但价格未突破 | +5/-5 | 分歧信号，潜在反转 |
| 价包量不包 | 价格突破但成交量<前日×0.8 | +2/-2 | 情绪驱动，反转概率低 |
| 极致缩量 | 成交量<近10日均量×0.5 | ±8 | 顶底反转预警 |

### 📈 市场状态过滤（量价仓分析）

| 状态 | 条件 | 多头调整 | 空头调整 | 含义 |
|------|------|---------|---------|------|
| 真突破 | 价涨+放量+增仓 | +5 | -3 | 新资金入场，趋势强劲 |
| 空头回补 | 价涨+放量+减仓 | -8 | 0 | 空头止损虚假上涨，禁开多 |
| 多头踩踏 | 价跌+放量+减仓 | +3 | -5 | 恐慌止损，底部临近 |
| 背离衰竭 | 创新高/低+仓量不配合 | -5 | -5 | 动力枯竭，反转风险 |
| 低位吸筹 | 横盘+稳量+增仓 | +8 | -3 | 主力建仓，关注突破 |

---
"""


def _get_boll_position_desc(boll: dict) -> str:
    """获取布林带位置描述"""
    pos = boll.get("position", "")
    pos_map = {
        "above_upper": "突破上轨",
        "upper_half": "上轨区间",
        "middle": "中轨附近",
        "lower_half": "下轨区间",
        "below_lower": "跌破下轨",
    }
    return pos_map.get(pos, "中轨附近")


def format_variety_compact(d: dict) -> str:
    """格式化单个品种的详细技术信息（多行）"""
    contract = d.get("display_contract", d.get("contract", ""))
    name = d.get("name", "")
    price = d.get("current_price", "N/A")
    scores = d.get("scores", {})
    ti = d.get("technical_indicators", {})
    signals = d.get("technical_signals", [])

    # 基础信息行（基准50分±加减分，区间0-100）
    total = scores.get('total', '-')
    if isinstance(total, (int, float)):
        score_desc = f"{total}分(基准50±)" if 30 <= total <= 70 else f"{total}分"
    else:
        score_desc = str(total)
    lines = [f"- **{name}**({contract}) 价格:{price} 评分:{score_desc}"]

    # 技术信号行 - 从 technical_signals 提取加减分信号
    tech_parts = []
    for sig in signals:
        if any(x in sig for x in ["+", "-"]) and not sig.startswith("✓") and not sig.startswith("📈"):
            tech_parts.append(sig)
    if tech_parts:
        lines.append(f"  📊 技术信号: {' | '.join(tech_parts)}")

    # 量价确认行
    vol_parts = [s for s in signals if s.startswith("✓") or "量价" in s]
    adx_parts = [s for s in signals if "ADX" in s]
    if vol_parts or adx_parts:
        vol_str = vol_parts[0] if vol_parts else ""
        adx_str = adx_parts[0].replace("📈 ", "") if adx_parts else ""
        confirm_line = "  " + " | ".join(filter(None, [vol_str, adx_str]))
        lines.append(confirm_line)

    # 布林带行
    boll = ti.get("boll", {})
    if boll:
        upper = boll.get('upper', 0)
        lower = boll.get('lower', 0)
        pos_desc = _get_boll_position_desc(boll)
        lines.append(f"  📈 布林带: [{lower:.0f}-{upper:.0f}] 当前位于{pos_desc}")

    # 信号一致性行
    cons = ti.get("signal_consistency", {})
    if cons:
        cons_val = cons.get("consistency", 0)
        count = cons.get("count", 0)
        direction = cons.get("direction", "neutral")
        dir_icon = "🟢" if direction == "bullish" else "🔴" if direction == "bearish" else "⚪"
        lines.append(f"  🎯 信号一致性: {cons_val:.0%} ({count}个指标同向) {dir_icon}")

    return "\n".join(lines)

