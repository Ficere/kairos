"""主力合约更新模块 - 支持移仓换月双合约监控"""
import json
from datetime import datetime, timedelta
import akshare as ak
from kairos.futures.config import get_config_path, ensure_config_dir

EXCHANGE_NAME_MAP = {"上期所": "SHFE", "大商所": "DCE", "郑商所": "CZCE", "中金所": "CFFEX", "广期所": "GFEX"}
SWITCH_MONITOR_DAYS = 30  # 移仓监控天数

# 排除的交易所（金融期货不适合本系统的商品期货分析逻辑）
EXCLUDED_EXCHANGES = {"CFFEX"}
# 排除的品种代码（中金所金融期货）
EXCLUDED_VARIETIES = {"IC", "IF", "IH", "IM", "T", "TF", "TL", "TS"}


def load_config() -> dict:
    """加载配置文件"""
    try:
        with open(get_config_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_config(config: dict):
    """保存配置文件"""
    ensure_config_dir()
    with open(get_config_path(), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def fetch_futures_rules() -> dict:
    """从 futures_rule 获取品种基础信息（排除中金所金融期货）"""
    try:
        df = ak.futures_rule()
        result = {}
        for _, row in df.iterrows():
            code = str(row.get("代码", "")).upper()
            if not code or "期权" in str(row.get("品种", "")):
                continue
            exchange = EXCHANGE_NAME_MAP.get(row.get("交易所", ""), "UNKNOWN")
            # 排除中金所金融期货
            if exchange in EXCLUDED_EXCHANGES or code in EXCLUDED_VARIETIES:
                continue
            multiplier = row.get("合约乘数", 1)
            tick = row.get("最小变动价位", 1)
            try:
                multiplier = int(str(multiplier).replace(",", "").split("元")[0].split("/")[0])
            except (ValueError, IndexError):
                multiplier = 1
            try:
                tick = float(str(tick).replace(",", "").split("元")[0])
            except (ValueError, IndexError):
                tick = 1
            result[code] = {
                "name": str(row.get("品种", code)),
                "exchange": exchange,
                "multiplier": multiplier,
                "tick": tick,
            }
        return result
    except Exception as e:
        print(f"⚠️ 获取品种规则失败: {e}")
        return {}


def fetch_main_contracts() -> dict:
    """批量获取所有品种的主力合约代码，返回 {品种代码: 主力合约代码}"""
    try:
        end = datetime.now().strftime("%Y%m%d")
        start = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
        df = ak.futures_spot_price_daily(start_day=start, end_day=end)
        if df is not None and not df.empty:
            latest = df.sort_values("date", ascending=False).drop_duplicates("symbol")
            return dict(zip(latest["symbol"].str.upper(), latest["dominant_contract"].str.upper()))
    except Exception as e:
        print(f"⚠️ 获取主力合约失败: {e}")
    return {}


def update_or_add_variety(variety: str, config: dict, rules: dict, main_map: dict) -> tuple[str, str]:
    """更新或添加品种，返回 (状态, 切换信息)
    状态: 'added', 'updated', 'switched', 'unchanged', 'not_found'
    """
    info = rules.get(variety)
    if not info:
        return "not_found", ""

    today = datetime.now().strftime("%Y-%m-%d")
    new_main = main_map.get(variety, f"{variety}0")

    if variety not in config:
        config[variety] = {
            "name": info.get("name", variety), "exchange": info.get("exchange", "UNKNOWN"),
            "multiplier": info.get("multiplier", 1), "tick": info.get("tick", 1),
            "main_contract": new_main, "previous_contract": "", "contract_switch_date": "", "last_updated": today,
        }
        return "added", ""

    old_main = config[variety].get("main_contract", "")
    if new_main != old_main and not new_main.endswith("0") and old_main:
        # 检测到主力合约切换
        config[variety]["previous_contract"] = old_main
        config[variety]["contract_switch_date"] = today
        config[variety]["main_contract"] = new_main
        config[variety]["last_updated"] = today
        return "switched", f"{old_main} → {new_main}"
    elif new_main != old_main and not new_main.endswith("0"):
        config[variety]["main_contract"] = new_main
        config[variety]["last_updated"] = today
        return "updated", ""

    return "unchanged", ""


def is_in_switch_period(config: dict) -> bool:
    """检查是否在移仓监控期内"""
    switch_date = config.get("contract_switch_date", "")
    if not switch_date:
        return False
    try:
        switch_dt = datetime.strptime(switch_date, "%Y-%m-%d")
        return (datetime.now() - switch_dt).days <= SWITCH_MONITOR_DAYS
    except ValueError:
        return False


def get_switch_varieties(config: dict) -> list[dict]:
    """获取正在移仓的品种列表"""
    switches = []
    for variety, info in config.items():
        if is_in_switch_period(info):
            switches.append({
                "variety": variety, "name": info.get("name", variety),
                "main_contract": info.get("main_contract", ""),
                "previous_contract": info.get("previous_contract", ""),
                "switch_date": info.get("contract_switch_date", ""),
            })
    return switches


def update_contracts(varieties: list[str] | None = None, add_all: bool = False) -> tuple[int, int, int, int]:
    """更新主力合约配置
    Returns: (新增, 更新, 切换, 无变化)
    """
    print("正在获取品种规则...")
    rules = fetch_futures_rules()
    if not rules:
        return 0, 0, 0, 0
    print(f"✓ 获取到 {len(rules)} 个品种")

    print("正在获取主力合约...")
    main_map = fetch_main_contracts()
    print(f"✓ 获取到 {len(main_map)} 个主力合约")

    config = load_config()
    target = list(rules.keys()) if add_all else ([v.replace("0", "").upper() for v in varieties] if varieties else list(config.keys()) or list(rules.keys()))

    added, updated, switched, unchanged = 0, 0, 0, 0
    for variety in sorted(target):
        status, switch_info = update_or_add_variety(variety, config, rules, main_map)
        contract = config.get(variety, {}).get("main_contract", "N/A")
        if status == "added":
            added += 1
            print(f"  + {variety}: {contract} (新增)")
        elif status == "switched":
            switched += 1
            print(f"  🔄 {variety}: {switch_info} (移仓)")
        elif status == "updated":
            updated += 1
            print(f"  ✓ {variety}: {contract} (更新)")
        elif status == "not_found":
            print(f"  ⚠ {variety}: 未找到数据")
        else:
            unchanged += 1

    if added or updated or switched:
        save_config(config)
        print(f"\n✅ 新增{added} 更新{updated} 移仓{switched} 无变化{unchanged}")
    else:
        print(f"\n✅ 所有 {unchanged} 个品种均为最新")

    # 显示正在移仓的品种
    switches = get_switch_varieties(config)
    if switches:
        print(f"\n⚠️ 移仓监控 ({len(switches)}个):")
        for s in switches:
            print(f"   {s['name']}: {s['previous_contract']} → {s['main_contract']} (切换于{s['switch_date']})")

    return added, updated, switched, unchanged

