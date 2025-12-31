"""分钟级和多周期K线数据获取模块"""
import akshare as ak
import pandas as pd
from kairos.futures.config import CONTRACTS


def get_intraday_data(contract_id: str, period: str = "15") -> pd.DataFrame:
    """获取分钟级K线数据

    Args:
        contract_id: 合约ID
        period: K线周期，支持 "1"(1分钟)、"5"、"15"、"30"、"60"(1小时)

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
    """
    config = CONTRACTS.get(contract_id)
    if not config:
        return pd.DataFrame()

    symbol = config["symbol"]
    try:
        df = ak.futures_zh_minute_sina(symbol=symbol.lower(), period=period)
        if df is not None and not df.empty:
            df = df.rename(columns={
                "datetime": "date", "open": "open", "high": "high",
                "low": "low", "close": "close", "volume": "volume"
            })
            return df.tail(100)
    except Exception as e:
        print(f"获取{period}分钟数据失败({contract_id}): {e}")
    return pd.DataFrame()


def get_multi_timeframe_data(contract_id: str) -> dict[str, pd.DataFrame]:
    """获取多周期K线数据

    Returns:
        字典，key为周期("1m","5m","15m","1h","4h","1d")，value为DataFrame
    """
    from kairos.futures.data_fetcher import get_historical_data
    
    result = {}

    # 日线数据
    daily = get_historical_data(contract_id, days=60)
    if not daily.empty:
        result["1d"] = daily

    # 分钟线数据
    period_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
    for tf, period in period_map.items():
        df = get_intraday_data(contract_id, period)
        if not df.empty:
            result[tf] = df

    # 4小时线由1小时线合成
    if "1h" in result and len(result["1h"]) >= 4:
        result["4h"] = _resample_to_4h(result["1h"])

    return result


def _resample_to_4h(df_1h: pd.DataFrame) -> pd.DataFrame:
    """将1小时K线合成4小时K线"""
    if df_1h.empty:
        return pd.DataFrame()
    df = df_1h.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    resampled = df.resample("4h").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "volume": "sum"
    }).dropna()
    return resampled.reset_index()

