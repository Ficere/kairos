"""评分引擎 - 重构后的技术面评分系统"""
from kairos.scoring.config import (
    SCORING_CONFIG, get_adaptive_weights, get_market_regime,
    TIMEFRAME_WEIGHTS, MACD_CROSS_BY_TIMEFRAME, TREND_BY_TIMEFRAME,
    DIVERGENCE_CONFIG
)


def _score_trend(indicators: dict) -> tuple[int, str | None]:
    """评分：趋势"""
    trend = indicators.get("trend", "sideways")
    score = SCORING_CONFIG["trend"].get(trend, 0)
    signal = None
    if trend == "bullish":
        signal = f"均线多头排列 +{score}"
    elif trend == "bearish":
        signal = f"均线空头排列 {score}"
    return score, signal


def _score_macd(indicators: dict) -> tuple[int, str | None]:
    """评分：MACD"""
    macd = indicators.get("macd", {})
    macd_signal = macd.get("signal", "")
    score = SCORING_CONFIG["macd"].get(macd_signal, 0)
    
    signal_map = {
        "golden_cross": "MACD金叉",
        "death_cross": "MACD死叉",
        "bullish": "MACD多头",
        "bearish": "MACD空头",
    }
    signal = None
    if macd_signal in signal_map:
        signal = f"{signal_map[macd_signal]} {score:+d}"
    return score, signal


def _score_momentum(indicators: dict) -> tuple[int, str | None]:
    """评分：动量组（合并 KDJ + RSI，避免重复计分）"""
    kdj = indicators.get("kdj", {})
    rsi = indicators.get("rsi", {})
    
    kdj_zone = kdj.get("zone", "neutral")
    rsi_zone = rsi.get("zone", "neutral")
    
    # 判断是否双重信号
    both_oversold = kdj_zone == "oversold" and rsi_zone == "oversold"
    both_overbought = kdj_zone == "overbought" and rsi_zone == "overbought"
    any_oversold = kdj_zone == "oversold" or rsi_zone == "oversold"
    any_overbought = kdj_zone == "overbought" or rsi_zone == "overbought"
    
    cfg = SCORING_CONFIG["momentum"]
    if both_oversold:
        return cfg["strong_oversold"], f"KDJ+RSI双重超卖 +{cfg['strong_oversold']}"
    elif both_overbought:
        return cfg["strong_overbought"], f"KDJ+RSI双重超买 {cfg['strong_overbought']}"
    elif any_oversold:
        ind = "KDJ" if kdj_zone == "oversold" else "RSI"
        return cfg["oversold"], f"{ind}超卖 +{cfg['oversold']}"
    elif any_overbought:
        ind = "KDJ" if kdj_zone == "overbought" else "RSI"
        return cfg["overbought"], f"{ind}超买 {cfg['overbought']}"
    return 0, None


def _score_boll(indicators: dict) -> tuple[int, str | None]:
    """评分：布林带"""
    boll = indicators.get("boll", {})
    position = boll.get("position", "")
    score = SCORING_CONFIG["boll"].get(position, 0)
    
    signal_map = {
        "below_lower": "价格破布林下轨",
        "above_upper": "价格破布林上轨",
    }
    signal = None
    if position in signal_map:
        signal = f"{signal_map[position]} {score:+d}"
    return score, signal


def _score_adx(indicators: dict) -> tuple[int, str | None]:
    """评分：ADX 趋势强度"""
    adx = indicators.get("adx", {})
    strength = adx.get("strength", "weak")
    direction = adx.get("direction", "")
    
    cfg = SCORING_CONFIG["adx"]
    if strength == "strong":
        key = f"strong_{direction}"
        score = cfg.get(key, 0)
        signal = f"ADX强趋势({direction}) {score:+d}" if score else None
    elif strength == "moderate":
        key = f"moderate_{direction}"
        score = cfg.get(key, 0)
        signal = f"ADX中等趋势({direction}) {score:+d}" if score else None
    else:
        return 0, None
    return score, signal


