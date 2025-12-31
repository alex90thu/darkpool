"""
Streamlit frontend for the Dark Pool trading simulator.
This replaces the Gradio UI while reusing existing backend logic and shared state.
"""
import os
import streamlit as st
from shared import GAME
from backend import (
    get_dashboard_info,
    get_admin_dashboard_info,
    admin_start,
    admin_skip_time,
    admin_skip_to_end,
    admin_restart_game,
)

st.set_page_config(page_title="暗仓: Streamlit", layout="wide")


def init_state():
    defaults = {
        "email": "",
        "display_name": "",
        "logged_in": False,
        "token": "",
        "login_message": "",
        "action_result": "",
        "message_input": "",
    }
    for key, val in defaults.items():
        st.session_state.setdefault(key, val)


def try_token_login():
    params = st.experimental_get_query_params()
    token = params.get("token", [None])[0]
    if not token or st.session_state.get("logged_in"):
        return
    player = GAME.get_user_by_token(token)
    if player:
        st.session_state.update(
            {
                "email": player.email,
                "display_name": player.display_name,
                "token": player.token,
                "logged_in": True,
                "login_message": f"欢迎回来, {player.display_name} (免密登录)",
            }
        )


def build_magic_link():
    if not st.session_state.get("token"):
        return None
    host = os.getenv("PUBLIC_HOST", "localhost")
    port = os.getenv("PUBLIC_PORT", os.getenv("STREAMLIT_SERVER_PORT", "8001"))
    return f"http://{host}:{port}/?token={st.session_state.token}"


def ensure_logged_in():
    if st.session_state.get("logged_in"):
        return True
    st.info("请输入邮箱和操盘代号完成登录，或使用 token 链接自动登录。")
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("电子邮箱", placeholder="user@test.com")
        name = st.text_input("操盘代号", placeholder="Trader X")
        submitted = st.form_submit_button("接入交易网络")
    if submitted:
        success, message, token = GAME.register(email, name)
        st.session_state.update(
            {
                "email": email,
                "display_name": name,
                "token": token,
                "logged_in": success,
                "login_message": f"{message}: {name}",
            }
        )
        st.success(st.session_state["login_message"])
        st.experimental_rerun()
    return False


def render_player_dashboard():
    status_md, price_md, trend_md, logs_str, messages_str, leaderboard_df, plot, hint_text = get_dashboard_info(
        GAME, st.session_state.email
    )

    st.markdown(st.session_state.get("login_message", ""))
    top_cols = st.columns([2, 1])
    with top_cols[0]:
        st.markdown(status_md)
    with top_cols[1]:
        st.markdown(price_md)
        if trend_md:
            st.markdown(trend_md)

    if plot:
        st.plotly_chart(plot, use_container_width=True)

    st.markdown(hint_text)

    act_cols = st.columns(4)
    with act_cols[0]:
        buy_qty = st.number_input("买入数量", min_value=1, value=100, step=100)
        if st.button("买入 (Long)"):
            if GAME.phase != "交易阶段":
                st.session_state["action_result"] = "❌ 交易未开启"
            else:
                st.session_state["action_result"] = GAME.buy_stock(st.session_state.email, buy_qty)
            st.experimental_rerun()
    with act_cols[1]:
        sell_qty = st.number_input("卖出数量", min_value=1, value=100, step=100)
        if st.button("卖出/做空 (Short)"):
            if GAME.phase != "交易阶段":
                st.session_state["action_result"] = "❌ 交易未开启"
            else:
                st.session_state["action_result"] = GAME.sell_stock(st.session_state.email, sell_qty)
            st.experimental_rerun()
    with act_cols[2]:
        intel_dir = st.radio("舆情方向", ["看涨", "看跌"], horizontal=True)
        if st.button("购买舆情 ($5k)"):
            if GAME.phase != "交易阶段":
                st.session_state["action_result"] = "❌ 交易未开启"
            else:
                st.session_state["action_result"] = GAME.purchase_intel(
                    st.session_state.email, intel_dir
                )
            st.experimental_rerun()
    with act_cols[3]:
        loan_amt = st.number_input("贷款金额", min_value=1000, value=10000, step=1000)
        if st.button("申请高利贷 (30%)"):
            st.session_state["action_result"] = GAME.take_loan(st.session_state.email, loan_amt)
            st.experimental_rerun()

    st.info(st.session_state.get("action_result", "准备就绪..."))

    msg_cols = st.columns([2, 1])
    with msg_cols[0]:
        st.subheader("💬 交易员大厅")
        st.text_area("聊天记录", value=messages_str, height=260, disabled=True)
        st.session_state["message_input"] = st.text_input(
            "发送消息", value=st.session_state.get("message_input", "")
        )
        if st.button("发送"):
            content = st.session_state.get("message_input", "").strip()
            if content:
                st.session_state["action_result"] = GAME.post_message(
                    st.session_state.email, content
                )
            else:
                st.session_state["action_result"] = "内容为空"
            st.session_state["message_input"] = ""
            st.experimental_rerun()
    with msg_cols[1]:
        st.subheader("📟 News Ticker")
        st.text_area("系统日志", value=logs_str, height=260, disabled=True)

    st.subheader("🏆 实时/最终 排行榜")
    st.dataframe(leaderboard_df, use_container_width=True)

    st.caption("点击下方按钮手动刷新行情")
    if st.button("刷新数据", type="secondary"):
        st.experimental_rerun()


def render_admin_dashboard():
    admin_plot, admin_table, admin_logs, admin_msgs, admin_status = get_admin_dashboard_info(GAME)

    top = st.columns([3, 1])
    with top[0]:
        st.plotly_chart(admin_plot, use_container_width=True)
    with top[1]:
        st.markdown(admin_status)
        if st.button("🚀 强制开始游戏"):
            st.session_state["action_result"] = admin_start()
            st.experimental_rerun()
        if st.button("⏭️ 跳过 1 小时"):
            st.session_state["action_result"] = admin_skip_time()
            st.experimental_rerun()
        if st.button("⏩ 快进至结局"):
            st.session_state["action_result"] = admin_skip_to_end()
            st.experimental_rerun()
        if st.button("🔄 重置/新游戏"):
            st.session_state["action_result"] = admin_restart_game()
            st.experimental_rerun()
        st.info(st.session_state.get("action_result", ""))

    log_cols = st.columns(2)
    with log_cols[0]:
        st.subheader("👥 玩家资产")
        st.dataframe(admin_table, use_container_width=True)
    with log_cols[1]:
        st.subheader("📟 日志 & 留言")
        st.text_area("系统日志", value=admin_logs, height=220, disabled=True)
        st.text_area("玩家对话监控", value=admin_msgs, height=220, disabled=True)

    if st.button("刷新管理端数据", type="secondary"):
        st.experimental_rerun()


# ===== 页面入口 =====
init_state()
try_token_login()

st.title("📉 暗仓 (Dark Pool) - Streamlit 终端")
tab_player, tab_admin = st.tabs(["玩家端", "管理员端"])

with tab_player:
    if ensure_logged_in():
        magic_link = build_magic_link()
        if magic_link:
            st.success(f"🔗 免密登录链接: {magic_link}")
        render_player_dashboard()

with tab_admin:
    render_admin_dashboard()
