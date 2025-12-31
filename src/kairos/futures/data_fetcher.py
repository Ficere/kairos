"""期货数据获取模块 - 支持 Tushare 和新浪财经双数据源，带增量缓存"""
import akshare as ak
import pandas as pd
from kairos.futures.config import CONTRACTS, MarketData
from kairos.futures.data_tushare import is_tushare_available, get_historical_tushare
from kairos.futures.daily_cache import get_cached_or_fetch, get_missing_days

# 向后兼容：从 data_intraday 模块重新导出
from kairos.futures.data_intraday import get_intraday_data, get_multi_timeframe_data


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


def _fetch_historical_raw(contract_id: str, days: int) -> pd.DataFrame:
    """从 API 获取原始历史数据（内部函数，供缓存系统调用）"""
    config = CONTRACTS.get(contract_id)
    if not config:
        return pd.DataFrame()

    variety = config.get("variety", contract_id.replace("0", ""))
    exchange = config.get("exchange", "")

    # 优先使用 Tushare
    if is_tushare_available():
        df = get_historical_tushare(variety, exchange, days)
        if not df.empty:
            return df

    # 备用：新浪财经
    return _get_historical_sina(config, days, True)


def get_historical_data(contract_id: str, days: int = 15, use_cache: bool = True) -> pd.DataFrame:
    """获取历史行情数据（带增量缓存）

    数据源优先级：
    1. 本地缓存（增量更新）
    2. Tushare（如果配置了 TUSHARE_TOKEN）
    3. 新浪财经（备用数据源）
    """
    if not use_cache:
        return _fetch_historical_raw(contract_id, days)

    # 使用增量缓存
    missing = get_missing_days(contract_id, days)
    if missing == 0:
        # 缓存已是最新，直接使用
        from kairos.futures.daily_cache import load_cached_daily
        cached = load_cached_daily(contract_id)
        if len(cached) >= 20:  # 确保有足够数据
            return cached.tail(days)

    # 增量获取并更新缓存
    return get_cached_or_fetch(contract_id, _fetch_historical_raw, days)


def _get_historical_sina(config: dict, days: int, use_real_contract: bool) -> pd.DataFrame:
    """从新浪财经获取历史数据（内部函数）"""
    symbol = config["symbol"]
    main_contract = config.get("main_contract", "")
    exchange = config.get("exchange", "")

    # 郑商所(CZCE)的真实合约接口不可用，跳过
    skip_real = exchange == "CZCE"

    # 优先获取真实主力合约数据
    if use_real_contract and main_contract and not main_contract.endswith("0") and not skip_real:
        try:
            df = ak.futures_zh_daily_sina(symbol=main_contract.lower())
            if df is not None and not df.empty:
                df = df.rename(columns={
                    "日期": "date", "开盘价": "open", "最高价": "high",
                    "最低价": "low", "收盘价": "close", "成交量": "volume", "持仓量": "hold"
                })
                if len(df) >= days:
                    return df.tail(days)
        except Exception:
            pass  # 静默回退到连续合约

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

