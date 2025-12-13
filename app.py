import gradio as gr
from shared import GAME 
from backend import (
    get_dashboard_info, 
    get_admin_dashboard_info, 
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

# === CSS 修复：强制滚动条 & 颜色 ===
custom_css = """
.dark-terminal {
    background-color: #161a25 !important;
    border: 1px solid #2a2e39 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
}
.dark-terminal h1, .dark-terminal h2, .dark-terminal h3, 
.dark-terminal p, .dark-terminal span, .dark-terminal label {
    color: #e0e0e0 !important;
}
.buy-btn { background-color: #2E7D32 !important; color: white !important; }
.sell-btn { background-color: #C62828 !important; color: white !important; }
.intel-btn { background-color: #1565C0 !important; color: white !important; }
.loan-btn { background-color: #6A1B9A !important; color: white !important; }
.msg-btn { background-color: #455A64 !important; color: white !important; }
button { border-radius: 8px !important; }

/* === 核心修复：强制显示滚动条并固定高度 === */
.scroll-box textarea {
    height: 300px !important;     /* 固定高度 */
    max_height: 300px !important; 
    overflow-y: scroll !important; /* 强制显示垂直滚动条 */
}

/* 添加刷新按钮样式 */
.refresh-btn {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 100;
}
"""

# === 逻辑保持不变 ===

def login_ui(email, name):
    if not email or not name: return gr.update(visible=True), gr.update(visible=False), "请输入信息"
    if email not in GAME.players:
        success, message = GAME.register(email, name)
        if not success: return gr.update(visible=True), gr.update(visible=False), message
    return gr.update(visible=False), gr.update(visible=True), f"欢迎, {name}"

# 跟踪上次更新K线图的时间
last_kline_update = {"hour": -1, "plot": None}

def draw_kline_chart(game_instance):
    from backend import draw_kline_chart as backend_draw_kline
    return backend_draw_kline(game_instance)

def update_dashboard(email):
    # backend 返回 8 个数据，注意不需要 visible 更新了
    status, price, trend, logs, messages, leaderboard_df, _, hint_text = get_dashboard_info(GAME, email)
    
    # 只有当游戏时间发生变化时才更新K线图，否则使用缓存的图表
    current_hour = GAME.game_clock
    if current_hour != last_kline_update["hour"] or last_kline_update["plot"] is None:
        # 更新K线图并缓存
        plot = draw_kline_chart(GAME)
        last_kline_update["hour"] = current_hour
        last_kline_update["plot"] = plot
    else:
        # 使用缓存的K线图
        plot = last_kline_update["plot"]
    
    return status, price, trend, logs, messages, leaderboard_df, plot, hint_text

def common_action(func, email, *args):
    if GAME.phase != "交易阶段":
        res = get_dashboard_info(GAME, email) 
        return *res[:7], res[7], "❌ 交易未开启"
    result_text = func(email, *args)
    res = get_dashboard_info(GAME, email)
    return *res[:7], res[7], result_text

# 动作绑定
def buy_action(email, qty): return common_action(GAME.buy_stock, email, qty)
def sell_action(email, qty): return common_action(GAME.sell_stock, email, qty)
def intel_action(email, direction): return common_action(GAME.purchase_intel, email, direction)
def loan_action(email, amount): return common_action(GAME.take_loan, email, amount)
def post_message_action(email, msg): 
    if not msg.strip(): 
        res = get_dashboard_info(GAME, email)
        return *res[:7], res[7], "内容为空"
    return common_action(GAME.post_message, email, msg)

def update_admin_dashboard():
    return get_admin_dashboard_info(GAME)

# ==========================================
# 界面 1: 玩家端 (Public UI) - Port 8001
# ==========================================
with gr.Blocks(title="暗仓: 看不见的手") as public_app:
    user_email_state = gr.State("") 
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    with gr.Group(visible=True) as login_group:
        with gr.Row():
            email_input = gr.Textbox(label="电子邮箱", placeholder="user@test.com")
            name_input = gr.Textbox(label="操盘代号", placeholder="Trader X")
        login_btn = gr.Button("接入交易网络", variant="primary")
        login_msg = gr.Markdown("")

    with gr.Group(visible=False) as game_group:
        # 添加刷新按钮到右上角
        with gr.Row():
            gr.Markdown("## 📉 暗仓 (Dark Pool) - 模拟交易终端")
            refresh_btn = gr.Button("🔄 刷新", elem_classes="refresh-btn")
        
        with gr.Group(elem_classes="dark-terminal"):
            with gr.Row():
                with gr.Column(scale=2): status_display = gr.Markdown("加载中...")
                with gr.Column(scale=1): price_display = gr.Markdown("Price")
            with gr.Row():
                with gr.Column(scale=3): kline_chart = gr.Plot(label="Market Data")
                with gr.Column(scale=1): trend_display = gr.Markdown("情报加载中...")
        
        with gr.Group():
            hint_display = gr.Markdown("💡 提示: 等待行情更新...", elem_id="hint-box")
            with gr.Row():
                with gr.Column(scale=1):
                    buy_qty_box = gr.Number(label="买入数量", value=100)
                    buy_btn = gr.Button("买入 (Long)", elem_classes="buy-btn")
                with gr.Column(scale=1):
                    sell_qty_box = gr.Number(label="卖出数量", value=100)
                    sell_btn = gr.Button("卖出/做空 (Short)", elem_classes="sell-btn")
                with gr.Column(scale=1):
                    intel_direction = gr.Radio(["看涨", "看跌"], label="方向", value="看涨")
                    intel_btn = gr.Button("购买舆情 ($5k)", elem_classes="intel-btn")
                with gr.Column(scale=1):
                    loan_amount = gr.Number(label="贷款金额", value=10000)
                    loan_btn = gr.Button("申请高利贷 (30%)", elem_classes="loan-btn")
            
            action_result = gr.Markdown("准备就绪...")
            gr.Markdown("---")
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### 💬 交易员大厅")
                    # 应用 .scroll-box 样式
                    message_display = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
                    with gr.Row():
                        message_input = gr.Textbox(show_label=False, placeholder="输入消息...", scale=4)
                        send_msg_btn = gr.Button("发送", scale=1, elem_classes="msg-btn")
                with gr.Column(scale=1):
                    gr.Markdown("### 📟 News Ticker")
                    # 应用 .scroll-box 样式
                    log_display = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
            
            # 排行榜始终可见，解决跳动问题
            gr.Markdown("### 🏆 实时/最终 排行榜")
            leaderboard_table = gr.Dataframe(
                headers=["排名", "玩家", "身份", "资产", "状态"],
                visible=True, # 始终可见，为空时只显示表头
                interactive=False
            )
            # Output 移除了 visible update
    refresh_outs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_table, kline_chart, hint_display]
    common_outs = [*refresh_outs, action_result]

    login_btn.click(login_ui, [email_input, name_input], [login_group, game_group, login_msg]).then(
        fn=lambda e: e, inputs=email_input, outputs=user_email_state
    ).then(update_dashboard, user_email_state, refresh_outs)
    
    # 手动刷新按钮，替代原来的定时器
    refresh_btn.click(update_dashboard, user_email_state, refresh_outs)
    
    buy_btn.click(buy_action, [user_email_state, buy_qty_box], common_outs)
    sell_btn.click(sell_action, [user_email_state, sell_qty_box], common_outs)
    intel_btn.click(intel_action, [user_email_state, intel_direction], common_outs)
    loan_btn.click(loan_action, [user_email_state, loan_amount], common_outs)
    send_msg_btn.click(post_message_action, [user_email_state, message_input], common_outs).then(lambda: "", None, message_input)


