"""技术指标计算模块"""
import pandas as pd
import numpy as np
from kairos.futures.indicators_advanced import calc_obv, calc_adx


def _ema_with_sma_init(series: pd.Series, period: int) -> pd.Series:
    """使用 SMA 初始化的 EMA（与同花顺/通达信一致）

    算法：前 period 个数据用 SMA，之后用 EMA 递推
    EMA_t = EMA_{t-1} * (1 - α) + Close_t * α, 其中 α = 2 / (period + 1)
    """
    # 边界检查：数据不足时返回全 NaN
    if len(series) < period:
        return pd.Series([float('nan')] * len(series), index=series.index)

    alpha = 2 / (period + 1)
    result = pd.Series(index=series.index, dtype=float)
    # 第一个有效 EMA 值 = 前 period 个数据的 SMA
    sma_init = series.iloc[:period].mean()
    result.iloc[period - 1] = sma_init
    # 递推计算后续 EMA
    for i in range(period, len(series)):
        result.iloc[i] = result.iloc[i - 1] * (1 - alpha) + series.iloc[i] * alpha
    return result


def calc_macd_series(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """计算 MACD 序列（使用 SMA 初始化的 EMA，与同花顺/通达信一致）"""
    # 数据不足时返回空结果
    min_required = slow + signal
    if len(close) < min_required:
        empty = pd.Series([float('nan')] * len(close), index=close.index)
        return {"dif": empty, "dea": empty, "macd": empty}

    ema_fast = _ema_with_sma_init(close, fast)
    ema_slow = _ema_with_sma_init(close, slow)
    dif = ema_fast - ema_slow

    # DEA 计算：从 DIF 有效值开始
    dif_valid = dif.dropna()
    if len(dif_valid) < signal:
        dea_full = pd.Series([float('nan')] * len(close), index=close.index)
    else:
        dea_values = _ema_with_sma_init(dif_valid.reset_index(drop=True), signal)
        dea_full = pd.Series(index=close.index, dtype=float)
        start_idx = dif_valid.index[0]
        dea_full.loc[dif_valid.index] = dea_values.values

    macd = (dif - dea_full) * 2  # 国内习惯：MACD柱 = (DIF - DEA) * 2
    return {"dif": dif, "dea": dea_full, "macd": macd}


def calc_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    """计算 RSI 序列（使用 Wilder 平滑法，与通达信一致）"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    # 使用 Wilder 平滑（alpha = 1/period）
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_basic_indicators(df: pd.DataFrame) -> dict:
    """计算基础技术指标（供 scan_all_main 使用）"""
    if df.empty or len(df) < 5:
        return {}
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)

    ma5 = close.rolling(5).mean().iloc[-1] if len(close) >= 5 else close.mean()
    ma10 = close.rolling(10).mean().iloc[-1] if len(close) >= 10 else close.mean()

    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().iloc[-1] if len(tr) >= 14 else tr.mean()

    recent_high, recent_low = high.tail(10).max(), low.tail(10).min()
    pivot = (recent_high + recent_low + close.iloc[-1]) / 3

    return {
        "ma5": ma5, "ma10": ma10, "atr": atr,
        "recent_high": recent_high, "recent_low": recent_low,
        "r1": 2 * pivot - recent_low, "s1": 2 * pivot - recent_high,
        "trend": "bullish" if ma5 > ma10 else "bearish",
    }


def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """计算MACD指标（复用 calc_macd_series 避免代码重复）"""
    series = calc_macd_series(close, fast, slow, signal)
    dif, dea, macd = series["dif"], series["dea"], series["macd"]
    return {
        "dif": round(float(dif.iloc[-1]), 4),
        "dea": round(float(dea.iloc[-1]), 4),
        "macd": round(float(macd.iloc[-1]), 4),
        "signal": "golden_cross" if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]
                  else "death_cross" if dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]
                  else "bullish" if dif.iloc[-1] > dea.iloc[-1] else "bearish",
    }


def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9) -> dict:
    """计算KDJ指标"""
    lowest_low = low.rolling(n).min()
    highest_high = high.rolling(n).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(50)
    
    k = rsv.ewm(com=2, adjust=False).mean()
    d = k.ewm(com=2, adjust=False).mean()
    j = 3 * k - 2 * d
    
    k_val, d_val, j_val = float(k.iloc[-1]), float(d.iloc[-1]), float(j.iloc[-1])
    zone = "overbought" if k_val > 80 or d_val > 80 else "oversold" if k_val < 20 or d_val < 20 else "neutral"
    
    return {
        "k": round(k_val, 2), "d": round(d_val, 2), "j": round(j_val, 2),
        "zone": zone,
        "signal": "golden_cross" if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2]
                  else "death_cross" if k.iloc[-1] < d.iloc[-1] and k.iloc[-2] >= d.iloc[-2]
                  else "bullish" if k.iloc[-1] > d.iloc[-1] else "bearish",
    }


def calc_rsi(close: pd.Series, periods: list[int] = None) -> dict:
    """计算多周期 RSI 指标（默认 RSI6, RSI12, RSI24）"""
    if periods is None:
        periods = [6, 12, 24]

    result = {}
    for period in periods:
        rsi = calc_rsi_series(close, period)
        result[f"rsi{period}"] = round(float(rsi.iloc[-1]), 2)

    # 使用 RSI6 判断超买超卖区域（短周期更敏感）
    rsi6 = result.get("rsi6", result.get(f"rsi{periods[0]}", 50))
    zone = "overbought" if rsi6 > 70 else "oversold" if rsi6 < 30 else "neutral"
    result["zone"] = zone
    return result


def calc_boll(close: pd.Series, period: int = 20, std_dev: int = 2) -> dict:
    """计算布林带指标"""
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std

    price = float(close.iloc[-1])
    upper_val, mid_val, lower_val = float(upper.iloc[-1]), float(mid.iloc[-1]), float(lower.iloc[-1])
    band_width = (upper_val - lower_val) / mid_val * 100

    if price > upper_val:
        position = "above_upper"
    elif price < lower_val:
        position = "below_lower"
    elif price > mid_val:
        position = "upper_half"
    else:
        position = "lower_half"

    return {"upper": round(upper_val, 2), "mid": round(mid_val, 2), "lower": round(lower_val, 2),
            "bandwidth": round(band_width, 2), "position": position}


def calc_ma(close: pd.Series, periods: list[int] = None) -> dict:
    """计算多周期移动平均线"""
    if periods is None:
        periods = [5, 10, 20, 30, 60]
    result = {}
    for period in periods:
        if len(close) >= period:
            result[f"ma{period}"] = round(float(close.rolling(period).mean().iloc[-1]), 2)
    return result


def calc_all_indicators(df: pd.DataFrame) -> dict:
    """计算所有技术指标"""
    if df.empty or len(df) < 20:
        return {}

    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float) if 'volume' in df.columns else None

    ma = calc_ma(close)
    ma5 = ma.get("ma5", close.iloc[-1])
    ma10 = ma.get("ma10", close.iloc[-1])
    ma20 = ma.get("ma20", close.iloc[-1])

    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])

    result = {
        "ma": ma,
        "atr": round(atr, 2),
        "trend": "bullish" if ma5 > ma10 > ma20 else "bearish" if ma5 < ma10 < ma20 else "sideways",
        "macd": calc_macd(close),
        "kdj": calc_kdj(high, low, close),
        "rsi": calc_rsi(close),
        "boll": calc_boll(close),
        "adx": calc_adx(high, low, close),
    }

    # 成交量指标（如果有成交量数据）
    if volume is not None and volume.sum() > 0:
        result["obv"] = calc_obv(close, volume)

    return result

