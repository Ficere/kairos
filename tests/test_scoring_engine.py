"""测试评分引擎"""
import pytest
from kairos.scoring.engine import (
    _score_trend, _score_macd, _score_momentum,
    _score_boll, _score_adx, _score_obv,
    score_technical_v2, calc_signal_consistency
)


class TestScoreTrend:
    """趋势评分测试"""

    def test_bullish_trend(self):
        score, signal = _score_trend({"trend": "bullish"})
        assert score == 15
        assert "多头" in signal

    def test_bearish_trend(self):
        score, signal = _score_trend({"trend": "bearish"})
        assert score == -15
        assert "空头" in signal

    def test_sideways_trend(self):
        score, signal = _score_trend({"trend": "sideways"})
        assert score == 0
        assert signal is None


class TestScoreMACD:
    """MACD 评分测试"""

    def test_golden_cross(self):
        score, signal = _score_macd({"macd": {"signal": "golden_cross"}})
        assert score == 10
        assert "金叉" in signal

    def test_death_cross(self):
        score, signal = _score_macd({"macd": {"signal": "death_cross"}})
        assert score == -10
        assert "死叉" in signal

    def test_bullish_macd(self):
        score, signal = _score_macd({"macd": {"signal": "bullish"}})
        assert score == 5


class TestScoreMomentum:
    """动量组评分测试（KDJ + RSI 合并）"""

    def test_double_oversold(self):
        """双重超卖应该给更高分数"""
        indicators = {"kdj": {"zone": "oversold"}, "rsi": {"zone": "oversold"}}
        score, signal = _score_momentum(indicators)
        assert score == 12
        assert "双重超卖" in signal

    def test_double_overbought(self):
        """双重超买应该给更大负分"""
        indicators = {"kdj": {"zone": "overbought"}, "rsi": {"zone": "overbought"}}
        score, signal = _score_momentum(indicators)
        assert score == -12
        assert "双重超买" in signal

    def test_single_oversold(self):
        """单一超卖"""
        indicators = {"kdj": {"zone": "oversold"}, "rsi": {"zone": "neutral"}}
        score, signal = _score_momentum(indicators)
        assert score == 8
        assert "KDJ超卖" in signal

    def test_neutral(self):
        """中性状态"""
        indicators = {"kdj": {"zone": "neutral"}, "rsi": {"zone": "neutral"}}
        score, signal = _score_momentum(indicators)
        assert score == 0
        assert signal is None


class TestScoreADX:
    """ADX 评分测试"""

    def test_strong_bullish(self):
        indicators = {"adx": {"strength": "strong", "direction": "bullish"}}
        score, signal = _score_adx(indicators)
        assert score == 8
        assert "强趋势" in signal

    def test_strong_bearish(self):
        indicators = {"adx": {"strength": "strong", "direction": "bearish"}}
        score, signal = _score_adx(indicators)
        assert score == -8

    def test_weak_trend(self):
        indicators = {"adx": {"strength": "weak", "direction": "bullish"}}
        score, signal = _score_adx(indicators)
        assert score == 0
        assert signal is None


class TestScoreOBV:
    """OBV 评分测试"""

    def test_strong_bullish_obv(self):
        indicators = {"obv": {"signal": "bullish", "momentum": 15}}
        score, signal = _score_obv(indicators)
        assert score == 8
        assert "bullish" in signal

    def test_normal_bearish_obv(self):
        indicators = {"obv": {"signal": "bearish", "momentum": 3}}
        score, signal = _score_obv(indicators)
        assert score == -5


class TestScoreTechnicalV2:
    """综合评分测试"""

    def test_score_range(self):
        """评分应该在 0-100 范围内"""
        # 极端看多
        bullish = {
            "trend": "bullish",
            "macd": {"signal": "golden_cross"},
            "kdj": {"zone": "oversold"}, "rsi": {"zone": "oversold"},
            "adx": {"strength": "strong", "direction": "bullish"},
            "obv": {"signal": "bullish", "momentum": 15}
        }
        result = score_technical_v2(bullish)
        assert 0 <= result["score"] <= 100

        # 极端看空
        bearish = {
            "trend": "bearish",
            "macd": {"signal": "death_cross"},
            "kdj": {"zone": "overbought"}, "rsi": {"zone": "overbought"},
            "adx": {"strength": "strong", "direction": "bearish"},
            "obv": {"signal": "bearish", "momentum": -15}
        }
        result = score_technical_v2(bearish)
        assert 0 <= result["score"] <= 100

    def test_neutral_returns_around_50(self):
        """中性指标应返回约 50 分"""
        neutral = {
            "trend": "sideways",
            "macd": {"signal": "neutral"},
            "kdj": {"zone": "neutral"}, "rsi": {"zone": "neutral"},
            "adx": {"strength": "weak"},
            "obv": {}
        }
        result = score_technical_v2(neutral)
        assert 45 <= result["score"] <= 55


class TestCalcSignalConsistency:
    """信号一致性测试"""

    def test_all_bullish(self):
        """所有信号看多"""
        indicators = {
            "trend": "bullish",
            "macd": {"signal": "bullish"},
            "adx": {"direction": "bullish"},
            "obv": {"signal": "bullish"}
        }
        result = calc_signal_consistency(indicators)
        assert result["consistency"] == 1.0
        assert result["direction"] == "bullish"
        assert result["count"] == 4

    def test_mixed_signals(self):
        """混合信号"""
        indicators = {
            "trend": "bullish",
            "macd": {"signal": "bearish"},
            "adx": {"direction": "bullish"},
            "obv": {"signal": "bearish"}
        }
        result = calc_signal_consistency(indicators)
        assert result["consistency"] == 0.0
        assert result["direction"] == "neutral"

