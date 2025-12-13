import random
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shared import GAME  

def draw_kline_chart(game_instance):
    """
    绘制专业的暗色系 K线图
    """
    data = game_instance.kline_data
    
    # 配色方案 (中国/加密货币习惯：红涨绿跌)
    # 如果你是美股习惯，把下面两个颜色对调即可
    COLOR_UP = '#ff3333'   # 涨 - 红
    COLOR_DOWN = '#00ff00' # 跌 - 绿
    BG_COLOR = '#161a25'   # 深色背景 (类似 TradingView)

    if not data:
        fig = go.Figure()
        fig.update_layout(
            title="等待开盘数据...", 
            xaxis_title="时间", 
            yaxis_title="价格",
            template="plotly_dark",
            paper_bgcolor=BG_COLOR,
            plot_bgcolor=BG_COLOR,
            font=dict(color='#d1d4dc')
        )
        return fig

    df = pd.DataFrame(data)
    
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.7, 0.3]
    )

    # 1. K线图
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="Price",
        increasing_line_color=COLOR_UP,
        decreasing_line_color=COLOR_DOWN
    ), row=1, col=1)

    # 2. 成交量 (颜色跟随涨跌)
    vol_colors = [COLOR_UP if row['close'] >= row['open'] else COLOR_DOWN for index, row in df.iterrows()]
    fig.add_trace(go.Bar(
        x=df['time'], y=df['volume'], 
        marker_color=vol_colors, 
        name="Volume"
    ), row=2, col=1)

    # 3. 样式精修 (去除网格，纯粹的黑底)
    fig.update_layout(
        title=dict(
            text=f"HK.8888 实时走势 (当前: ${game_instance.current_price:.2f})",
            font=dict(color='white', size=16)
        ),
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        paper_bgcolor=BG_COLOR, # 画布背景
        plot_bgcolor=BG_COLOR,  # 图表背景
        margin=dict(l=40, r=20, t=60, b=20),
        height=450,
        showlegend=False,
        # 隐藏讨厌的网格线，看起来更专业
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='#2a2e39', zeroline=False),
        yaxis2=dict(showgrid=False, zeroline=False),
    )
    
    return fig

def get_dashboard_info(game_instance, email):
    # 1. 检查登录
    if email not in game_instance.players:
        return (
            f"## 🚫 未登录 (在线: {len(game_instance.players)})", 
            "请登录", "无数据", "", "", None, None, 
            "请先登录", "请先登录"
        )
    
    p = game_instance.players[email]
    current_price = game_instance.current_price
    
    # --- 动态提示信息 ---
    _, _, avail_cash, _ = p.get_margin_info(current_price)
    max_buy = int(avail_cash / (current_price * 1.05))
    buy_hint = f"💰 最大可买: {max_buy} 股"
    
    if p.stock > 0:
        sell_hint = f"📦 持仓: {p.stock} 股"
    elif p.stock < 0:
        sell_hint = f"📉 做空: {abs(p.stock)} 股"
    else:
        max_short = int((p.cash * 2) / current_price) if p.cash > 0 else 0
        sell_hint = f"⚡ 最大可空: ~{max_short} 股"

    # --- 状态数据 ---
    net_worth = p.get_net_worth(current_price)
    short_val, frozen, avail, risk_ratio = p.get_margin_info(current_price)
    status_label = p.get_account_status(current_price)
    
    # 状态栏图标
    if "正常" in status_label: status_icon = "🟢"
    elif "冻结" in status_label: status_icon = "🟠"
    else: status_icon = "🔴"
    
    role_display = p.role if game_instance.phase != "报名阶段" else "等待分配"
    
    # 注意：这里的 Markdown 会被放入暗色背景，所以尽量不要用黑色字
    # Gradio Markdown 在暗色模式下会自动变白，但我们可以用 HTML 强制
    status_md = f"""
    ### {status_icon} 账户状态: {status_label}
    * **代号**: {p.display_name} | **身份**: {role_display}
    * **净值**: **${net_worth:,.2f}** (现金: ${p.cash:,.0f})
    * **购买力**: ${avail:,.0f} | **冻结**: ${frozen:,.0f}
    """
    
    trend_md = ""
    if game_instance.phase == "交易阶段":
        if p.role == "散户":
            trend_md = f"📊 **市场情绪**: 空头拥挤度 {game_instance.short_pressure*100:.0f}%"
        elif p.role == "操盘手":
            daily_proj = game_instance.hourly_trend * 12 * 100
            trend_md = f"""
            #### 👁️ 上帝视角
            * 趋势: {game_instance.hourly_trend*100:+.2f}%/h
            * 动能: {game_instance.current_momentum*100:+.2f}%
            """
            
    price_md = f"# ${game_instance.current_price:.2f}"
    
    kline_plot = draw_kline_chart(game_instance)
    
    logs_str = "\n".join(game_instance.system_logs[-8:]) 
    messages_str = "\n".join(getattr(game_instance, 'messages', [])[-8:] or ["暂无留言..."])

    leaderboard_md = ""
    if game_instance.phase == "结算阶段":
        sorted_players = sorted(game_instance.players.values(), key=lambda x: x.cash, reverse=True)
        leaderboard_md = "### 🏆 最终排行榜\n| 排名 | 玩家 | 身份 | 资产 |\n|---|---|---|---|\n"
        for idx, pl in enumerate(sorted_players):
            icon = "💀" if pl.cash <= 0 else "💰"
            leaderboard_md += f"| {idx+1} | {pl.display_name} | {pl.role} | {icon} ${pl.cash:,.0f} |\n"
            
    return status_md, price_md, trend_md, logs_str, messages_str, leaderboard_md, kline_plot, buy_hint, sell_hint

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