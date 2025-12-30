"""Perplexity API 客户端 - 宏观面和基本面分析"""
import json
import re
import pandas as pd
from datetime import datetime
from pathlib import Path

PLANS_DIR = Path(__file__).parent.parent.parent / "plans"


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
    pd.DataFrame(records).to_csv(output_path, index=False, encoding="utf-8-sig")


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

    save_suggestions_csv(data, output_path)
    print(f"✅ Perplexity 建议已保存: {output_path} ({len(data)} 条)")
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

