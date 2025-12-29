"""技术分析结果展示组件"""
from dash import html, dcc, dash_table
import plotly.graph_objects as go

FILTERS = {"做多": "#27ae60", "做空": "#e74c3c", "观望": "#95a5a6", "总计": "#3498db"}
STATUS_ICONS = {"主力": "🔥", "移仓中": "📦", "稳定": "✅"}


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
    macd = ti.get("macd", {})
    kdj = ti.get("kdj", {})
    rsi = ti.get("rsi", {})
    div = ti.get("divergence", {})
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
    
    stats = html.Div(
        [create_stat_card(k, counts[k], v, is_all or k == current_filter) for k, v in FILTERS.items()],
        style={"display": "flex", "justifyContent": "center", "gap": "20px", "marginBottom": "30px"})
    
    def get_conf(dec): return dec.get("confidence", dec.get("position", "-"))
    def get_ctr(d): return d.get("display_contract", d.get("contract", "-"))
    def get_status(d):
        s = d.get("contract_status", "稳定")
        return f"{STATUS_ICONS.get(s, '✅')} {s}"
    
    table_data = []
    for d in filtered:
        macd, kdj, rsi, div = format_indicators(d)
        table_data.append({
            "合约": get_ctr(d), "状态": get_status(d), "名称": d["name"],
            "价格": f'{d["current_price"]:.2f}', "方向": d["decision"]["direction"],
            "评分": d["scores"]["total"], "MACD": macd, "KDJ": kdj, "RSI": rsi,
            "背离信号": div, "确定性": get_conf(d["decision"])})
    
    cols = ["合约", "状态", "名称", "价格", "方向", "评分", "MACD", "KDJ", "RSI", "背离信号", "确定性"]
    table = dash_table.DataTable(
        data=table_data, columns=[{"name": c, "id": c} for c in cols],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "8px", "fontSize": "13px"},
        style_header={"backgroundColor": "#3498db", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": '{方向} = "做多"'}, "backgroundColor": "#d5f5e3"},
            {"if": {"filter_query": '{方向} = "做空"'}, "backgroundColor": "#fadbd8"},
            {"if": {"filter_query": '{状态} contains "移仓中"'}, "backgroundColor": "#fff3cd"}],
        sort_action="native", filter_action="native", page_size=20)
    
    fig = go.Figure(data=[go.Histogram(x=[d["scores"]["total"] for d in filtered], nbinsx=20, marker_color="#3498db")])
    fig.update_layout(title="评分分布", xaxis_title="综合评分", yaxis_title="数量", height=300)
    
    return html.Div([
        stats,
        html.H3("📋 分析结果", style={"color": "#2c3e50"}),
        table,
        html.H3("📊 评分分布", style={"color": "#2c3e50", "marginTop": "30px"}),
        dcc.Graph(figure=fig)])

