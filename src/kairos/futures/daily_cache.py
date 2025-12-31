"""持久化日线数据缓存模块 - 支持增量更新

缓存数据保存在 data/daily_cache/ 目录下，每个合约一个 CSV 文件。
实现增量获取：只下载本地缓存中缺失的日期数据。
"""
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

CACHE_DIR = Path("data") / "daily_cache"


def get_cache_path(contract_id: str) -> Path:
    """获取合约的缓存文件路径"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{contract_id}.csv"


def load_cached_daily(contract_id: str) -> pd.DataFrame:
    """加载缓存的日线数据"""
    path = get_cache_path(contract_id)
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path, encoding="utf-8")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def get_cache_date_range(contract_id: str) -> tuple[str | None, str | None]:
    """获取缓存数据的日期范围 (最早日期, 最新日期)"""
    df = load_cached_daily(contract_id)
    if df.empty or "date" not in df.columns:
        return None, None
    dates = pd.to_datetime(df["date"])
    return dates.min().strftime("%Y-%m-%d"), dates.max().strftime("%Y-%m-%d")


def get_missing_days(contract_id: str, required_days: int = 60) -> int:
    """计算需要从 API 获取的天数
    
    Returns:
        需要获取的天数（0 表示缓存已是最新）
    """
    _, latest = get_cache_date_range(contract_id)
    if latest is None:
        return required_days  # 无缓存，获取全部
    
    latest_date = datetime.strptime(latest, "%Y-%m-%d")
    today = datetime.now()
    days_diff = (today - latest_date).days
    
    return max(0, days_diff)


def update_cache(contract_id: str, new_data: pd.DataFrame) -> pd.DataFrame:
    """更新缓存数据（合并新旧数据，去重）
    
    Args:
        contract_id: 合约ID
        new_data: 新获取的数据
    
    Returns:
        合并后的完整数据
    """
    if new_data.empty:
        return load_cached_daily(contract_id)
    
    old_data = load_cached_daily(contract_id)
    
    if old_data.empty:
        merged = new_data.copy()
    else:
        # 合并并按日期去重，保留最新数据
        merged = pd.concat([old_data, new_data], ignore_index=True)
        if "date" in merged.columns:
            merged["date"] = pd.to_datetime(merged["date"])
            merged = merged.drop_duplicates(subset=["date"], keep="last")
            merged = merged.sort_values("date").reset_index(drop=True)
    
    # 保存更新后的缓存
    save_cache(contract_id, merged)
    return merged


def save_cache(contract_id: str, df: pd.DataFrame):
    """保存数据到缓存"""
    path = get_cache_path(contract_id)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


def get_cached_or_fetch(contract_id: str, fetch_func, days: int = 60) -> pd.DataFrame:
    """获取日线数据（优先使用缓存，增量获取缺失数据）
    
    Args:
        contract_id: 合约ID
        fetch_func: 获取数据的函数 (contract_id, days) -> DataFrame
        days: 需要的历史天数
    
    Returns:
        完整的日线数据
    """
    missing_days = get_missing_days(contract_id, days)
    
    if missing_days == 0:
        # 缓存已是最新（今天的数据）
        cached = load_cached_daily(contract_id)
        if len(cached) >= days:
            return cached.tail(days)
        missing_days = days - len(cached) + 5  # 补充缺失数据
    
    # 获取增量数据（多获取几天确保连续性）
    fetch_days = min(missing_days + 5, days)
    new_data = fetch_func(contract_id, fetch_days)
    
    if new_data is not None and not new_data.empty:
        merged = update_cache(contract_id, new_data)
        return merged.tail(days)
    
    # 获取失败，返回缓存数据
    return load_cached_daily(contract_id).tail(days)


def clear_old_cache(keep_days: int = 365):
    """清理过期的缓存数据（可选）"""
    if not CACHE_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=keep_days)
    for path in CACHE_DIR.glob("*.csv"):
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime < cutoff:
                path.unlink()
        except Exception:
            continue

