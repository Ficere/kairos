"""测试评分引擎"""
import pytest
from kairos.scoring.engine import (
    _score_trend, _score_macd, _score_momentum,
    _score_boll, _score_adx, _score_obv,
    score_technical_v2, calc_signal_consistency,
    score_multi_timeframe
)


class TestScoreTrend:
    """趋势评分测试"""

    def test_bullish_trend(self):
        score, signal = _score_trend({"trend": "bullish"})
        assert score == 12  # 配置: trend.bullish = 12
        assert "多头" in signal

    def test_bearish_trend(self):
        score, signal = _score_trend({"trend": "bearish"})
        assert score == -12  # 配置: trend.bearish = -12
        assert "空头" in signal

    def test_sideways_trend(self):
        score, signal = _score_trend({"trend": "sideways"})
        assert score == 0
        assert signal is None


class TestScoreMACD:
    """MACD 评分测试"""

    def test_golden_cross(self):
        score, signal = _score_macd({"macd": {"signal": "golden_cross"}})
        assert score == 8  # 配置: macd.golden_cross = 8
        assert "金叉" in signal

    def test_death_cross(self):
        score, signal = _score_macd({"macd": {"signal": "death_cross"}})
        assert score == -8  # 配置: macd.death_cross = -8
        assert "死叉" in signal

    def test_bullish_macd(self):
        score, signal = _score_macd({"macd": {"signal": "bullish"}})
        assert score == 4  # 配置: macd.bullish = 4


class TestScoreMomentum:
    """动量组评分测试（KDJ + RSI 合并）"""

    def test_double_oversold(self):
        """双重超卖应该给更高分数"""
        indicators = {"kdj": {"zone": "oversold"}, "rsi": {"zone": "oversold"}}
        score, signal = _score_momentum(indicators)
        assert score == 10  # 配置: momentum.strong_oversold = 10
        assert "双重超卖" in signal

    def test_double_overbought(self):
        """双重超买应该给更大负分"""
        indicators = {"kdj": {"zone": "overbought"}, "rsi": {"zone": "overbought"}}
        score, signal = _score_momentum(indicators)
        assert score == -10  # 配置: momentum.strong_overbought = -10
        assert "双重超买" in signal

    def test_single_oversold(self):
        """单一超卖"""
        indicators = {"kdj": {"zone": "oversold"}, "rsi": {"zone": "neutral"}}
        score, signal = _score_momentum(indicators)
        assert score == 6  # 配置: momentum.oversold = 6
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
        assert score == 6  # 配置: adx.strong_bullish = 6
        assert "强趋势" in signal

    def test_strong_bearish(self):
        indicators = {"adx": {"strength": "strong", "direction": "bearish"}}
        score, signal = _score_adx(indicators)
        assert score == -6  # 配置: adx.strong_bearish = -6

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
        assert score == 6  # 配置: obv.strong_bullish = 6 (momentum > 10)
        assert "bullish" in signal

    def test_normal_bearish_obv(self):
        indicators = {"obv": {"signal": "bearish", "momentum": 3}}
        score, signal = _score_obv(indicators)
        assert score == -3  # 配置: obv.bearish = -3 (momentum < 10)


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


