import random
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shared import GAME  

# 1. 图表绘制逻辑
def draw_kline_chart(game_instance):
    data = game_instance.kline_data
    COLOR_UP = '#ff3333'; COLOR_DOWN = '#00ff00'; BG_COLOR = '#161a25'

    if not data:
        fig = go.Figure()
        fig.update_layout(title="等待开盘数据...", template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, font=dict(color='#d1d4dc'))
        return fig

    df = pd.DataFrame(data)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Price", increasing_line_color=COLOR_UP, decreasing_line_color=COLOR_DOWN), row=1, col=1)
    vol_colors = [COLOR_UP if row['close'] >= row['open'] else COLOR_DOWN for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df['time'], y=df['volume'], marker_color=vol_colors, name="Volume"), row=2, col=1)
    fig.update_layout(title=dict(text=f"HK.8888 实时走势 (当前: ${game_instance.current_price:.2f})", font=dict(color='white', size=16)), xaxis_rangeslider_visible=False, template="plotly_dark", paper_bgcolor=BG_COLOR, plot_bgcolor=BG_COLOR, margin=dict(l=40, r=20, t=60, b=20), height=450, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#2a2e39'), yaxis2=dict(showgrid=False))
    return fig

# 2. 玩家端数据接口
def get_dashboard_info(game_instance, email):
    if email not in game_instance.players:
        empty_df = pd.DataFrame(columns=["排名", "玩家", "身份", "资产", "状态"])
        return (f"## 🚫 未登录", "请登录", "无数据", "", "", empty_df, None, "")
    
    p = game_instance.players[email]
    current_price = game_instance.current_price
    
    # 动态提示
    _, _, avail_cash, _ = p.get_margin_info(current_price)
    max_buy = int(avail_cash / (current_price * 1.05))
    if p.stock > 0: hint_text = f"💡 提示: 最大可买 {max_buy} | 持仓 {p.stock}"
    elif p.stock < 0: hint_text = f"💡 提示: 最大可买 {max_buy} | 做空 {abs(p.stock)}"
    else: hint_text = f"💡 提示: 最大可买 {max_buy} | 可空 ~{int(p.cash*2/current_price)}"

    # 状态栏 (传入 game_clock 以计算冷却)
    net_worth = p.get_net_worth(current_price)
    short_val, frozen, avail, risk_ratio = p.get_margin_info(current_price)
    status_label = p.get_account_status(current_price, game_instance.game_clock)
    
    if "正常" in status_label or "待机" in status_label: status_icon = "🟢"
    elif "冻结" in status_label or "冷却" in status_label: status_icon = "🟠"
    else: status_icon = "🔴"
    
    role_display = p.role if game_instance.phase != "报名阶段" else "等待分配"
    
    status_md = f"""
    ### {status_icon} 账户: {status_label}
    * **{p.display_name}** ({role_display}) | **净值: ${net_worth:,.0f}**
    * 购买力: ${avail:,.0f} | 冻结: ${frozen:,.0f} | 现金: ${p.cash:,.0f}
    """
    
    # 趋势
    trend_md = ""
    if game_instance.phase == "交易阶段":
        if p.role == "散户": trend_md = f"📊 **市场情绪**: 空头拥挤度 {game_instance.short_pressure*100:.0f}%"
        elif p.role == "操盘手": trend_md = f"👁️ **上帝视角**: 趋势 {game_instance.hourly_trend*100:+.2f}%/h | 动能 {game_instance.current_momentum*100:+.2f}%"
            
    price_md = f"# ${game_instance.current_price:.2f}"
    kline_plot = draw_kline_chart(game_instance)
    
    logs_str = "\n".join(game_instance.system_logs[-20:]) 
    messages_str = "\n".join(getattr(game_instance, 'messages', [])[-20:] or ["暂无留言..."])

    if game_instance.phase == "结算阶段":
        data = []
        sorted_players = sorted(game_instance.players.values(), key=lambda x: x.cash, reverse=True)
        for idx, pl in enumerate(sorted_players):
            status = "破产" if pl.cash <= 0 else "盈利"
            data.append([idx+1, pl.display_name, pl.role, f"${pl.cash:,.0f}", status])
        leaderboard_df = pd.DataFrame(data, columns=["排名", "玩家", "身份", "资产", "状态"])
    else:
        leaderboard_df = pd.DataFrame(columns=["排名", "玩家", "身份", "资产", "状态"])
            
    return status_md, price_md, trend_md, logs_str, messages_str, leaderboard_df, kline_plot, hint_text

# 3. 管理员端数据接口
def get_admin_dashboard_info(game_instance):
    kline_plot = draw_kline_chart(game_instance)
    player_data = []
    sorted_players = sorted(game_instance.players.values(), key=lambda x: x.get_net_worth(game_instance.current_price), reverse=True)
    for p in sorted_players:
        net_worth = p.get_net_worth(game_instance.current_price)
        # 传入 game_clock
        status = p.get_account_status(game_instance.current_price, game_instance.game_clock)
        player_data.append([p.display_name, p.email, p.role, f"${p.cash:,.0f}", p.stock, f"${net_worth:,.0f}", status])
    
    df = pd.DataFrame(player_data, columns=["代号", "邮箱", "身份", "现金", "持仓", "净值", "状态"])
    logs_str = "\n".join(game_instance.system_logs[-30:])
    messages_str = "\n".join(getattr(game_instance, 'messages', [])[-30:] or ["暂无留言..."])
    status_info = f"阶段: {game_instance.phase} | 时间: {game_instance.game_clock}/12h | 在线: {len(game_instance.players)}"
    return kline_plot, df, logs_str, messages_str, status_info

# 4. 管理员函数
def admin_start():
    if len(GAME.players) < 1: GAME.register("bot1@ai.com", "Bot A") 
    return GAME.start_game()
def admin_skip_time():
    if not GAME.is_running: return "❌ 游戏未开始"
    GAME.next_hour()
    return f"✅ 已跳至第 {GAME.game_clock} 小时"
def admin_skip_to_end():
    if not GAME.is_running: return "❌ 游戏未开始"
    c=0
    while GAME.game_clock<12 and c<20: GAME.next_hour(); c+=1
    return "⏩ 结束"
def admin_restart_game():
    GAME.prepare_next_round()
    return "🔄 重置"