"""Tushare 期货数据源模块"""
import os
import pandas as pd
from datetime import datetime, timedelta

# Tushare API 初始化（延迟导入避免未安装时报错）
_ts_api = None
_ts_available = None


def is_tushare_available() -> bool:
    """检查 Tushare 是否可用（已安装且配置了 token）"""
    global _ts_available, _ts_api
    if _ts_available is not None:
        return _ts_available
    
    token = os.environ.get("TUSHARE_TOKEN", "")
    if not token:
        _ts_available = False
        return False
    
    try:
        import tushare as ts
        ts.set_token(token)
        _ts_api = ts.pro_api()
        # 简单测试 API 是否可用
        _ts_api.trade_cal(exchange='DCE', start_date='20240101', end_date='20240101')
        _ts_available = True
        print("✓ Tushare 数据源已启用")
    except Exception as e:
        print(f"⚠️ Tushare 初始化失败: {e}")
        _ts_available = False
    
    return _ts_available


def _get_api():
    """获取 Tushare API 实例"""
    global _ts_api
    if _ts_api is None:
        is_tushare_available()
    return _ts_api


def _convert_ts_code(variety: str, exchange: str) -> str:
    """将品种代码转换为 Tushare 格式 (如 J.DCE)"""
    exchange_map = {"大商所": "DCE", "郑商所": "CZCE", "上期所": "SHFE", "中金所": "CFFEX", "上海能源": "INE"}
    ts_exchange = exchange_map.get(exchange, "DCE")
    return f"{variety.upper()}.{ts_exchange}"


def get_realtime_tushare(contracts: dict) -> dict:
    """从 Tushare 获取实时行情数据
    
    注意：Tushare 期货实时行情需要较高权限，此函数主要用于日线数据
    """
    # Tushare 免费版不支持实时行情，返回空
    return {}


def get_historical_tushare(variety: str, exchange: str, days: int = 60) -> pd.DataFrame:
    """从 Tushare 获取历史日线数据
    
    Args:
        variety: 品种代码（如 J, RB）
        exchange: 交易所名称（如 大商所, 上期所）
        days: 获取天数
    
    Returns:
        标准格式的 DataFrame，包含 date, open, high, low, close, volume, hold 列
    """
    api = _get_api()
    if api is None:
        return pd.DataFrame()
    
    try:
        ts_code = _convert_ts_code(variety, exchange)
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days + 30)).strftime("%Y%m%d")
        
        # 获取主力合约映射
        mapping = api.fut_mapping(ts_code=ts_code)
        if mapping is None or mapping.empty:
            return pd.DataFrame()
        
        # 获取当前主力合约代码
        main_contract = mapping.iloc[0]["mapping_ts_code"]
        
        # 获取日线数据
        df = api.fut_daily(ts_code=main_contract, start_date=start_date, end_date=end_date)
        if df is None or df.empty:
            return pd.DataFrame()
        
        # 转换为标准格式
        df = df.rename(columns={
            "trade_date": "date",
            "open": "open",
            "high": "high", 
            "low": "low",
            "close": "close",
            "vol": "volume",
            "oi": "hold"
        })
        
        # 转换日期格式
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
        df = df.sort_values("date").reset_index(drop=True)
        
        # 只保留需要的列
        columns = ["date", "open", "high", "low", "close", "volume", "hold"]
        df = df[[c for c in columns if c in df.columns]]
        
        return df.tail(days)
        
    except Exception as e:
        print(f"⚠️ Tushare 获取 {variety} 历史数据失败: {e}")
        return pd.DataFrame()


def get_main_contract_tushare(variety: str, exchange: str) -> str | None:
    """从 Tushare 获取当前主力合约代码"""
    api = _get_api()
    if api is None:
        return None
    
    try:
        ts_code = _convert_ts_code(variety, exchange)
        mapping = api.fut_mapping(ts_code=ts_code)
        if mapping is not None and not mapping.empty:
            # 返回格式如 J2505.DCE -> J2505
            full_code = mapping.iloc[0]["mapping_ts_code"]
            return full_code.split(".")[0]
    except Exception:
        pass
    return None

