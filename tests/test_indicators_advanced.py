"""测试高级技术指标计算 - OBV 和 ADX"""
import pytest
import pandas as pd
import numpy as np
from kairos.futures.indicators_advanced import calc_obv, calc_adx


@pytest.fixture
def sample_data():
    """生成测试用 K 线数据"""
    np.random.seed(42)
    n = 30
    close = pd.Series(100 + np.cumsum(np.random.randn(n) * 2))
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = pd.Series(np.random.randint(1000, 5000, n))
    return {"close": close, "high": high, "low": low, "volume": volume}


class TestCalcOBV:
    """OBV 能量潮指标测试"""

    def test_obv_returns_required_keys(self, sample_data):
        """测试返回必要的键"""
        result = calc_obv(sample_data["close"], sample_data["volume"])
        assert "obv" in result
        assert "obv_ma" in result
        assert "signal" in result
        assert "momentum" in result

    def test_obv_signal_bullish_or_bearish(self, sample_data):
        """测试信号只能是 bullish 或 bearish"""
        result = calc_obv(sample_data["close"], sample_data["volume"])
        assert result["signal"] in ["bullish", "bearish"]

    def test_obv_with_uptrend(self):
        """测试上升趋势的 OBV"""
        # 创建持续上涨的价格序列
        close = pd.Series([100 + i for i in range(20)])
        volume = pd.Series([1000] * 20)
        result = calc_obv(close, volume)
        # 持续上涨应该累积正 OBV
        assert result["obv"] > 0
        assert result["signal"] == "bullish"

    def test_obv_with_downtrend(self):
        """测试下降趋势的 OBV"""
        close = pd.Series([120 - i for i in range(20)])
        volume = pd.Series([1000] * 20)
        result = calc_obv(close, volume)
        # 持续下跌应该累积负 OBV
        assert result["obv"] < 0
        assert result["signal"] == "bearish"


class TestCalcADX:
    """ADX 趋势强度指标测试"""

    def test_adx_returns_required_keys(self, sample_data):
        """测试返回必要的键"""
        result = calc_adx(sample_data["high"], sample_data["low"], sample_data["close"])
        assert "adx" in result
        assert "plus_di" in result
        assert "minus_di" in result
        assert "strength" in result
        assert "direction" in result

    def test_adx_strength_values(self, sample_data):
        """测试强度值只能是 strong/moderate/weak"""
        result = calc_adx(sample_data["high"], sample_data["low"], sample_data["close"])
        assert result["strength"] in ["strong", "moderate", "weak"]

    def test_adx_direction_values(self, sample_data):
        """测试方向只能是 bullish 或 bearish"""
        result = calc_adx(sample_data["high"], sample_data["low"], sample_data["close"])
        assert result["direction"] in ["bullish", "bearish"]

    def test_adx_range(self, sample_data):
        """测试 ADX 值在合理范围内 (0-100)"""
        result = calc_adx(sample_data["high"], sample_data["low"], sample_data["close"])
        assert 0 <= result["adx"] <= 100

    def test_adx_strong_trend(self):
        """测试强趋势检测"""
        # 创建强趋势数据：每天价格上涨，波动小
        n = 30
        base = [100 + i * 2 for i in range(n)]
        high = pd.Series([b + 0.5 for b in base])
        low = pd.Series([b - 0.5 for b in base])
        close = pd.Series(base)
        result = calc_adx(high, low, close)
        # 强趋势 ADX 通常 > 25
        assert result["adx"] > 20
        assert result["direction"] == "bullish"

    def test_adx_insufficient_data(self):
        """测试数据不足时返回默认值"""
        # 只有 20 条数据，不足 29 条
        n = 20
        base = [100 + i for i in range(n)]
        high = pd.Series([b + 1 for b in base])
        low = pd.Series([b - 1 for b in base])
        close = pd.Series(base)
        result = calc_adx(high, low, close)
        # 数据不足应返回默认值
        assert result["adx"] == 20.0
        assert result["strength"] == "weak"
        assert result["direction"] == "neutral"

    def test_adx_no_nan(self):
        """测试返回值不包含 NaN"""
        np.random.seed(42)
        n = 35  # 足够的数据
        close = pd.Series(100 + np.cumsum(np.random.randn(n) * 2))
        high = close + np.abs(np.random.randn(n))
        low = close - np.abs(np.random.randn(n))
        result = calc_adx(high, low, close)
        # 确保没有 NaN
        assert not np.isnan(result["adx"])
        assert not np.isnan(result["plus_di"])
        assert not np.isnan(result["minus_di"])