class TestScoreMultiTimeframe:
    """多周期融合评分测试"""

    def test_empty_input(self):
        """空输入应返回默认分数"""
        result = score_multi_timeframe({})
        assert result["score"] == 50
        assert result["signals"] == []

    def test_single_timeframe(self):
        """单一周期"""
        mtf = {"1d": {"trend": "bullish", "macd": {"signal": "golden_cross"}}}
        result = score_multi_timeframe(mtf)
        assert result["score"] > 50
        assert len(result["timeframe_scores"]) == 1

    def test_multi_timeframe_bullish_alignment(self):
        """多周期多头对齐应加分"""
        mtf = {
            "1h": {"trend": "bullish", "macd": {"signal": "bullish"}},
            "4h": {"trend": "bullish", "macd": {"signal": "golden_cross"}},
            "1d": {"trend": "bullish", "macd": {"signal": "bullish"}},
        }
        result = score_multi_timeframe(mtf)
        assert result["score"] > 60
        assert result["alignment"]["alignment_score"] > 0.5

    def test_multi_timeframe_bearish_alignment(self):
        """多周期空头对齐应减分"""
        mtf = {
            "1h": {"trend": "bearish", "macd": {"signal": "death_cross"}},
            "4h": {"trend": "bearish", "macd": {"signal": "bearish"}},
            "1d": {"trend": "bearish", "macd": {"signal": "bearish"}},
        }
        result = score_multi_timeframe(mtf)
        assert result["score"] < 40
        assert result["alignment"]["alignment_score"] < -0.5

    def test_conflicting_timeframes(self):
        """周期间信号冲突应趋于中性"""
        mtf = {
            "1h": {"trend": "bullish", "macd": {"signal": "golden_cross"}},
            "4h": {"trend": "bearish", "macd": {"signal": "death_cross"}},
            "1d": {"trend": "sideways", "macd": {"signal": "neutral"}},
        }
        result = score_multi_timeframe(mtf)
        assert 40 <= result["score"] <= 60
        assert abs(result["alignment"]["alignment_score"]) < 0.5

    def test_timeframe_weights_applied(self):
        """验证不同周期权重差异"""
        # 只有日线金叉
        daily_only = {"1d": {"trend": "bullish", "macd": {"signal": "golden_cross"}}}
        # 只有1分钟金叉
        minute_only = {"1m": {"trend": "bullish", "macd": {"signal": "golden_cross"}}}

        daily_result = score_multi_timeframe(daily_only)
        minute_result = score_multi_timeframe(minute_only)

        # 日线信号应该更强（权重更高的信号分数更高）
        # 注意：由于归一化，单一周期的分数会被放大，但日线的基础分更高
        assert daily_result["timeframe_scores"]["1d"]["score"] > minute_result["timeframe_scores"]["1m"]["score"]


class TestCZCESwitchPeriod:
    """郑商所移仓敏感期降权测试"""

    def test_czce_in_switch_period_reduces_score(self):
        """郑商所品种在移仓期内，评分应向中性收敛"""
        from kairos.scoring.adaptive import score_with_adaptive_weights
        from datetime import datetime

        bullish_indicators = {
            "trend": "bullish",
            "macd": {"signal": "golden_cross"},
            "kdj": {"zone": "oversold"}, "rsi": {"zone": "oversold"},
            "adx": {"strength": "strong", "direction": "bullish"},
            "obv": {"signal": "bullish", "momentum": 15}
        }

        # 模拟郑商所品种在移仓期内
        czce_config = {
            "exchange": "CZCE",
            "contract_switch_date": datetime.now().strftime("%Y-%m-%d"),  # 今天切换
        }

        # 非移仓期（非CZCE）
        normal_config = {"exchange": "SHFE"}

        result_switch = score_with_adaptive_weights(bullish_indicators, contract_config=czce_config)
        result_normal = score_with_adaptive_weights(bullish_indicators, contract_config=normal_config)

        # 移仓期评分应更接近50
        assert abs(result_switch["score"] - 50) < abs(result_normal["score"] - 50)
        assert any("移仓敏感期" in s for s in result_switch["signals"])

    def test_non_czce_not_affected(self):
        """非郑商所品种不受移仓期影响"""
        from kairos.scoring.adaptive import score_with_adaptive_weights
        from datetime import datetime

        bullish_indicators = {"trend": "bullish", "macd": {"signal": "golden_cross"}}

        # 非CZCE品种即使有切换日期也不受影响
        shfe_config = {
            "exchange": "SHFE",
            "contract_switch_date": datetime.now().strftime("%Y-%m-%d"),
        }

        result = score_with_adaptive_weights(bullish_indicators, contract_config=shfe_config)
        assert not any("移仓敏感期" in s for s in result["signals"])
