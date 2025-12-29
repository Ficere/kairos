"""Perplexity 分析结果展示组件"""
from dash import html, dcc, dash_table

# 方向对应的颜色和图标
DIRECTION_STYLES = {
    "做多": {"bg": "#d5f5e3", "icon": "🟢"},
    "做空": {"bg": "#fadbd8", "icon": "🔴"},
    "观望": {"bg": "#f8f9fa", "icon": "⚪"},
    "止损平仓": {"bg": "#fff3cd", "icon": "⚠️"},
    "减仓观望": {"bg": "#e3f2fd", "icon": "📉"},
    "震荡偏多": {"bg": "#e8f5e9", "icon": "📈"},
    "逢高做空": {"bg": "#ffebee", "icon": "🔻"},
}


def build_perplexity_view(suggestions: list, selected_date: str, available_dates: list):
    """构建 Perplexity 分析展示视图"""
    # 日期选择器
    date_selector = html.Div([
        html.Label("📅 选择日期：", style={"marginRight": "10px", "fontWeight": "bold"}),
        dcc.Dropdown(
            id="perplexity-date-selector",
            options=[{"label": d, "value": d} for d in available_dates],
            value=selected_date,
            style={"width": "200px", "display": "inline-block"},
            placeholder="选择有数据的日期",
            clearable=False,
        ),
        html.Span(f"  共 {len(suggestions)} 条建议", style={"marginLeft": "15px", "color": "#7f8c8d"}),
    ], style={"marginBottom": "20px", "display": "flex", "alignItems": "center"})
    
    if not suggestions:
        return html.Div([
            date_selector,
            html.Div([
                html.Div("📭 暂无宏观面分析结果", style={"fontSize": "20px", "marginBottom": "10px"}),
                html.Div("请选择其他日期或运行：", style={"marginBottom": "5px"}),
                html.Code("uv run kairos-perplexity", style={"backgroundColor": "#f0f0f0", "padding": "5px 10px"})
            ], style={"textAlign": "center", "color": "#95a5a6", "padding": "30px"})
        ])
    
    # 构建表格数据
    table_data = []
    for s in suggestions:
        direction = s.get("方向", "观望")
        style_info = DIRECTION_STYLES.get(direction, DIRECTION_STYLES["观望"])
        table_data.append({
            "品种": s.get("品种", ""),
            "合约": s.get("合约", ""),
            "方向": f"{style_info['icon']} {direction}",
            "最新价": s.get("最新价", "")[:30] if s.get("最新价") else "",
            "开仓区间": s.get("参考开仓价区间", ""),
            "目标价": s.get("目标价", ""),
            "止损价": s.get("止损价", ""),
            "评级": s.get("交易确定性评级", "")[:10] if s.get("交易确定性评级") else "",
        })
    
    cols = ["品种", "合约", "方向", "最新价", "开仓区间", "目标价", "止损价", "评级"]
    table = dash_table.DataTable(
        id="perplexity-table",
        data=table_data,
        columns=[{"name": c, "id": c} for c in cols],
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "10px", "fontSize": "13px", "whiteSpace": "normal"},
        style_header={"backgroundColor": "#9b59b6", "color": "white", "fontWeight": "bold"},
        style_data_conditional=[
            {"if": {"filter_query": '{方向} contains "做多"'}, "backgroundColor": "#d5f5e3"},
            {"if": {"filter_query": '{方向} contains "做空"'}, "backgroundColor": "#fadbd8"},
            {"if": {"filter_query": '{方向} contains "止损"'}, "backgroundColor": "#fff3cd"},
            {"if": {"filter_query": '{方向} contains "观望"'}, "backgroundColor": "#f8f9fa"},
        ],
        sort_action="native",
        page_size=15,
        row_selectable="single",
    )
    
    # 详情展示区域
    detail_section = html.Div(id="perplexity-detail", style={"marginTop": "20px"})
    
    return html.Div([date_selector, table, detail_section])


def build_suggestion_detail(suggestion: dict):
    """构建单个建议的详情视图"""
    if not suggestion:
        return html.Div("点击表格行查看详细分析", style={"color": "#95a5a6", "textAlign": "center", "padding": "20px"})
    
    card_style = {"backgroundColor": "#f8f9fa", "padding": "15px", "borderRadius": "8px", "marginBottom": "15px"}
    
    return html.Div([
        html.H4(f"📊 {suggestion.get('品种', '')} ({suggestion.get('合约', '')})", style={"color": "#2c3e50"}),
        html.Div([
            html.Div([
                html.Strong("技术面分析："),
                html.P(suggestion.get("技术面简述", "暂无"), style={"margin": "5px 0", "lineHeight": "1.6"}),
            ], style=card_style),
            html.Div([
                html.Strong("消息面/基本面分析："),
                html.P(suggestion.get("消息面简述", "暂无"), style={"margin": "5px 0", "lineHeight": "1.6"}),
            ], style=card_style),
        ])
    ])

