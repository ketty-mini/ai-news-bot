import os
import feedparser
import requests
from openai import OpenAI
from dotenv import load_dotenv

# ================= 配置区 =================
SERVER_CHAN_KEY = "SCT309802ThCDjXg9iP50l5l5dzzZH3fbf"  # 🔴 记得填回你的 Key
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
    url = f"https://sctapi.ftqq.com/{SERVER_CHAN_KEY}.send"
    data = {"title": title, "desp": content}
    try:
        requests.post(url, data=data)
        print("✅ 微信推送成功！")
    except Exception as e:
        print(f"❌ 推送失败: {e}")

def check_and_summarize(source_name, title, content):
    """
    让 AI 既做裁判（判断是不是AI新闻），又做运动员（写总结）
    """
    print(f"🤖 正在分析【{source_name}】：{title} ...")
    
    # 针对卡兹克做特别处理，他一般都写AI，但语气要骚
    if "卡兹克" in source_name or "Rockhazix" in source_name:
        style = "用极客、幽默、搞钱的语气"
        # 卡兹克的内容默认视为 AI 相关，稍微放宽标准
        role_prompt = "你是卡兹克的粉丝，重点关注AI新玩法。"
    else:
        style = "用专业分析师的语气"
        role_prompt = "你是一个严格的 AI 内容过滤器。"

    prompt = f"""
    {role_prompt}
    
    请执行两个步骤：
    1. **判断**：这篇文章是否与“人工智能、AI、大模型、LLM、AIGC、机器人”高度相关？
       - 如果是讲手机硬件、纯商业并购、汽车试驾、娱乐八卦等与AI技术无关的内容，请直接回复四个字母：SKIP
    2. **总结**：如果这篇文章是关于 AI 的，请{style}，总结3个核心干货点。

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
        
        # 如果 AI 说跳过，那就返回 None
        if "SKIP" in result:
            print(f"   🗑️  不是 AI 内容，跳过。")
            return None
        
        return result
    except Exception as e:
        print(f"❌ 报错: {e}")
        return None

def main():
    print("🌍 正在启动 AI 专属抓取任务...")
    daily_report = "### 📅 今日 AI 纯享版早报\n\n"
    count = 0 # 记录找到了几条 AI 新闻
    
    for url in rss_list:
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                continue
            
            # 智能判断来源名字
            if "Rockhazix" in url or "feeddd" in url:
                source_name = "数字生命卡兹克"
            else:
                source_name = feed.feed.title if 'title' in feed.feed else "科技新闻"

            # 🔁 每个源检查前 2 篇，防止第一篇是广告错过了后面的 AI 干货
            # (如果你觉得太慢，可以把 [:2] 改成 [:1])
            for post in feed.entries[:2]:
                title = post.title
                link = post.link
                content = post.summary if 'summary' in post else post.title
                
                # 让 AI 审核 + 总结
                summary = check_and_summarize(source_name, title, content)
                
                if summary: # 如果不是 None，说明是 AI 新闻
                    daily_report += f"#### 【{source_name}】{title}\n"
                    daily_report += f"{summary}\n"
                    daily_report += f"[👉 原文]({link})\n\n"
                    daily_report += "---\n\n"
                    count += 1
            
        except Exception as e:
            print(f"⚠️ 抓取 {url} 时出错，跳过。")
            continue

    if count > 0:
        print(f"🚀 筛选出 {count} 条 AI 新闻，正在发送...")
        push_to_wechat(f"今日AI早报：{count}条精选", daily_report)
    else:
        print("🤷‍♂️ 扫了一圈，今天好像没有值得看的 AI 新闻（或者都被过滤掉了）。")

if __name__ == "__main__":
    main()