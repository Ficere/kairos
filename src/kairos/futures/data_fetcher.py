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


def get_historical_data(contract_id: str, days: int = 15) -> pd.DataFrame:
    """获取历史行情数据"""
    config = CONTRACTS.get(contract_id)
    if not config:
        return pd.DataFrame()

    symbol = config["symbol"]

    # 主力连续合约（XX0 格式）使用 futures_main_sina（需要小写）
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

