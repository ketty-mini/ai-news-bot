import os
import feedparser
import requests
import json      # <--- 新增
import hashlib   # <--- 新增
from datetime import datetime, timedelta, timezone
from openai import OpenAI

# ... (原有的配置代码) ...

# === 新增：记忆文件配置 ===
HISTORY_FILE = "history.json"

# ================= ⚡️ 你的“即时雷达”配置 =================
# 1. 扫描频率配合：这里设定只看“过去 2 小时”的新闻
# (设为 2 小时是为了防止 GitHub 运行排队导致的漏抓，稍微宽裕一点)
LOOKBACK_HOURS = 24 

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

# === 新增：记忆助手函数 (放在 is_recent 上面) ===
def load_history():
    """读取历史发送记录"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                # 读取列表并转为集合(set)，方便快速查找
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_history(history_set):
    """保存最新的 500 条记录"""
    history_list = list(history_set)
    # 只保留最后 500 条，防止文件越来越大
    if len(history_list) > 500:
        history_list = history_list[-500:]
        
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, indent=2, ensure_ascii=False)

def generate_id(entry):
    """生成文章唯一指纹"""
    # 优先用 link，没有链接就用标题
    val = entry.get('link') or entry.get('title') or "unknown"
    # 计算 MD5
    return hashlib.md5(val.encode('utf-8')).hexdigest()

# ... (接着是你原来的 is_recent 函数) ...

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
    """
    功能：抓取新闻 -> 记忆去重 -> 格式化成文字 -> 返回文本列表
    """
    print(f"🚀 正在扫描 {len(rss_list)} 个源...")
    
    # 1. 准备工作
    sent_ids = load_history() # 读取“已发送历史”
    new_sent_ids = set()      # 准备一个小本本，记录这次新发的
    formatted_news_list = []  # 准备一个篮子，装处理好的“文字消息”
    
    # 2. 开始遍历所有 RSS 源
    for url in rss_list:
        try:
            # 伪装浏览器 User-Agent，防止被 Reddit 等屏蔽
            feed = feedparser.parse(url, agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)")
            
            # 3. 遍历该源下的每一篇文章
            for entry in feed.entries:
                # --- A. 查重逻辑 ---
                uid = generate_id(entry) # 算出身份证号(MD5)
                if uid in sent_ids:      # 如果历史记录里有
                    continue             # 跳过，不处理
                
                # --- B. 时间逻辑 ---
                if not is_recent(entry): # 如果是几年前的老坟
                    continue             # 跳过
                
                # --- C. 找到了新文章！开始“格式化” (这里是关键修改) ---
                print(f"    - 🎉 新发现: {entry.get('title')}")
                
                # C1. 提取标题和链接
                title = entry.get('title', '无标题')
                link = entry.get('link', '')
                
                # C2. 提取并清洗简介 (把你原来的清洗逻辑搬进来了)
                if 'summary' in entry:
                    desc = entry.summary
                else:
                    desc = title # 没简介就用标题凑数
                
                # 去掉 HTML 标签和换行符，只取前 150 字
                desc = desc.replace('<p>', '').replace('</p>', '').replace('\n', ' ')[:150]
                
                # C3. 拼装成最终的一条字符串
                news_str = f"【来源】{feed.feed.get('title', '未知源')}\n【标题】{title}\n【链接】{link}\n【简介】{desc}\n"
                
                # 放入篮子
                formatted_news_list.append(news_str)
                
                # 记录下来，下次就不发了
                sent_ids.add(uid)
                new_sent_ids.add(uid)
                
        except Exception as e:
            print(f"❌ 抓取出错 {url}: {e}")

    # 4. 收尾：如果有新记录，保存回硬盘
    if new_sent_ids:
        print(f"💾 更新记忆... 新增 {len(new_sent_ids)} 条")
        save_history(sent_ids)
    else:
        print("💤 没有新内容")

    # 5. 返回的是“字符串列表”，main 函数就能直接用了！
    return formatted_news_list

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


