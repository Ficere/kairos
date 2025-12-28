"""自适应评分和信号确认模块"""
from kairos.scoring.config import get_adaptive_weights, get_market_regime
from kairos.scoring.engine import score_technical_v2, calc_signal_consistency


def check_volume_confirmation(indicators: dict, direction: str) -> dict:
    """检查成交量是否确认价格信号
    
    Args:
        indicators: 技术指标字典
        direction: 信号方向 "bullish" 或 "bearish"
        
    Returns:
        确认结果字典，包含是否确认和原因
    """
    obv = indicators.get("obv", {})
    if not obv:
        return {"confirmed": False, "reason": "无成交量数据", "strength": 0}
    
    obv_signal = obv.get("signal", "")
    obv_momentum = obv.get("momentum", 0)
    
    # 方向一致性检查
    direction_match = (
        (direction == "bullish" and obv_signal == "bullish") or
        (direction == "bearish" and obv_signal == "bearish")
    )
    
    # 动量强度检查
    momentum_strong = abs(obv_momentum) > 5
    
    if direction_match and momentum_strong:
        return {
            "confirmed": True, 
            "reason": f"OBV方向一致且动量强({obv_momentum:.1f}%)",
            "strength": min(abs(obv_momentum) / 10, 1.0)
        }
    elif direction_match:
        return {
            "confirmed": True, 
            "reason": "OBV方向一致",
            "strength": 0.5
        }
    elif not direction_match and obv_signal:
        return {
            "confirmed": False, 
            "reason": f"OBV方向相反({obv_signal})",
            "strength": -0.3
        }
    return {"confirmed": False, "reason": "OBV信号不明确", "strength": 0}


def calc_enhanced_confidence(
    base_score: int, 
    consistency: dict, 
    volume_confirm: dict,
    market_regime: str
) -> dict:
    """增强的置信度计算
    
    Args:
        base_score: 基础技术评分 (0-100)
        consistency: 信号一致性结果
        volume_confirm: 成交量确认结果
        market_regime: 市场状态 (trending/ranging/neutral)
        
    Returns:
        置信度结果字典
    """
    # 基础置信度：偏离中性(50)越远，置信度越高
    base_conf = abs(base_score - 50) / 50
    
    # 一致性调整 (0.7 基础 + 0.3 一致性加成)
    consistency_val = consistency.get("consistency", 0)
    conf = base_conf * (0.7 + 0.3 * consistency_val)
    
    # 成交量确认调整
    vol_strength = volume_confirm.get("strength", 0)
    if vol_strength > 0:
        conf *= (1 + vol_strength * 0.3)  # 最多加成30%
    elif vol_strength < 0:
        conf *= (1 + vol_strength * 0.5)  # 相反时惩罚更重
    
    # 市场状态调整
    if market_regime == "trending":
        # 趋势市场：趋势信号更可靠
        if consistency.get("direction") != "neutral":
            conf *= 1.1
    elif market_regime == "ranging":
        # 震荡市场：极端值信号更可靠
        if base_score > 70 or base_score < 30:
            conf *= 0.9  # 震荡市趋势信号打折
    
    conf = min(max(conf, 0), 1.0)
    
    # 置信度等级
    if conf >= 0.7:
        level = "高确定性"
        position_pct = "30-50%"
    elif conf >= 0.5:
        level = "中确定性"
        position_pct = "20-30%"
    elif conf >= 0.3:
        level = "低确定性"
        position_pct = "10-20%"
    else:
        level = "观望"
        position_pct = "0%"
    
    return {
        "confidence_score": round(conf, 3),
        "level": level,
        "position_pct": position_pct,
        "factors": {
            "base": round(base_conf, 3),
            "consistency": consistency_val,
            "volume": vol_strength,
            "regime": market_regime
        }
    }


def score_with_adaptive_weights(indicators: dict) -> dict:
    """带自适应权重的综合评分
    
    根据市场状态(ADX)动态调整各指标组的权重
    """
    # 获取市场状态和自适应权重
    regime = get_market_regime(indicators)
    weights = get_adaptive_weights(indicators)
    
    # 基础评分
    base_result = score_technical_v2(indicators)
    base_score = base_result["score"]
    signals = base_result["signals"]
    
    # 计算信号一致性
    consistency = calc_signal_consistency(indicators)
    
    # 确定信号方向
    direction = "bullish" if base_score >= 55 else "bearish" if base_score <= 45 else "neutral"
    
    # 成交量确认
    volume_confirm = check_volume_confirmation(indicators, direction)
    
    # 计算增强置信度
    confidence = calc_enhanced_confidence(base_score, consistency, volume_confirm, regime)
    
    # 添加额外信号说明
    if volume_confirm["confirmed"]:
        signals.append(f"✓ 量价配合: {volume_confirm['reason']}")
    elif volume_confirm.get("strength", 0) < 0:
        signals.append(f"⚠ 量价背离: {volume_confirm['reason']}")
    
    signals.append(f"📊 市场状态: {regime}")
    
    return {
        "score": base_score,
        "signals": signals,
        "market_regime": regime,
        "adaptive_weights": weights,
        "consistency": consistency,
        "volume_confirmation": volume_confirm,
        "confidence": confidence
    }

