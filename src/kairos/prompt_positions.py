"""持仓相关的提示词格式化工具"""
import json
import re


def parse_user_positions(template: str) -> list:
    """从模板中解析用户持仓信息

    Args:
        template: 模板内容

    Returns:
        用户持仓列表，每项包含 contract, direction, avg_price 等字段
    """
    pattern = r'<!-- USER_POSITIONS_START -->.*?```json\s*(.*?)\s*```.*?<!-- USER_POSITIONS_END -->'
    match = re.search(pattern, template, re.DOTALL)
    if not match:
        return []

    json_str = match.group(1).strip()
    if not json_str or json_str == "[]":
        return []

    # 移除 JSON 中的尾随逗号
    json_str = re.sub(r',\s*]', ']', json_str)
    json_str = re.sub(r',\s*}', '}', json_str)

    try:
        positions = json.loads(json_str)
        valid_positions = []
        for p in positions:
            if all(k in p for k in ("contract", "direction", "avg_price")):
                valid_positions.append(p)
        return valid_positions
    except json.JSONDecodeError:
        return []


def generate_positions_table(positions: list, decisions: list) -> str:
    """生成用户持仓信息的 Markdown 表格"""
    from kairos.futures.config import get_varieties

    if not positions:
        return "暂无持仓信息。\n"

    varieties = get_varieties()
    
    # 构建合约到决策的映射
    decision_map = {}
    for d in decisions:
        contract = d.get("contract", "")
        display = d.get("display_contract", "")
        decision_map[contract] = d
        decision_map[display] = d
        variety = re.sub(r'\d+$', '', contract.upper())
        if variety and variety not in decision_map:
            decision_map[variety] = d

    lines = [
        "| 品种 | 合约 | 方向 | 开仓价 | 当前价 | 浮盈亏 | 技术信号 |",
        "|------|------|------|--------|--------|--------|----------|",
    ]

    for pos in positions:
        contract = pos.get("contract", "")
        direction = pos.get("direction", "")
        avg_price = pos.get("avg_price", 0)

        variety = re.sub(r'\d+$', '', contract.upper())
        variety_info = varieties.get(variety, {})
        name = variety_info.get("name", variety)

        d = decision_map.get(contract.upper()) or decision_map.get(variety)

        if d:
            current_price = d.get("current_price", "N/A")
            signal = d["decision"]["direction"]
            if isinstance(current_price, (int, float)) and avg_price:
                pnl = (current_price - avg_price) if direction == "做多" else (avg_price - current_price)
                pnl_str = f"{pnl:+.2f}" if pnl != 0 else "0"
            else:
                pnl_str = "-"
        else:
            current_price = "N/A"
            signal = "未分析"
            pnl_str = "-"

        lines.append(f"| {name} | {contract} | {direction} | {avg_price} | {current_price} | {pnl_str} | {signal} |")

    return "\n".join(lines)


def replace_positions_config(template: str, decisions: list) -> str:
    """替换模板中的 USER_POSITIONS 区域为持仓表格"""
    positions = parse_user_positions(template)

    if not positions:
        pattern = r'## 1\.5 我当前的持仓情况（可选）.*?(?=## 2\.)'
        return re.sub(pattern, '', template, flags=re.DOTALL)

    positions_table = generate_positions_table(positions, decisions)

    pattern = r'<!-- USER_POSITIONS_START -->.*?<!-- USER_POSITIONS_END -->'
    result = re.sub(pattern, positions_table, template, flags=re.DOTALL)

    result = re.sub(r'\n> 💡 \*\*持仓配置说明\*\*：.*?(?=\n\*\*如果您有持仓)', '', result, flags=re.DOTALL)

    return result