def _score_obv(indicators: dict) -> tuple[int, str | None]:
    """评分：OBV 成交量"""
    obv = indicators.get("obv", {})
    if not obv:
        return 0, None
    
    signal_type = obv.get("signal", "")
    momentum = obv.get("momentum", 0)
    cfg = SCORING_CONFIG["obv"]
    
    # 强动量判断
    if abs(momentum) > 10:
        key = f"strong_{signal_type}"
        score = cfg.get(key, cfg.get(signal_type, 0))
    else:
        score = cfg.get(signal_type, 0)
    
    signal = f"OBV{signal_type} {score:+d}" if score else None
    return score, signal


def score_divergence(divergence: dict) -> tuple[int, str | None]:
    """评分：背离信号（分级体系）

    Args:
        divergence: 背离检测结果，包含 type, confidence, indicator 字段

    Returns:
        (分数调整值, 信号描述)
    """
    if not divergence or divergence.get("type") == "无背离":
        return 0, None

    div_type = divergence.get("type", "")
    confidence = divergence.get("confidence", "低")
    indicator = divergence.get("indicator", "")

    # 判断背离强度类型
    is_multi_indicator = "+" in indicator  # 如 "MACD+RSI"

    if is_multi_indicator:
        cfg = DIVERGENCE_CONFIG["strong"]
    else:
        cfg = DIVERGENCE_CONFIG["regular"]

    # 获取基础分数
    if div_type == "顶背离":
        base_score = cfg["bearish"]
    elif div_type == "底背离":
        base_score = cfg["bullish"]
    else:
        return 0, None

    # 应用置信度系数
    multiplier = DIVERGENCE_CONFIG["confidence_multiplier"].get(confidence, 0.5)
    final_score = int(base_score * multiplier)

    # 生成信号描述
    strength = "强" if is_multi_indicator else ""
    signal = f"{strength}{div_type}({indicator},置信{confidence}) {final_score:+d}"

    return final_score, signal


def score_technical_v2(indicators: dict) -> dict:
    """重构后的技术面评分（0-100）
    
    特点：
    1. 配置驱动，权重外置
    2. KDJ/RSI 合并为动量组，避免重复计分
    3. 新增 ADX 趋势强度和 OBV 成交量指标
    """
    score, signals = 50, []
    
    scorers = [
        _score_trend,
        _score_macd,
        _score_momentum,
        _score_boll,
        _score_adx,
        _score_obv,
    ]
    
    for scorer in scorers:
        delta, signal = scorer(indicators)
        score += delta
        if signal:
            signals.append(signal)
    
    return {"score": max(0, min(100, score)), "signals": signals}


def calc_signal_consistency(indicators: dict) -> dict:
    """计算各指标信号一致性"""
    signals = []
    
    # 趋势
    trend = indicators.get("trend", "sideways")
    if trend == "bullish":
        signals.append(1)
    elif trend == "bearish":
        signals.append(-1)
    
    # MACD
    macd_sig = indicators.get("macd", {}).get("signal", "")
    if "bullish" in macd_sig or "golden" in macd_sig:
        signals.append(1)
    elif "bearish" in macd_sig or "death" in macd_sig:
        signals.append(-1)
    
    # ADX 方向
    adx_dir = indicators.get("adx", {}).get("direction", "")
    if adx_dir == "bullish":
        signals.append(1)
    elif adx_dir == "bearish":
        signals.append(-1)
    
    # OBV
    obv_sig = indicators.get("obv", {}).get("signal", "")
    if obv_sig == "bullish":
        signals.append(1)
    elif obv_sig == "bearish":
        signals.append(-1)
    
    if not signals:
        return {"consistency": 0, "direction": "neutral", "count": 0}

    avg = sum(signals) / len(signals)
    consistency = abs(avg)
    direction = "bullish" if avg > 0.3 else "bearish" if avg < -0.3 else "neutral"

    return {"consistency": round(consistency, 2), "direction": direction, "count": len(signals)}


