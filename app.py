import gradio as gr
import time
from shared import GAME  # <--- 核心：从 shared 导入全局唯一的游戏对象
from backend import (
    get_dashboard_info, 
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

# --- 1. 逻辑封装层 ---

def login_ui(email, name):
    if not email or not name:
        return gr.update(visible=True), gr.update(visible=False), "请输入邮箱和昵称"
    
    # 尝试注册
    if email not in GAME.players:
        success, message = GAME.register(email, name)
        if not success:
            return gr.update(visible=True), gr.update(visible=False), message
    
    return gr.update(visible=False), gr.update(visible=True), f"欢迎, {name}"

def update_dashboard(email):
    """定时器调用的核心刷新函数"""
    status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
    # 如果有排行榜数据，则显示排行榜，否则隐藏
    show_leaderboard = bool(leaderboard)
    return status, price, trend, logs, messages, leaderboard, gr.update(visible=show_leaderboard)

def buy_action(email, quantity):
    if GAME.phase != "交易阶段":
        # 如果游戏没开始，直接刷新界面并返回错误提示
        status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
        return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), "❌ 交易未开启"
    
    result = GAME.buy_stock(email, quantity)
    # 操作完立即刷新数据
    status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), result

def sell_action(email, quantity):
    if GAME.phase != "交易阶段":
        status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
        return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), "❌ 交易未开启"
    
    result = GAME.sell_stock(email, quantity)
    status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), result

def intel_action(email, direction):
    if GAME.phase != "交易阶段":
        status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
        return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), "❌ 交易未开启"
    
    result = GAME.purchase_intel(email, direction)
    status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), result

def post_message_action(email, message):
    if not message.strip():
        status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
        return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), "内容不能为空"
    
    result = GAME.post_message(email, message)
    status, price, trend, logs, messages, leaderboard = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard, gr.update(visible=False), result


# --- 2. 界面构建 ---

with gr.Blocks(title="暗仓: 看不见的手", theme=gr.themes.Monochrome()) as demo:
    
    # Session 状态：存储当前用户的邮箱
    user_email_state = gr.State("") 
    
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    # === 登录页 ===
    with gr.Group(visible=True) as login_group:
        with gr.Row():
            email_input = gr.Textbox(label="电子邮箱 (唯一ID)", placeholder="user@example.com")
            name_input = gr.Textbox(label="操盘代号 (昵称)", placeholder="Mr. Big")
        login_btn = gr.Button("接入交易网络", variant="primary")
        login_msg = gr.Markdown("")

    # === 游戏主页 (默认隐藏) ===
    with gr.Group(visible=False) as game_group:
        
        # 顶部状态栏
        with gr.Row():
            status_display = gr.Markdown("加载中...")
            price_display = gr.Markdown("股价加载中...")
        
        with gr.Row():
            trend_display = gr.Markdown("情报加载中...")
            
        gr.Markdown("---")
        
        # 操作区
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 🟢 买入 (做多)")
                buy_quantity = gr.Number(label="数量", value=100, precision=0, minimum=1)
                buy_btn = gr.Button("买入股票", variant="secondary")
            
            with gr.Column(scale=1):
                gr.Markdown("#### 🔴 卖出 (做空)")
                sell_quantity = gr.Number(label="数量", value=100, precision=0, minimum=1)
                sell_btn = gr.Button("卖出/做空", variant="stop")
            
            with gr.Column(scale=1):
                gr.Markdown("#### 📢 舆情操纵 ($5,000)")
                intel_direction = gr.Radio(["看涨", "看跌"], label="制造趋势", value="看涨")
                intel_btn = gr.Button("购买舆情")
        
        # 操作结果提示 (临时显示)
        action_result = gr.Markdown("准备就绪")
        
        # 信息区
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 💬 匿名留言板")
                message_display = gr.TextArea(label="实时讨论", interactive=False, lines=10, max_lines=10)
                with gr.Row():
                    message_input = gr.Textbox(show_label=False, placeholder="输入消息...", scale=4)
                    send_message_btn = gr.Button("发送", scale=1)
            
            with gr.Column(scale=1):
                gr.Markdown("### 📟 系统日志")
                log_display = gr.TextArea(label="News Ticker", interactive=False, lines=12, max_lines=12)
        
        # 排行榜（结算时显示）
        leaderboard_display = gr.Markdown("", visible=False)
        
        # 核心：定时刷新器 (每2秒同步一次)
        timer = gr.Timer(2)

    # === 管理员调试页 ===
    with gr.Accordion("🛠️ 管理员/上帝模式", open=False):
        gr.Markdown("警告：以下操作会影响全局游戏进程")
        with gr.Row():
            admin_start_btn = gr.Button("🚀 强制开始游戏")
            admin_skip_btn = gr.Button("⏭️ 跳过1小时")
            admin_skip_all_btn = gr.Button("⏩ 快进至结束")
            admin_restart_btn = gr.Button("🔄 重置游戏")
        admin_out = gr.Markdown("")

    # --- 3. 事件绑定 ---
    
    # 登录
    login_btn.click(
        login_ui, 
        inputs=[email_input, name_input], 
        outputs=[login_group, game_group, login_msg]
    ).then(
        fn=lambda e: e, inputs=email_input, outputs=user_email_state 
    ).then(
        # 登录成功后立即触发一次刷新
        update_dashboard,
        inputs=[user_email_state],
        outputs=[status_display, price_display, trend_display, log_display, message_display, leaderboard_display, leaderboard_display]
    )
    
    # 定时自动刷新 (实现多人联机的关键)
    timer.tick(
        update_dashboard,
        inputs=[user_email_state],
        outputs=[status_display, price_display, trend_display, log_display, message_display, leaderboard_display, leaderboard_display]
    )
    
    # 玩家操作 (Buy/Sell/Intel)
    # 注意：outputs 包含了 action_result 用于显示"资金不足"等提示
    common_outputs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_display, leaderboard_display, action_result]
    
    buy_btn.click(buy_action, inputs=[user_email_state, buy_quantity], outputs=common_outputs)
    sell_btn.click(sell_action, inputs=[user_email_state, sell_quantity], outputs=common_outputs)
    intel_btn.click(intel_action, inputs=[user_email_state, intel_direction], outputs=common_outputs)
    
    # 发送消息 (发送后清空输入框)
    send_message_btn.click(
        post_message_action, 
        inputs=[user_email_state, message_input], 
        outputs=common_outputs
    ).then(
        lambda: "", None, message_input
    )
    
    # 管理员操作
    # 关键逻辑：管理员操作 -> 更新后端 -> 触发前端刷新
    
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out).then(
        update_dashboard, inputs=user_email_state, outputs=common_outputs[:-1] # 除去 action_result
    )
    
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out).then(
        update_dashboard, inputs=user_email_state, outputs=common_outputs[:-1]
    )
    
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out).then(
        update_dashboard, inputs=user_email_state, outputs=common_outputs[:-1]
    )
    
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out).then(
        update_dashboard, inputs=user_email_state, outputs=common_outputs[:-1]
    )

if __name__ == "__main__":
    # 关闭 debug 模式以防单例重置，允许局域网访问
    demo.launch(server_name="0.0.0.0", share=False)