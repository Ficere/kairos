"""市场状态过滤器测试"""
import pytest
import pandas as pd
import numpy as np
from kairos.scoring.market_filter import (
    calc_volume_oi_metrics, detect_market_state, score_market_state, MarketState
)


def make_test_df(
    price_trend: str = "up",
    vol_amplify: bool = False,
    oi_trend: str = "up",
    days: int = 10
) -> pd.DataFrame:
    """构造测试用 DataFrame

    注意：需要确保生成的数据能够满足阈值条件：
    - 价格变化 > 2% (up) 或 < -2% (down)
    - 成交量放大 > 1.5 倍
    - 持仓量变化 > 3% (up) 或 < -3% (down)
    """
    base_price = 100
    base_vol = 1000
    base_oi = 50000

    dates = pd.date_range("2025-01-01", periods=days, freq="D")

    # 价格趋势（确保前5日和后5日均值差 > 2%）
    if price_trend == "up":
        # 前5天均价约95，后5天均价约105，变化约10%
        prices = np.concatenate([
            np.linspace(base_price * 0.93, base_price * 0.97, days // 2),
            np.linspace(base_price * 1.03, base_price * 1.07, days - days // 2)
        ])
    elif price_trend == "down":
        prices = np.concatenate([
            np.linspace(base_price * 1.07, base_price * 1.03, days // 2),
            np.linspace(base_price * 0.97, base_price * 0.93, days - days // 2)
        ])
    else:  # sideways - 波动小于1.5%
        np.random.seed(42)
        prices = base_price + np.random.uniform(-0.5, 0.5, days)

    # 成交量（前5天低量，后5天高量，确保比值 > 1.5）
    if vol_amplify:
        volumes = np.concatenate([
            np.full(days // 2, base_vol * 0.6),       # 前半段低量
            np.full(days - days // 2, base_vol * 2.0) # 后半段放量2倍
        ])
    else:
        volumes = np.full(days, base_vol)

    # 持仓量（确保最近5日变化 > 3%）
    if oi_trend == "up":
        # 最后5日增加约5%
        ois = np.concatenate([
            np.full(days // 2, base_oi),
            np.linspace(base_oi, base_oi * 1.08, days - days // 2)
        ])
    elif oi_trend == "down":
        ois = np.concatenate([
            np.full(days // 2, base_oi),
            np.linspace(base_oi, base_oi * 0.92, days - days // 2)
        ])
    else:  # sideways
        ois = np.full(days, base_oi)

    return pd.DataFrame({
        "date": dates,
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "volume": volumes,
        "hold": ois,
    })


class TestCalcVolumeOiMetrics:
    """量价仓指标计算测试"""

    def test_empty_df(self):
        """空数据应返回无效"""
        result = calc_volume_oi_metrics(pd.DataFrame())
        assert result["valid"] is False

    def test_insufficient_data(self):
        """数据不足应返回无效"""
        df = make_test_df(days=5)
        result = calc_volume_oi_metrics(df, lookback=10)
        assert result["valid"] is False

    def test_valid_metrics_calculation(self):
        """正常数据应返回有效指标"""
        df = make_test_df(price_trend="up", vol_amplify=True, oi_trend="up", days=15)
        result = calc_volume_oi_metrics(df, lookback=10)
        
        assert result["valid"] is True
        assert "price_change_pct" in result
        assert "vol_ratio" in result
        assert "oi_change_pct" in result
        assert result["price_change_pct"] > 0  # 上涨


class TestDetectMarketState:
    """市场状态检测测试"""

    def test_valid_breakout(self):
        """真突破：价涨+放量+增仓"""
        df = make_test_df(price_trend="up", vol_amplify=True, oi_trend="up")
        metrics = calc_volume_oi_metrics(df)
        state, desc = detect_market_state(metrics)
        assert state == MarketState.VALID_BREAKOUT

    def test_short_covering(self):
        """空头回补：价涨+放量+减仓"""
        df = make_test_df(price_trend="up", vol_amplify=True, oi_trend="down")
        metrics = calc_volume_oi_metrics(df)
        state, desc = detect_market_state(metrics)
        assert state == MarketState.SHORT_COVERING

    def test_long_liquidation(self):
        """多头踩踏：价跌+放量+减仓"""
        df = make_test_df(price_trend="down", vol_amplify=True, oi_trend="down")
        metrics = calc_volume_oi_metrics(df)
        state, desc = detect_market_state(metrics)
        assert state == MarketState.LONG_LIQUIDATION

    def test_accumulation(self):
        """低位吸筹：横盘+稳量+增仓"""
        df = make_test_df(price_trend="sideways", vol_amplify=False, oi_trend="up")
        metrics = calc_volume_oi_metrics(df)
        state, desc = detect_market_state(metrics)
        assert state == MarketState.ACCUMULATION

    def test_normal_state(self):
        """正常状态：无明显特征"""
        df = make_test_df(price_trend="sideways", vol_amplify=False, oi_trend="sideways")
        metrics = calc_volume_oi_metrics(df)
        state, desc = detect_market_state(metrics)
        assert state == MarketState.NORMAL


class TestScoreMarketState:
    """市场状态评分测试"""

    def test_valid_breakout_bullish(self):
        """真突破对多头信号加分"""
        score, signal = score_market_state(MarketState.VALID_BREAKOUT, "bullish")
        assert score > 0
        assert "真突破" in signal

    def test_short_covering_bullish(self):
        """空头回补对多头信号减分"""
        score, signal = score_market_state(MarketState.SHORT_COVERING, "bullish")
        assert score < 0
        assert "空头回补" in signal

    def test_long_liquidation_bearish(self):
        """多头踩踏对空头信号减分"""
        score, signal = score_market_state(MarketState.LONG_LIQUIDATION, "bearish")
        assert score < 0

    def test_accumulation_bullish(self):
        """低位吸筹对多头信号加分"""
        score, signal = score_market_state(MarketState.ACCUMULATION, "bullish")
        assert score > 0
        assert "低位吸筹" in signal

    def test_normal_state_no_signal(self):
        """正常状态无信号"""
        score, signal = score_market_state(MarketState.NORMAL, "bullish")
        assert score == 0
        assert signal is None