def score_multi_timeframe(mtf_indicators: dict[str, dict]) -> dict:
    """多周期融合评分

    Args:
        mtf_indicators: 多周期指标，key为周期("1m","5m"等)，value为指标字典

    Returns:
        包含加权评分和各周期信号的结果字典
    """
    if not mtf_indicators:
        return {"score": 50, "signals": [], "timeframe_scores": {}}

    weighted_score = 0.0
    total_weight = 0.0
    tf_scores = {}
    signals = []

    for tf, indicators in mtf_indicators.items():
        weight = TIMEFRAME_WEIGHTS.get(tf, 0.1)

        # 基础分50
        tf_score = 50.0
        tf_signals = []

        # 趋势评分（按周期加权）
        trend = indicators.get("trend", "sideways")
        trend_cfg = TREND_BY_TIMEFRAME.get(tf, {"bullish": 10, "bearish": -10})
        trend_delta = trend_cfg.get(trend, 0)
        tf_score += trend_delta
        if trend != "sideways":
            tf_signals.append(f"{tf}趋势{trend} {trend_delta:+d}")

        # MACD评分（金叉死叉按周期加权）
        macd_sig = indicators.get("macd", {}).get("signal", "")
        macd_cfg = MACD_CROSS_BY_TIMEFRAME.get(tf, SCORING_CONFIG["macd"])
        if macd_sig in ("golden_cross", "death_cross"):
            macd_delta = macd_cfg.get(macd_sig, 0)
            tf_score += macd_delta
            label = "金叉" if macd_sig == "golden_cross" else "死叉"
            tf_signals.append(f"{tf}MACD{label} {macd_delta:+d}")
        elif macd_sig in ("bullish", "bearish"):
            # 非金叉死叉使用较小权重
            macd_delta = 3 if macd_sig == "bullish" else -3
            tf_score += macd_delta

        # 动量指标（只对主要周期评分，避免过度加分）
        if tf in ("1h", "4h", "1d"):
            momentum_delta, momentum_sig = _score_momentum(indicators)
            tf_score += momentum_delta * 0.5  # 降低权重避免重复
            if momentum_sig:
                tf_signals.append(f"{tf}{momentum_sig}")

        tf_scores[tf] = {
            "score": round(tf_score, 1),
            "weight": weight,
            "signals": tf_signals
        }

        weighted_score += tf_score * weight
        total_weight += weight
        signals.extend(tf_signals)

    # 归一化
    final_score = weighted_score / total_weight if total_weight > 0 else 50
    final_score = max(0, min(100, final_score))

    # 添加多周期对齐加分
    alignment = _calc_timeframe_alignment(mtf_indicators)
    if alignment["alignment_score"] > 0.6:
        final_score += 5
        signals.append(f"多周期多头共振 +5")
    elif alignment["alignment_score"] < -0.6:
        final_score -= 5
        signals.append(f"多周期空头共振 -5")

    return {
        "score": round(final_score),
        "signals": signals,
        "timeframe_scores": tf_scores,
        "alignment": alignment
    }


def _calc_timeframe_alignment(mtf_indicators: dict[str, dict]) -> dict:
    """计算多周期信号对齐度"""
    bullish = bearish = 0
    for tf, ind in mtf_indicators.items():
        trend = ind.get("trend", "sideways")
        macd = ind.get("macd", {}).get("signal", "")
        direction = 0
        if trend == "bullish": direction += 1
        elif trend == "bearish": direction -= 1
        if "bullish" in macd or "golden" in macd: direction += 1
        elif "bearish" in macd or "death" in macd: direction -= 1

        if direction > 0: bullish += 1
        elif direction < 0: bearish += 1

    total = len(mtf_indicators)
    score = (bullish - bearish) / total if total > 0 else 0
    return {
        "bullish_count": bullish,
        "bearish_count": bearish,
        "total": total,
        "alignment_score": round(score, 2)
    }

