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
from kairos.prompt_indicators import INDICATOR_DOCS, format_variety_compact

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "docs" / "deep_research_template.md"


def _dedupe_by_variety(decisions: list, direction: str) -> list:
    """按品种去重，每个品种只保留评分最高的合约"""
    filtered = [d for d in decisions if d["decision"]["direction"] == direction]
    variety_best = {}
    for d in filtered:
        variety = d.get("variety", d.get("contract", "")[:2].upper())
        if variety not in variety_best or d["scores"]["total"] > variety_best[variety]["scores"]["total"]:
            variety_best[variety] = d
    return list(variety_best.values())


def _process_template(date_str: str, decisions: list, switches: list) -> str:
    """处理模板并生成提示词内容"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    positions = parse_user_positions(template)

    template = template.replace("[请在此处填写日期，例如：2025-12-11]", date_str)
    template = replace_tracking_config(template, decisions)
    template = replace_positions_config(template, decisions)

    # 按品种去重，确保数量统计准确
    longs = _dedupe_by_variety(decisions, "做多")
    shorts = _dedupe_by_variety(decisions, "做空")

    return _build_prompt(
        date_str, longs, shorts,
        format_variety_list(decisions, "做多"),
        format_variety_list(decisions, "做空"),
        format_switch_list(switches),
        _build_position_reminder(positions) if positions else "",
        template, decisions
    )


def generate_deep_research_prompt(results: dict, output_dir: str) -> str | None:
    """生成 Deep Research 提示词"""
    decisions = results.get("decisions", [])
    switches = results.get("switches", [])

    if not decisions:
        print("⚠️ 无分析结果，跳过生成 Deep Research 提示词")
        return None

    if not TEMPLATE_PATH.exists():
        print(f"⚠️ 模板文件不存在: {TEMPLATE_PATH}")
        return None

    date_str = datetime.now().strftime("%Y-%m-%d")
    prompt = _process_template(date_str, decisions, switches)

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


def _build_indicator_details(decisions: list, direction: str, max_items: int = 5) -> str:
    """为指定方向的品种构建紧凑指标摘要（每个品种只保留评分最高的合约）"""
    filtered = [d for d in decisions if d["decision"]["direction"] == direction]
    if not filtered:
        return ""
    # 按品种去重，保留评分最高的
    variety_best = {}
    for d in filtered:
        variety = d.get("variety", d.get("contract", "")[:2].upper())
        if variety not in variety_best or d["scores"]["total"] > variety_best[variety]["scores"]["total"]:
            variety_best[variety] = d
    sorted_items = sorted(variety_best.values(), key=lambda x: -x["scores"]["total"])[:max_items]
    return "\n".join(format_variety_compact(d) for d in sorted_items)


def _build_prompt(
    date_str: str, longs: list, shorts: list,
    long_list: str, short_list: str, switch_list: str,
    position_reminder: str, template: str, decisions: list
) -> str:
    """构建完整的提示词内容"""
    long_details = _build_indicator_details(decisions, "做多", 5)
    short_details = _build_indicator_details(decisions, "做空", 5)

    return f"""# 期货市场深度分析请求 - {date_str}

{INDICATOR_DOCS}
## 技术分析信号汇总

### 做多信号（{len(longs)}个）
{long_list}
### 做空信号（{len(shorts)}个）
{short_list}
### 移仓提示
{switch_list}
{position_reminder}
## 📈 重点品种指标详情

**做多前5**:
{long_details if long_details else "无"}

**做空前5**:
{short_details if short_details else "无"}

---

{template}
"""


def regenerate_prompt_from_file(date_str: str | None = None, force: bool = False) -> str | None:
    """从已有的分析结果文件重新生成 Deep Research 提示词"""
    if date_str is None:
        date_str = get_latest_analysis_date()
        if date_str is None:
            print("❌ 未找到任何分析结果文件")
            print("   请先运行 'kairos-analyze --all' 生成分析结果")
            return None
        print(f"📅 使用最新分析结果: {date_str}")
    elif not validate_date_format(date_str):
        print(f"❌ 日期格式错误: {date_str}，正确格式: YYYY-MM-DD")
        return None

    output_path = PLANS_DIR / f"deep_research_{date_str}.md"
    if output_path.exists() and not force:
        response = input(f"⚠️  文件已存在: {output_path}\n   是否覆盖? (y/N): ").strip().lower()
        if response not in ('y', 'yes'):
            return None

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

    if not TEMPLATE_PATH.exists():
        print(f"❌ 模板文件不存在: {TEMPLATE_PATH}")
        return None

    print(f"🔄 重新生成 Deep Research 提示词...")
    prompt = _process_template(date_str, decisions, switches)

    os.makedirs(PLANS_DIR, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    longs = [d for d in decisions if d["decision"]["direction"] == "做多"]
    shorts = [d for d in decisions if d["decision"]["direction"] == "做空"]

    print(f"✅ Deep Research 提示词已重新生成: {output_path}")
    print(f"   📊 做多信号: {len(longs)} 个 | 做空信号: {len(shorts)} 个")
    print(f"   📦 移仓提示: {len(switches)} 个")

    return str(output_path)

