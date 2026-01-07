"""主力连续合约数据处理模块

构建包含主力合约代码的连续价格序列，处理移仓换月问题。
数据结构：每日记录当日主力合约号，支持前复权和收益率修正。
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# 连续合约数据存储目录
CONTINUOUS_DIR = Path("data/continuous")


def get_continuous_path(variety: str) -> Path:
    """获取品种的连续合约数据路径"""
    CONTINUOUS_DIR.mkdir(parents=True, exist_ok=True)
    return CONTINUOUS_DIR / f"{variety.upper()}.parquet"


def detect_switch_days(df: pd.DataFrame) -> pd.DataFrame:
    """检测主力合约切换日并计算调整因子

    Args:
        df: 必须包含 date, main_contract, close 列

    Returns:
        添加了 is_switch_day, switch_ratio, adj_factor 列的 DataFrame
    """
    df = df.copy().sort_values("date").reset_index(drop=True)

    # 检测合约切换
    df["prev_contract"] = df["main_contract"].shift(1)
    df["is_switch_day"] = (df["main_contract"] != df["prev_contract"]) & df["prev_contract"].notna()

    # 计算切换日的价格比率（新合约收盘价 / 旧合约前一日收盘价的估算）
    # 注意：理想情况下应该用切换日两个合约的价格，这里简化处理
    df["switch_ratio"] = 1.0
    df.loc[df["is_switch_day"], "switch_ratio"] = df["close"] / df["close"].shift(1)

    # 累计复权因子（从最新日期向前累乘）
    df["adj_factor"] = 1.0
    switch_indices = df[df["is_switch_day"]].index.tolist()

    # 从后向前计算累计调整因子
    cumulative = 1.0
    for i in range(len(df) - 1, -1, -1):
        if i in switch_indices:
            cumulative *= df.loc[i, "switch_ratio"]
        df.loc[i, "adj_factor"] = cumulative

    df.drop(columns=["prev_contract"], inplace=True)
    return df


def calc_adjusted_prices(df: pd.DataFrame) -> pd.DataFrame:
    """计算前复权价格和修正后的对数收益率

    Args:
        df: 必须包含 adj_factor, close, open, high, low 列

    Returns:
        添加了 adj_close, adj_open, adj_high, adj_low, log_return 列的 DataFrame
    """
    df = df.copy()

    # 前复权价格
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[f"adj_{col}"] = df[col] / df["adj_factor"]

    # 对数收益率（使用复权价格，避免换月跳跃）
    df["log_return"] = np.log(df["adj_close"] / df["adj_close"].shift(1))
    df.loc[0, "log_return"] = 0  # 第一天无收益率

    return df


def build_continuous_series(
    variety: str,
    daily_data: pd.DataFrame,
    main_contract_col: str = "main_contract"
) -> pd.DataFrame:
    """构建单品种的主力连续合约序列

    Args:
        variety: 品种代码 (CU, AU, ...)
        daily_data: 包含 date, main_contract, OHLCV 的原始数据
        main_contract_col: 主力合约列名

    Returns:
        完整的连续合约 DataFrame
    """
    required_cols = ["date", main_contract_col, "open", "high", "low", "close", "volume"]
    missing = [c for c in required_cols if c not in daily_data.columns]
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    df = daily_data.copy()
    df["variety"] = variety.upper()
    df.rename(columns={main_contract_col: "main_contract"}, inplace=True)

    # 确保日期格式
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 检测换月日并计算调整因子
    df = detect_switch_days(df)

    # 计算复权价格和收益率
    df = calc_adjusted_prices(df)

    return df


def save_continuous_data(variety: str, df: pd.DataFrame):
    """保存连续合约数据为 Parquet 格式"""
    path = get_continuous_path(variety)
    df.to_parquet(path, index=False)


def load_continuous_data(variety: str) -> pd.DataFrame:
    """加载连续合约数据"""
    path = get_continuous_path(variety)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def get_volume_weight(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """计算成交量权重（用于模型训练）

    低成交量时段降低权重，避免流动性不足导致的噪声。
    """
    avg_vol = df["volume"].rolling(window, min_periods=1).mean()
    weight = df["volume"] / avg_vol
    return weight.clip(0.5, 2.0)  # 限制权重范围


def get_oi_momentum(df: pd.DataFrame, period: int = 5) -> pd.Series:
    """计算持仓量动量（用于多空力量判断）

    持仓量增加 + 价格上涨 = 多头增仓
    持仓量增加 + 价格下跌 = 空头增仓
    """
    if "open_interest" not in df.columns:
        return pd.Series(0, index=df.index)

    oi_change = df["open_interest"].pct_change(period)
    price_change = df["close"].pct_change(period)

    # 正值=多头主导，负值=空头主导
    return oi_change * np.sign(price_change)

