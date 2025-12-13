import random
import math
import os
from datetime import datetime

class Player:
    def __init__(self, email, display_name):
        self.email = email
        self.display_name = display_name
        self.role = "散户"
        self.cash = 100000.0
        self.stock = 0
        self.debt = 0.0
        self.logs = []
        self.last_event = None 

    def get_net_worth(self, current_price):
        """计算净资产"""
        stock_value = self.stock * current_price
        return self.cash + stock_value - self.debt

    def get_margin_info(self, current_price):
        """计算保证金详情"""
        if self.stock >= 0:
            return 0.0, 0.0, self.cash, 0.0
        
        short_val = abs(self.stock * current_price)
        # 冻结规则：做空市值 * 1.5 (含100%卖出所得 + 50%初始保证金)
        frozen_cash = short_val * 1.5
        available_cash = self.cash - frozen_cash
        
        # 风险率 = 当前总权益 / 做空市值
        equity = self.cash - short_val
        risk_ratio = equity / short_val if short_val > 0 else 999.0
        
        return short_val, frozen_cash, max(0, available_cash), risk_ratio

    def get_account_status(self, current_price):
        """返回账户的当前状态标签"""
        if self.last_event == "LIQUIDATED":
            return "☠️ 刚刚爆仓"
        
        if self.stock >= 0:
            return "✅ 正常"
        
        short_val, frozen, avail, risk = self.get_margin_info(current_price)
        
        if risk < 1.15: 
            return "🆘 濒临强平"
        elif risk < 1.35:
            return "⚠️ 保证金告急"
        elif avail < 5000:
            return "🔒 资产冻结"
        else:
            return "📉 做空持仓中"

