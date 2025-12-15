"""输出目录管理模块"""
import os
from datetime import datetime


def get_daily_output_dir() -> str:
    """获取按日期命名的输出目录"""
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("plans", today)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir

