"""历史数据批量获取和构建模块

获取 2024-01-01 至今的所有品种历史数据，构建连续合约序列。
使用 Tushare 获取每日主力合约信息。
"""
import pandas as pd
from datetime import datetime
from pathlib import Path

from kairos.futures.config import CONTRACTS, load_contracts
from kairos.futures.continuous_contract import (
    build_continuous_series, save_continuous_data,
    load_continuous_data, CONTINUOUS_DIR
)

# 数据起始日期
START_DATE = "2024-01-01"


def get_all_varieties() -> list[str]:
    """获取所有支持的品种代码"""
    load_contracts()
    return [c.get("variety", "") for c in CONTRACTS.values() if c.get("variety")]


def fetch_variety_history_tushare(variety: str, start_date: str = START_DATE) -> pd.DataFrame:
    """从 Tushare 获取品种的主力合约历史数据（含每日主力合约号）

    Tushare 的 fut_daily 接口返回数据包含 ts_code（合约代码）。
    需要结合 fut_mapping 或 fut_basic 确定每日主力合约。
    """
    from kairos.futures.data_tushare import is_tushare_available, get_tushare_api

    if not is_tushare_available():
        print(f"⚠️ Tushare 不可用，跳过 {variety}")
        return pd.DataFrame()

    try:
        pro = get_tushare_api()
        end_date = datetime.now().strftime("%Y%m%d")
        start_fmt = start_date.replace("-", "")

        # 获取主力合约映射（每日主力合约号）
        mapping = pro.fut_mapping(
            ts_code=f"{variety}.{_get_exchange(variety)}",
            start_date=start_fmt,
            end_date=end_date
        )

        if mapping is None or mapping.empty:
            print(f"⚠️ {variety} 无主力合约映射数据")
            return pd.DataFrame()

        # mapping 包含: trade_date, ts_code, mapping_ts_code（主力合约）
        mapping["date"] = pd.to_datetime(mapping["trade_date"], format="%Y%m%d")
        mapping = mapping.rename(columns={"mapping_ts_code": "main_contract"})

        # 获取主力合约的日线数据
        all_data = []
        for contract in mapping["main_contract"].unique():
            df = pro.fut_daily(ts_code=contract, start_date=start_fmt, end_date=end_date)
            if df is not None and not df.empty:
                all_data.append(df)

        if not all_data:
            return pd.DataFrame()

        daily = pd.concat(all_data, ignore_index=True)
        daily["date"] = pd.to_datetime(daily["trade_date"], format="%Y%m%d")
        daily = daily.rename(columns={
            "ts_code": "contract", "open": "open", "high": "high",
            "low": "low", "close": "close", "vol": "volume", "oi": "open_interest"
        })

        # 合并主力合约信息
        result = daily.merge(
            mapping[["date", "main_contract"]],
            on="date",
            how="inner"
        )
        # 只保留当日主力合约的数据
        result = result[result["contract"] == result["main_contract"]]

        return result[["date", "main_contract", "open", "high", "low", "close",
                       "volume", "open_interest"]].sort_values("date")

    except Exception as e:
        print(f"❌ 获取 {variety} 数据失败: {e}")
        return pd.DataFrame()


def _get_exchange(variety: str) -> str:
    """获取品种对应的交易所代码（Tushare格式）"""
    exchange_map = {
        "SHFE": "SHF", "DCE": "DCE", "CZCE": "ZCE",
        "INE": "INE", "GFEX": "GFE"
    }
    for cid, cfg in CONTRACTS.items():
        if cfg.get("variety", "").upper() == variety.upper():
            ex = cfg.get("exchange", "SHFE")
            return exchange_map.get(ex, "SHF")
    return "SHF"


def build_variety_continuous(variety: str, force: bool = False) -> bool:
    """构建单个品种的连续合约数据

    Args:
        variety: 品种代码
        force: 是否强制重建（忽略已有数据）

    Returns:
        是否成功
    """
    # 检查是否已有数据
    if not force:
        existing = load_continuous_data(variety)
        if not existing.empty:
            latest = existing["date"].max()
            today = datetime.now()
            if (today - latest).days <= 1:
                print(f"✓ {variety} 数据已是最新")
                return True

    print(f"🔄 获取 {variety} 历史数据...")
    raw = fetch_variety_history_tushare(variety)

    if raw.empty:
        print(f"⚠️ {variety} 获取数据失败")
        return False

    print(f"📊 构建 {variety} 连续合约序列 ({len(raw)} 条)...")
    continuous = build_continuous_series(variety, raw)

    switch_count = continuous["is_switch_day"].sum()
    print(f"   发现 {switch_count} 次主力合约切换")

    save_continuous_data(variety, continuous)
    print(f"✅ {variety} 保存成功")
    return True


def build_all_continuous(force: bool = False) -> dict:
    """批量构建所有品种的连续合约数据"""
    varieties = get_all_varieties()
    results = {"success": [], "failed": []}

    print(f"📦 开始构建 {len(varieties)} 个品种的连续合约数据...")
    print(f"   数据范围: {START_DATE} ~ {datetime.now().strftime('%Y-%m-%d')}")
    print(f"   存储目录: {CONTINUOUS_DIR}")
    print("-" * 50)

    for variety in varieties:
        if build_variety_continuous(variety, force):
            results["success"].append(variety)
        else:
            results["failed"].append(variety)

    print("-" * 50)
    print(f"✅ 成功: {len(results['success'])} 个")
    if results["failed"]:
        print(f"❌ 失败: {', '.join(results['failed'])}")

    return results

