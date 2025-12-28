"""测试自适应评分模块"""
import pytest
from kairos.scoring.adaptive import (
    check_volume_confirmation,
    calc_enhanced_confidence,
    score_with_adaptive_weights
)
from kairos.scoring.config import get_market_regime, get_adaptive_weights


class TestCheckVolumeConfirmation:
    """量价确认测试"""

    def test_confirmed_with_strong_momentum(self):
        """量价配合且动量强"""
        indicators = {"obv": {"signal": "bullish", "momentum": 12}}
        result = check_volume_confirmation(indicators, "bullish")
        assert result["confirmed"] is True
        assert result["strength"] == 1.0
        assert "动量强" in result["reason"]

    def test_confirmed_weak_momentum(self):
        """量价配合但动量弱"""
        indicators = {"obv": {"signal": "bullish", "momentum": 3}}
        result = check_volume_confirmation(indicators, "bullish")
        assert result["confirmed"] is True
        assert result["strength"] == 0.5

    def test_not_confirmed_opposite_direction(self):
        """量价背离"""
        indicators = {"obv": {"signal": "bearish", "momentum": -8}}
        result = check_volume_confirmation(indicators, "bullish")
        assert result["confirmed"] is False
        assert result["strength"] == -0.3
        assert "相反" in result["reason"]

    def test_no_volume_data(self):
        """无成交量数据"""
        result = check_volume_confirmation({}, "bullish")
        assert result["confirmed"] is False
        assert result["strength"] == 0


class TestGetMarketRegime:
    """市场状态识别测试"""

    def test_trending_market(self):
        """趋势市场 (ADX > 30)"""
        indicators = {"adx": {"adx": 35, "strength": "strong"}}
        assert get_market_regime(indicators) == "trending"

    def test_ranging_market(self):
        """震荡市场 (ADX < 20)"""
        indicators = {"adx": {"adx": 15, "strength": "weak"}}
        assert get_market_regime(indicators) == "ranging"

    def test_neutral_market(self):
        """中性市场 (20 <= ADX <= 30)"""
        indicators = {"adx": {"adx": 25, "strength": "moderate"}}
        assert get_market_regime(indicators) == "neutral"


class TestGetAdaptiveWeights:
    """自适应权重测试"""

    def test_trending_weights(self):
        """趋势市场权重调整 - 趋势权重最大"""
        indicators = {"adx": {"adx": 35, "strength": "strong"}}
        weights = get_adaptive_weights(indicators)
        # 趋势市场，趋势权重 > 动量权重
        assert weights["trend"] > weights["momentum"]
        assert weights["trend"] == 0.40

    def test_ranging_weights(self):
        """震荡市场权重调整 - 动量权重最大"""
        indicators = {"adx": {"adx": 15, "strength": "weak"}}
        weights = get_adaptive_weights(indicators)
        # 震荡市场，动量权重 > 趋势权重
        assert weights["momentum"] > weights["trend"]
        assert weights["momentum"] == 0.35


class TestCalcEnhancedConfidence:
    """增强置信度测试"""

    def test_high_confidence(self):
        """高置信度场景"""
        result = calc_enhanced_confidence(
            base_score=85,
            consistency={"consistency": 1.0, "direction": "bullish"},
            volume_confirm={"strength": 1.0, "confirmed": True},
            market_regime="trending"
        )
        assert result["level"] == "高确定性"
        assert result["confidence_score"] >= 0.7

    def test_low_confidence_with_divergence(self):
        """量价背离降低置信度"""
        result = calc_enhanced_confidence(
            base_score=65,
            consistency={"consistency": 0.5, "direction": "bullish"},
            volume_confirm={"strength": -0.3, "confirmed": False},
            market_regime="neutral"
        )
        assert result["confidence_score"] < 0.5

    def test_ranging_market_reduces_trend_confidence(self):
        """震荡市场降低趋势信号置信度"""
        result = calc_enhanced_confidence(
            base_score=75,
            consistency={"consistency": 0.8, "direction": "bullish"},
            volume_confirm={"strength": 0.5, "confirmed": True},
            market_regime="ranging"
        )
        # 震荡市场趋势信号打折
        assert result["confidence_score"] < 0.7


class TestScoreWithAdaptiveWeights:
    """综合自适应评分测试"""

    def test_returns_all_required_fields(self):
        """测试返回所有必要字段"""
        indicators = {
            "trend": "bullish",
            "macd": {"signal": "bullish"},
            "kdj": {"zone": "neutral"}, "rsi": {"zone": "neutral"},
            "adx": {"adx": 28, "strength": "moderate", "direction": "bullish"},
            "obv": {"signal": "bullish", "momentum": 8}
        }
        result = score_with_adaptive_weights(indicators)
        
        assert "score" in result
        assert "signals" in result
        assert "market_regime" in result
        assert "adaptive_weights" in result
        assert "consistency" in result
        assert "volume_confirmation" in result
        assert "confidence" in result

    def test_signals_include_volume_confirmation(self):
        """信号应包含量价确认信息"""
        indicators = {
            "trend": "bullish",
            "macd": {"signal": "bullish"},
            "kdj": {"zone": "neutral"}, "rsi": {"zone": "neutral"},
            "adx": {"adx": 30, "strength": "strong", "direction": "bullish"},
            "obv": {"signal": "bullish", "momentum": 15}
        }
        result = score_with_adaptive_weights(indicators)
        signals_text = " ".join(result["signals"])
        assert "量价配合" in signals_text or "市场状态" in signals_text

    def test_bearish_scenario(self):
        """看空场景测试"""
        indicators = {
            "trend": "bearish",
            "macd": {"signal": "death_cross"},
            "kdj": {"zone": "overbought"}, "rsi": {"zone": "overbought"},
            "adx": {"adx": 32, "strength": "strong", "direction": "bearish"},
            "obv": {"signal": "bearish", "momentum": -12}
        }
        result = score_with_adaptive_weights(indicators)
        assert result["score"] < 30
        assert result["consistency"]["direction"] == "bearish"

