"""
界面管理模块
"""

def get_dashboard_info(game_state, email):
    # 这是一个轮询函数，每隔几秒刷新一次界面
    if email not in game_state.players:
        return "未登录", "", "", None, None, ""
    
    p = game_state.players[email]
    
    # 计算负债（只有空头仓位才产生负债）
    debt = abs(min(0, p.stock)) * game_state.current_price
    
    # 1. 构建状态文本
    status_text = f"""
    ## 个人终端
    **ID**: {p.display_name} | **身份**: {p.role if game_state.phase != '报名阶段' else '待定'}
    **资金**: ${p.cash:.2f} | **净持仓**: {p.stock} 股 | **负债**: ${debt:.2f}
    **当前时间**: 第 {game_state.game_clock}/12 小时
    **游戏阶段**: {game_state.phase}
    """
    
    # 2. 构建价格显示 (所有玩家都显示真实股价)
    display_price = game_state.current_price
    trend_info = "数据加密中..."
    
    if game_state.phase == "交易阶段":
        # 所有玩家都显示真实股价
        price_text = f"## 当前股价: ${display_price:.2f}"
        
        if p.role == "散户":
            trend_info = "分析师预测：震荡"
        elif p.role == "操盘手":
            trend_info = f"【上帝视角】真实趋势参数: {game_state.true_trend:.2f}"
            
        # 移除散户的高级情报显示
                
    elif game_state.phase == "结算阶段":
        # 游戏结束后显示真实价格
        price_text = f"## 当前股价: ${display_price:.2f}"
        trend_info = f"最终价格: ${game_state.current_price:.2f}"
    else:
        price_text = f"## 当前股价: ${display_price:.2f}"
    
    # 3. 构建日志显示
    log_text = "\n".join(game_state.system_logs[-10:]) # 显示最近10条系统日志
    
    # 4. 构建留言板显示
    message_text = "\n".join(game_state.messages[-10:]) if game_state.messages else "暂无留言"
    
    # 5. 构建排行榜显示
    leaderboard_text = ""
    if game_state.phase == "结算阶段" and game_state.leaderboard:
        leaderboard_text = "## 🏆 最终排行榜\n"
        leaderboard_text += "| 排名 | 玩家 | 邮箱 | 身份 | 总资产 |\n"
        leaderboard_text += "|------|------|------|------|--------|\n"
        for i, player in enumerate(game_state.leaderboard, 1):
            leaderboard_text += f"| {i} | {player['name']} | {player['email']} | {player['role']} | ${player['asset']:.2f} |\n"
    
    return status_text, price_text, trend_info, log_text, message_text, leaderboard_text