import os
import json
import urllib.request
import feedparser

# APIキーの取得（設定されていない場合は空文字）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ユーザーエージェントを設定してアクセス遮断（403エラー）を防ぐ
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

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

    # --- 2. 海外ニュース取得（安定した国際フィード） ---
    global_sources = [
        {"name": "WTT Official", "url": "https://www.worldtabletennis.com/rss/news"},
        {"name": "ITTF", "url": "https://www.ittf.com/feed/"},
        {"name": "MyTischtennis", "url": "https://www.mytischtennis.de/rss/news.xml"}
    ]

    for src in global_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries[:4]:
                title = entry.title
                summary = "海外の最新卓球ニュースです。"
                
                global_news.append({
                    "source": src["name"],
                    "title": f"📌 {title}",
                    "url": entry.link,
                    "orig": title,
                    "summary": summary,
                    "time": "最新"
                })

    # 海外ニュースが取得できなかった場合のフォールバック（画面から消えるのを防止）
    if not global_news:
        global_news.append({
            "source": "WTT Official",
            "title": "📌 World Table Tennis Latest Updates",
            "url": "https://www.worldtabletennis.com/news",
            "orig": "World Table Tennis Latest Updates",
            "summary": "WTT公式の国際大会最新ニュース一覧",
            "time": "最新"
        })

    output_data = {
        "domestic": domestic_news[:8],
        "global": global_news[:8]
    }

    # data ディレクトリの作成と保存
    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated news.json (Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
