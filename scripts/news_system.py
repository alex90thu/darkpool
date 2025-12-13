import os
import json
import random
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

class DeepSeekChat:
    def __init__(self):
        # 初始化API端点
        self.url = "https://models.sjtu.edu.cn/api/v1/chat/completions"
        self.model = "qwen3vl" 
        
    def get_api_key(self):
        load_dotenv()
        api_key = os.getenv("DEEPSEEK_API_KEY")
        return api_key

    def chat(self, prompt):
        """发送请求给 LLM"""
        api_key = self.get_api_key()
        if not api_key:
            print("⚠️ 未找到 DEEPSEEK_API_KEY，使用备用模板")
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """你是一个金融市场新闻生成器。
请根据用户要求的方向（利好/利空），生成一条简短、专业、震撼的财经快讯。
要求：
1. 字数控制在30字以内。
2. 风格模仿彭博社或路透社快讯。
3. 不要包含"根据您的要求"等废话，直接输出新闻标题。
4. 包含具体的（虚构的）行业或事件，例如"半导体"、"美联储"、"地缘政治"、"财报"。
"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 1.2, 
            # 【修改点1】大幅增加 Token 上限，防止思考过程被截断
            # R1 模型思考过程很长，通常需要 500-1000 tokens
            "max_tokens": 2000 
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                raw_content = result["choices"][0]["message"]["content"]
                
                # 【修改点2】添加 DEBUG 信息，查看完整返回
                print("-" * 30)
                print(f"[DEBUG] LLM 原始返回:\n{raw_content}")
                print("-" * 30)
                
                # === 核心修复逻辑 ===
                clean_content = raw_content
                
                # 1. 检查是否存在思考闭合标签 </think>
                if "</think>" in raw_content:
                    # 如果有闭合标签，我们只取标签之后的内容（即最终回答）
                    parts = raw_content.split("</think>")
                    clean_content = parts[-1].strip()
                elif "<think>" in raw_content:
                    # 如果有开始标签但没有结束标签，说明还是被截断了，或者思考出错
                    print("[DEBUG] 警告：思考过程未闭合（可能被截断），无法提取正文")
                    return None # 返回 None 以便触发备用模板
                
                # 2. 清理残留的格式
                clean_content = clean_content.replace('"', '').replace("'", "").strip()
                
                # 3. 再次检查内容是否为空
                if not clean_content:
                    print("[DEBUG] 警告：提取后内容为空")
                    return None

                return clean_content
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"LLM Connection Failed: {e}")
            return None

# 全局实例
llm_client = DeepSeekChat()

def generate_news(news_type):
    """
    生成新闻内容 (优先使用LLM，失败则回退到模板)
    """
    prompt = ""
    if news_type == "positive":
        prompt = "生成一条关于股市的【重大利好】消息，例如技术突破、政策支持或业绩大增。"
    else:
        prompt = "生成一条关于股市的【重大利空】消息，例如战争爆发、监管制裁或巨头暴雷。"

    # 1. 尝试调用 LLM
    print(f"[系统] 正在请求 AI 生成 {news_type} 新闻...")
    ai_news = llm_client.chat(prompt)
    
    if ai_news:
        print(f"[系统] AI 生成成功: {ai_news}")
        return ai_news
    
    print("[系统] AI 生成失败或超时，使用备用模板")
    # 2. 失败后的备用模板
    if news_type == "positive":
        templates = [
            "重磅：央行宣布降准0.5个百分点，释放长期资金约1万亿元",
            "突发：半导体巨头宣布3nm工艺取得革命性突破",
            "快讯：知名基金大举增持，市场信心显著回升",
            "利好：国家出台新一轮大规模基础设施投资计划"
        ]
    else:
        templates = [
            "突发：地缘政治局势升级，全球避险情绪升温",
            "利空：监管层严查违规资金入市，多家机构被约谈",
            "暴雷：某行业龙头财务造假被立案调查，面临退市风险",
            "数据：最新PMI指数跌破荣枯线，经济衰退担忧加剧"
        ]
    return random.choice(templates)

def format_news_for_display(news_content):
    """格式化显示"""
    timestamp = datetime.now().strftime("%H:%M")
    return f"[{timestamp}] 📢 {news_content}"