import os
import json
import urllib.request
import urllib.parse
import feedparser

# ユーザーエージェントを設定してアクセス遮断を防ぐ
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def translate_to_japanese(text):
    """タイトルを自動で日本語に翻訳する関数（APIキー不要）"""
    if not text:
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            translated = "".join([item[0] for item in result[0] if item[0]])
            return translated
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def fetch_feed(url):
    """RSSフィードを安全に取得する関数"""
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

    # --- 1. 国内ニュース取得 ---
    domestic_sources = [
        {"name": "Rallys", "url": "https://rallys.online/feed/"},
        {"name": "卓球王国", "url": "https://world-tt.com/blog/news/feed/"}
    ]

    for src in domestic_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries[:5]:
                domestic_news.append({
                    "source": src["name"],
                    "title": entry.title,
                    "url": entry.link,
                    "time": "最新"
                })

    # --- 2. 海外ニュース取得 & 自動日本語翻訳 ---
    global_sources = [
        # 中国ニュース (Google News RSS: 乒乓球)
        {"name": "🇨🇳 中国", "url": "https://news.google.com/rss/search?q=%E4%B9%93%E4%B9%93%E7%90%83&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"},
        # 韓国ニュース (Google News RSS: 탁구)
        {"name": "🇰🇷 韓国", "url": "https://news.google.com/rss/search?q=%ED%83%81%EA%B5%AC&hl=ko&gl=KR&ceid=KR:ko"},
        # WTT / 国際大会公式
        {"name": "🌐 WTT公式", "url": "https://www.worldtabletennis.com/rss/news"},
        # ドイツ/欧州ニュース
        {"name": "🇩🇪 ドイツ", "url": "https://www.mytischtennis.de/rss/news.xml"}
    ]

    for src in global_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries[:3]:
                raw_title = entry.title
                clean_title = raw_title.split(" - ")[0] if " - " in raw_title else raw_title
                
                # 自動日本語翻訳を実行
                jp_title = translate_to_japanese(clean_title)
                
                global_news.append({
                    "source": src["name"],
                    "title": f"📌 [AI和訳] {jp_title}",
                    "url": entry.link,
                    "orig": raw_title,
                    "summary": f"原文: {raw_title}",
                    "time": "最新"
                })

    # バックアップ用
    if not global_news:
        global_news.append({
            "source": "WTT公式",
            "title": "📌 [AI和訳] WTT公式 最新卓球ニュース",
            "url": "https://www.worldtabletennis.com/news",
            "orig": "World Table Tennis Latest Updates",
            "summary": "WTT公式の国際大会最新ニュース一覧",
            "time": "最新"
        })

    output_data = {
        "domestic": domestic_news[:8],
        "global": global_news[:8]
    }

    # 保存
    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated news.json with translations (Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
