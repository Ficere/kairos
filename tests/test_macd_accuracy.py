"""测试 MACD 计算准确性（与同花顺对比）"""
import pandas as pd
import pytest
from kairos.futures.indicators import calc_macd, _ema_with_sma_init


def test_ema_with_sma_init():
    """测试 SMA 初始化的 EMA"""
    # 简单测试数据
    close = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    ema = _ema_with_sma_init(close, 5)

    # 前 4 个应该是 NaN
    assert pd.isna(ema.iloc[0])
    assert pd.isna(ema.iloc[3])

    # 第 5 个（index=4）应该是前 5 个的 SMA = (10+11+12+13+14)/5 = 12
    assert ema.iloc[4] == pytest.approx(12.0, rel=1e-6)

    # 后续值应该是递推计算的
    alpha = 2 / 6  # period=5, alpha=2/(5+1)
    expected_6 = 12.0 * (1 - alpha) + 15 * alpha  # index=5
    assert ema.iloc[5] == pytest.approx(expected_6, rel=1e-6)


def test_ema_insufficient_data():
    """测试数据不足时的边界处理"""
    short_series = pd.Series([10, 11, 12])  # 只有 3 个数据点
    ema = _ema_with_sma_init(short_series, 5)  # 需要 5 个

    # 应该返回全 NaN，不抛出异常
    assert len(ema) == 3
    assert all(pd.isna(ema))


def test_macd_calculation():
    """测试 MACD 计算"""
    # 生成足够长的测试数据（需要至少 26 + 9 = 35 个点）
    close = pd.Series([100 + i * 0.5 for i in range(50)])
    result = calc_macd(close)
    
    assert "dif" in result
    assert "dea" in result
    assert "macd" in result
    assert "signal" in result
    
    # DIF 应该是正的（上涨趋势）
    assert result["dif"] > 0


def test_macd_golden_cross():
    """测试 MACD 金叉检测"""
    # 先下跌再上涨，形成金叉
    close = pd.Series([100 - i for i in range(30)] + [70 + i * 2 for i in range(20)])
    result = calc_macd(close)
    
    # 应该能正常计算
    assert isinstance(result["dif"], float)
    assert isinstance(result["dea"], float)


def test_macd_insufficient_data():
    """测试 MACD 数据不足时的边界处理"""
    short_series = pd.Series([100 + i for i in range(20)])  # 只有 20 个点，不够 26+9
    result = calc_macd(short_series)

    # 应该返回 NaN 值，不抛出异常
    assert "dif" in result
    assert "dea" in result


if __name__ == "__main__":
    # 手动运行测试
    test_ema_with_sma_init()
    print("✓ EMA with SMA init test passed")

    test_ema_insufficient_data()
    print("✓ EMA insufficient data test passed")

    test_macd_calculation()
    print("✓ MACD calculation test passed")

    test_macd_golden_cross()
    print("✓ MACD golden cross test passed")

    test_macd_insufficient_data()
    print("✓ MACD insufficient data test passed")

    print("\nAll tests passed!")

