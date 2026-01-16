import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from openai import OpenAI

# ================= 🌟 终极情报源配置 =================
rss_list = [
    # --- 🇨🇳 国内主力 (你的最爱) ---
    # 选用官网源（内容和公众号一致，但极度稳定，不会报错）
    "https://www.jiqizhixin.com/rss",          # 机器之心
    "https://www.qbitai.com/feed",             # 量子位
    "https://www.geekpark.net/rss",            # 极客公园
    "https://feed.feeddd.org/feeds/Rockhazix", # 数字生命卡兹克 (个人号，很稳)

    # --- 🌍 海外前沿 (补充视野) ---
    # 既然你要做最酷的助手，必须要有硅谷的一手消息
    "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day", # Reddit (开源大模型大本营)
    "https://hnrss.org/newest?points=100",                # Hacker News (全球技术热点)
    "https://openai.com/blog/rss.xml",                    # OpenAI 官方博客
]

# AI 设置
api_key = os.getenv("OPENAI_API_KEY")
api_base = os.getenv("OPENAI_API_BASE")
client = OpenAI(api_key=api_key, base_url=api_base)
# =======================================================

def get_rss_content(url):
    """
    全能抓取函数：
    1. 伪装成 Mac 电脑上的 Chrome 浏览器（防拦截）。
    2. 兼容 RSS 和 Atom 两种格式（防报错）。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # 设置超时，Reddit 有时候慢
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ 抓取失败 {url}: {response.status_code}")
            return []
            
        content = response.text
        # 容错解析
        try:
            root = ET.fromstring(content)
        except:
            root = ET.fromstring(content.encode('utf-8'))

        items = []
        # 命名空间处理 (用于解析国外 Atom 格式)
        ns = {'atom': 'http://www.w3.org/2005/Atom'} 
        has_ns = 'http://www.w3.org/2005/Atom' in content
        
        # 混合查找所有文章
        entries = root.findall('.//item') + root.findall('.//atom:entry', ns if has_ns else {})
        
        # 每个源只取前 6 条，避免内容太多消化不了
        for item in entries[:6]: 
            # 标题
            title_node = item.find('title') if item.find('title') is not None else item.find('atom:title', ns if has_ns else {})
            title = title_node.text if title_node is not None else "无标题"
            
            # 链接
            link = ""
            if item.find('link') is not None:
                link = item.find('link').text
            elif has_ns and item.find('atom:link', ns) is not None:
                link = item.find('atom:link', ns).attrib.get('href')
            
            # 简介 (用来帮 AI 筛选)
            desc = ""
            if item.find('description') is not None:
                desc = item.find('description').text
            elif has_ns and item.find('atom:summary', ns) is not None:
                desc = item.find('atom:summary', ns).text
                
            # 简单清洗 HTML 标签
            if desc:
                desc = desc.replace('<p>', '').replace('</p>', '')[:200]

            items.append(f"【来源】{url}\n【标题】{title}\n【简介】{desc}\n【链接】{link}\n")
            
        print(f"✅ 成功抓取 {url}，获取 {len(items)} 条")
        return items
    except Exception as e:
        print(f"⚠️ 抓取出错 {url}: {e}") # 出错不中断，继续抓下一个
        return []

def main():
    print("🚀 开始全网扫描 (国内+国外)...")
    all_news = []
    
    for url in rss_list:
        news_items = get_rss_content(url)
        all_news.extend(news_items)
    
    if not all_news:
        print("📭 居然一条新闻都没抓到，请检查网络或源地址")
        return

    content_text = "\n\n".join(all_news)
    
    print("🤖 AI 正在阅读中英双语材料并撰写周报...")

    # 🔥 核心 Prompt：中西合璧版
    prompt = f"""
    你现在是全网最懂 AI 的“科技情报官”。你的桌子上堆满了来自【机器之心】、【Reddit】、【OpenAI】的最新情报。
    
    请把这些中英文混杂的内容，整理成一份**“今日 AI 必读”**。

    ### 你的任务：
    1.  **筛选**：挑出 **6-8 条** 真正重要的新闻。
        -   如果有**国内**的大模型/大厂动态，必须保留。
        -   如果有**国外**的开源/技术突破 (来自 Reddit/HN)，必须保留并**翻译成中文**。
    2.  **风格**：
        -   标题要像“公众号爆款文”，带 Emoji，吸引人点击。
        -   内容要“说人话”，不要枯燥的翻译腔。如果国外新闻比较硬核，请用通俗的语言解释一下“这有什么用”。
    3.  **格式**：
        -   **[🌍 全球视野]** (放国外重磅)
        -   **[🇨🇳 国内动态]** (放机器之心/量子位的内容)
        -   **[🛠️ 开发者/工具]** (新出的好玩工具)
        -   每条新闻最后都要附上 [🔗原文链接]。

    ### 输入素材：
    {content_text}
    """

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.0 # 保持高创造性
    )
    
    print("="*30)
    print(response.choices[0].message.content)
    print("="*30)

if __name__ == "__main__":
    main()
