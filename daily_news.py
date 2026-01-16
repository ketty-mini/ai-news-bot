import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from openai import OpenAI

# ================= 🌟 终极情报源配置 =================
rss_list = [
    # --- 🇨🇳 国内主力 ---
    "https://www.jiqizhixin.com/rss",          # 机器之心
    "https://www.qbitai.com/feed",             # 量子位
    "https://www.geekpark.net/rss",            # 极客公园
    "https://feed.feeddd.org/feeds/Rockhazix", # 数字生命卡兹克

    # --- 🌍 海外前沿 ---
    "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day", # Reddit LocalLLaMA
    "https://hnrss.org/newest?points=100",                # Hacker News
    "https://openai.com/blog/rss.xml",                    # OpenAI Blog
]

# 🔑 密钥配置 (适配 ServerChan)
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
server_chan_key = os.getenv("SERVER_CHAN_KEY") # 读取 ServerChan Key
client = OpenAI(api_key=api_key, base_url=api_base)
# =======================================================

def get_rss_content(url):
    """抓取 RSS 内容 (带浏览器伪装)"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []
            
        content = response.text
        try:
            root = ET.fromstring(content)
        except:
            root = ET.fromstring(content.encode('utf-8'))

        items = []
        ns = {'atom': 'http://www.w3.org/2005/Atom'} 
        has_ns = 'http://www.w3.org/2005/Atom' in content
        entries = root.findall('.//item') + root.findall('.//atom:entry', ns if has_ns else {})
        
        for item in entries[:6]: 
            title_node = item.find('title') if item.find('title') is not None else item.find('atom:title', ns if has_ns else {})
            title = title_node.text if title_node is not None else "无标题"
            
            link = ""
            if item.find('link') is not None:
                link = item.find('link').text
            elif has_ns and item.find('atom:link', ns) is not None:
                link = item.find('atom:link', ns).attrib.get('href')
            
            desc = ""
            if item.find('description') is not None:
                desc = item.find('description').text
            elif has_ns and item.find('atom:summary', ns) is not None:
                desc = item.find('atom:summary', ns).text
            
            if desc:
                desc = desc.replace('<p>', '').replace('</p>', '')[:200]

            items.append(f"【来源】{url}\n【标题】{title}\n【简介】{desc}\n【链接】{link}\n")
        return items
    except Exception as e:
        print(f"⚠️ 抓取出错 {url}: {e}")
        return []

def send_to_wechat(title, content):
    """🚀 推送消息到微信 (ServerChan 版)"""
    if not server_chan_key:
        print("❌ 未配置 SERVER_CHAN_KEY，跳过推送")
        return

    # ServerChan 的 API 地址
    url = f"https://sctapi.ftqq.com/{server_chan_key}.send"
    
    data = {
        "title": title,
        "desp": content # ServerChan 把正文叫做 'desp'
    }
    
    try:
        resp = requests.post(url, data=data)
        result = resp.json()
        if result.get('code') == 0:
            print("✅ 微信推送成功！(ServerChan)")
        else:
            print(f"❌ 微信推送失败: {result}")
    except Exception as e:
        print(f"❌ 推送网络错误: {e}")

def main():
    print("🚀 开始抓取 (ServerChan版)...")
    all_news = []
    for url in rss_list:
        all_news.extend(get_rss_content(url))
    
    if not all_news:
        print("📭 无内容")
        return

    content_text = "\n\n".join(all_news)
    print("🤖 AI 正在撰写日报...")

    prompt = f"""
    你是 AI 科技情报官。请根据以下素材写一份【今日 AI 必读】日报。
    
    要求：
    1. 挑选 6-8 条最重要的中外 AI 新闻。
    2. 标题要像公众号爆款，带 Emoji。
    3. 内容说人话，解释技术背后的意义。
    4. 必须包含 [🌍全球] 和 [🇨🇳国内] 两个板块。
    5. 每条新闻后附上 [🔗原文链接]。
    6. 结尾加一句简短的“小编热评”。

    素材：
    {content_text}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0
    )
    
    daily_report = response.choices[0].message.content
    
    print("="*30)
    print(daily_report)
    print("="*30)
    
    # 🔥 发送！
    today_date = datetime.now().strftime("%Y-%m-%d")
    send_to_wechat(f"🤖 AI日報 {today_date}", daily_report)

if __name__ == "__main__":
    main()
