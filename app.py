import gradio as gr
from shared import GAME 
from backend import (
    get_dashboard_info, 
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

# === 自定义 CSS (保留之前的彭博终端风格) ===
custom_css = """
.dark-terminal {
    background-color: #161a25 !important;
    border: 1px solid #2a2e39 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
}
.dark-terminal h1, .dark-terminal h2, .dark-terminal h3, 
.dark-terminal p, .dark-terminal span, .dark-terminal label, 
.dark-terminal .prose {
    color: #e0e0e0 !important;
}
.buy-btn { background-color: #2E7D32 !important; color: white !important; }
.sell-btn { background-color: #C62828 !important; color: white !important; }
.intel-btn { background-color: #1565C0 !important; color: white !important; }
.loan-btn { background-color: #6A1B9A !important; color: white !important; }
.msg-btn { background-color: #455A64 !important; color: white !important; }
button { border-radius: 8px !important; }
"""

# ==========================================
# 逻辑函数包装 (保持不变)
# ==========================================

def login_ui(email, name):
    if not email or not name: return gr.update(visible=True), gr.update(visible=False), "请输入信息"
    if email not in GAME.players:
        success, message = GAME.register(email, name)
        if not success: return gr.update(visible=True), gr.update(visible=False), message
    return gr.update(visible=False), gr.update(visible=True), f"欢迎, {name}"

def update_dashboard(email):
    status, price, trend, logs, messages, leaderboard, plot, buy_hint, sell_hint = get_dashboard_info(GAME, email)
    return (
        status, price, trend, logs, messages, leaderboard, plot, 
        gr.update(visible=bool(leaderboard)),
        gr.update(info=buy_hint),
        gr.update(info=sell_hint)
    )

def common_action(func, email, *args):
    if GAME.phase != "交易阶段":
        res = get_dashboard_info(GAME, email) 
        return *res[:7], gr.update(visible=False), gr.update(), gr.update(), "❌ 交易未开启"
    result_text = func(email, *args)
    res = get_dashboard_info(GAME, email)
    return *res[:7], gr.update(visible=False), gr.update(info=res[7]), gr.update(info=res[8]), result_text

def buy_action(email, qty): return common_action(GAME.buy_stock, email, qty)
def sell_action(email, qty): return common_action(GAME.sell_stock, email, qty)
def intel_action(email, direction): return common_action(GAME.purchase_intel, email, direction)
def loan_action(email, amount): return common_action(GAME.take_loan, email, amount)
def post_message_action(email, msg): 
    if not msg.strip(): 
        res = get_dashboard_info(GAME, email)
        return *res[:7], gr.update(visible=False), gr.update(), gr.update(), "内容为空"
    return common_action(GAME.post_message, email, msg)


# ==========================================
# 界面 1: 玩家端 (Public UI) - Port 8001
# ==========================================
with gr.Blocks(title="暗仓: 看不见的手", css=custom_css) as public_app:
    user_email_state = gr.State("") 
    
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    # 登录区
    with gr.Group(visible=True) as login_group:
        with gr.Row():
            email_input = gr.Textbox(label="电子邮箱", placeholder="user@test.com")
            name_input = gr.Textbox(label="操盘代号", placeholder="Trader X")
        login_btn = gr.Button("接入交易网络", variant="primary")
        login_msg = gr.Markdown("")

    # 游戏区
    with gr.Group(visible=False) as game_group:
        
        # 黑色终端风格显示区
        with gr.Group(elem_classes="dark-terminal"):
            with gr.Row():
                with gr.Column(scale=2): status_display = gr.Markdown("加载中...")
                with gr.Column(scale=1): price_display = gr.Markdown("Price")
            with gr.Row():
                with gr.Column(scale=3): kline_chart = gr.Plot(label="Market Data")
                with gr.Column(scale=1): trend_display = gr.Markdown("情报加载中...")
        
        # 白色操作区
        with gr.Group():
            gr.Markdown("### 🕹️ 交易指令台")
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("#### 🟢 买入 (Long)")
                    buy_qty_box = gr.Number(label="数量", value=100)
                    buy_btn = gr.Button("买入股票", elem_classes="buy-btn")
                with gr.Column(scale=1):
                    gr.Markdown("#### 🔴 卖出 (Short)")
                    sell_qty_box = gr.Number(label="数量", value=100)
                    sell_btn = gr.Button("卖出/平仓", elem_classes="sell-btn")
                with gr.Column(scale=1):
                    gr.Markdown("#### 📢 舆情 ($5k)")
                    intel_direction = gr.Radio(["看涨", "看跌"], label="方向", value="看涨")
                    intel_btn = gr.Button("购买舆情", elem_classes="intel-btn")
                with gr.Column(scale=1):
                    gr.Markdown("#### 🏦 融资 (30%)")
                    loan_amount = gr.Number(label="金额", value=10000)
                    loan_btn = gr.Button("申请贷款", elem_classes="loan-btn")
            
            action_result = gr.Markdown("准备就绪...")
            gr.Markdown("---")
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### 💬 交易员大厅")
                    message_display = gr.TextArea(show_label=False, interactive=False, lines=8)
                    with gr.Row():
                        message_input = gr.Textbox(show_label=False, placeholder="输入消息...", scale=4)
                        send_msg_btn = gr.Button("发送", scale=1, elem_classes="msg-btn")
                with gr.Column(scale=1):
                    gr.Markdown("### 📟 News Ticker")
                    log_display = gr.TextArea(show_label=False, interactive=False, lines=10)
            
            leaderboard_display = gr.Markdown("", visible=False)
            timer = gr.Timer(2)

    # 玩家端绑定
    refresh_outs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_display, kline_chart, leaderboard_display, buy_qty_box, sell_qty_box]
    common_outs = [*refresh_outs, action_result]

    login_btn.click(login_ui, [email_input, name_input], [login_group, game_group, login_msg]).then(
        fn=lambda e: e, inputs=email_input, outputs=user_email_state
    ).then(update_dashboard, user_email_state, refresh_outs)
    
    timer.tick(update_dashboard, user_email_state, refresh_outs)
    
    buy_btn.click(buy_action, [user_email_state, buy_qty_box], common_outs)
    sell_btn.click(sell_action, [user_email_state, sell_qty_box], common_outs)
    intel_btn.click(intel_action, [user_email_state, intel_direction], common_outs)
    loan_btn.click(loan_action, [user_email_state, loan_amount], common_outs)
    send_msg_btn.click(post_message_action, [user_email_state, message_input], common_outs).then(lambda: "", None, message_input)


