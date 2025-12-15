"""Deep Research 提示词生成器"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent.parent.parent / "docs" / "deep_research_template.md"


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
        c, n, p = d.get("display_contract", d.get("contract", "")), d.get("name", ""), d.get("current_price", "N/A")
        lines.append(f"{i}. **{n}**({c}) - 价格: {p} - 评分: {d['scores']['total']} - {format_indicator_summary(d)}")
    return "\n".join(lines) + "\n"


def parse_user_tracking_config(template: str) -> list:
    """从模板中解析用户追踪品种配置"""
    pattern = r'<!-- TRACKING_CONFIG_START -->\s*```json\s*(.*?)\s*```\s*<!-- TRACKING_CONFIG_END -->'
    match = re.search(pattern, template, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return []


def format_tracking_json(decisions: list, user_config: list = None) -> str:
    """生成追踪品种的 JSON 列表（用户配置优先，否则自动选择做多/做空）"""
    decision_map = {d.get("contract", ""): d for d in decisions}
    for d in decisions:
        if d.get("display_contract"):
            decision_map[d["display_contract"]] = d

    tracking = []
    if user_config:
        for cfg in user_config:
            contract, d = cfg.get("contract", ""), decision_map.get(cfg.get("contract", ""))
            if d:
                tracking.append({"contract": d.get("display_contract", contract), "name": d.get("name", ""),
                    "price": d.get("current_price", "N/A"), "direction": d["decision"]["direction"],
                    "score": d["scores"]["total"], "reason": cfg.get("reason", "")})
            else:
                tracking.append({"contract": contract, "name": cfg.get("name", ""), "price": "N/A",
                    "direction": "未分析", "score": 0, "reason": cfg.get("reason", "")})
    else:
        for d in sorted(decisions, key=lambda x: -x["scores"]["total"]):
            if d["decision"]["direction"] in ("做多", "做空"):
                tracking.append({"contract": d.get("display_contract", d.get("contract", "")),
                    "name": d.get("name", ""), "price": d.get("current_price", "N/A"),
                    "direction": d["decision"]["direction"], "score": d["scores"]["total"]})
    return json.dumps(tracking, ensure_ascii=False, indent=2)


def format_switch_list(switches: list) -> str:
    """格式化移仓列表"""
    if not switches:
        return "无当前移仓品种\n"
    return "\n".join(f"- {s['name']}: {s['previous_contract']} → {s['main_contract']}" +
                     (f" (切换于{s['switch_date']})" if s.get('switch_date') else "")
                     for s in switches) + "\n"


def format_tracking_description(tracking_data: list) -> str:
    """生成追踪品种的 Markdown 描述"""
    if not tracking_data:
        return "暂无配置追踪品种。\n"
    lines = ["根据用户配置，今天重点跟踪以下品种（详细数据见上方结构化数据）：\n"]
    for t in tracking_data:
        if t["direction"] == "未分析":
            lines.append(f"- **{t['name']}**({t['contract']}) - ⚠️ 未分析")
        else:
            lines.append(f"- **{t['name']}**({t['contract']}) - {t['direction']} - 价格: {t['price']} - 评分: {t['score']}")
        if t.get("reason"):
            lines.append(f"  理由：{t['reason']}")
    lines.append("\n请在分析时优先覆盖上述品种的当前主力合约，并在表格中写出具体合约号。")
    return "\n".join(lines)


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

    # 统计
    longs = [d for d in decisions if d["decision"]["direction"] == "做多"]
    shorts = [d for d in decisions if d["decision"]["direction"] == "做空"]
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 解析用户追踪配置并生成追踪数据
    user_tracking = parse_user_tracking_config(template)
    tracking_json = format_tracking_json(decisions, user_tracking)
    tracking_data = json.loads(tracking_json)  # 解析回列表以生成描述
    tracking_desc = format_tracking_description(tracking_data)

    # 替换模板中的"## 1. 我当前重点跟踪的品种"章节
    pattern = r'(## 1\. 我当前重点跟踪的品种\s*\n).*?((?=\n## 2\.)|$)'
    replacement = f"\\1\n{tracking_desc}\n\n"
    template = re.sub(pattern, replacement, template, flags=re.DOTALL)

    # 生成品种列表
    long_list = format_variety_list(decisions, "做多")
    short_list = format_variety_list(decisions, "做空")
    switch_list = format_switch_list(switches)

    # 构建提示词
    prompt = f"""# 期货市场深度分析请求 - {date_str}

## 技术分析信号汇总

### 做多信号品种（{len(longs)}个）
{long_list}
### 做空信号品种（{len(shorts)}个）
{short_list}
### 移仓提示
{switch_list}

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