# ==========================================
# 界面 2: 管理员端 (Admin UI) - Port 7001
# ==========================================
with gr.Blocks(title="暗仓: 上帝控制台", css=custom_css) as admin_app:
    with gr.Group():
        with gr.Row():
            gr.Markdown("# 🛠️ 上帝控制台 (Admin Panel)")
            admin_refresh_btn = gr.Button("🔄 刷新", elem_classes="refresh-btn")
    
    with gr.Row():
        with gr.Column(scale=3):
            admin_kline = gr.Plot(label="全局行情监控")
        with gr.Column(scale=1):
            admin_status = gr.Markdown("状态: ---")
            admin_start_btn = gr.Button("🚀 强制开始游戏", variant="primary")
            admin_skip_btn = gr.Button("⏭️ 跳过 1 小时")
            admin_skip_all_btn = gr.Button("⏩ 快进至结局")
            admin_restart_btn = gr.Button("🔄 重置/新游戏")
            admin_out_text = gr.Markdown("") 

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 👥 玩家资产")
            admin_player_table = gr.Dataframe(
                headers=["代号", "邮箱", "身份", "现金", "持仓", "净值", "状态"],
                interactive=False
            )
        with gr.Column(scale=1):
            gr.Markdown("### 📟 日志 & 舆情")
            # 应用 .scroll-box 样式
            admin_logs = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
        with gr.Column(scale=1):
            gr.Markdown("### 💬 玩家对话监控")
            # 新增：管理员查看对话
            admin_messages = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
    
    # 绑定操作
    admin_outputs = [admin_kline, admin_player_table, admin_logs, admin_messages, admin_status]
    
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    
    # 管理员端也使用手动刷新
    admin_refresh_btn.click(update_admin_dashboard, outputs=admin_outputs)

# ==========================================
# 启动逻辑
# ==========================================
if __name__ == "__main__":
    print("正在启动双端服务...")
    print("1. 玩家端 (Public): http://localhost:8001")
    print("2. 管理端 (Admin):  http://localhost:7001 (请保密)")
    
    admin_app.launch(
        server_name="0.0.0.0", 
        server_port=7001, 
        prevent_thread_lock=True, 
        share=False,
        theme=gr.themes.Soft()
    )
    
    public_app.launch(
        server_name="0.0.0.0", 
        server_port=8001, 
        share=False, 
        css=custom_css
    )