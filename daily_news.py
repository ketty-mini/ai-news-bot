import os
import feedparser
import requests
import time
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from dotenv import load_dotenv

# ================= 配置区 =================
# 🔴 你的 ServerChan Key
SERVER_CHAN_KEY = os.getenv("SERVER_CHAN_KEY") 

# ⏱️ 抓取时间窗口：只看过去 X 小时内发布的新闻
# 如果你计划每 1 小时运行一次脚本，这里建议填 2 (稍微多一点防止漏掉)
LOOKBACK_HOURS = 2 
# =========================================

load_dotenv(override=True)
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
client = OpenAI(api_key=api_key, base_url=api_base)

# ✅ 你的 RSS 列表
rss_list = [
    "https://feed.feeddd.org/feeds/Rockhazix",  # 数字生命卡兹克
    "https://www.huxiu.com/rss/0.xml",          # 虎嗅
    "https://www.jiqizhixin.com/rss",           # 机器之心
    "http://www.geekpark.net/rss",              # 极客公园
    "https://www.ifanr.com/feed",               # APPSO/爱范儿
    "https://www.qbitai.com/feed",              # 量子位
    "http://www.aiera.com.cn/feed"              # 新智元
]

def push_to_wechat(title, content):
    if not SERVER_CHAN_KEY:
        print("❌ 未检测到 ServerChan Key，无法推送")
        return
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    data = {"title": title, "desp": content}
    try:
        requests.post(url, data=data)
        print("✅ 微信推送成功！")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def is_recent_post(entry):
    """
    判断文章是否是【最近 LOOKBACK_HOURS 小时】内发布的
    """
    try:
        # 获取文章发布时间 (struct_time)
        published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        
        if not published_struct:
            # 如果源没提供时间，为了不漏消息，默认算作新的（或者你可以选择跳过）
            return True

        # 转换为 UTC 时间对象
        pub_time = datetime(*published_struct[:6], tzinfo=timezone.utc)
        
        # 获取当前 UTC 时间
        now = datetime.now(timezone.utc)
        
        # 计算时间差
        diff = now - pub_time
        
        # 判断是否在窗口期内
        if diff <= timedelta(hours=LOOKBACK_HOURS):
            return True
        else:
            return False
    except Exception as e:
        print(f"   ⚠️ 时间解析失败，默认放行: {e}")
        return True

def check_and_summarize(source_name, title, content):
    print(f"🤖 正在分析【{source_name}】：{title} ...")
    
    if "卡兹克" in source_name or "Rockhazix" in source_name:
        style = "用极客、幽默、搞钱的语气"
        role_prompt = "你是卡兹克的粉丝，重点关注AI新玩法。"
    else:
        style = "用专业分析师的语气"
        role_prompt = "你是一个严格的 AI 内容过滤器。"

    prompt = f"""
    {role_prompt}
    请执行两个步骤：
    1. **判断**：这篇文章是否与“人工智能、AI、大模型、LLM、AIGC、机器人”高度相关？
       - 如果无关（如手机硬件、纯商业并购、汽车、娱乐），直接回复：SKIP
    2. **总结**：如果是 AI 相关的，{style}，总结3个核心干货点。

    文章标题：{title}
    文章内容：{content[:1000]}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        result = response.choices[0].message.content.strip()
        if "SKIP" in result:
            print(f"   🗑️  不是 AI 内容，跳过。")
            return None
        return result
    except Exception as e:
        print(f"❌ API 报错: {e}")
        return None

def main():
    print(f"🌍 开始巡逻... 只寻找过去 {LOOKBACK_HOURS} 小时内的新闻")
    daily_report = ""
    count = 0
    
    for url in rss_list:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            
            if "Rockhazix" in url or "feeddd" in url:
                source_name = "数字生命卡兹克"
            else:
                source_name = feed.feed.title if 'title' in feed.feed else "科技新闻"

            # 检查前 3 篇（防止连发好几篇，只看第1篇可能会漏）
            for post in feed.entries[:3]:
                # 1️⃣ 第一关：时间过滤器
                if not is_recent_post(post):
                    continue # 太旧了，跳过，看下一篇
                
                # 2️⃣ 第二关：AI 内容过滤器
                title = post.title
                link = post.link
                content = post.summary if 'summary' in post else post.title
                
                summary = check_and_summarize(source_name, title, content)
                
                if summary:
                    daily_report += f"#### 【{source_name}】{title}\n"
                    daily_report += f"{summary}\n"
                    daily_report += f"[👉 原文]({link})\n\n---\n\n"
                    count += 1
            
        except Exception as e:
            print(f"⚠️ 抓取 {url} 出错跳过")
            continue

    if count > 0:
        print(f"🚀 发现 {count} 条最新 AI 资讯，正在推送...")
        # 标题带上时间，方便区分
        current_hour = datetime.now().hour
        push_to_wechat(f"AI快讯 ({current_hour}点档)", daily_report)
    else:
        print("😴 过去几小时内没有新的 AI 内容。")

if __name__ == "__main__":
    main()
