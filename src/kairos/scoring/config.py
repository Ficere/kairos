"""评分系统配置 - 将硬编码的权重外置化，支持动态调整"""

# 多周期权重配置
TIMEFRAME_WEIGHTS = {
    "1m": 0.05,   # 噪声大，权重低
    "5m": 0.10,
    "15m": 0.15,
    "1h": 0.25,
    "4h": 0.25,
    "1d": 0.20,   # 日线权重高但期货以短线为主
}

# MACD 金叉/死叉按周期加权（越长周期越可靠）
MACD_CROSS_BY_TIMEFRAME = {
    "1m": {"golden_cross": 2, "death_cross": -2},
    "5m": {"golden_cross": 4, "death_cross": -4},
    "15m": {"golden_cross": 6, "death_cross": -6},
    "1h": {"golden_cross": 10, "death_cross": -10},
    "4h": {"golden_cross": 12, "death_cross": -12},
    "1d": {"golden_cross": 15, "death_cross": -15},
}

# 趋势信号按周期加权
TREND_BY_TIMEFRAME = {
    "1m": {"bullish": 3, "bearish": -3},
    "5m": {"bullish": 5, "bearish": -5},
    "15m": {"bullish": 8, "bearish": -8},
    "1h": {"bullish": 12, "bearish": -12},
    "4h": {"bullish": 15, "bearish": -15},
    "1d": {"bullish": 15, "bearish": -15},
}

# 背离信号分级配置
DIVERGENCE_CONFIG = {
    # 常规背离（单指标）
    "regular": {
        "bullish": 8,    # 底背离
        "bearish": -8,   # 顶背离
    },
    # 隐藏背离（较弱信号）
    "hidden": {
        "bullish": 5,
        "bearish": -5,
    },
    # 强背离（多指标共振，如 MACD+RSI 同时背离）
    "strong": {
        "bullish": 12,
        "bearish": -12,
    },
    # 置信度调整系数
    "confidence_multiplier": {
        "高": 1.0,
        "中": 0.7,
        "低": 0.4,
    },
}

# 各指标评分配置（单周期，已优化权重）
SCORING_CONFIG = {
    # 趋势指标 (±15 → ±12，降低滞后性影响)
    "trend": {
        "bullish": 12,
        "bearish": -12,
        "sideways": 0,
    },
    # MACD 指标 (金叉按周期分级，单周期保持 ±8)
    "macd": {
        "golden_cross": 8,
        "death_cross": -8,
        "bullish": 4,
        "bearish": -4,
    },
    # 动量指标组 (±8~12 → ±6~10，减少假信号)
    "momentum": {
        "strong_oversold": 10,   # KDJ 和 RSI 同时超卖
        "oversold": 6,           # 单一指标超卖
        "strong_overbought": -10,
        "overbought": -6,
        "neutral": 0,
    },
    # 布林带 (保持不变)
    "boll": {
        "below_lower": 5,
        "above_upper": -5,
        "lower_half": 2,
        "upper_half": -2,
    },
    # ADX 趋势强度 (±4~8 → ±4~6，作为过滤器)
    "adx": {
        "strong_bullish": 6,
        "strong_bearish": -6,
        "moderate_bullish": 4,
        "moderate_bearish": -4,
        "weak": 0,
    },
    # OBV 成交量 (±5~8 → ±3~6，期货量价关系较弱)
    "obv": {
        "bullish": 3,
        "bearish": -3,
        "strong_bullish": 6,
        "strong_bearish": -6,
    },
}

# 指标组权重配置（用于自适应权重）
DEFAULT_GROUP_WEIGHTS = {
    "trend": 0.30,      # 趋势类
    "momentum": 0.25,   # 动量类
    "volatility": 0.20, # 波动率类
    "volume": 0.15,     # 成交量类
    "adx": 0.10,        # 趋势强度
}


def get_adaptive_weights(indicators: dict) -> dict:
    """根据 ADX 判断市场状态，动态调整权重
    
    Args:
        indicators: 技术指标字典，需包含 adx 数据
        
    Returns:
        调整后的权重字典
    """
    adx_data = indicators.get("adx", {})
    adx_val = adx_data.get("adx", 25)
    
    if adx_val > 30:
        # 强趋势市场：加大趋势权重，降低震荡指标权重
        return {
            "trend": 0.40,
            "momentum": 0.20,
            "volatility": 0.15,
            "volume": 0.15,
            "adx": 0.10,
        }
    elif adx_val < 20:
        # 震荡市场：加大动量和波动率权重
        return {
            "trend": 0.15,
            "momentum": 0.35,
            "volatility": 0.30,
            "volume": 0.15,
            "adx": 0.05,
        }
    else:
        # 中性市场：使用默认权重
        return DEFAULT_GROUP_WEIGHTS.copy()


def get_market_regime(indicators: dict) -> str:
    """判断当前市场状态
    
    Returns:
        "trending" | "ranging" | "neutral"
    """
    adx_data = indicators.get("adx", {})
    adx_val = adx_data.get("adx", 25)
    
    if adx_val > 30:
        return "trending"
    elif adx_val < 20:
        return "ranging"
    return "neutral"


# 市场状态过滤器配置
MARKET_STATE_CONFIG = {
    # 判定阈值
    "thresholds": {
        "price_up_threshold": 2.0,        # 价格上涨阈值 %
        "price_down_threshold": -2.0,     # 价格下跌阈值 %
        "price_extreme_threshold": 5.0,   # 极端价格变化阈值 %
        "vol_amplify_ratio": 1.5,         # 成交量放大倍数（相对20日均量）
        "oi_increase_threshold": 3.0,     # 持仓量增加阈值 %
        "oi_decrease_threshold": -3.0,    # 持仓量减少阈值 %
    },
    # 评分调整配置
    "score_adjustments": {
        "valid_breakout": {
            "icon": "📊", "label": "真突破",
            "description": "量价仓共振",
            "bullish_adj": 5, "bearish_adj": -3, "neutral_adj": 3,
        },
        "short_covering": {
            "icon": "⚠️", "label": "空头回补",
            "description": "虚假上涨",
            "bullish_adj": -8, "bearish_adj": 0, "neutral_adj": -5,
        },
        "long_liquidation": {
            "icon": "🔄", "label": "多头踩踏",
            "description": "底部临近",
            "bullish_adj": 3, "bearish_adj": -5, "neutral_adj": 0,
        },
        "divergence_exhaustion": {
            "icon": "⚡", "label": "背离衰竭",
            "description": "动力枯竭",
            "bullish_adj": -5, "bearish_adj": -5, "neutral_adj": 0,
        },
        "accumulation": {
            "icon": "🔍", "label": "低位吸筹",
            "description": "主力建仓",
            "bullish_adj": 8, "bearish_adj": -3, "neutral_adj": 5,
        },
    },
    # 双日反包形态评分配置
    "engulf_adjustments": {
        "vol_price_engulf": {
            "icon": "🔥", "label": "量价双包",
            "description": "强反转确认",
            "bullish_adj": 10, "bearish_adj": -10,
        },
        "vol_engulf_only": {
            "icon": "⚡", "label": "量包价不包",
            "description": "分歧潜在反转",
            "bullish_adj": 5, "bearish_adj": -5,
        },
        "price_engulf_only": {
            "icon": "💨", "label": "价包量不包",
            "description": "情绪驱动",
            "bullish_adj": 2, "bearish_adj": -2,
        },
        "extreme_shrink": {
            "icon": "🔻", "label": "极致缩量",
            "description": "顶底预警",
            "bullish_adj": 8, "bearish_adj": -8,
        },
    },
}
