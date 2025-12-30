"""背离检测模块 - 检测价格与技术指标之间的背离"""
import pandas as pd
import numpy as np
from kairos.futures.indicators import calc_macd_series, calc_rsi_series


def find_local_extrema(series: pd.Series, order: int = 5) -> tuple[list, list]:
    """查找局部极值点（高点和低点）
    Args:
        series: 数据序列
        order: 窗口大小，点必须是前后 order 个点中的最大/最小值
    Returns:
        (高点索引列表, 低点索引列表)
    """
    highs, lows = [], []
    values = series.values
    n = len(values)

    for i in range(order, n - order):
        window = values[i - order:i + order + 1]
        if values[i] == np.max(window):
            highs.append(i)
        if values[i] == np.min(window):
            lows.append(i)
    return highs, lows


def detect_divergence(df: pd.DataFrame, lookback: int = 30) -> dict:
    """检测价格与指标之间的背离
    Args:
        df: 包含 OHLC 数据的 DataFrame，需要至少 lookback 行数据
        lookback: 回溯天数
    Returns:
        背离检测结果字典
    """
    result = {"type": "无背离", "confidence": "低", "indicator": "", "description": "未检测到明显背离"}

    if df.empty or len(df) < lookback:
        return result

    recent = df.tail(lookback).copy()
    close = recent['close'].astype(float)

    # 使用统一的指标计算函数（避免代码重复）
    dif = calc_macd_series(close)["dif"]
    rsi = calc_rsi_series(close)
    
    # 查找价格和指标的局部极值
    price_highs, price_lows = find_local_extrema(close, order=3)
    dif_highs, dif_lows = find_local_extrema(dif, order=3)
    rsi_highs, rsi_lows = find_local_extrema(rsi, order=3)
    
    divergences = []
    
    # 检测顶背离（价格创新高但指标未创新高）
    if len(price_highs) >= 2:
        ph1, ph2 = price_highs[-2], price_highs[-1]
        price_vals = close.iloc[[ph1, ph2]].values
        
        if price_vals[1] > price_vals[0]:
            if len(dif_highs) >= 2:
                dh1, dh2 = dif_highs[-2], dif_highs[-1]
                dif_vals = dif.iloc[[dh1, dh2]].values
                if dif_vals[1] < dif_vals[0]:
                    divergences.append(("顶背离", "MACD", abs(dif_vals[0] - dif_vals[1])))
            
            if len(rsi_highs) >= 2:
                rh1, rh2 = rsi_highs[-2], rsi_highs[-1]
                rsi_vals = rsi.iloc[[rh1, rh2]].values
                if not np.isnan(rsi_vals).any() and rsi_vals[1] < rsi_vals[0]:
                    divergences.append(("顶背离", "RSI", abs(rsi_vals[0] - rsi_vals[1])))
    
    # 检测底背离（价格创新低但指标未创新低）
    if len(price_lows) >= 2:
        pl1, pl2 = price_lows[-2], price_lows[-1]
        price_vals = close.iloc[[pl1, pl2]].values
        
        if price_vals[1] < price_vals[0]:
            if len(dif_lows) >= 2:
                dl1, dl2 = dif_lows[-2], dif_lows[-1]
                dif_vals = dif.iloc[[dl1, dl2]].values
                if dif_vals[1] > dif_vals[0]:
                    divergences.append(("底背离", "MACD", abs(dif_vals[1] - dif_vals[0])))
            
            if len(rsi_lows) >= 2:
                rl1, rl2 = rsi_lows[-2], rsi_lows[-1]
                rsi_vals = rsi.iloc[[rl1, rl2]].values
                if not np.isnan(rsi_vals).any() and rsi_vals[1] > rsi_vals[0]:
                    divergences.append(("底背离", "RSI", abs(rsi_vals[1] - rsi_vals[0])))
    
    if not divergences:
        return result
    
    divergences.sort(key=lambda x: x[2], reverse=True)
    div_type, indicator, strength = divergences[0]
    
    same_type = [d for d in divergences if d[0] == div_type]
    if len(same_type) > 1:
        indicator = "+".join(sorted(set(d[1] for d in same_type)))
    
    confidence = "高" if len(same_type) > 1 else "中" if strength > 5 else "低"
    
    desc_map = {
        ("顶背离", "MACD"): "价格创新高但MACD未创新高，存在顶背离风险",
        ("顶背离", "RSI"): "价格创新高但RSI未创新高，存在顶背离风险",
        ("顶背离", "MACD+RSI"): "价格创新高但MACD和RSI均未创新高，顶背离信号较强",
        ("底背离", "MACD"): "价格创新低但MACD未创新低，存在底背离机会",
        ("底背离", "RSI"): "价格创新低但RSI未创新低，存在底背离机会",
        ("底背离", "MACD+RSI"): "价格创新低但MACD和RSI均未创新低，底背离信号较强",
    }
    
    return {"type": div_type, "confidence": confidence, "indicator": indicator,
            "description": desc_map.get((div_type, indicator), f"{div_type}信号({indicator})")}

