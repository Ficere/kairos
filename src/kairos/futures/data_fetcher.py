"""期货数据获取模块"""
import akshare as ak
import pandas as pd
from kairos.futures.config import CONTRACTS, MarketData


def get_realtime_data() -> dict[str, MarketData]:
    """获取实时行情数据 - 尝试多种方式"""
    print("=" * 60)
    print("正在获取期货实时行情数据...")
    print("=" * 60)

    result = {}

    try:
        spot_df = ak.futures_zh_realtime(symbol="全部")
        for contract_id, config in CONTRACTS.items():
            symbol_upper = config["symbol"].upper()
            matched = spot_df[spot_df['代码'].str.upper() == symbol_upper]

            if not matched.empty:
                row = matched.iloc[0]
                result[contract_id] = MarketData(
                    symbol=contract_id, name=config["name"],
                    current_price=float(row.get('最新价', 0)),
                    open_price=float(row.get('今开', 0)),
                    high_price=float(row.get('最高', 0)),
                    low_price=float(row.get('最低', 0)),
                    volume=int(row.get('成交量', 0)),
                    open_interest=int(row.get('持仓量', 0)),
                    change_pct=float(row.get('涨跌幅', 0)),
                )
                print(f"✓ {contract_id} ({config['name']}) 实时数据获取成功")
    except Exception as e:
        print(f"东方财富实时数据获取异常: {e}")

    return result


def get_historical_data(contract_id: str, days: int = 15, use_real_contract: bool = True) -> pd.DataFrame:
    """获取历史行情数据

    Args:
        contract_id: 合约ID（如 J0）
        days: 获取天数
        use_real_contract: 是否优先使用真实主力合约数据（避免连续合约价格跳空导致指标失真）
    """
    config = CONTRACTS.get(contract_id)
    if not config:
        return pd.DataFrame()

    symbol = config["symbol"]
    main_contract = config.get("main_contract", "")

    # 优先获取真实主力合约数据（避免连续合约换月跳空导致 MACD 等指标失真）
    if use_real_contract and main_contract and not main_contract.endswith("0"):
        try:
            df = ak.futures_zh_daily_sina(symbol=main_contract.lower())
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "date", "开盘价": "open", "最高价": "high",
                    "最低价": "low", "收盘价": "close", "成交量": "volume", "持仓量": "hold"
                })
                if len(df) >= days:
                    return df.tail(days)
        except Exception as e:
            print(f"获取真实合约 {main_contract} 数据失败，回退到连续合约: {e}")

    # 回退：主力连续合约（XX0 格式）
    if symbol.upper().endswith("0"):
        try:
            df = ak.futures_main_sina(symbol=symbol.lower(), start_date="20240101", end_date="20261231")
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "date", "开盘价": "open", "最高价": "high",
                    "最低价": "low", "收盘价": "close", "成交量": "volume", "持仓量": "hold"
                })
                return df.tail(days)
        except Exception as e:
            print(f"获取主力连续数据失败: {e}")
    else:
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df is not None and not df.empty:
                return df.tail(days)
        except Exception as e:
            print(f"获取历史数据失败: {e}")

    return pd.DataFrame()


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
        # 使用新浪分钟线接口
        df = ak.futures_zh_minute_sina(symbol=symbol.lower(), period=period)
        if df is not None and not df.empty:
            df = df.rename(columns={
                "datetime": "date", "open": "open", "high": "high",
                "low": "low", "close": "close", "volume": "volume"
            })
            return df.tail(100)  # 保留最近100根K线
    except Exception as e:
        print(f"获取{period}分钟数据失败({contract_id}): {e}")
    return pd.DataFrame()


def get_multi_timeframe_data(contract_id: str) -> dict[str, pd.DataFrame]:
    """获取多周期K线数据

    Returns:
        字典，key为周期("1m","5m","15m","1h","4h","1d")，value为DataFrame
    """
    result = {}

    # 日线数据
    daily = get_historical_data(contract_id, days=60)
    if not daily.empty:
        result["1d"] = daily

    # 分钟线数据（period参数映射）
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


def get_market_data_with_history(contract_id: str, config: dict,
                                  realtime: dict) -> tuple[MarketData | None, pd.DataFrame]:
    """获取市场数据和历史数据的组合"""
    hist_df = get_historical_data(contract_id)

    if contract_id not in realtime and not hist_df.empty:
        last_row = hist_df.iloc[-1]
        market_data = MarketData(
            symbol=contract_id, name=config["name"],
            current_price=float(last_row['close']),
            open_price=float(last_row['open']),
            high_price=float(last_row['high']),
            low_price=float(last_row['low']),
            volume=int(last_row.get('volume', 0)),
            open_interest=int(last_row.get('hold', 0)),
            change_pct=0.0, hist_data=hist_df,
        )
        return market_data, hist_df

    if contract_id in realtime:
        market_data = realtime[contract_id]
        market_data.hist_data = hist_df
        return market_data, hist_df

    return None, hist_df

