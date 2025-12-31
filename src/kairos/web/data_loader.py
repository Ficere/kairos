"""数据加载模块"""
import csv
import json
import os
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path("plans")


def get_available_dates() -> list[str]:
    """获取有分析结果的日期列表"""
    dates = []
    if PLANS_DIR.exists():
        for item in PLANS_DIR.iterdir():
            if item.is_dir() and len(item.name) == 10:
                dates.append(item.name)
    return sorted(dates, reverse=True)[:30]


def get_perplexity_dates() -> list[str]:
    """获取有 Perplexity 分析的日期列表"""
    dates = []
    if PLANS_DIR.exists():
        for f in PLANS_DIR.iterdir():
            if f.name.startswith("perplexity_suggestion_") and f.name.endswith(".csv"):
                date_str = f.name.replace("perplexity_suggestion_", "").replace(".csv", "")
                if len(date_str) == 10:
                    dates.append(date_str)
    return sorted(dates, reverse=True)


def load_perplexity_csv(date_str: str) -> list[dict]:
    """加载 Perplexity 分析 CSV 文件"""
    csv_path = PLANS_DIR / f"perplexity_suggestion_{date_str}.csv"
    if not csv_path.exists():
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def load_results(date_str: str | None = None) -> tuple[list, list, str]:
    """加载分析结果，返回 (decisions, switches, generated_at)"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    output_dir = PLANS_DIR / date_str
    decisions, switches = [], []
    generated_at = ""

    if output_dir.exists():
        for f in output_dir.iterdir():
            if f.name.endswith("_decision.json"):
                with open(f, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
                    decisions.append(d)
                    # 从 decision 提取移仓信息和时间戳
                    if not generated_at and d.get("timestamp"):
                        generated_at = d["timestamp"][:16].replace("T", " ")
                    if d.get("contract_status") == "移仓中":
                        switches.append({"name": d.get("name", ""), "variety": d.get("variety", "")})

    return sorted(decisions, key=lambda x: -x.get("scores", {}).get("total", 0)), switches, generated_at

