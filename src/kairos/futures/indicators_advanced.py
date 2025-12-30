"""高级技术指标 - OBV 成交量和 ADX 趋势强度"""
import pandas as pd
import numpy as np


def calc_obv(close: pd.Series, volume: pd.Series, ma_period: int = 10) -> dict:
    """计算 OBV 能量潮指标
    
    OBV 通过累计成交量来衡量买卖压力，价格上涨时加成交量，下跌时减成交量
    """
    direction = np.sign(close.diff())
    direction.iloc[0] = 0
    obv = (direction * volume).cumsum()
    obv_ma = obv.rolling(ma_period).mean()
    
    obv_val = float(obv.iloc[-1])
    obv_ma_val = float(obv_ma.iloc[-1])
    
    # 判断 OBV 趋势
    obv_trend = "bullish" if obv_val > obv_ma_val else "bearish"
    
    # 计算 OBV 动量（近期变化率）
    obv_change = (obv.iloc[-1] - obv.iloc[-5]) / abs(obv.iloc[-5]) * 100 if obv.iloc[-5] != 0 else 0
    
    return {
        "obv": round(obv_val, 0),
        "obv_ma": round(obv_ma_val, 0),
        "signal": obv_trend,
        "momentum": round(float(obv_change), 2)
    }


def calc_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> dict:
    """计算 ADX 趋势强度指标

    ADX > 25 表示强趋势，< 20 表示弱趋势/震荡
    +DI > -DI 表示多头占优，反之空头占优

    注意：需要至少 2*period 个数据点才能计算有效的 ADX
    """
    min_required = 2 * period + 1
    if len(high) < min_required:
        # 数据不足时返回默认值
        return {"adx": 20.0, "plus_di": 25.0, "minus_di": 25.0, "strength": "weak", "direction": "neutral"}

    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # +DM 和 -DM
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    # 平滑计算 - 使用 ATR 避免除零
    atr = tr.rolling(period).mean()
    atr_safe = atr.replace(0, np.nan).fillna(1)  # 避免除零
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_safe
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_safe

    # DX 和 ADX - 处理 NaN 和除零
    di_sum = plus_di + minus_di
    di_diff = abs(plus_di - minus_di)
    di_sum_safe = di_sum.replace(0, np.nan).fillna(1)
    dx = 100 * di_diff / di_sum_safe
    adx = dx.rolling(period).mean()

    # 获取最新有效值（跳过 NaN）
    adx_val = _get_last_valid(adx, default=20.0)
    plus_di_val = _get_last_valid(plus_di, default=25.0)
    minus_di_val = _get_last_valid(minus_di, default=25.0)

    # 趋势强度判断
    if adx_val > 30:
        strength = "strong"
    elif adx_val > 20:
        strength = "moderate"
    else:
        strength = "weak"

    # 趋势方向
    direction = "bullish" if plus_di_val > minus_di_val else "bearish"

    return {
        "adx": round(adx_val, 2),
        "plus_di": round(plus_di_val, 2),
        "minus_di": round(minus_di_val, 2),
        "strength": strength,
        "direction": direction
    }


def _get_last_valid(series: pd.Series, default: float = 0.0) -> float:
    """获取序列中最后一个有效值，跳过 NaN"""
    valid = series.dropna()
    if len(valid) == 0:
        return default
    return float(valid.iloc[-1])

