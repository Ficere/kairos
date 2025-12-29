"""Perplexity API 客户端 - 宏观面和基本面分析"""
import json
import re
import csv
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path(__file__).parent.parent.parent / "plans"

# CSV 输出字段映射
CSV_FIELDS = [
    ("品种及主力合约", "品种"),
    ("合约", "合约"),
    ("方向", "方向"),
    ("最新价", "最新价"),
    ("参考开仓价区间", "参考开仓价区间"),
    ("目标价", "目标价"),
    ("止损价", "止损价"),
    ("技术面简述", "技术面简述"),
    ("消息面/基本面简述", "消息面简述"),
    ("交易确定性评级", "交易确定性评级"),
]

DEFAULT_RECORD = {
    "品种": "未知",
    "合约": "",
    "方向": "观望",
    "最新价": "",
    "参考开仓价区间": "",
    "目标价": "",
    "止损价": "",
    "技术面简述": "数据解析失败",
    "消息面简述": "数据解析失败",
    "交易确定性评级": "低：数据获取失败",
}


def extract_json_from_text(text: str) -> list[dict] | None:
    """从文本中提取 JSON 数组"""
    # 尝试直接解析
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass

    # 尝试提取 ```json ... ``` 代码块
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```",
        r"\[\s*\{[\s\S]*\}\s*\]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                content = match.group(1) if "```" in pattern else match.group(0)
                data = json.loads(content)
                return data if isinstance(data, list) else [data]
            except (json.JSONDecodeError, IndexError):
                continue
    return None


def normalize_record(raw: dict) -> dict:
    """将 Perplexity 返回的记录规范化为 CSV 格式"""
    record = DEFAULT_RECORD.copy()

    # 直接映射字段（Perplexity 实际返回的格式）
    field_map = {
        "品种": "品种",
        "合约": "合约",
        "方向": "方向",
        "最新价": "最新价",
        "参考开仓价区间": "参考开仓价区间",
        "目标价": "目标价",
        "止损价": "止损价",
        "技术面简述": "技术面简述",
        "基本面简述": "消息面简述",
        "交易确定性": "交易确定性评级",
    }
    for src, dst in field_map.items():
        if src in raw and raw[src] is not None:
            record[dst] = str(raw[src])
    return record


def call_perplexity_api(prompt: str, max_retries: int = 3, timeout: int = 120) -> str:
    """调用 Perplexity API，支持重试机制"""
    try:
        from perplexity import Perplexity
    except ImportError:
        raise ImportError(
            "请安装 perplexity 包: uv pip install perplexityai\n"
            "或使用: uv pip install 'kairos[perplexity]'"
        )

    client = Perplexity()
    messages = [{"role": "user", "content": prompt}]

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
                disable_search=False,
                stream=True,
                web_search_options={"search_type": "pro"},
            )
            content_parts = []
            for chunk in response:
                _content = chunk.choices[0].delta.content
                if _content:
                    print(_content, end="")
                    content_parts.append(_content)
            return "".join(content_parts)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                import time
                wait = 2 ** attempt
                print(f"  ⚠️ API 调用失败，{wait}秒后重试 ({attempt + 1}/{max_retries})")
                time.sleep(wait)

    raise RuntimeError(f"Perplexity API 调用失败: {last_error}")

def save_suggestions_text(text: str, output_path: Path) -> None:
    """保存建议到文本文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)

def save_suggestions_csv(records: list[dict], output_path: Path) -> None:
    """保存建议到 CSV 文件"""
    headers = [f[1] for f in CSV_FIELDS]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def run_perplexity_analysis(prompt_path: str | Path) -> Path | None:
    """执行 Perplexity 分析并生成 CSV"""
    prompt_path = Path(prompt_path)
    if not prompt_path.exists():
        print(f"❌ 提示词文件不存在: {prompt_path}")
        return None

    prompt = prompt_path.read_text(encoding="utf-8")
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = Path("plans") / f"perplexity_suggestion_{date_str}.csv"

    print("🔄 正在调用 Perplexity API 进行宏观面分析...")
    try:
        response_text = call_perplexity_api(prompt)
        save_suggestions_text(response_text, output_path.with_suffix(".json"))
    except (ImportError, RuntimeError) as e:
        print(f"❌ {e}")
        return None

    print("📊 解析 Perplexity 响应...")
    data = extract_json_from_text(response_text)
    if not data:
        print("⚠️ 无法解析 JSON，生成默认数据")
        data = [{"品种及主力合约": "解析失败", "方向": "观望"}]

    records = [normalize_record(r) for r in data]
    save_suggestions_csv(records, output_path)
    print(f"✅ Perplexity 建议已保存: {output_path} ({len(records)} 条)")
    return output_path


def get_latest_prompt_file() -> Path | None:
    """获取最新的 Deep Research 提示词文件"""
    if not PLANS_DIR.exists():
        return None
    prompts = sorted(PLANS_DIR.glob("deep_research_*.md"), reverse=True)
    return prompts[0] if prompts else None


def get_prompt_file_by_date(date_str: str) -> Path | None:
    """根据日期获取提示词文件"""
    path = PLANS_DIR / f"deep_research_{date_str}.md"
    return path if path.exists() else None


def get_csv_output_path(date_str: str) -> Path:
    """获取 CSV 输出路径"""
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    return PLANS_DIR / f"perplexity_suggestion_{date_str}.csv"


def check_csv_exists(date_str: str) -> bool:
    """检查指定日期的 CSV 是否已存在"""
    return get_csv_output_path(date_str).exists()

