import random
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shared import GAME  

def draw_kline_chart(game_instance):
    """
    使用 Plotly 绘制专业的 K线图 + 成交量柱状图
    """
    data = game_instance.kline_data
    
    # 如果没有数据（游戏刚开始），显示一个空的占位图
    if not data:
        fig = go.Figure()
        fig.update_layout(
            title="等待开盘数据...", 
            xaxis_title="时间 (小时)", 
            yaxis_title="价格",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)', # 透明背景
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    # 转换为 DataFrame 方便处理
    df = pd.DataFrame(data)
    
    # 创建子图：上面是K线，下面是成交量
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3]
    )

    # 1. 绘制 K线 (Candlestick)
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name="股价"
    ), row=1, col=1)

    # 2. 绘制成交量 (Volume)
    # 颜色逻辑：收盘 > 开盘 显示绿色，否则红色
    colors = ['#00ff00' if row['close'] >= row['open'] else '#ff0000' for index, row in df.iterrows()]
    
    fig.add_trace(go.Bar(
        x=df['time'],
        y=df['volume'],
        marker_color=colors,
        name="成交量"
    ), row=2, col=1)

    # 3. 样式美化
    fig.update_layout(
        title=f"HK.8888 实时走势 (当前: ${game_instance.current_price:.2f})",
        xaxis_rangeslider_visible=False, # 隐藏下方自带的滑块
        template="plotly_dark", # 黑色极客风格
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=10, t=40, b=10),
        height=400 # 固定高度
    )
    
    return fig

def get_dashboard_info(game_instance, email):
    # 1. 检查登录
    if email not in game_instance.players:
        return (
            f"## 🚫 未登录 (在线: {len(game_instance.players)})", 
            "请登录", "无数据", "", "", None, None # 多返回一个 plot 对象
        )
    
    p = game_instance.players[email]
    
    # --- 构建状态栏 ---
    current_price = game_instance.current_price
    net_worth = p.get_net_worth(current_price)
    
    short_val, frozen, avail, risk_ratio = p.get_margin_info(current_price)
    status_label = p.get_account_status(current_price)
    
    status_line = f"**账户状态**: {status_label}"
    if "正常" in status_label: status_line = f"🟢 {status_line}"
    elif "冻结" in status_label: status_line = f"🟠 {status_line}"
    else: status_line = f"🔴 {status_line} (风险率: {risk_ratio:.2f})"

    cash_detail = f"总现金: ${p.cash:,.0f}"
    if p.stock < 0: cash_detail += f" | 🔒 冻结: ${frozen:,.0f} | ✅ **可用**: ${avail:,.0f}"
    else: cash_detail += f" | ✅ **可用**: ${avail:,.0f}"

    role_display = p.role if game_instance.phase != "报名阶段" else "等待分配"
    online_str = " | ".join([pl.display_name for pl in game_instance.players.values()])
    
    status_md = f"""
    ### 👤 交易终端 | {p.display_name} ({role_display})
    {status_line}
    * **资金**: {cash_detail}
    * **持仓**: {p.stock} 股 (市值 ${p.stock * current_price:,.0f})
    * **净值**: **${net_worth:,.2f}**
    * **时间**: {game_instance.phase} (第 {game_instance.game_clock}/12 小时)
    ---
    **🌐 大厅**: {online_str}
    """
    
    # 3. 价格与趋势
    trend_md = ""
    if game_instance.phase == "交易阶段":
        if p.role == "散户":
            trend_md = f"📊 **简报**: 做空拥挤度 {game_instance.short_pressure*100:.0f}% | 交易费率 5%起"
        elif p.role == "操盘手":
            daily_proj = game_instance.hourly_trend * 12 * 100
            trend_md = f"""
            #### 👁️ 上帝视角
            * 每小时自然趋势: {game_instance.hourly_trend*100:+.2f}%
            * 全天预计偏差: {daily_proj:+.2f}%
            * 当前人为动能: {game_instance.current_momentum*100:+.2f}%
            """
            
    price_md = f"# 📈 ${game_instance.current_price:.2f}"
    
    # 4. 图表生成 (核心新增)
    kline_plot = draw_kline_chart(game_instance)
    
    # 5. 日志与排行
    logs_str = "\n".join(game_instance.system_logs[-8:]) 
    messages_str = "\n".join(getattr(game_instance, 'messages', [])[-8:] or ["暂无留言..."])

    leaderboard_md = ""
    if game_instance.phase == "结算阶段":
        sorted_players = sorted(game_instance.players.values(), key=lambda x: x.cash, reverse=True)
        leaderboard_md = "### 🏆 最终排行榜\n| 排名 | 玩家 | 邮箱 | 身份 | 资产 |\n|---|---|---|---|---|\n"
        for idx, pl in enumerate(sorted_players):
            icon = "💀" if pl.cash <= 0 else "💰"
            leaderboard_md += f"| {idx+1} | {pl.display_name} | {pl.email} | {pl.role} | {icon} ${pl.cash:,.0f} |\n"
            
    return status_md, price_md, trend_md, logs_str, messages_str, leaderboard_md, kline_plot

# 管理员功能保持不变
def admin_start():
    if len(GAME.players) < 1: GAME.register("bot1@ai.com", "Bot A") 
    return GAME.start_game()
def admin_skip_time():
    if not GAME.is_running: return "❌ 未开始"
    GAME.next_hour()
    return f"✅ 第 {GAME.game_clock} 小时"
def admin_skip_to_end():
    if not GAME.is_running: return "❌ 未开始"
    c=0
    while GAME.game_clock<12 and c<20: GAME.next_hour(); c+=1
    return "⏩ 结束"
def admin_restart_game():
    GAME.prepare_next_round()
    return "🔄 重置"