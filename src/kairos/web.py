"""期货分析 Web 应用 - 纯展示模式（数据由后端定时任务更新）"""
import io
import json
import os
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, callback, dash_table, ctx, ALL
import pandas as pd
import plotly.graph_objects as go

app = Dash(__name__, title="Kairos 期货分析系统", suppress_callback_exceptions=True)
FILTERS = {"做多": "#27ae60", "做空": "#e74c3c", "观望": "#95a5a6", "总计": "#3498db"}
STATUS_ICONS = {"主力": "🔥", "移仓中": "📦", "稳定": "✅"}


def get_output_dir() -> str:
    return f"plans/{datetime.now().strftime('%Y-%m-%d')}"


def load_results() -> tuple[list, list]:
    """加载今日分析结果，返回 (decisions, switches)"""
    output_dir = get_output_dir()
    date_str = datetime.now().strftime("%Y-%m-%d")
    decisions, switches = [], []
    # 从 plans/ 根目录加载 summary
    summary_path = os.path.join("plans", f"summary_{date_str}.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as fp:
            switches = json.load(fp).get("switches", [])
    # 从日期目录加载 decisions
    if os.path.exists(output_dir):
        for f in os.listdir(output_dir):
            if f.endswith("_decision.json"):
                with open(os.path.join(output_dir, f), "r", encoding="utf-8") as fp:
                    decisions.append(json.load(fp))
    return sorted(decisions, key=lambda x: -x["scores"]["total"]), switches


def create_layout():
    """创建页面布局 - 纯展示模式"""
    decisions, switches = load_results()
    btn_style = {"padding": "10px 20px", "color": "white", "border": "none", "borderRadius": "5px", "cursor": "pointer", "marginRight": "10px"}
    return html.Div([
        html.H1("📈 Kairos 期货分析系统", style={"textAlign": "center", "color": "#2c3e50"}),
        html.Div([
            html.Button("🔄 刷新结果", id="refresh-btn", n_clicks=0, style={**btn_style, "backgroundColor": "#27ae60"}),
            html.Button("📥 导出 Excel", id="export-btn", n_clicks=0, style={**btn_style, "backgroundColor": "#3498db"}),
        ], style={"textAlign": "center", "margin": "20px"}),
        dcc.Download(id="download-excel"),
        html.Div(id="switch-alert", style={"textAlign": "center", "margin": "10px"}),
        html.Div(id="status-msg", style={"textAlign": "center", "margin": "10px", "color": "#7f8c8d"}),
        dcc.Store(id="decisions-store", data={"decisions": decisions, "switches": switches}),
        dcc.Store(id="selected-filters", data="总计"),
        dcc.Loading(html.Div(id="results-container"), type="circle"),
    ], style={"fontFamily": "Arial, sans-serif", "maxWidth": "1200px", "margin": "0 auto", "padding": "20px"})


def create_stat_card(key: str, value: int, color: str, highlighted: bool):
    """创建统计卡片"""
    icons = {"做多": "🟢", "做空": "🔴", "观望": "⚪", "总计": "📊"}
    border = f"3px solid {color}" if highlighted else "3px solid transparent"
    opacity = "1" if highlighted else "0.6"
    return html.Button(
        [html.Div(f"{icons[key]} {key}", style={"fontSize": "14px", "color": "#7f8c8d"}),
         html.Div(str(value), style={"fontSize": "32px", "fontWeight": "bold", "color": color})],
        id={"type": "filter-btn", "key": key}, n_clicks=0,
        style={"backgroundColor": "white", "padding": "20px 40px", "borderRadius": "10px", "border": border,
               "boxShadow": "0 2px 10px rgba(0,0,0,0.1)", "textAlign": "center", "cursor": "pointer",
               "opacity": opacity, "transition": "all 0.2s"})


def format_indicators(d: dict) -> tuple:
    """格式化技术指标"""
    ti = d.get("technical_indicators", {})
    if not ti:
        return ("-", "-", "-", "⚪无")
    macd, kdj, rsi, div = ti.get("macd", {}), ti.get("kdj", {}), ti.get("rsi", {}), ti.get("divergence", {})
    macd_str = f"DIF:{macd.get('dif', 0):.2f} DEA:{macd.get('dea', 0):.2f}" if macd else "-"
    kdj_str = f"K:{int(kdj.get('k', 0))} D:{int(kdj.get('d', 0))} J:{int(kdj.get('j', 0))}" if kdj else "-"
    rsi_str = f"RSI:{int(rsi.get('value', 0))}" if rsi else "-"
    div_type, div_ind = div.get("type", "无背离"), div.get("indicator", "")
    div_str = f"🔴顶背离({div_ind})" if div_type == "顶背离" else f"🟢底背离({div_ind})" if div_type == "底背离" else "⚪无"
    return (macd_str, kdj_str, rsi_str, div_str)


def build_results_view(decisions: list, current_filter: str):
    """构建结果视图"""
    if not decisions:
        return html.Div([
            html.Div("📭 暂无今日分析结果", style={"fontSize": "24px", "marginBottom": "10px"}),
            html.Div("请等待后端定时任务执行，或手动运行：", style={"marginBottom": "5px"}),
            html.Code("uv run kairos-analyze --all", style={"backgroundColor": "#f0f0f0", "padding": "5px 10px"})
        ], style={"textAlign": "center", "color": "#95a5a6", "padding": "50px"})
    counts = {"做多": 0, "做空": 0, "观望": 0, "总计": len(decisions)}
    for d in decisions:
        counts[d["decision"]["direction"]] = counts.get(d["decision"]["direction"], 0) + 1
    is_all = (current_filter == "总计")
    filtered = decisions if is_all else [d for d in decisions if d["decision"]["direction"] == current_filter]
    stats = html.Div([create_stat_card(k, counts[k], v, is_all or k == current_filter) for k, v in FILTERS.items()],
                     style={"display": "flex", "justifyContent": "center", "gap": "20px", "marginBottom": "30px"})
    def get_conf(dec): return dec.get("confidence", dec.get("position", "-"))
    def get_ctr(d): return d.get("display_contract", d.get("contract", "-"))
    def get_status(d):
        s = d.get("contract_status", "稳定")
        return f"{STATUS_ICONS.get(s, '✅')} {s}"
    table_data = []
    for d in filtered:
        macd, kdj, rsi, div = format_indicators(d)
        table_data.append({"合约": get_ctr(d), "状态": get_status(d), "名称": d["name"],
                           "价格": f'{d["current_price"]:.2f}', "方向": d["decision"]["direction"],
                           "评分": d["scores"]["total"], "MACD": macd, "KDJ": kdj, "RSI": rsi,
                           "背离信号": div, "确定性": get_conf(d["decision"])})
    cols = ["合约", "状态", "名称", "价格", "方向", "评分", "MACD", "KDJ", "RSI", "背离信号", "确定性"]
    table = dash_table.DataTable(
        data=table_data, columns=[{"name": c, "id": c} for c in cols],
        style_table={"overflowX": "auto"}, style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px"},
        style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[{"if": {"filter_query": '{方向} = "做多"'}, "backgroundColor": "#d5f5e3"},
                                {"if": {"filter_query": '{方向} = "做空"'}, "backgroundColor": "#fadbd8"},
                                {"if": {"filter_query": '{状态} contains "移仓中"'}, "backgroundColor": "#fff3cd"}],
        sort_action="native", filter_action="native", page_size=20)
    fig = go.Figure(data=[go.Histogram(x=[d["scores"]["total"] for d in filtered], nbinsx=20, marker_color="#3498db")])
    fig.update_layout(title="评分分布", xaxis_title="综合评分", yaxis_title="数量", height=300)
    return html.Div([stats, html.H3("📋 分析结果", style={"color": "#2c3e50"}), table,
                     html.H3("📊 评分分布", style={"color": "#2c3e50", "marginTop": "30px"}), dcc.Graph(figure=fig)])


app.layout = create_layout


@callback(Output("decisions-store", "data"), Output("status-msg", "children"),
          Input("refresh-btn", "n_clicks"), prevent_initial_call=True)
def handle_refresh(n_clicks):
    """刷新结果（仅重新读取文件，不触发分析）"""
    decisions, switches = load_results()
    count = len(decisions)
    msg = f"✅ 已刷新 ({datetime.now().strftime('%H:%M:%S')}) - 共 {count} 条记录" if count else "📭 暂无今日分析结果"
    return {"decisions": decisions, "switches": switches}, msg


def build_export_data(decisions: list, current_filter: str) -> list[dict]:
    """构建导出数据"""
    filtered = decisions if current_filter == "总计" else [d for d in decisions if d["decision"]["direction"] == current_filter]
    rows = []
    for d in filtered:
        macd, kdj, rsi, div = format_indicators(d)
        rows.append({"合约": d.get("display_contract", d.get("contract", "-")),
                     "状态": d.get("contract_status", "稳定"), "名称": d["name"],
                     "价格": d["current_price"], "方向": d["decision"]["direction"],
                     "评分": d["scores"]["total"], "MACD": macd, "KDJ": kdj, "RSI": rsi,
                     "背离信号": div.replace("🔴", "").replace("🟢", "").replace("⚪", ""),
                     "确定性": d["decision"].get("confidence", d["decision"].get("position", "-"))})
    return rows


@callback(Output("download-excel", "data"), Input("export-btn", "n_clicks"),
          Input("decisions-store", "data"), Input("selected-filters", "data"), prevent_initial_call=True)
def export_excel(n_clicks, store_data, current_filter):
    """导出 Excel 文件"""
    if ctx.triggered_id != "export-btn":
        return None
    decisions = store_data.get("decisions", []) if isinstance(store_data, dict) else store_data
    if not decisions:
        return None
    rows = build_export_data(decisions, current_filter)
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)
    filename = f"kairos_分析结果_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"
    return dcc.send_bytes(output.getvalue(), filename)


