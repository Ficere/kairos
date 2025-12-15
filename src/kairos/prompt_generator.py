"""Deep Research 提示词生成器"""
import os
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
    """格式化品种列表"""
    filtered = [d for d in decisions if d["decision"]["direction"] == direction]
    if not filtered:
        return "无\n"
    
    lines = []
    for i, d in enumerate(sorted(filtered, key=lambda x: -x["scores"]["total"]), 1):
        contract = d.get("display_contract", d.get("contract", ""))
        name = d.get("name", "")
        score = d["scores"]["total"]
        indicators = format_indicator_summary(d)
        lines.append(f"{i}. **{name}**({contract}) - 评分: {score} - {indicators}")
    
    return "\n".join(lines) + "\n"


def format_switch_list(switches: list) -> str:
    """格式化移仓列表"""
    if not switches:
        return "无当前移仓品种\n"

    lines = []
    for s in switches:
        date_info = f" (切换于{s['switch_date']})" if s.get('switch_date') else ""
        lines.append(f"- {s['name']}: {s['previous_contract']} → {s['main_contract']}{date_info}")

    return "\n".join(lines) + "\n"


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

