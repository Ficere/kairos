"""原始市场数据缓存模块

用于保存和加载原始K线数据，支持技术面重算功能。
缓存数据保存在 plans/YYYY-MM-DD/raw_data/ 目录下。
"""
import os
import json
from pathlib import Path
from datetime import datetime
import pandas as pd


def get_cache_dir(date_str: str | None = None) -> Path:
    """获取缓存数据目录
    
    Args:
        date_str: 日期字符串 (YYYY-MM-DD)，默认使用当天
    
    Returns:
        缓存目录路径
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    return Path("plans") / date_str / "raw_data"


def save_historical_data(contract_id: str, df: pd.DataFrame, date_str: str | None = None) -> Path:
    """保存历史K线数据到缓存
    
    Args:
        contract_id: 合约ID (如 CU0, AU0)
        df: K线数据 DataFrame
        date_str: 日期字符串，默认当天
    
    Returns:
        保存的文件路径
    """
    cache_dir = get_cache_dir(date_str)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = cache_dir / f"{contract_id}_daily.csv"
    df.to_csv(file_path, index=False, encoding="utf-8")
    return file_path


def save_multi_timeframe_data(contract_id: str, mtf_data: dict[str, pd.DataFrame], 
                               date_str: str | None = None) -> dict[str, Path]:
    """保存多周期K线数据到缓存
    
    Args:
        contract_id: 合约ID
        mtf_data: 多周期数据字典 {timeframe: DataFrame}
        date_str: 日期字符串
    
    Returns:
        保存的文件路径字典
    """
    cache_dir = get_cache_dir(date_str)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    saved_paths = {}
    for timeframe, df in mtf_data.items():
        if df is not None and not df.empty:
            file_path = cache_dir / f"{contract_id}_{timeframe}.csv"
            df.to_csv(file_path, index=False, encoding="utf-8")
            saved_paths[timeframe] = file_path
    return saved_paths


def load_historical_data(contract_id: str, date_str: str) -> pd.DataFrame | None:
    """从缓存加载历史K线数据
    
    Args:
        contract_id: 合约ID
        date_str: 日期字符串
    
    Returns:
        K线数据 DataFrame 或 None
    """
    cache_dir = get_cache_dir(date_str)
    file_path = cache_dir / f"{contract_id}_daily.csv"
    
    if not file_path.exists():
        return None
    
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
        # 确保日期列正确解析
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception as e:
        print(f"⚠️ 加载缓存数据失败 ({contract_id}): {e}")
        return None


def load_multi_timeframe_data(contract_id: str, date_str: str) -> dict[str, pd.DataFrame]:
    """从缓存加载多周期K线数据
    
    Args:
        contract_id: 合约ID
        date_str: 日期字符串
    
    Returns:
        多周期数据字典
    """
    cache_dir = get_cache_dir(date_str)
    result = {}
    
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    for tf in timeframes:
        file_path = cache_dir / f"{contract_id}_{tf}.csv"
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, encoding="utf-8")
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])
                result[tf] = df
            except Exception:
                continue
    
    return result


def has_cached_data(contract_id: str, date_str: str) -> bool:
    """检查是否存在缓存数据"""
    cache_dir = get_cache_dir(date_str)
    daily_file = cache_dir / f"{contract_id}_daily.csv"
    return daily_file.exists()


def list_cached_contracts(date_str: str) -> list[str]:
    """列出指定日期的所有缓存合约"""
    cache_dir = get_cache_dir(date_str)
    if not cache_dir.exists():
        return []
    
    contracts = set()
    for f in cache_dir.glob("*_daily.csv"):
        contract_id = f.stem.replace("_daily", "")
        contracts.add(contract_id)
    return sorted(contracts)

