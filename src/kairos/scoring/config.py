"""评分系统配置 - 将硬编码的权重外置化，支持动态调整"""

# 各指标评分配置
SCORING_CONFIG = {
    # 趋势指标
    "trend": {
        "bullish": 15,
        "bearish": -15,
        "sideways": 0,
    },
    # MACD 指标
    "macd": {
        "golden_cross": 10,
        "death_cross": -10,
        "bullish": 5,
        "bearish": -5,
    },
    # 动量指标组（KDJ + RSI 合并，避免重复计分）
    "momentum": {
        "strong_oversold": 12,   # KDJ 和 RSI 同时超卖
        "oversold": 8,           # 单一指标超卖
        "strong_overbought": -12,
        "overbought": -8,
        "neutral": 0,
    },
    # 布林带
    "boll": {
        "below_lower": 5,
        "above_upper": -5,
        "lower_half": 2,
        "upper_half": -2,
    },
    # ADX 趋势强度（新增）
    "adx": {
        "strong_bullish": 8,    # 强趋势 + 多头
        "strong_bearish": -8,   # 强趋势 + 空头
        "moderate_bullish": 4,
        "moderate_bearish": -4,
        "weak": 0,              # 弱趋势/震荡，不加分
    },
    # OBV 成交量（新增）
    "obv": {
        "bullish": 5,
        "bearish": -5,
        "strong_bullish": 8,    # OBV 动量 > 10%
        "strong_bearish": -8,
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

