"""
玩家管理模块
"""

class Player:
    def __init__(self, email, display_name, role="散户"):
        self.email = email
        self.display_name = display_name
        self.role = role  # "散户" 或 "操盘手"
        self.cash = 1000000.0
        self.stock = 0  # 正数表示持有多头仓位，负数表示持有空头仓位
        self.debt = 0.0  # 做空时的债务金额（按做空时股价计算）
        self.logs = [] # 个人操作日志
        self.intel_purchased = False # 是否购买了舆情信息
        self.intel_count = 0 # 购买舆情的次数