"""Deep Research 提示词格式化工具"""
import json
import re


def format_indicator_summary(d: dict) -> str:
    """格式化技术指标摘要"""
    ti = d.get("technical_indicators", {})
    parts = []

    # MACD
    macd = ti.get("macd", {})
    if macd:
        dif, dea = macd.get("dif", 0), macd.get("dea", 0)
        parts.append("MACD多头" if dif > dea else "MACD空头")

    # RSI
    rsi = ti.get("rsi", {})
    if rsi:
        val = rsi.get("value", 50)
        if val > 70:
            parts.append(f"RSI超买({int(val)})")
        elif val < 30:
            parts.append(f"RSI超卖({int(val)})")
        else:
            parts.append(f"RSI:{int(val)}")

    # 背离
    div = ti.get("divergence", {})
    if div and div.get("type") != "无背离":
        parts.append(f"{div.get('type')}({div.get('indicator', '')})")

    return "，".join(parts) if parts else "指标中性"


def format_variety_list(decisions: list, direction: str) -> str:
    """格式化品种列表（含价格）"""
    filtered = [d for d in decisions if d["decision"]["direction"] == direction]
    if not filtered:
        return "无\n"
    lines = []
    for i, d in enumerate(sorted(filtered, key=lambda x: -x["scores"]["total"]), 1):
        c = d.get("display_contract", d.get("contract", ""))
        n, p = d.get("name", ""), d.get("current_price", "N/A")
        lines.append(f"{i}. **{n}**({c}) - 价格: {p} - 评分: {d['scores']['total']} - {format_indicator_summary(d)}")
    return "\n".join(lines) + "\n"


def format_switch_list(switches: list) -> str:
    """格式化移仓列表"""
    if not switches:
        return "无当前移仓品种\n"
    return "\n".join(f"- {s['name']}: {s['previous_contract']} → {s['main_contract']}" +
                     (f" (切换于{s['switch_date']})" if s.get('switch_date') else "")
                     for s in switches) + "\n"


def parse_user_tracking_config(template: str) -> list:
    """从模板中解析用户追踪品种配置

    支持 JSON 中的尾随逗号（trailing comma），这是用户常见的编辑习惯。
    """
    pattern = r'<!-- TRACKING_CONFIG_START -->.*?```json\s*(.*?)\s*```.*?<!-- TRACKING_CONFIG_END -->'
    match = re.search(pattern, template, re.DOTALL)
    if not match:
        return []

    json_str = match.group(1).strip()
    if not json_str:
        return []

    # 移除 JSON 中的尾随逗号
    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r',\s*}', '}', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []


def generate_tracking_table(user_config: list, decisions: list) -> str:
    """生成重点跟踪品种的 Markdown 表格（包含实时数据）

    Args:
        user_config: 用户配置的品种列表（从模板解析）
        decisions: 分析结果列表

    Returns:
        Markdown 格式的表格字符串
    """
    if not user_config:
        return "暂无配置重点跟踪品种。\n"

    # 构建合约到决策的映射
    decision_map = {d.get("contract", ""): d for d in decisions}
    for d in decisions:
        if d.get("display_contract"):
            decision_map[d["display_contract"]] = d

    # 生成表格
    lines = [
        "| 品种 | 合约 | 当前价格 | 方向 | 评分 | 跟踪理由 | 技术状态 |",
        "|------|------|---------|------|------|---------|---------|",
    ]

    for cfg in user_config:
        contract = cfg.get("contract", "")
        name = cfg.get("name", "")
        reason = cfg.get("reason", "")

        # 查找分析数据
        d = decision_map.get(contract)
        if d:
            display = d.get("display_contract", contract)
            price = d.get("current_price", "N/A")
            direction = d["decision"]["direction"]
            score = d["scores"]["total"]
            tech_status = format_indicator_summary(d)
        else:
            display = contract
            price = "N/A"
            direction = "未分析"
            score = "-"
            tech_status = "-"

        lines.append(f"| {name} | {display} | {price} | {direction} | {score} | {reason} | {tech_status} |")

    return "\n".join(lines)


def replace_tracking_config(template: str, decisions: list) -> str:
    """替换模板中的 TRACKING_CONFIG 区域为实时数据表格，并移除开发者配置说明

    Args:
        template: 模板内容
        decisions: 分析结果列表

    Returns:
        替换后的模板内容
    """
    user_config = parse_user_tracking_config(template)
    if not user_config:
        return template

    tracking_table = generate_tracking_table(user_config, decisions)

    # 替换 TRACKING_CONFIG 区域为表格（不保留 HTML 注释标记）
    pattern = r'<!-- TRACKING_CONFIG_START -->.*?<!-- TRACKING_CONFIG_END -->'
    replacement = tracking_table
    result = re.sub(pattern, replacement, template, flags=re.DOTALL)

    # 移除配置说明段落（包含 💡 配置说明 的行）
    result = re.sub(r'\n> 💡 \*\*配置说明\*\*：[^\n]*\n', '\n', result)

    # 移除开发者说明文字（"先列出你需要查找..."）
    result = re.sub(
        r'先列出你需要查找的关键数据和报告类型，然后按步骤完成推理，每一步都显式写出前提与结论。',
        '',
        result
    )

    return result

