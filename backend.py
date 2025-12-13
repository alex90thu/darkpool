import random
from shared import GAME  

def get_dashboard_info(game_instance, email):
    # 1. 检查登录
    if email not in game_instance.players:
        return (
            f"## 🚫 未登录 (在线: {len(game_instance.players)})", 
            "请登录", "无数据", "", "", None
        )
    
    p = game_instance.players[email]
    
    # --- 构建状态栏 (核心修改) ---
    current_price = game_instance.current_price
    net_worth = p.get_net_worth(current_price)
    
    # 获取详细资金情况
    short_val, frozen, avail, risk_ratio = p.get_margin_info(current_price)
    status_label = p.get_account_status(current_price)
    
    # 状态栏颜色/Emoji处理
    status_line = f"**账户状态**: {status_label}"
    if "正常" in status_label:
        status_line = f"🟢 {status_line}"
    elif "冻结" in status_label:
        status_line = f"🟠 {status_line} (请平仓释放资金)"
    else: # 告急或爆仓
        status_line = f"🔴 {status_line} (风险率: {risk_ratio:.2f})"

    # 资金详情显示
    cash_detail = f"总现金: ${p.cash:,.0f}"
    if p.stock < 0:
        cash_detail += f" | 🔒 冻结: ${frozen:,.0f} | ✅ **可用购买力**: ${avail:,.0f}"
    else:
        cash_detail += f" | ✅ **可用购买力**: ${avail:,.0f}"

    role_display = p.role if game_instance.phase != "报名阶段" else "等待分配"
    online_str = " | ".join([pl.display_name for pl in game_instance.players.values()])
    
    status_md = f"""
    ### 👤 交易终端 | {p.display_name} ({role_display})
    {status_line}
    * **资金详情**: {cash_detail}
    * **持仓市值**: {p.stock} 股 (市值 ${p.stock * current_price:,.0f})
    * **当前净值**: **${net_worth:,.2f}**
    * **游戏阶段**: {game_instance.phase} (第 {game_instance.game_clock}/12 小时)
    ---
    **🌐 大厅**: {online_str}
    """
    
    # 3. 价格与趋势
    display_price = current_price
    trend_md = ""
    if game_instance.phase == "交易阶段":
        if p.role == "散户":
            trend_md = f"📊 **市场简报**: 做空拥挤度 {game_instance.short_pressure*100:.0f}% | 交易费率 5%起"
        elif p.role == "操盘手":
            daily_proj = game_instance.hourly_trend * 12 * 100
            trend_md = f"""
            #### 👁️ 上帝视角
            * 每小时自然趋势: {game_instance.hourly_trend*100:+.2f}%
            * 全天预计偏差: {daily_proj:+.2f}%
            * 当前人为动能: {game_instance.current_momentum*100:+.2f}%
            """
            
    price_md = f"# 📈 ${display_price:.2f}"
    
    # 4. 日志
    logs_str = "\n".join(game_instance.system_logs[-8:]) 
    messages_list = getattr(game_instance, 'messages', [])
    messages_str = "\n".join(messages_list[-8:]) if messages_list else "暂无留言..."

    # 5. 排行榜
    leaderboard_md = ""
    if game_instance.phase == "结算阶段":
        sorted_players = sorted(
            game_instance.players.values(), 
            key=lambda x: x.cash, 
            reverse=True
        )
        leaderboard_md = "### 🏆 最终排行榜\n| 排名 | 玩家 | 邮箱 | 身份 | 资产 |\n|---|---|---|---|---|\n"
        for idx, pl in enumerate(sorted_players):
            icon = "💀" if pl.cash <= 0 else "💰"
            leaderboard_md += f"| {idx+1} | {pl.display_name} | {pl.email} | {pl.role} | {icon} ${pl.cash:,.0f} |\n"
            
    return status_md, price_md, trend_md, logs_str, messages_str, leaderboard_md

# 管理员功能保持不变
def admin_start():
    if len(GAME.players) < 1: GAME.register("bot1@ai.com", "Bot A") 
    return GAME.start_game()

def admin_skip_time():
    if not GAME.is_running: return "❌ 游戏未开始"
    GAME.next_hour()
    return f"✅ 跳至第 {GAME.game_clock} 小时"

def admin_skip_to_end():
    if not GAME.is_running: return "❌ 游戏未开始"
    count = 0
    while GAME.game_clock < 12 and count < 20:
        GAME.next_hour()
        count += 1
    return "⏩ 加速结束"

def admin_restart_game():
    GAME.prepare_next_round()
    return "🔄 游戏已重置"