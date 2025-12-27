"""Deep Research 提示词生成器"""
import os
from datetime import datetime
from pathlib import Path

from kairos.prompt_loader import (
    load_analysis_results,
    get_latest_analysis_date,
    validate_date_format,
    PLANS_DIR,
)
from kairos.prompt_formatter import (
    format_variety_list,
    format_switch_list,
    replace_tracking_config,
    replace_positions_config,
    parse_user_positions,
)

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "docs" / "deep_research_template.md"


def generate_deep_research_prompt(results: dict, output_dir: str) -> str | None:
    """生成 Deep Research 提示词
    
    Args:
        results: 分析结果字典，包含 decisions 和 switches
        output_dir: 输出目录
    
    Returns:
        生成的文件路径，失败返回 None
    """
    decisions = results.get("decisions", [])
    switches = results.get("switches", [])
    
    if not decisions:
        print("⚠️ 无分析结果，跳过生成 Deep Research 提示词")
        return None
    
    # 加载模板
    if not TEMPLATE_PATH.exists():
        print(f"⚠️ 模板文件不存在: {TEMPLATE_PATH}")
        return None
    
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 替换模板中的日期占位符
    date_str = datetime.now().strftime("%Y-%m-%d")
    template = template.replace("[请在此处填写日期，例如：2025-12-11]", date_str)

    # 解析用户持仓信息（在替换前）
    positions = parse_user_positions(template)

    # 替换 TRACKING_CONFIG 区域为包含实时数据的表格
    template = replace_tracking_config(template, decisions)

    # 替换 USER_POSITIONS 区域
    template = replace_positions_config(template, decisions)

    # 统计
    longs = [d for d in decisions if d["decision"]["direction"] == "做多"]
    shorts = [d for d in decisions if d["decision"]["direction"] == "做空"]

    # 生成品种列表
    long_list = format_variety_list(decisions, "做多")
    short_list = format_variety_list(decisions, "做空")
    switch_list = format_switch_list(switches)

    # 生成持仓提醒（如果有持仓）
    position_reminder = _build_position_reminder(positions) if positions else ""

    # 构建提示词
    prompt = f"""# 期货市场深度分析请求 - {date_str}

## 技术分析信号汇总

### 做多信号品种（{len(longs)}个）
{long_list}
### 做空信号品种（{len(shorts)}个）
{short_list}
### 移仓提示
{switch_list}
{position_reminder}
---

## 请基于以上技术信号，按照以下模板进行深度分析：

{template}
"""
    
    # 保存文件到 plans/ 根目录
    os.makedirs("plans", exist_ok=True)
    output_path = os.path.join("plans", f"deep_research_{date_str}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"✅ Deep Research 提示词已生成: {output_path}")
    return output_path


def _build_position_reminder(positions: list) -> str:
    """构建持仓提醒文本"""
    if not positions:
        return ""

    lines = ["\n### ⚠️ 用户当前持仓提醒\n"]
    lines.append("**请在分析时特别关注以下持仓，并给出明确的操作建议：**\n")
    for pos in positions:
        contract = pos.get("contract", "")
        direction = pos.get("direction", "")
        avg_price = pos.get("avg_price", 0)
        lines.append(f"- **{contract}** {direction} @ {avg_price}")
    lines.append("\n对于每个持仓，请分析：持有/止盈/止损/加仓/减仓，并给出理由和关键价位。\n")
    return "\n".join(lines)


def regenerate_prompt_from_file(date_str: str | None = None, force: bool = False) -> str | None:
    """从已有的分析结果文件重新生成 Deep Research 提示词

    Args:
        date_str: 日期字符串 YYYY-MM-DD，如果为 None 则使用最新日期
        force: 是否强制覆盖已存在的文件

    Returns:
        生成的文件路径，失败返回 None
    """
    # 确定日期
    if date_str is None:
        date_str = get_latest_analysis_date()
        if date_str is None:
            print("❌ 未找到任何分析结果文件")
            print("   请先运行 'kairos-analyze --all' 生成分析结果")
            return None
        print(f"📅 使用最新分析结果: {date_str}")
    else:
        # 验证日期格式
        if not validate_date_format(date_str):
            print(f"❌ 日期格式错误: {date_str}")
            print("   正确格式: YYYY-MM-DD (例如: 2025-12-15)")
            return None

    # 检查输出文件是否已存在
    output_path = PLANS_DIR / f"deep_research_{date_str}.md"
    if output_path.exists() and not force:
        response = input(f"⚠️  文件已存在: {output_path}\n   是否覆盖? (y/N): ").strip().lower()
        if response not in ('y', 'yes'):
            print("❌ 已取消")
            return None

    # 加载分析结果
    print(f"📂 加载分析结果: {date_str}")
    results = load_analysis_results(date_str)
    if results is None:
        print(f"❌ 未找到日期 {date_str} 的分析结果文件")
        print(f"   请检查目录: {PLANS_DIR / date_str}")
        return None

    decisions = results.get("decisions", [])
    switches = results.get("switches", [])
    print(f"   ✓ 加载了 {len(decisions)} 个决策记录")
    print(f"   ✓ 加载了 {len(switches)} 个移仓提示")

    # 检查模板文件
    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板文件不存在: {TEMPLATE_PATH}")
        return None

    # 生成提示词
    print(f"🔄 重新生成 Deep Research 提示词...")

    # 加载模板
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 解析用户持仓信息（在替换前）
    positions = parse_user_positions(template)

    # 替换模板中的日期占位符
    template = template.replace("[请在此处填写日期，例如：2025-12-11]", date_str)

    # 替换 TRACKING_CONFIG 区域为包含实时数据的表格
    template = replace_tracking_config(template, decisions)

    # 替换 USER_POSITIONS 区域
    template = replace_positions_config(template, decisions)

    # 统计
    longs = [d for d in decisions if d["decision"]["direction"] == "做多"]
    shorts = [d for d in decisions if d["decision"]["direction"] == "做空"]

    # 生成品种列表
    long_list = format_variety_list(decisions, "做多")
    short_list = format_variety_list(decisions, "做空")
    switch_list = format_switch_list(switches)

    # 生成持仓提醒（如果有持仓）
    position_reminder = _build_position_reminder(positions) if positions else ""

    # 构建提示词
    prompt = f"""# 期货市场深度分析请求 - {date_str}

## 技术分析信号汇总

### 做多信号品种（{len(longs)}个）
{long_list}
### 做空信号品种（{len(shorts)}个）
{short_list}
### 移仓提示
{switch_list}
{position_reminder}
---

## 请基于以上技术信号，按照以下模板进行深度分析：

{template}
"""

    # 保存文件
    os.makedirs(PLANS_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"✅ Deep Research 提示词已重新生成: {output_path}")
    print(f"   📊 做多信号: {len(longs)} 个")
    print(f"   📊 做空信号: {len(shorts)} 个")
    print(f"   📦 移仓提示: {len(switches)} 个")
    if positions:
        print(f"   💼 用户持仓: {len(positions)} 个")

    return str(output_path)

