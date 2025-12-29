"""市场状态过滤器 - 基于持仓量和成交量判断市场状态"""
import pandas as pd
from enum import Enum
from kairos.scoring.config import MARKET_STATE_CONFIG


class MarketState(Enum):
    """市场状态枚举"""
    VALID_BREAKOUT = "valid_breakout"         # 真突破
    SHORT_COVERING = "short_covering"         # 空头回补
    LONG_LIQUIDATION = "long_liquidation"     # 多头踩踏
    DIVERGENCE_EXHAUSTION = "divergence_exhaustion"  # 背离衰竭
    ACCUMULATION = "accumulation"             # 低位吸筹
    NORMAL = "normal"                         # 正常状态


from kairos.scoring.engulf_pattern import (
    EngulfPattern, detect_engulf_pattern, score_engulf_pattern
)


def calc_volume_oi_metrics(df: pd.DataFrame, lookback: int = 10) -> dict:
    """计算量价仓指标
    
    Args:
        df: 历史数据，需包含 close, volume, hold(持仓量) 列
        lookback: 回溯天数
    
    Returns:
        量价仓变化指标字典
    """
    if df.empty or len(df) < lookback:
        return {"valid": False}
    
    recent = df.tail(lookback).copy()
    
    # 确保列名统一（hold 或 open_interest）
    oi_col = "hold" if "hold" in recent.columns else "open_interest"
    if oi_col not in recent.columns:
        return {"valid": False, "reason": "无持仓量数据"}
    
    close = recent["close"].astype(float)
    volume = recent["volume"].astype(float)
    oi = recent[oi_col].astype(float)
    
    # 价格变化（最近5日 vs 前5日）
    price_recent = close.tail(5).mean()
    price_prev = close.head(5).mean()
    price_change_pct = (price_recent - price_prev) / price_prev * 100
    
    # 成交量变化（最近5日均量 vs 前期均量）
    vol_recent = volume.tail(5).mean()
    vol_prev = volume.head(max(len(volume) - 5, 5)).mean()  # 前期均量
    vol_ratio = vol_recent / vol_prev if vol_prev > 0 else 1.0
    
    # 持仓量变化
    oi_recent = oi.iloc[-1]
    oi_prev = oi.iloc[-5] if len(oi) >= 5 else oi.iloc[0]
    oi_change_pct = (oi_recent - oi_prev) / oi_prev * 100 if oi_prev > 0 else 0
    
    # 持仓量趋势（连续增加/减少）
    oi_trend = "increasing" if oi.diff().tail(3).sum() > 0 else "decreasing"
    
    # 价格波动率（判断横盘）
    price_volatility = close.pct_change().std() * 100
    is_sideways = price_volatility < 1.5 and abs(price_change_pct) < 3
    
    return {
        "valid": True,
        "price_change_pct": price_change_pct,
        "vol_ratio": vol_ratio,
        "oi_change_pct": oi_change_pct,
        "oi_trend": oi_trend,
        "is_sideways": is_sideways,
        "price_volatility": price_volatility,
    }


def detect_market_state(metrics: dict) -> tuple[MarketState, str]:
    """检测市场状态
    
    Args:
        metrics: calc_volume_oi_metrics 返回的指标字典
    
    Returns:
        (市场状态枚举, 状态描述)
    """
    if not metrics.get("valid"):
        return MarketState.NORMAL, "数据不足"
    
    cfg = MARKET_STATE_CONFIG["thresholds"]
    price_chg = metrics["price_change_pct"]
    vol_ratio = metrics["vol_ratio"]
    oi_chg = metrics["oi_change_pct"]
    is_sideways = metrics["is_sideways"]
    
    price_up = price_chg > cfg["price_up_threshold"]
    price_down = price_chg < cfg["price_down_threshold"]
    vol_high = vol_ratio > cfg["vol_amplify_ratio"]
    oi_up = oi_chg > cfg["oi_increase_threshold"]
    oi_down = oi_chg < cfg["oi_decrease_threshold"]
    
    # 1. 真突破：价格上涨 + 成交量放大 + 持仓量增加
    if price_up and vol_high and oi_up:
        return MarketState.VALID_BREAKOUT, "量价仓共振,新资金入场"
    
    # 2. 空头回补：价格上涨 + 成交量放大 + 持仓量减少
    if price_up and vol_high and oi_down:
        return MarketState.SHORT_COVERING, "虚假上涨,空头止损"
    
    # 3. 多头踩踏：价格下跌 + 成交量放大 + 持仓量减少
    if price_down and vol_high and oi_down:
        return MarketState.LONG_LIQUIDATION, "多头恐慌止损,底部临近"
    
    # 4. 背离衰竭：价格创新高/新低但持仓量不增或减少
    if (price_up or price_down) and not oi_up:
        if abs(price_chg) > cfg["price_extreme_threshold"]:
            return MarketState.DIVERGENCE_EXHAUSTION, "趋势动力枯竭"
    
    # 5. 低位吸筹：价格横盘 + 成交量平稳 + 持仓量持续增加
    if is_sideways and vol_ratio < 1.3 and oi_up:
        return MarketState.ACCUMULATION, "主力潜伏建仓"
    
    return MarketState.NORMAL, "正常状态"


def score_market_state(state: MarketState, base_direction: str) -> tuple[int, str]:
    """根据市场状态计算评分调整
    
    Args:
        state: 市场状态
        base_direction: 基础信号方向 ("bullish", "bearish", "neutral")
    
    Returns:
        (分数调整, 信号描述)
    """
    cfg = MARKET_STATE_CONFIG["score_adjustments"]
    state_cfg = cfg.get(state.value, {})
    
    if not state_cfg:
        return 0, None
    
    icon = state_cfg.get("icon", "📊")
    label = state_cfg.get("label", state.value)
    
    # 根据方向获取分数调整
    if base_direction == "bullish":
        score = state_cfg.get("bullish_adj", 0)
    elif base_direction == "bearish":
        score = state_cfg.get("bearish_adj", 0)
    else:
        score = state_cfg.get("neutral_adj", 0)
    
    if score == 0:
        return 0, None
    
    desc = state_cfg.get("description", "")
    signal = f"{icon} 市场状态: {label}({desc}) {score:+d}"
    return score, signal
