"""期货合约配置 - 支持用户配置目录"""
import json
import os
from dataclasses import dataclass
from typing import Optional
import pandas as pd
from platformdirs import user_config_dir

# 配置目录和文件路径
APP_NAME = "kairos"
CONFIG_DIR = user_config_dir(APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "contracts.json")


def ensure_config_dir():
    """确保配置目录存在"""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def get_config_path() -> str:
    """获取配置文件路径，优先使用用户配置目录，其次使用当前目录"""
    if os.path.exists(CONFIG_FILE):
        return CONFIG_FILE
    # 兼容旧版：检查当前目录
    local_config = "contracts.json"
    if os.path.exists(local_config):
        return local_config
    # 首次使用时创建配置目录
    ensure_config_dir()
    return CONFIG_FILE


# 排除的交易所和品种（中金所金融期货不适合商品期货分析）
EXCLUDED_EXCHANGES = {"CFFEX"}
EXCLUDED_VARIETIES = {"IC", "IF", "IH", "IM", "T", "TF", "TL", "TS"}


def load_contracts() -> dict:
    """从 JSON 文件加载合约配置，支持 XX0 格式和实际合约代码（排除中金所）"""
    global CONTRACTS
    config_path = get_config_path()
    if not os.path.exists(config_path):
        CONTRACTS = {}
        return CONTRACTS
    with open(config_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    contracts = {}
    for variety, info in raw.items():
        # 排除中金所金融期货
        exchange = info.get("exchange", "")
        if exchange in EXCLUDED_EXCHANGES or variety in EXCLUDED_VARIETIES:
            continue
        main = info.get("main_contract", f"{variety}0")
        is_real = main and not main.endswith("0")
        key = f"{variety}0"
        contracts[key] = {
            "symbol": f"{variety.lower()}0",
            "name": info.get("name", variety),
            "exchange": exchange,
            "multiplier": info.get("multiplier", 1),
            "tick": info.get("tick", 1),
            "variety": variety,
            "main_contract": main if is_real else key,
        }
    CONTRACTS = contracts
    return contracts


def get_varieties() -> dict:
    """获取原始品种配置（以品种代码为 key）"""
    config_path = get_config_path()
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 目标合约配置（兼容旧代码）
CONTRACTS = load_contracts()


@dataclass
class MarketData:
    """市场数据结构"""
    symbol: str
    name: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    open_interest: int
    change_pct: float
    hist_data: Optional[pd.DataFrame] = None