@callback(Output("switch-alert", "children"), Input("decisions-store", "data"))
def update_switch_alert(store_data):
    switches = store_data.get("switches", []) if isinstance(store_data, dict) else []
    if not switches:
        return ""
    alerts = [html.Span(f"⚠️ {s['name']}: {s['previous_contract']} → {s['main_contract']} ", style={"marginRight": "20px"}) for s in switches]
    return html.Div(alerts, style={"backgroundColor": "#fff3cd", "padding": "10px", "borderRadius": "5px", "color": "#856404"})


@callback(Output("selected-filters", "data"), Input({"type": "filter-btn", "key": ALL}, "n_clicks"), prevent_initial_call=True)
def update_filter(n_clicks):
    return ctx.triggered_id["key"] if ctx.triggered_id and any(n_clicks) else "总计"


@callback(Output("results-container", "children"), Input("decisions-store", "data"), Input("selected-filters", "data"))
def render_results(store_data, current_filter):
    decisions = store_data.get("decisions", []) if isinstance(store_data, dict) else store_data
    return build_results_view(decisions, current_filter)


if __name__ == "__main__":
    print("🚀 启动 Kairos 期货分析系统 Web 应用...")
    print("   访问地址: http://127.0.0.1:8050")
    app.run(debug=True, host="0.0.0.0", port=8050)

