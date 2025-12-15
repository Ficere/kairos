"""高级技术指标计算模块"""
import pandas as pd
import numpy as np


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
    """计算MACD指标"""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    macd = (dif - dea) * 2
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


def calc_rsi(close: pd.Series, period: int = 14) -> dict:
    """计算RSI指标"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1])
    zone = "overbought" if rsi_val > 70 else "oversold" if rsi_val < 30 else "neutral"
    return {"rsi": round(rsi_val, 2), "zone": zone}


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


def calc_all_indicators(df: pd.DataFrame) -> dict:
    """计算所有技术指标"""
    if df.empty or len(df) < 20:
        return {}
    
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    
    ma5 = close.rolling(5).mean().iloc[-1]
    ma10 = close.rolling(10).mean().iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = float(tr.rolling(14).mean().iloc[-1])
    
    return {
        "ma": {"ma5": round(float(ma5), 2), "ma10": round(float(ma10), 2), "ma20": round(float(ma20), 2)},
        "atr": round(atr, 2),
        "trend": "bullish" if ma5 > ma10 > ma20 else "bearish" if ma5 < ma10 < ma20 else "sideways",
        "macd": calc_macd(close), "kdj": calc_kdj(high, low, close),
        "rsi": calc_rsi(close), "boll": calc_boll(close),
    }

