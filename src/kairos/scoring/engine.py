"""评分引擎 - 重构后的技术面评分系统"""
from kairos.scoring.config import SCORING_CONFIG, get_adaptive_weights, get_market_regime


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

