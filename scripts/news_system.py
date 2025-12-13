"""
系统公告功能模块
为接入LLM API做好准备
"""

import random
from datetime import datetime

def generate_news(news_type):
    """
    生成新闻内容
    
    Args:
        news_type (str): 新闻类型，"positive" 或 "negative"
    
    Returns:
        str: 生成的新闻内容
    """
    # TODO: 接入LLM API生成真实的新闻内容
    # 示例代码（注释掉）：
    # from openai import OpenAI
    # client = OpenAI(api_key="your-api-key")
    # response = client.completions.create(
    #     model="text-davinci-003",
    #     prompt=f"Generate a short financial market news about {news_type} impact.",
    #     max_tokens=50
    # )
    # return response.choices[0].text.strip()
    
    # 临时使用固定字符串代替
    if news_type == "positive":
        positive_news_templates = [
            "【市场新闻】利好消息：行业巨头宣布重大投资计划",
            "【市场新闻】政策红利：政府出台刺激经济新措施",
            "【市场新闻】技术创新：某公司发布革命性新产品",
            "【市场新闻】业绩超预期：多家上市公司财报表现亮眼"
        ]
        return random.choice(positive_news_templates)
    else:
        negative_news_templates = [
            "【市场新闻】利空消息：监管机构警告市场风险增加",
            "【市场新闻】经济担忧：最新数据显示经济增长放缓",
            "【市场新闻】突发事件：国际局势紧张引发市场恐慌",
            "【市场新闻】丑闻曝光：某知名企业财务造假被调查"
        ]
        return random.choice(negative_news_templates)

def format_news_for_display(news_content):
    """
    格式化新闻内容用于显示
    
    Args:
        news_content (str): 新闻内容
    
    Returns:
        str: 格式化后的新闻内容
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"[{timestamp}] **系统公告**: {news_content}"