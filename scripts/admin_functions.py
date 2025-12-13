"""
管理员功能模块
"""

def admin_skip_time(game_state):
    game_state.next_hour()
    return "已跳过 1 小时"

def admin_skip_to_end(game_state):
    # 修复：直接调用GameState的内部逻辑而不是不存在的方法
    while game_state.game_clock < 12:
        game_state.next_hour()
    return "游戏已加速至结束"

def admin_start(game_state):
    return game_state.start_game()