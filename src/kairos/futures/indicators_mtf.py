"""多周期技术指标计算模块"""
import pandas as pd
from kairos.futures.indicators import calc_macd, calc_kdj, calc_rsi, calc_boll
from kairos.futures.indicators_advanced import calc_adx, calc_obv


def calc_indicators_for_timeframe(df: pd.DataFrame) -> dict:
    """计算单个周期的技术指标（简化版，用于多周期融合）"""
    if df.empty or len(df) < 20:
        return {}

    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float) if 'volume' in df.columns else None

    # 计算均线趋势
    ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else close.mean()
    ma10 = close.rolling(10).mean().iloc[-1] if len(close) >= 10 else close.mean()
    ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else close.mean()

    trend = "bullish" if ma5 > ma10 > ma20 else "bearish" if ma5 < ma10 < ma20 else "sideways"

    result = {
        "trend": trend,
        "macd": calc_macd(close),
        "kdj": calc_kdj(high, low, close),
        "rsi": calc_rsi(close),
    }

    # 布林带需要20根K线
    if len(close) >= 20:
        result["boll"] = calc_boll(close)

    # ADX需要14根K线
    if len(close) >= 14:
        result["adx"] = calc_adx(high, low, close)

    # OBV需要成交量
    if volume is not None and volume.sum() > 0:
        result["obv"] = calc_obv(close, volume)

    return result


def calc_multi_timeframe_indicators(mtf_data: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """计算多周期指标
    
    Args:
        mtf_data: 多周期K线数据，key为周期，value为DataFrame
        
    Returns:
        多周期指标字典，key为周期，value为该周期的指标
    """
    result = {}
    for timeframe, df in mtf_data.items():
        indicators = calc_indicators_for_timeframe(df)
        if indicators:
            result[timeframe] = indicators
    return result


def get_timeframe_alignment(mtf_indicators: dict[str, dict]) -> dict:
    """分析多周期信号对齐情况
    
    Returns:
        对齐分析结果：
        - aligned_bullish: 多头对齐的周期数
        - aligned_bearish: 空头对齐的周期数
        - total: 总周期数
        - alignment_score: 对齐得分 (-1 到 1)
        - details: 各周期详情
    """
    details = {}
    bullish_count = 0
    bearish_count = 0
    total = 0

    for tf, indicators in mtf_indicators.items():
        trend = indicators.get("trend", "sideways")
        macd_sig = indicators.get("macd", {}).get("signal", "")
        
        # 计算该周期的方向
        direction = 0
        if trend == "bullish":
            direction += 1
        elif trend == "bearish":
            direction -= 1
            
        if "bullish" in macd_sig or "golden" in macd_sig:
            direction += 1
        elif "bearish" in macd_sig or "death" in macd_sig:
            direction -= 1

        details[tf] = {
            "trend": trend,
            "macd_signal": macd_sig,
            "direction": "bullish" if direction > 0 else "bearish" if direction < 0 else "neutral"
        }

        if direction > 0:
            bullish_count += 1
        elif direction < 0:
            bearish_count += 1
        total += 1

    alignment_score = (bullish_count - bearish_count) / total if total > 0 else 0

    return {
        "aligned_bullish": bullish_count,
        "aligned_bearish": bearish_count,
        "total": total,
        "alignment_score": round(alignment_score, 2),
        "details": details
    }

