import os
import feedparser
import requests
from datetime import datetime, timedelta, timezone
from openai import OpenAI

# ================= ⚡️ 你的“即时雷达”配置 =================
# 1. 扫描频率配合：这里设定只看“过去 2 小时”的新闻
# (设为 2 小时是为了防止 GitHub 运行排队导致的漏抓，稍微宽裕一点)
LOOKBACK_HOURS = 2 

# 2. 情报源 (保持你的中西合璧配置)
rss_list = [
    # --- 🇨🇳 国内主力 ---
    "https://www.jiqizhixin.com/rss",          # 机器之心
    "https://www.qbitai.com/feed",             # 量子位
    "https://www.geekpark.net/rss",            # 极客公园
    "https://feed.feeddd.org/feeds/Rockhazix", # 数字生命卡兹克

    # --- 🌍 海外前沿 ---
    "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day", # Reddit
    "https://hnrss.org/newest?points=100",                # Hacker News
    "https://openai.com/blog/rss.xml",                    # OpenAI 
]

# 🔑 密钥配置
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
server_chan_key = os.getenv("SERVER_CHAN_KEY")
client = OpenAI(api_key=api_key, base_url=api_base)
# =======================================================

def is_recent(entry):
    """判断文章是否是最近发布的"""
    try:
        # feedparser 会自动把各种格式的时间转成 struct_time
        published = entry.get('published_parsed') or entry.get('updated_parsed')
        if not published:
            return False # 没有时间的文章直接跳过，防止乱发
        
        # 转换成 UTC 时间对象
        pub_time = datetime(*published[:6], tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        
        # 检查时间差
        if (now - pub_time) <= timedelta(hours=LOOKBACK_HOURS):
            return True
        return False
    except:
        return False

def get_latest_news():
    """只抓取最近更新的新闻"""
    recent_items = []
    
    print(f"📡 正在扫描过去 {LOOKBACK_HOURS} 小时的更新...")
    
    for url in rss_list:
        try:
            # 使用 feedparser 解析，因为它对时间处理最强
            feed = feedparser.parse(url)
            
            for entry in feed.entries[:5]: # 每个源只看最新的5条，再筛时间
                if is_recent(entry):
                    title = entry.title
                    link = entry.link
                    # 简介截取
                    desc = entry.summary if 'summary' in entry else entry.title
                    desc = desc[:150].replace('<p>','').replace('</p>','')
                    
                    recent_items.append(f"【来源】{feed.feed.title}\n【标题】{title}\n【链接】{link}\n【简介】{desc}\n")
        except Exception as e:
            print(f"⚠️ 抓取跳过 {url}: {e}")
            continue
            
    return recent_items

def send_to_wechat(title, content):
    if not server_chan_key: return
    url = f"https://sctapi.ftqq.com/{server_chan_key}.send"
    data = {"title": title, "desp": content}
    requests.post(url, data=data)
    print("✅ 消息已推送")

def main():
    # 1. 抓取
    news = get_latest_news()
    
    # 2. 如果没有新东西，直接下班
    if not news:
        print("😴 过去一小时风平浪静，没有新消息。")
        return

    print(f"🚀 发现 {len(news)} 条新情报！正在分析...")
    content_text = "\n\n".join(news)

    # 3. AI 分析 (Prompt 换成了“快讯”风格)
    prompt = f"""
    这里有几条刚刚发生的 AI 科技新闻。请快速生成一份**【即时快讯】**。
    
    要求：
    1. 不要写成日报，要写成**“突发消息”**的感觉。
    2. 只保留有价值的内容，如果是无聊的广告直接忽略。
    3. 格式：
       🔥 **标题**
       内容：一句话讲清楚发生了什么。
       [🔗原文]
    
    素材：
    {content_text}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    result = response.choices[0].message.content
    print("="*30)
    print(result)
    print("="*30)
    
    # 4. 推送
    # 标题带上具体时间，比如 "AI快讯 14:00"
    # 强制加上 8 小时时差，修正为北京时间
    bj_time = datetime.now(timezone(timedelta(hours=8)))
    current_time = bj_time.strftime("%H:%M")
    send_to_wechat(f"🚨 AI快讯 {current_time}", result)

if __name__ == "__main__":
    main()

