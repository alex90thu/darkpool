import random
import math
import os
from datetime import datetime

class Player:
    def __init__(self, email, display_name):
        self.email = email
        self.display_name = display_name
        self.role = "散户"
        self.cash = 1000000.0
        self.stock = 0
        self.debt = 0.0
        self.logs = []
        self.last_event = None 

    def get_net_worth(self, current_price):
        """计算净资产 = 现金 + 股票市值 - 债务"""
        stock_value = self.stock * current_price
        return self.cash + stock_value - self.debt

    def get_margin_info(self, current_price):
        if self.stock >= 0:
            return 0.0, 0.0, self.cash, 0.0
        
        short_val = abs(self.stock * current_price)
        frozen_cash = short_val * 1.5
        available_cash = self.cash - frozen_cash
        equity = self.cash - short_val
        risk_ratio = equity / short_val if short_val > 0 else 999.0
        
        return short_val, frozen_cash, max(0, available_cash), risk_ratio

    def get_account_status(self, current_price):
        if self.last_event == "LIQUIDATED": return "☠️ 刚刚爆仓"
        short_val, frozen, avail, risk = self.get_margin_info(current_price)
        
        status = []
        if self.debt > 0: status.append("💸 负债中")
        if self.stock < 0:
            if risk < 1.15: status.append("🆘 濒临强平")
            elif risk < 1.35: status.append("⚠️ 保证金告急")
            elif avail < 5000: status.append("🔒 资产冻结")
            else: status.append("📉 做空")
        elif self.stock > 0:
            status.append("📈 持仓")
        else:
            status.append("✅ 空仓")
            
        return " | ".join(status)

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
        
        self.kline_data = [] 
        self.current_open = 100.0 
        self.current_volume = 0
        
        # 记录本局总结，用于战报
        self.final_summary = ""

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.system_logs.append(f"[{timestamp}] {message}")
        if len(self.system_logs) > 200: self.system_logs.pop(0)

    def register(self, email, name):
        if email in self.players: return False, "已注册"
        new_player = Player(email, name)
        if self.is_running: new_player.role = "散户"
        self.players[email] = new_player
        return True, "注册成功"

    def start_game(self):
        if len(self.players) < 1: return "人数不足"
        self.is_running = True
        self.phase = "交易阶段"
        self.game_clock = 0
        self.hourly_trend = random.uniform(-0.02, 0.02)
        
        self.current_open = 100.0
        self.current_volume = 0
        self.kline_data = []
        self.final_summary = ""
        
        emails = list(self.players.keys())
        num_mm = max(1, int(len(emails) * 0.1))
        mm = random.sample(emails, num_mm)
        for e in self.players:
            self.players[e].role = "操盘手" if e in mm else "散户"
        
        self.log(f"开盘！共{len(self.players)}人入场。")
        return "游戏开始"

    def next_hour(self):
        if not self.is_running or self.game_clock >= 12: return

        # K线与价格计算
        hour_open = self.current_open
        prev_price = self.current_price # 记录上一小时价格用于计算涨跌幅
        
        noise = random.uniform(-0.01, 0.01)
        change = self.hourly_trend + self.current_momentum + noise
        change = max(-0.5, min(0.5, change))
        self.current_price *= (1 + change)
        hour_close = self.current_price
        
        volatility = abs(hour_open - hour_close) + (hour_open * 0.01)
        hour_high = max(hour_open, hour_close) + random.uniform(0, volatility * 0.5)
        hour_low = min(hour_open, hour_close) - random.uniform(0, volatility * 0.5)
        
        self.kline_data.append({
            'time': self.game_clock,
            'open': hour_open, 'high': hour_high, 'low': hour_low, 'close': hour_close,
            'volume': self.current_volume
        })
        
        self.game_clock += 1
        self.history.append(self.current_price)
        
        # === LLM 小时点评 ===
        from scripts.news_system import generate_hourly_comment, format_news_for_display
        
        # 在子线程或者直接调用（注意 Qwen3VL 可能会稍微卡顿 1-2秒，这里直接同步调用）
        # 计算本小时实际涨跌百分比
        hour_change_pct = ((hour_close - prev_price) / prev_price) * 100
        comment = generate_hourly_comment(self.game_clock, hour_close, hour_change_pct, self.current_volume)
        formatted_comment = format_news_for_display(comment, tag="🤖 盘面分析")
        
        self.system_logs.append(formatted_comment)
        # 也可以推送到留言板
        self.messages.append(formatted_comment)
        
        # 重置下一小时
        self.current_open = self.current_price
        self.current_volume = 0
        self.current_momentum = 0.0 
        
        # 强平检查
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
        if self.game_clock >= 12: self.end_game()

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
        
        # 1. 资产结算 (扣除管理费)
        retail_players = [] # 存储散户对象
        mm_players = []     # 存储操盘手对象
        
        for p in self.players.values():
            val = p.get_net_worth(self.current_price)
            fee = val * 0.10
            final_val = val - fee
            
            p.cash = final_val
            p.stock = 0
            p.debt = 0
            p.logs.append(f"结算完成，管理费 ${fee:,.2f}，最终净值 ${final_val:,.2f}")
            
            if p.role == "操盘手":
                mm_players.append(p)
            else:
                retail_players.append(p)

        # 2. 计算【收割指标】(Harvest Metrics)
        # 统计散户的总初始资金 vs 总最终资金
        initial_capital_per_person = 1000000.0
        total_retail_loss = 0.0
        
        for rp in retail_players:
            # 只统计亏损的人，赚的人不算在"收割"里
            loss = initial_capital_per_person - rp.cash
            if loss > 0:
                total_retail_loss += loss
        
        # 设定目标：必须收割至少 20% 的散户本金，或者固定金额 $1,500,000
        # 这里使用动态目标：散户总人数 * 2万
        harvest_target = len(retail_players) * 200000
        mm_mission_success = total_retail_loss >= harvest_target
        
        # 3. 寻找表面赢家 (资产最高者)
        sorted_players = sorted(self.players.values(), key=lambda x: x.cash, reverse=True)
        top_player = sorted_players[0] if sorted_players else None
        losers_count = sum(1 for p in sorted_players if p.cash < initial_capital_per_person)
        
        # 4. 构建传给 LLM 的数据包
        # 我们把操盘手的特殊表现打包进去
        game_stats = {
            "start_price": self.history[0],
            "end_price": self.current_price,
            "top_player": top_player,
            "losers_count": losers_count,
            "total_retail_loss": total_retail_loss,
            "harvest_target": harvest_target,
            "mm_success": mm_mission_success,
            "mm_names": [m.display_name for m in mm_players]
        }
        
        # === DEBUG 输出 ===
        print("-" * 40)
        print(f"[DEBUG] 结算数据:")
        print(f"散户总失血: ${total_retail_loss:,.2f} / 目标: ${harvest_target:,.2f}")
        print(f"操盘手任务: {'✅ 达标' if mm_mission_success else '❌ 失败'}")
        print("-" * 40)

        # 5. LLM 结局分析
        from scripts.news_system import generate_end_game_summary
        if top_player:
            self.final_summary = generate_end_game_summary(game_stats)
            self.system_logs.append(f"📝 {self.final_summary}")
        
        self.log("游戏结束，收割完成。")
        self.save_game_report()

    def take_loan(self, email, amount):
        """【新增】申请高利贷"""
        try: amount = int(amount)
        except: return "请输入整数金额"
        if amount <= 0: return "金额需大于0"
        
        p = self.players[email]
        
        # 额度限制：当前持有现金的 90%
        # 这里指"手里现有的钱"，不包括已经借来的钱的限制，但利息会教做人
        max_loan = int(p.cash * 0.9)
        
        if amount > max_loan:
            return f"❌ 信用额度不足。当前最高可借: ${max_loan:,.0f} (现金的90%)"
        
        # 执行贷款
        interest_rate = 0.30
        repayment_amount = amount * (1 + interest_rate)
        
        p.cash += amount
        p.debt += repayment_amount
        
        p.logs.append(f"💸 申请贷款 ${amount:,.0f}，实到 ${amount:,.0f}，新增负债 ${repayment_amount:,.0f} (利率30%)")
        self.log(f"玩家 {p.display_name} 申请了高杠杆贷款，背水一战！")
        
        return "贷款成功，资金已到账"



    def save_game_report(self):
        save_dir = "savedata"
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{save_dir}/game_report_{timestamp}.md"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# 📉 暗仓战报 - {timestamp}\n\n")
                
                if self.final_summary:
                    f.write(f"> **市场总评**: {self.final_summary}\n\n")
                
                f.write(f"**最终股价**: ${self.current_price:.2f}\n\n")
                
                # 写入排行榜
                f.write("## 🏆 最终排行榜\n| 排名 | 玩家 | 身份 | 资产 |\n|---|---|---|---|\n")
                sorted_players = sorted(self.players.values(), key=lambda x: x.cash, reverse=True)
                for i, p in enumerate(sorted_players):
                    icon = "💀" if p.cash <= 0 else "💰"
                    f.write(f"| {i+1} | {p.display_name} | {p.role} | {icon} ${p.cash:,.2f} |\n")
                
                # === 修复：写入交易员大厅记录 ===
                f.write("\n## 💬 交易员大厅 (Chat Logs)\n")
                if self.messages:
                    for msg in self.messages:
                        f.write(f"- {msg}\n")
                else:
                    f.write("- (本局无对话记录)\n")

                # 写入日志
                f.write("\n## 📟 系统日志 (System Logs)\n")
                for log in self.system_logs:
                    f.write(f"- {log}\n")

                # K线数据
                f.write("\n## 📈 K线数据\n| 时间 | 开盘 | 最高 | 最低 | 收盘 | 成交量 |\n|---|---|---|---|---|---|\n")
                for k in self.kline_data:
                    f.write(f"| {k['time']}h | {k['open']:.2f} | {k['high']:.2f} | {k['low']:.2f} | {k['close']:.2f} | {k['volume']} |\n")
                    
            print(f"战报已保存: {filename}")
        except Exception as e:
            print(f"Error saving report: {e}")


    # 记得保留 prepare_next_round, calculate_short_fee, calculate_impact
    def prepare_next_round(self):
        saved = {e: Player(e, p.display_name) for e, p in self.players.items()}
        self.reset()
        self.players = saved

    def calculate_short_fee(self):
        total_short = sum(abs(p.stock) for p in self.players.values() if p.stock < 0)
        crowding = min(1.0, total_short / 1000000)
        self.short_pressure = crowding
        return 0.05 + (0.45 * crowding)

    def calculate_impact(self, current, impact, limit):
        target = current + impact
        if abs(target) < abs(current) or (target * current < 0): return impact
        dist = limit - abs(current)
        return impact * (dist / limit) if dist > 0 else 0.0

    def purchase_intel(self, email, direction):
        from scripts.news_system import generate_news, format_news_for_display
        p = self.players[email]
        cost = 5000
        status = p.get_account_status(self.current_price)
        if "锁定" in status or "冻结" in status or "爆仓" in status: return f"❌ 拒绝：账户{status}"
        _, _, avail, _ = p.get_margin_info(self.current_price)
        if avail < cost: return f"❌ 资金不足"

        p.cash -= cost
        base = 0.15 if p.role == "操盘手" else 0.05
        impact = base * (1 if direction == "看涨" else -1)
        actual = self.calculate_impact(self.current_momentum, impact, self.volatility_limit)
        self.current_momentum += actual
        
        news_type = "positive" if direction == "看涨" else "negative"
        raw_news = generate_news(news_type)
        formatted_log = format_news_for_display(raw_news)
        self.system_logs.append(formatted_log)
        self.messages.append(formatted_log)
        p.logs.append(f"购买{direction}舆情，造成 {actual*100:+.2f}% 动能")
        return "舆情购买成功"

    def buy_stock(self, email, quantity):
        try: quantity = int(quantity)
        except: return "整数"
        if quantity <= 0: return "无效数量"
        p = self.players[email]
        cost = quantity * self.current_price * 1.05
        _, _, avail, _ = p.get_margin_info(self.current_price)
        if avail < cost: return f"资金不足"
        p.cash -= cost
        p.stock += quantity
        self.current_volume += quantity
        p.logs.append(f"买入 {quantity} 股")
        return "买入成功"

    def sell_stock(self, email, quantity):
        try: quantity = int(quantity)
        except: return "整数"
        if quantity <= 0: return "无效数量"
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
        tag = "【投资者】" if p.role == "操盘手" else "【投资者】"
        self.messages.append(f"{tag} {p.display_name}: {content}")
        return "发送成功"