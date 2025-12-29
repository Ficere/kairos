"""期货分析 Web 应用 - 主入口"""
from datetime import datetime
from dash import Dash, html, dcc, Input, Output, callback, ctx, ALL, State

from kairos.web.data_loader import load_results, get_perplexity_dates, load_perplexity_csv
from kairos.web.results_view import build_results_view, FILTERS
from kairos.web.perplexity_view import build_perplexity_view, build_suggestion_detail

app = Dash(__name__, title="Kairos 期货分析系统", suppress_callback_exceptions=True)


def create_layout():
    """创建页面布局"""
    decisions, switches, generated_at = load_results()
    perplexity_dates = get_perplexity_dates()
    today = datetime.now().strftime("%Y-%m-%d")
    initial_ppl_date = perplexity_dates[0] if perplexity_dates else today
    ppl_suggestions = load_perplexity_csv(initial_ppl_date)
    
    btn_style = {"padding": "10px 20px", "color": "white", "border": "none", "borderRadius": "5px", 
                 "cursor": "pointer", "marginRight": "10px"}
    time_info = f"🕐 {generated_at.split(' ')[1]}" if generated_at and ' ' in generated_at else ""
    
    tab_style = {"padding": "12px 25px", "cursor": "pointer", "borderBottom": "3px solid transparent"}
    tab_selected = {**tab_style, "borderBottom": "3px solid #3498db", "fontWeight": "bold"}
    
    return html.Div([
        html.H1("📈 Kairos 期货分析系统", style={"textAlign": "center", "color": "#2c3e50"}),
        html.Div(f"📅 {today}  {time_info}", style={"textAlign": "center", "color": "#7f8c8d", "marginBottom": "10px"}),
        
        # Tab 导航
        html.Div([
            html.Button("📊 技术分析", id="tab-technical", n_clicks=1, style=tab_selected),
            html.Button("🔍 宏观面分析", id="tab-perplexity", n_clicks=0, style=tab_style),
        ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px", "borderBottom": "1px solid #eee"}),
        
        # 操作按钮
        html.Div([
            html.Button("🔄 刷新", id="refresh-btn", n_clicks=0, style={**btn_style, "backgroundColor": "#27ae60"}),
            html.Button("📥 导出", id="export-btn", n_clicks=0, style={**btn_style, "backgroundColor": "#3498db"}),
        ], style={"textAlign": "center", "margin": "15px"}),
        
        dcc.Download(id="download-excel"),
        html.Div(id="switch-alert", style={"textAlign": "center", "margin": "10px"}),
        html.Div(id="status-msg", style={"textAlign": "center", "margin": "10px", "color": "#7f8c8d"}),
        
        # 数据存储
        dcc.Store(id="decisions-store", data={"decisions": decisions, "switches": switches}),
        dcc.Store(id="selected-filters", data="总计"),
        dcc.Store(id="active-tab", data="technical"),
        dcc.Store(id="perplexity-data", data={"date": initial_ppl_date, "suggestions": ppl_suggestions, "dates": perplexity_dates}),
        
        # 内容区域
        dcc.Loading(html.Div(id="main-content"), type="circle"),
    ], style={"fontFamily": "Arial, sans-serif", "maxWidth": "1200px", "margin": "0 auto", "padding": "20px"})


app.layout = create_layout


@callback(Output("active-tab", "data"), Output("tab-technical", "style"), Output("tab-perplexity", "style"),
          Input("tab-technical", "n_clicks"), Input("tab-perplexity", "n_clicks"), prevent_initial_call=True)
def switch_tab(tech_clicks, ppl_clicks):
    """切换 Tab"""
    tab_style = {"padding": "12px 25px", "cursor": "pointer", "borderBottom": "3px solid transparent"}
    tab_selected = {**tab_style, "borderBottom": "3px solid #3498db", "fontWeight": "bold"}
    
    if ctx.triggered_id == "tab-perplexity":
        return "perplexity", tab_style, tab_selected
    return "technical", tab_selected, tab_style


@callback(Output("main-content", "children"),
          Input("active-tab", "data"), Input("decisions-store", "data"),
          Input("selected-filters", "data"), Input("perplexity-data", "data"))
def render_content(active_tab, store_data, current_filter, ppl_data):
    """渲染主内容区域"""
    if active_tab == "perplexity":
        return build_perplexity_view(ppl_data.get("suggestions", []), ppl_data.get("date", ""), ppl_data.get("dates", []))
    decisions = store_data.get("decisions", []) if isinstance(store_data, dict) else store_data
    return build_results_view(decisions, current_filter)


@callback(Output("perplexity-data", "data"),
          Input("perplexity-date-selector", "value"), State("perplexity-data", "data"), prevent_initial_call=True)
def update_perplexity_date(selected_date, current_data):
    """更新 Perplexity 数据日期"""
    if not selected_date:
        return current_data
    suggestions = load_perplexity_csv(selected_date)
    return {"date": selected_date, "suggestions": suggestions, "dates": current_data.get("dates", [])}


@callback(Output("perplexity-detail", "children"),
          Input("perplexity-table", "selected_rows"), State("perplexity-data", "data"), prevent_initial_call=True)
def show_perplexity_detail(selected_rows, ppl_data):
    """显示 Perplexity 建议详情"""
    if not selected_rows:
        return build_suggestion_detail(None)
    suggestions = ppl_data.get("suggestions", [])
    if selected_rows[0] < len(suggestions):
        return build_suggestion_detail(suggestions[selected_rows[0]])
    return build_suggestion_detail(None)


@callback(Output("decisions-store", "data"), Output("status-msg", "children"),
          Input("refresh-btn", "n_clicks"), prevent_initial_call=True)
def handle_refresh(n_clicks):
    """刷新结果"""
    decisions, switches, generated_at = load_results()
    count = len(decisions)
    time_info = f" | 数据生成于 {generated_at}" if generated_at else ""
    msg = f"✅ 已刷新 ({datetime.now().strftime('%H:%M:%S')}) - 共 {count} 条记录{time_info}" if count else "📭 暂无今日分析结果"
    return {"decisions": decisions, "switches": switches}, msg


@callback(Output("switch-alert", "children"), Input("decisions-store", "data"))
def update_switch_alert(store_data):
    """更新移仓提示"""
    switches = store_data.get("switches", []) if isinstance(store_data, dict) else []
    if not switches:
        return ""
    alerts = [html.Span(f"⚠️ {s['name']}: {s['previous_contract']} → {s['main_contract']} ", style={"marginRight": "20px"}) for s in switches]
    return html.Div(alerts, style={"backgroundColor": "#fff3cd", "padding": "10px", "borderRadius": "5px", "color": "#856404"})


@callback(Output("selected-filters", "data"), Input({"type": "filter-btn", "key": ALL}, "n_clicks"), prevent_initial_call=True)
def update_filter(n_clicks):
    """更新筛选器"""
    return ctx.triggered_id["key"] if ctx.triggered_id and any(n_clicks) else "总计"


def main():
    """启动 Web 应用"""
    print("🚀 启动 Kairos 期货分析系统 Web 应用...")
    print("   访问地址: http://127.0.0.1:8050")
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    main()