class GameState:
    def __init__(self):
        self.players = {}
        self.reset()

    def reset(self):
        self.is_running = False
        self.phase = "报名阶段"
        self.game_clock = 0
        self.system_logs = []
        self.players = {}
        self.messages = []
        
        self.base_price = 100.0
        self.current_price = 100.0
        self.hourly_trend = 0.0 
        self.current_momentum = 0.0 
        self.volatility_limit = 0.30 
        self.history = [100.0]
        self.short_pressure = 0.0
        
        # K线数据结构
        self.kline_data = [] 
        self.current_open = 100.0 
        self.current_volume = 0   

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.system_logs.append(f"[{timestamp}] {message}")
        if len(self.system_logs) > 200:
            self.system_logs.pop(0)

    def register(self, email, name):
        if email in self.players:
            return False, "已注册"
        new_player = Player(email, name)
        if self.is_running:
            new_player.role = "散户"
        self.players[email] = new_player
        return True, "注册成功"

    def start_game(self):
        if len(self.players) < 1:
            return "人数不足"
        self.is_running = True
        self.phase = "交易阶段"
        self.game_clock = 0
        self.hourly_trend = random.uniform(-0.02, 0.02)
        
        # 初始化K线
        self.current_open = 100.0
        self.current_volume = 0
        self.kline_data = []
        
        emails = list(self.players.keys())
        num_mm = max(1, int(len(emails) * 0.1))
        mm = random.sample(emails, num_mm)
        for e in self.players:
            self.players[e].role = "操盘手" if e in mm else "散户"
        
        self.log(f"开盘！共{len(self.players)}人入场。")
        return "游戏开始"

    def next_hour(self):
        if not self.is_running or self.game_clock >= 12:
            return

        # 1. K线记录
        hour_open = self.current_open
        
        # 2. 价格计算
        noise = random.uniform(-0.01, 0.01)
        change = self.hourly_trend + self.current_momentum + noise
        change = max(-0.5, min(0.5, change))
        self.current_price *= (1 + change)
        hour_close = self.current_price
        
        # 3. 生成影线
        volatility = abs(hour_open - hour_close) + (hour_open * 0.01)
        hour_high = max(hour_open, hour_close) + random.uniform(0, volatility * 0.5)
        hour_low = min(hour_open, hour_close) - random.uniform(0, volatility * 0.5)
        
        self.kline_data.append({
            'time': self.game_clock,
            'open': hour_open,
            'high': hour_high,
            'low': hour_low,
            'close': hour_close,
            'volume': self.current_volume
        })
        
        self.game_clock += 1
        self.history.append(self.current_price)
        
        self.current_open = self.current_price
        self.current_volume = 0
        self.current_momentum = 0.0 
        
        # 4. 强平检查
        maintenance_margin = 1.10
        for p in self.players.values():
            p.last_event = None 
            if p.stock < 0:
                short_val, frozen, avail, risk = p.get_margin_info(self.current_price)
                if risk < maintenance_margin:
                    self.liquidate_player(p)
                elif risk < 1.3:
                    p.logs.append(f"⚠️ 警告：保证金水平({risk:.2f})过低！")

        self.log(f"第 {self.game_clock} 小时收盘，股价 ${self.current_price:.2f}")
        if self.game_clock >= 12:
            self.end_game()

    def liquidate_player(self, player):
        quantity = abs(player.stock)
        cost = quantity * self.current_price
        player.stock = 0
        player.cash -= cost 
        player.last_event = "LIQUIDATED" 
        msg = f"☠️ 爆仓通知：系统强制买回 {quantity} 股，扣除 ${cost:,.2f}。"
        player.logs.append(msg)
        self.log(f"玩家 {player.display_name} 爆仓强平！(市场动能+5%)")
        self.current_momentum += 0.05 
        self.current_volume += quantity

    def end_game(self):
        self.phase = "结算阶段"
        for p in self.players.values():
            val = p.get_net_worth(self.current_price)
            fee = val * 0.10
            p.cash = val - fee
            p.stock = 0
            p.logs.append(f"结算完成，扣除管理费 ${fee:,.2f}")
        
        self.log("游戏结束，所有资产已清算。")
        self.save_game_report()

    def save_game_report(self):
        save_dir = "savedata"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{save_dir}/game_report_{timestamp}.md"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# 📉 暗仓战报 - {timestamp}\n\n")
                f.write(f"**最终股价**: ${self.current_price:.2f}\n\n")
                
                f.write("## 🏆 最终排行榜\n| 排名 | 玩家 | 身份 | 资产 |\n|---|---|---|---|\n")
                sorted_players = sorted(self.players.values(), key=lambda x: x.cash, reverse=True)
                for i, p in enumerate(sorted_players):
                    f.write(f"| {i+1} | {p.display_name} | {p.role} | ${p.cash:,.2f} |\n")
                
                f.write("\n## 📈 K线数据\n| 时间 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |\n|---|---|---|---|---|---|\n")
                for k in self.kline_data:
                    f.write(f"| {k['time']}h | {k['open']:.2f} | {k['high']:.2f} | {k['low']:.2f} | {k['close']:.2f} | {k['volume']} |\n")
        except Exception as e:
            print(f"Error saving report: {e}")

    def prepare_next_round(self):
        saved = {e: Player(e, p.display_name) for e, p in self.players.items()}
        self.reset()
        self.players = saved

    def calculate_short_fee(self):
        total_short = sum(abs(p.stock) for p in self.players.values() if p.stock < 0)
        crowding = min(1.0, total_short / 100000)
        self.short_pressure = crowding
        return 0.05 + (0.45 * crowding)

    def calculate_impact(self, current, impact, limit):
        target = current + impact
        if abs(target) < abs(current) or (target * current < 0):
            return impact
        dist = limit - abs(current)
        return impact * (dist / limit) if dist > 0 else 0.0

    def purchase_intel(self, email, direction):
        # 引入我们在 scripts/news_system.py 中写好的生成器
        from scripts.news_system import generate_news, format_news_for_display
        
        p = self.players[email]
        cost = 5000
        
        status = p.get_account_status(self.current_price)
        if "锁定" in status or "冻结" in status or "爆仓" in status: 
            return f"❌ 拒绝：账户{status}"
        
        _, _, avail, _ = p.get_margin_info(self.current_price)
        if avail < cost: 
            return f"❌ 资金不足"

        p.cash -= cost
        base = 0.15 if p.role == "操盘手" else 0.05
        impact = base * (1 if direction == "看涨" else -1)
        
        actual = self.calculate_impact(self.current_momentum, impact, self.volatility_limit)
        self.current_momentum += actual
        
        # 调用 AI 生成新闻
        news_type = "positive" if direction == "看涨" else "negative"
        raw_news = generate_news(news_type)
        formatted_log = format_news_for_display(raw_news)
        
        self.system_logs.append(formatted_log)
        self.messages.append(formatted_log)
        
        p.logs.append(f"购买{direction}舆情，造成 {actual*100:+.2f}% 动能")
        
        return "舆情购买成功，新闻已发布"

    def buy_stock(self, email, quantity):
        try:
            quantity = int(quantity)
        except:
            return "整数"
        if quantity <= 0:
            return "无效数量"
        
        p = self.players[email]
        cost = quantity * self.current_price * 1.05
        _, _, avail, _ = p.get_margin_info(self.current_price)
        if avail < cost:
            return f"资金不足"
        
        p.cash -= cost
        p.stock += quantity
        self.current_volume += quantity
        p.logs.append(f"买入 {quantity} 股")
        return "买入成功"

    def sell_stock(self, email, quantity):
        try:
            quantity = int(quantity)
        except:
            return "整数"
        if quantity <= 0:
            return "无效数量"
        
        p = self.players[email]
        is_short = (p.stock - quantity) < 0
        fee_rate = self.calculate_short_fee() if is_short else 0.05
        
        if is_short:
            proceeds = quantity * self.current_price * (1 - fee_rate)
            if p.cash + proceeds < abs((p.stock - quantity) * self.current_price) * 1.5:
                return "保证金不足"

        proceeds = quantity * self.current_price * (1 - fee_rate)
        p.cash += proceeds
        p.stock -= quantity
        self.current_volume += quantity
        p.logs.append(f"{'做空' if is_short else '卖出'} {quantity} 股")
        return "交易成功"

    def post_message(self, email, content):
        p = self.players[email]
        tag = "【内幕】" if p.role == "操盘手" else "【投资者】"
        self.messages.append(f"{tag} {p.display_name}: {content}")
        return "发送成功"