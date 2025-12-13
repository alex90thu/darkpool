import os
import json
import random
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

class LLMClient:
    def __init__(self):
        # 初始化API端点
        self.url = "https://models.sjtu.edu.cn/api/v1/chat/completions"
        # 默认使用快模型 (用于每小时快讯/点评)
        self.default_model = "qwen3vl" 
        
    def get_api_key(self):
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY") 
        return api_key

    def chat(self, prompt, system_prompt="", model=None):
        """
        发送请求给 LLM
        :param model: 如果指定，则覆盖默认模型 (例如强制用 deepseek-r1)
        """
        api_key = self.get_api_key()
        if not api_key: return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 确定使用的模型
        target_model = model if model else self.default_model

        if not system_prompt:
            system_prompt = "你是一个专业的金融市场分析师，风格犀利、简练。"

        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 1.0, 
            # 如果是 DeepSeek-R1，给足 Token 让他思考
            "max_tokens": 2000 if "deepseek" in target_model else 1000 
        }

        try:
            # R1 比较慢，如果是 R1 则给 60秒超时，普通模型 30秒
            timeout = 60 if "deepseek" in target_model else 30
            
            # print(f"[DEBUG] Calling {target_model} (Timeout: {timeout}s)...")
            
            response = requests.post(self.url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 清洗 DeepSeek 的思考过程 <think>...</think>
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                return content
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"LLM Failed ({target_model}): {e}")
            return None

# 全局实例
llm_client = LLMClient()

def generate_news(news_type):
    """(保持使用默认快模型)"""
    prompt = f"生成一条关于股市的【重大{news_type}】快讯。要求：30字以内，模仿彭博社风格，包含具体虚构事件（如芯片、战争、财报）。直接输出标题。"
    res = llm_client.chat(prompt)
    if res: return res
    return "重磅：市场出现剧烈波动，神秘资金正在通过暗池进行大规模交易"

def generate_hourly_comment(hour, price, change_pct, volume):
    """(保持使用默认快模型)"""
    prompt = f"""
    当前是第 {hour} 小时交易结束。
    股价: ${price:.2f}
    本小时涨跌幅: {change_pct:+.2f}%
    成交量: {volume} 手
    
    请用【一句话】点评当前盘面情绪（恐慌/贪婪/观望）。30字以内，犀利一点。
    """
    res = llm_client.chat(prompt)
    return res if res else f"市场波动剧烈，多空双方在 ${price:.2f} 展开激烈争夺。"

def generate_end_game_summary(start_price, end_price, winner, losers_count):
    """
    【核心修改】结局分析 - 强制切换回 DeepSeek-R1
    """
    change = ((end_price - start_price) / start_price) * 100
    
    prompt = f"""
    【暗仓游戏结算数据】
    - 整体走势: ${start_price:.2f} -> ${end_price:.2f} (涨跌幅 {change:+.2f}%)
    - 最终赢家: {winner['name']} (身份: {winner['role']}, 资产: ${winner['cash']:,.2f})
    - 破产人数: {losers_count} (精确数据)

    请写一段 300字左右 的【市场收盘总结】。风格模仿《华尔街之狼》，极尽嘲讽。
    
    【核心指令】
    1. 必须精准引用数据：**绝对不要**写"有人"或"部分人"破产，必须明确写出"共有 {losers_count} 个倒霉蛋"！
    2. 如果破产人数为0，就嘲讽大家太怂了；如果大于0，就嘲讽这 {losers_count} 个人是市场的燃料。
    3. 分析赢家 {winner['name']} 是靠运气还是操纵。
    """
    
    # === 这里显式传入 model="deepseek-r1" ===
    print(f"[系统] 正在调用 DeepSeek-R1 生成深度战报 (预计需 10-20秒)...")
    res = llm_client.chat(prompt, model="deepseek-r1")
    
    # 兜底：万一 DeepSeek 还是没写对数字（虽然概率很低），强制修正
    if res and str(losers_count) not in res:
        res += f" (注：本次大清洗共埋葬了 {losers_count} 个破产者。)"
        
    return res if res else "交易结束。残酷的市场再次证明，只有少数人能带着金钱离开，其他人留下的只有债务。"

def format_news_for_display(content, tag="📢"):
    timestamp = datetime.now().strftime("%H:%M")
    return f"[{timestamp}] {tag} {content}"