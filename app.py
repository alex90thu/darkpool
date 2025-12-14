import gradio as gr
import os
from shared import GAME 
from backend import (
    get_dashboard_info, 
    get_admin_dashboard_info,
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

# === 自定义 CSS ===
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
.scroll-box textarea {
    height: 300px !important;     
    max_height: 300px !important; 
    overflow-y: scroll !important; 
}
/* 魔法链接样式 */
.magic-link {
    background-color: #e3f2fd;
    padding: 10px;
    border-radius: 5px;
    border: 1px solid #2196f3;
    color: #0d47a1;
    font-weight: bold;
    text-align: center;
    margin-top: 10px;
}
/* 登录页图片样式：居中，限制高度防止太占地 */
.login-img {
    display: flex;
    justify-content: center;
    align-items: center;
    margin-bottom: 20px;
}
.login-img img {
    max-height: 300px; /* 限制最大高度，可按需调整 */
    object-fit: contain;
}
"""

# ==========================================
# 1. 核心逻辑 (URL Token 自动登录)
# ==========================================

def auto_login_logic(request: gr.Request):
    """
    页面加载时：检查URL中是否有 token 参数
    """
    if not request: return gr.update(visible=True), gr.update(visible=False), "", "", "", ""
    
    params = request.query_params
    token = params.get("token")
    
    print(f"[DEBUG-PY] 收到请求 IP: {request.client.host}, 参数: {params}")
    
    if token:
        player = GAME.get_user_by_token(token)
        if player:
            print(f"[DEBUG-PY] Token {token} 验证成功，登录用户: {player.email}")
            return (
                gr.update(visible=False), 
                gr.update(visible=True),  
                f"欢迎回来, {player.display_name} (免密登录)", 
                player.email, 
                player.email, 
                player.display_name
            )
    
    return gr.update(visible=True), gr.update(visible=False), "", "", "", ""

def login_ui(email, name, request: gr.Request):
    """
    手动登录：生成 Token 并显示魔法链接
    """
    if not email or not name: return gr.update(visible=True), gr.update(visible=False), "请输入信息", ""
    
    success, message, token = GAME.register(email, name)
    
    host = request.headers.get("host", "localhost:8001")
    magic_link = f"http://{host}/?token={token}"
    
    magic_html = f"""
    <div class='magic-link'>
        🔗 <a href="{magic_link}" target="_blank" style="text-decoration:none; color:#0d47a1;">
        点击这里收藏您的【专属免密登录链接】 (书签/收藏夹)
        </a>
    </div>
    """
    
    return gr.update(visible=False), gr.update(visible=True), f"欢迎, {name}", magic_html

def update_dashboard(email):
    status, price, trend, logs, messages, leaderboard_df, plot, hint_text = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard_df, plot, hint_text

def common_action(func, email, *args):
    if GAME.phase != "交易阶段":
        res = get_dashboard_info(GAME, email) 
        return *res[:7], res[7], "❌ 交易未开启"
    result_text = func(email, *args)
    res = get_dashboard_info(GAME, email)
    return *res[:7], res[7], result_text

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
# 3. 界面构建
# ==========================================

with gr.Blocks(title="暗仓: 看不见的手") as public_app:
    user_email_state = gr.State("") 
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    # === 登录页 ===
    with gr.Group(visible=True) as login_group:
        
        # 【新增】登录封面图
        # 注意：如果 assets/login.png 不存在，Gradio 会显示破损图标，请确保文件存在
        if os.path.exists("assets/login.png"):
            with gr.Row(elem_classes="login-img"):
                gr.Image(
                    "assets/login.png", 
                    show_label=False, 
                    container=False, 
                    interactive=False,
                    width=800 # 限制显示宽度
                )
        else:
            gr.Markdown("*(提示: 请将封面图放置在 assets/login.png)*")

        with gr.Row():
            email_input = gr.Textbox(label="电子邮箱", placeholder="user@test.com")
            name_input = gr.Textbox(label="操盘代号", placeholder="Trader X")
        login_btn = gr.Button("接入交易网络", variant="primary")
        login_msg = gr.Markdown("")

    # === 游戏页 ===
    with gr.Group(visible=False) as game_group:
        magic_link_display = gr.HTML()
        
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
                    message_display = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
                    with gr.Row():
                        message_input = gr.Textbox(show_label=False, placeholder="输入消息...", scale=4)
                        send_msg_btn = gr.Button("发送", scale=1, elem_classes="msg-btn")
                with gr.Column(scale=1):
                    gr.Markdown("### 📟 News Ticker")
                    log_display = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
            
            gr.Markdown("### 🏆 实时/最终 排行榜")
            leaderboard_table = gr.Dataframe(
                headers=["排名", "玩家", "身份", "资产", "状态"],
                visible=True,
                interactive=False
            )
            timer = gr.Timer(15)

    refresh_outs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_table, kline_chart, hint_display]
    common_outs = [*refresh_outs, action_result]

    public_app.load(
        fn=auto_login_logic,
        inputs=None, 
        outputs=[login_group, game_group, login_msg, user_email_state, email_input, name_input]
    ).then(
        update_dashboard, user_email_state, refresh_outs 
    )

    login_btn.click(
        fn=login_ui, 
        inputs=[email_input, name_input], 
        outputs=[login_group, game_group, login_msg, magic_link_display] 
    ).then(
        fn=lambda e: e, inputs=email_input, outputs=user_email_state
    ).then(update_dashboard, user_email_state, refresh_outs)
    
    timer.tick(update_dashboard, user_email_state, refresh_outs)
    
    buy_btn.click(buy_action, [user_email_state, buy_qty_box], common_outs)
    sell_btn.click(sell_action, [user_email_state, sell_qty_box], common_outs)
    intel_btn.click(intel_action, [user_email_state, intel_direction], common_outs)
    loan_btn.click(loan_action, [user_email_state, loan_amount], common_outs)
    send_msg_btn.click(post_message_action, [user_email_state, message_input], common_outs).then(lambda: "", None, message_input)


# 界面 2: 管理员端
with gr.Blocks(title="暗仓: 上帝控制台", css=custom_css) as admin_app:
    gr.Markdown("# 🛠️ 上帝控制台 (Admin Panel)")
    with gr.Row():
        with gr.Column(scale=3): admin_kline = gr.Plot(label="全局行情监控")
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
            admin_player_table = gr.Dataframe(headers=["代号", "邮箱", "身份", "现金", "持仓", "净值", "状态"], interactive=False)
        with gr.Column(scale=1):
            gr.Markdown("### 📟 日志 & 舆情")
            admin_logs = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
        with gr.Column(scale=1):
            gr.Markdown("### 💬 玩家对话监控")
            admin_messages = gr.TextArea(show_label=False, interactive=False, elem_classes="scroll-box")
    admin_timer = gr.Timer(15)
    admin_outputs = [admin_kline, admin_player_table, admin_logs, admin_messages, admin_status]
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out_text).then(update_admin_dashboard, outputs=admin_outputs)
    admin_timer.tick(update_admin_dashboard, outputs=admin_outputs)

if __name__ == "__main__":
    print("正在启动双端服务...")
    print("1. 玩家端 (Public): http://localhost:8001")
    print("2. 管理端 (Admin):  http://localhost:8002 (请保密)")
    
    admin_app.launch(server_name="0.0.0.0", server_port=8002, prevent_thread_lock=True, theme=gr.themes.Soft())
    public_app.launch(server_name="0.0.0.0", server_port=8001, css=custom_css)