# ==========================================
# 界面 2: 管理员端 (Admin UI) - Port 1008
# ==========================================
with gr.Blocks(title="暗仓: 上帝控制台", theme=gr.themes.Soft()) as admin_app:
    gr.Markdown("# 🛠️ 上帝控制台 (Admin Panel)")
    gr.Markdown("警告：此页面拥有最高权限，请勿泄露给玩家。")
    
    with gr.Row():
        admin_start_btn = gr.Button("🚀 强制开始游戏", variant="primary")
        admin_restart_btn = gr.Button("🔄 重置/开启新一轮", variant="secondary")
    
    with gr.Row():
        admin_skip_btn = gr.Button("⏭️ 跳过 1 小时")
        admin_skip_all_btn = gr.Button("⏩ 快进至结局 (自动结算)")
        
    admin_out = gr.TextArea(label="执行结果", interactive=False, lines=10)
    
    # 管理员端绑定 (只负责执行命令，不需要刷新复杂界面)
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out)
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out)
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out)
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out)


# ==========================================
# 双端口启动逻辑
# ==========================================
if __name__ == "__main__":
    print("正在启动双端服务...")
    print("1. 玩家端 (Public): http://localhost:8001")
    print("2. 管理端 (Admin):  http://localhost:7001 (请保密)")
    
    # 关键参数: prevent_thread_lock=True
    # 这让 admin_app 在后台启动，不会阻塞代码执行，从而让 public_app 也能接着启动
    admin_app.launch(server_name="0.0.0.0", server_port=7001,share=True, prevent_thread_lock=True)
    
    # 玩家端作为主进程阻塞运行
    public_app.launch(server_name="0.0.0.0", server_port=8001, share=True)