import gradio as gr
from shared import GAME 
from backend import (
    get_dashboard_info, 
    admin_start, 
    admin_skip_time, 
    admin_skip_to_end, 
    admin_restart_game
)

def login_ui(email, name):
    if not email or not name: return gr.update(visible=True), gr.update(visible=False), "请输入信息"
    if email not in GAME.players:
        success, message = GAME.register(email, name)
        if not success: return gr.update(visible=True), gr.update(visible=False), message
    return gr.update(visible=False), gr.update(visible=True), f"欢迎, {name}"

def update_dashboard(email):
    status, price, trend, logs, messages, leaderboard, plot = get_dashboard_info(GAME, email)
    return status, price, trend, logs, messages, leaderboard, plot, gr.update(visible=bool(leaderboard))

def common_action(func, email, *args):
    if GAME.phase != "交易阶段":
        res = get_dashboard_info(GAME, email) 
        return *res, gr.update(visible=False), "❌ 交易未开启"
    result_text = func(email, *args)
    res = get_dashboard_info(GAME, email)
    return *res, gr.update(visible=False), result_text

def buy_action(email, qty): return common_action(GAME.buy_stock, email, qty)
def sell_action(email, qty): return common_action(GAME.sell_stock, email, qty)
def intel_action(email, direction): return common_action(GAME.purchase_intel, email, direction)
def loan_action(email, amount): return common_action(GAME.take_loan, email, amount) # 新增贷款回调

def post_message_action(email, msg): 
    if not msg.strip(): 
        res = get_dashboard_info(GAME, email)
        return *res, gr.update(visible=False), "内容为空"
    return common_action(GAME.post_message, email, msg)

# --- 界面构建 ---
with gr.Blocks(title="暗仓: 看不见的手") as demo:
    user_email_state = gr.State("") 
    
    gr.Markdown("# 📉 暗仓 (Dark Pool) - 模拟交易终端")
    
    with gr.Group(visible=True) as login_group:
        with gr.Row():
            email_input = gr.Textbox(label="邮箱", placeholder="user@test.com")
            name_input = gr.Textbox(label="代号", placeholder="Trader X")
        login_btn = gr.Button("接入网络", variant="primary")
        login_msg = gr.Markdown("")

    with gr.Group(visible=False) as game_group:
        
        with gr.Row():
            status_display = gr.Markdown("加载中...")
            price_display = gr.Markdown("股价...")
        
        with gr.Row():
            with gr.Column(scale=3):
                kline_chart = gr.Plot(label="K线走势图")
            with gr.Column(scale=1):
                trend_display = gr.Markdown("情报加载中...")
            
        gr.Markdown("---")
        
        # 操作区
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### 🟢 买入 / 🔴 卖出")
                stock_qty = gr.Number(label="股数", value=100)
                with gr.Row():
                    buy_btn = gr.Button("买入", variant="secondary")
                    sell_btn = gr.Button("卖出/做空", variant="stop")
            
            with gr.Column(scale=1):
                gr.Markdown("#### 📢 舆情 ($5,000)")
                intel_direction = gr.Radio(["看涨", "看跌"], label="方向", value="看涨")
                intel_btn = gr.Button("购买舆情")
                
            # 【新增】贷款专区
            with gr.Column(scale=1):
                gr.Markdown("#### 🏦 地下钱庄 (利率30%)")
                loan_amount = gr.Number(label="贷款金额", value=10000)
                loan_btn = gr.Button("申请高利贷")
        
        action_result = gr.Markdown("就绪")
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### 💬 留言板")
                message_display = gr.TextArea(show_label=False, interactive=False, lines=8)
                with gr.Row():
                    message_input = gr.Textbox(show_label=False, placeholder="输入消息...", scale=4)
                    send_msg_btn = gr.Button("发送", scale=1)
            with gr.Column(scale=1):
                gr.Markdown("### 📟 日志")
                log_display = gr.TextArea(show_label=False, interactive=False, lines=10)
        
        leaderboard_display = gr.Markdown("", visible=False)
        timer = gr.Timer(2)

    with gr.Accordion("🛠️ 上帝模式", open=False):
        with gr.Row():
            admin_start_btn = gr.Button("🚀 开始")
            admin_skip_btn = gr.Button("⏭️ 跳1小时")
            admin_skip_all_btn = gr.Button("⏩ 快进")
            admin_restart_btn = gr.Button("🔄 重置")
        admin_out = gr.Markdown("")

    # --- 绑定 ---
    common_outs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_display, kline_chart, leaderboard_display, action_result]
    refresh_outs = [status_display, price_display, trend_display, log_display, message_display, leaderboard_display, kline_chart, leaderboard_display]

    login_btn.click(login_ui, [email_input, name_input], [login_group, game_group, login_msg]).then(
        fn=lambda e: e, inputs=email_input, outputs=user_email_state
    ).then(update_dashboard, user_email_state, refresh_outs)
    
    timer.tick(update_dashboard, user_email_state, refresh_outs)
    
    buy_btn.click(buy_action, [user_email_state, stock_qty], common_outs)
    sell_btn.click(sell_action, [user_email_state, stock_qty], common_outs)
    intel_btn.click(intel_action, [user_email_state, intel_direction], common_outs)
    loan_btn.click(loan_action, [user_email_state, loan_amount], common_outs) # 绑定贷款按钮
    
    send_msg_btn.click(post_message_action, [user_email_state, message_input], common_outs).then(lambda: "", None, message_input)
    
    admin_start_btn.click(lambda: admin_start(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_skip_btn.click(lambda: admin_skip_time(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_skip_all_btn.click(lambda: admin_skip_to_end(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)
    admin_restart_btn.click(lambda: admin_restart_game(), outputs=admin_out).then(update_dashboard, user_email_state, refresh_outs)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", share=False)