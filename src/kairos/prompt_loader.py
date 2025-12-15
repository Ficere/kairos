"""Deep Research 分析结果加载器"""
import json
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path(__file__).parent.parent.parent / "plans"


def load_analysis_results(date_str: str) -> dict | None:
    """从JSON文件加载指定日期的分析结果

    Args:
        date_str: 日期字符串，格式为 YYYY-MM-DD

    Returns:
        包含 decisions 和 switches 的字典，失败返回 None
    """
    # 加载 summary 文件获取 switches
    summary_path = PLANS_DIR / f"summary_{date_str}.json"
    switches = []
    if summary_path.exists():
        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
                switches = summary.get("switches", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 读取 summary 文件失败: {e}")

    # 加载所有 decision 文件
    day_dir = PLANS_DIR / date_str
    if not day_dir.exists():
        return None

    decisions = []
    for decision_file in day_dir.glob("*_decision.json"):
        try:
            with open(decision_file, "r", encoding="utf-8") as f:
                decisions.append(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 读取 {decision_file.name} 失败: {e}")

    if not decisions:
        return None

    return {"decisions": decisions, "switches": switches}


def get_latest_analysis_date() -> str | None:
    """获取最新的分析结果日期

    Returns:
        最新日期字符串 YYYY-MM-DD，如果没有找到返回 None
    """
    if not PLANS_DIR.exists():
        return None

    # 查找所有日期目录
    date_dirs = [d.name for d in PLANS_DIR.iterdir()
                 if d.is_dir() and len(d.name) == 10 and d.name.count('-') == 2]

    if not date_dirs:
        return None

    return sorted(date_dirs, reverse=True)[0]


def validate_date_format(date_str: str) -> bool:
    """验证日期格式是否正确

    Args:
        date_str: 日期字符串

    Returns:
        如果格式正确返回 True，否则返回 False
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

