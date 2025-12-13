import gradio as gr
from shared import GAME 
from backend import (
    get_dashboard_info, 
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

# === CSS 样式表 ===
custom_css = """
/* 上半部分：黑色终端风格 */
.dark-terminal {
    background-color: #161a25 !important; /* 与图表背景一致 */
    border: 1px solid #2a2e39 !important;
    border-radius: 10px !important;
    padding: 20px !important;
    margin-bottom: 20px !important;
}

/* 强制覆盖暗色区域内的文字颜色为白色 */
.dark-terminal h1, .dark-terminal h2, .dark-terminal h3, 
.dark-terminal p, .dark-terminal span, .dark-terminal label, 
.dark-terminal .prose {
    color: #e0e0e0 !important;
}

/* 下半部分：操作按钮颜色 */
.buy-btn { background-color: #2E7D32 !important; color: white !important; }
.sell-btn { background-color: #C62828 !important; color: white !important; }
.intel-btn { background-color: #1565C0 !important; color: white !important; }
.loan-btn { background-color: #6A1B9A !important; color: white !important; }
.msg-btn { background-color: #455A64 !important; color: white !important; }

/* 全局圆角 */
button { border-radius: 6px !important; }
"""

# === 逻辑包装保持不变 ===
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
        base_res = res[:7]
        return *base_res, gr.update(visible=False), gr.update(), gr.update(), "❌ 交易未开启"
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

# === 界面构建 ===
with gr.Blocks(title="暗仓: 看不见的手", css=custom_css) as demo:
    user_email_state = gr.State("") 
    
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    with gr.Group(visible=True) as login_group:
        with gr.Row():
            email_input = gr.Textbox(label="邮箱", placeholder="user@test.com")
            name_input = gr.Textbox(label="代号", placeholder="Trader X")
        login_btn = gr.Button("接入交易网络", variant="primary")
        login_msg = gr.Markdown("")

    with gr.Group(visible=False) as game_group:
        
        # === 上半部分：黑色交易终端 ===
        # 使用 elem_classes 应用 CSS 样式
        with gr.Group(elem_classes="dark-terminal"):
            with gr.Row():
                # 左上：状态
                with gr.Column(scale=2):
                    status_display = gr.Markdown("加载中...")
                # 右上：价格大字
                with gr.Column(scale=1):
                    price_display = gr.Markdown("Price")
            
            with gr.Row():
                # 左下：图表
                with gr.Column(scale=3):
                    kline_chart = gr.Plot(label="Market Data")
                # 右下：趋势/情报
                with gr.Column(scale=1):
                    trend_display = gr.Markdown("情报加载中...")
        
        # === 分隔线 ===
        # 视觉上分隔黑区和白区
        
        # === 下半部分：白色操作区 ===
        with gr.Group(): # 默认背景，即白色/浅灰
            gr.Markdown("### 🕹️ 交易指令台")
            with gr.Row():
                # 1. 买入
                with gr.Column(scale=1):
                    gr.Markdown("#### 🟢 买入 (Long)")
                    buy_qty_box = gr.Number(label="数量", value=100)
                    buy_btn = gr.Button("买入股票", elem_classes="buy-btn")
                
                # 2. 卖出
                with gr.Column(scale=1):
                    gr.Markdown("#### 🔴 卖出 (Short)")
                    sell_qty_box = gr.Number(label="数量", value=100)
                    sell_btn = gr.Button("卖出/平仓", elem_classes="sell-btn")
                
                # 3. 舆情
                with gr.Column(scale=1):
                    gr.Markdown("#### 📢 舆情 ($5k)")
                    intel_direction = gr.Radio(["看涨", "看跌"], label="方向", value="看涨")
                    intel_btn = gr.Button("购买舆情", elem_classes="intel-btn")
                    
                # 4. 贷款
                with gr.Column(scale=1):
                    gr.Markdown("#### 🏦 融资 (30%)")
                    loan_amount = gr.Number(label="金额", value=10000)
                    loan_btn = gr.Button("申请贷款", elem_classes="loan-btn")
            
            action_result = gr.Markdown("准备就绪...")
            
            gr.Markdown("---")
            
            # 信息流区域
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

    with gr.Accordion("🛠️ 上帝模式", open=False):
        with gr.Row():
            admin_start_btn = gr.Button("🚀 强制开始")
            admin_skip_btn = gr.Button("⏭️ 跳过1小时")
            admin_skip_all_btn = gr.Button("⏩ 快进至结束")
            admin_restart_btn = gr.Button("🔄 重置游戏")
        admin_out = gr.Markdown("")

    # === 绑定 ===
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
    
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)

if __name__ == "__main__":
    print("启动服务器... 请访问 http://localhost:8001")
    demo.launch(server_name="0.0.0.0", server_port=8001, share=False)