import os
import json
import urllib.request
import urllib.parse
import feedparser

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 除外したいキーワード（セール・ギア・宣伝用）
EXCLUDE_KEYWORDS = [
    "セール", "限定", "特価", "割引", "ラバー", "ラケット", "ギア", "シューズ", 
    "新発売", "ショップ", "入荷", "試打", "レビュー", "比較"
]

def is_excluded(title):
    """タイトルに除外キーワードが含まれているか判定"""
    return any(keyword in title for keyword in EXCLUDE_KEYWORDS)

def translate_to_japanese(text):
    if not text:
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated = "".join([item for item in result if item])
            return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read()
            return feedparser.parse(html)
    except Exception as e:
        print(f"Feed fetch error ({url}): {e}")
        return None

def main():
    domestic_news = []
    global_news = []

    # --- 1. 国内ニュース取得（フィルター適用） ---
    domestic_sources = [
        {"name": "Rallys", "url": "https://rallys.online/feed/"},
        {"name": "卓球王国", "url": "https://world-tt.com/blog/news/feed/"}
    ]

    for src in domestic_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries:
                # セール・ギア記事はスキップ
                if is_excluded(entry.title):
                    continue
                
                domestic_news.append({
                    "source": src["name"],
                    "title": entry.title,
                    "url": entry.link,
                    "time": "最新"
                })
                if len(domestic_news) >= 8:
                    break

    # --- 2. 海外ニュース取得 & AI自動翻訳 ---
    global_sources = [
        {"name": "🇨🇳 中国", "url": "https://news.google.com/rss/search?q=%E4%B9%93%E4%B9%93%E7%90%83&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"},
        {"name": "🇰🇷 韓国", "url": "https://news.google.com/rss/search?q=%ED%83%81%EA%B5%AC&hl=ko&gl=KR&ceid=KR:ko"},
        {"name": "🌐 WTT公式", "url": "https://www.worldtabletennis.com/rss/news"},
        {"name": "🇩🇪 ドイツ", "url": "https://www.mytischtennis.de/rss/news.xml"}
    ]

    for src in global_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries[:3]:
                raw_title = entry.title
                clean_title = raw_title.split(" - ") if " - " in raw_title else raw_title
                jp_title = translate_to_japanese(clean_title)
                
                global_news.append({
                    "source": src["name"],
                    "title": f"📌 [AI和訳] {jp_title}",
                    "url": entry.link,
                    "orig": raw_title,
                    "summary": f"原文: {raw_title}",
                    "time": "最新"
                })

    output_data = {
        "domestic": domestic_news[:8],
        "global": global_news[:8]
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated news.json (Filtered Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
