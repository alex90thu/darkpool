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

def generate_end_game_summary(stats):
    """
    【核心修改】结局分析 - 引入操盘手收割KPI点评
    """
    start_price = stats["start_price"]
    end_price = stats["end_price"]
    change = ((end_price - start_price) / start_price) * 100
    
    winner = stats["top_player"]
    mm_names = ", ".join(stats["mm_names"])
    
    # 构建 Prompt 上下文
    context = f"""
    【暗仓游戏结算数据】
    - 股价走势: ${start_price:.2f} -> ${end_price:.2f} (涨跌幅 {change:+.2f}%)
    - 资产冠军: {winner.display_name} (身份: {winner.role}, 资产: ${winner.cash:,.2f})
    - 散户阵亡人数: {stats['losers_count']} 人
    - 操盘手名单: {mm_names}
    
    【操盘手(庄家) 绩效考核】
    - 目标收割金额: ${stats['harvest_target']:,.0f}
    - 实际造成散户亏损: ${stats['total_retail_loss']:,.0f}
    - 考核结果: {"✅ 收割成功 (血流成河)" if stats['mm_success'] else "❌ 收割失败 (散户甚至赚了)"}
    """

    prompt = f"""
    {context}
    
    请写一段 200字左右 的【市场收盘总结】，风格模仿《华尔街之狼》，极尽嘲讽与冷酷。
    
    【强制要求】
    1. **重点点评操盘手 ({mm_names}) 的表现**：
       - 如果考核结果是【成功】：称赞他们是冷血的屠夫，成功把散户变成了燃料，市场就是零和博弈的屠宰场。
       - 如果考核结果是【失败】：**无情嘲讽操盘手**！说他们是"吃素的狼"、"被散户反杀的废物"，即使他们资产很高，但没能让散户亏钱就是庄家的耻辱！
    
    2. 必须引用数据：明确提到散户总共亏损了 ${stats['total_retail_loss']:,.0f}。
    3. 结尾要升华：关于贪婪、恐惧和信息差的残酷真理。
    4. 不要出现“（字数：XXX）”。
    """
    
    print(f"[系统] 正在调用 DeepSeek-R1 生成深度战报 (含操盘手点评)...")
    res = llm_client.chat(prompt, model="deepseek-r1")
    
    # 兜底：防止 AI 漏掉关键数据
    if res and str(int(stats['total_retail_loss'])) not in res.replace(",",""):
         res += f" (注：本次操盘手共从散户身上榨取了 ${stats['total_retail_loss']:,.2f} 的血汗钱。)"
        
    return res if res else "交易结束。残酷的市场再次证明，资本的原始积累总是伴随着血腥。"

def format_news_for_display(content, tag="📢"):
    timestamp = datetime.now().strftime("%H:%M")
    return f"[{timestamp}] {tag} {content}"