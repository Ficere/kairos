"""双日反包形态检测模块"""
import pandas as pd
from enum import Enum
from kairos.scoring.config import MARKET_STATE_CONFIG


class EngulfPattern(Enum):
    """双日反包形态枚举"""
    VOL_PRICE_ENGULF = "vol_price_engulf"     # 量价双包
    VOL_ENGULF_ONLY = "vol_engulf_only"       # 量包价不包
    PRICE_ENGULF_ONLY = "price_engulf_only"   # 价包量不包
    EXTREME_SHRINK = "extreme_shrink"         # 极致缩量
    NONE = "none"                             # 无明显形态


def detect_engulf_pattern(df: pd.DataFrame) -> tuple[EngulfPattern, str, str]:
    """检测双日反包形态
    
    Args:
        df: 历史数据，需包含 open, high, low, close, volume 列
    
    Returns:
        (形态枚举, 方向"bullish"/"bearish", 描述)
    """
    if df.empty or len(df) < 10:
        return EngulfPattern.NONE, "neutral", "数据不足"
    
    today = df.iloc[-1]
    yesterday = df.iloc[-2]
    vol_ma10 = df["volume"].tail(10).mean()
    
    # 当日和前日数据
    t_high, t_low = float(today["high"]), float(today["low"])
    t_close, t_open = float(today["close"]), float(today["open"])
    t_vol = float(today["volume"])
    
    y_high, y_low = float(yesterday["high"]), float(yesterday["low"])
    y_vol = float(yesterday["volume"])
    
    # 判断方向
    direction = "bullish" if t_close > t_open else "bearish"
    
    # 价格包含判断：当日高低点完全包含前日
    price_engulf = t_high >= y_high and t_low <= y_low
    # 成交量放大判断
    vol_engulf = t_vol > y_vol * 1.2
    vol_amplify = t_vol > y_vol * 1.5
    vol_shrink = t_vol < y_vol * 0.8
    # 极致缩量
    extreme_shrink = t_vol < vol_ma10 * 0.5
    
    # 1. 量价双包
    if price_engulf and vol_engulf:
        return EngulfPattern.VOL_PRICE_ENGULF, direction, "量价双包,强反转确认"
    
    # 2. 量包价不包
    if vol_amplify and not price_engulf:
        return EngulfPattern.VOL_ENGULF_ONLY, direction, "放量分歧,潜在反转"
    
    # 3. 价包量不包
    if price_engulf and vol_shrink:
        return EngulfPattern.PRICE_ENGULF_ONLY, direction, "缩量突破,情绪驱动"
    
    # 4. 极致缩量
    if extreme_shrink:
        return EngulfPattern.EXTREME_SHRINK, direction, "极致缩量,顶底预警"
    
    return EngulfPattern.NONE, "neutral", "无明显形态"


def score_engulf_pattern(pattern: EngulfPattern, direction: str) -> tuple[int, str]:
    """根据反包形态计算评分
    
    Args:
        pattern: 反包形态
        direction: 形态方向 "bullish" / "bearish"
    
    Returns:
        (分数调整, 信号描述)
    """
    cfg = MARKET_STATE_CONFIG.get("engulf_adjustments", {})
    pattern_cfg = cfg.get(pattern.value, {})
    
    if not pattern_cfg:
        return 0, None
    
    icon = pattern_cfg.get("icon", "🔄")
    label = pattern_cfg.get("label", pattern.value)
    
    if direction == "bullish":
        score = pattern_cfg.get("bullish_adj", 0)
    else:
        score = pattern_cfg.get("bearish_adj", 0)
    
    if score == 0:
        return 0, None
    
    desc = pattern_cfg.get("description", "")
    signal = f"{icon} 反包形态: {label}({desc}) {score:+d}"
    return score, signal

