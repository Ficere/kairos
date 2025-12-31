"""Kairos API 服务 - 为微信小程序提供数据接口"""
import csv
import json
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from platformdirs import user_data_dir

app = FastAPI(title="Kairos API", version="1.0.0")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_plans_dir() -> Path:
    """获取 plans 目录路径"""
    return Path(user_data_dir("kairos", "kairos")) / "plans"


def get_date_str(date: str | None) -> str:
    """获取日期字符串，默认今天"""
    return date or datetime.now().strftime("%Y-%m-%d")


def load_decisions(date_str: str) -> tuple[list[dict], list[dict], str]:
    """加载所有 decision 文件，返回 (decisions, switches, generated_at)"""
    day_dir = get_plans_dir() / date_str
    if not day_dir.exists():
        return [], [], ""
    decisions, switches, generated_at = [], [], ""
    for f in day_dir.iterdir():
        if f.name.endswith("_decision.json"):
            with open(f, "r", encoding="utf-8") as fp:
                d = json.load(fp)
                decisions.append(d)
                if not generated_at and d.get("timestamp"):
                    generated_at = d["timestamp"][:16].replace("T", " ")
                if d.get("contract_status") == "移仓中":
                    switches.append({"name": d.get("name", ""), "variety": d.get("variety", "")})
    return sorted(decisions, key=lambda x: -x.get("scores", {}).get("total", 0)), switches, generated_at


def load_perplexity_csv(date_str: str) -> list[dict]:
    """加载 Perplexity 分析 CSV 文件"""
    csv_path = get_plans_dir() / f"perplexity_suggestion_{date_str}.csv"
    if not csv_path.exists():
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


@app.get("/api/dates")
def get_available_dates():
    """获取可用的历史日期列表"""
    dates = []
    plans_dir = get_plans_dir()
    if plans_dir.exists():
        for item in plans_dir.iterdir():
            if item.is_dir() and len(item.name) == 10:  # YYYY-MM-DD
                dates.append(item.name)
    return {"dates": sorted(dates, reverse=True)[:30]}


@app.get("/api/perplexity/dates")
def get_perplexity_dates():
    """获取有 Perplexity 分析数据的日期列表"""
    dates = []
    plans_dir = get_plans_dir()
    if plans_dir.exists():
        for f in plans_dir.iterdir():
            if f.name.startswith("perplexity_suggestion_") and f.name.endswith(".csv"):
                date_str = f.name.replace("perplexity_suggestion_", "").replace(".csv", "")
                if len(date_str) == 10:
                    dates.append(date_str)
    return {"dates": sorted(dates, reverse=True)}


@app.get("/api/perplexity")
def get_perplexity_analysis(date: str | None = None):
    """获取 Perplexity 宏观面分析结果"""
    date_str = get_date_str(date)
    rows = load_perplexity_csv(date_str)
    return {"date": date_str, "total": len(rows), "suggestions": rows}


@app.get("/api/summary")
def get_summary(date: str | None = None):
    """获取汇总信息（含移仓列表）"""
    date_str = get_date_str(date)
    decisions, switches, _ = load_decisions(date_str)
    longs = [d["contract"] for d in decisions if d.get("decision", {}).get("direction") == "做多"]
    shorts = [d["contract"] for d in decisions if d.get("decision", {}).get("direction") == "做空"]
    return {"date": date_str, "success": len(decisions), "switches": switches,
            "long_signals": longs, "short_signals": shorts}


@app.get("/api/results")
def get_results(date: str | None = None, direction: str | None = None):
    """获取指定日期的分析结果"""
    date_str = get_date_str(date)
    decisions, switches, generated_at = load_decisions(date_str)

    # 筛选方向
    if direction and direction != "总计":
        decisions = [d for d in decisions if d.get("decision", {}).get("direction") == direction]

    # 格式化返回数据（从 technical_signals 获取指标摘要）
    results = []
    for d in decisions:
        signals = d.get("technical_signals", [])
        signal_str = ", ".join(signals[:3]) if signals else "-"

        results.append({
            "contract": d.get("display_contract", d.get("contract", "")),
            "status": d.get("contract_status", "稳定"),
            "name": d.get("name", ""),
            "price": d.get("current_price", 0),
            "direction": d.get("decision", {}).get("direction", "观望"),
            "score": d.get("scores", {}).get("total", 0),
            "signals": signal_str,
            "confidence": d.get("decision", {}).get("confidence", "-"),
        })

    return {"date": date_str, "generated_at": generated_at, "total": len(results),
            "switches": switches, "results": results}


@app.get("/api/detail/{contract}")
def get_detail(contract: str, date: str | None = None):
    """获取单个品种的详细信息"""
    date_str = get_date_str(date)
    decisions, _, _ = load_decisions(date_str)
    for d in decisions:
        if d.get("contract") == contract or d.get("display_contract") == contract:
            return {"date": date_str, "data": d}
    raise HTTPException(status_code=404, detail=f"未找到合约 {contract}")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """启动 API 服务器"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()

