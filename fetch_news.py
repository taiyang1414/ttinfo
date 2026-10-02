import os
import json
import urllib.request
import urllib.parse
import re
import html
import feedparser

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 除外キーワード（セール・ギア・ショップ宣伝用）
EXCLUDE_KEYWORDS = [
    "セール", "限定", "特価", "割引", "ラバー", "ラケット", "ギア", "シューズ", 
    "新発売", "ショップ", "入荷", "試打", "レビュー", "比較"
]

def is_excluded(title):
    """タイトルに除外キーワードが含まれているか判定"""
    return any(keyword in title for keyword in EXCLUDE_KEYWORDS)

def clean_html(raw_html):
    """HTMLタグを除去して純粋なテキストのみを抽出"""
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return html.unescape(clean_text).strip()

def translate_to_japanese(text):
    """テキストを自動で日本語に翻訳する関数"""
    if not text:
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result and isinstance(result, list) and len(result) > 0 and result[0]:
                translated = "".join([item[0] for item in result[0] if item and isinstance(item, list) and len(item) > 0 and item[0]])
                return translated if translated else text
            return text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def get_article_summary(link, default_title):
    """記事ページから og:description や meta description（リード文）を直接取得"""
    if not link:
        return ""
    try:
        req = urllib.request.Request(link, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content_type = resp.headers.get_content_charset() or 'utf-8'
            html_text = resp.read().decode(content_type, errors='ignore')
            
            # meta description / og:description の抽出
            pattern = r'<meta\s+(?:name|property)=["\'](?:og:)?description["\']\s+content=["\']([^"\']+)["\']'
            match = re.search(pattern, html_text, re.IGNORECASE)
            if not match:
                pattern2 = r'content=["\']([^"\']+)["\']\s+(?:name|property)=["\'](?:og:)?description["\']'
                match = re.search(pattern2, html_text, re.IGNORECASE)
            
            if match:
                desc = clean_html(match.group(1))
                # タイトルと重複していないかチェック
                if len(desc) > 20 and desc.lower() not in default_title.lower():
                    return desc
    except Exception as e:
        print(f"Meta fetch error for {link}: {e}")
    return ""

def fetch_feed(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as response:
            html_data = response.read()
            return feedparser.parse(html_data)
    except Exception as e:
        print(f"Feed fetch error ({url}): {e}")
        return None

def main():
    domestic_news = []
    global_news = []

    # --- 1. 国内ニュース取得（除外フィルター適用） ---
    domestic_sources = [
        {"name": "Rallys", "url": "https://rallys.online/feed/"},
        {"name": "卓球王国", "url": "https://world-tt.com/blog/news/feed/"}
    ]

    for src in domestic_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries:
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

    # --- 2. 海外ニュース取得 ＆ 本文リード文抽出・AI自動要約 ---
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
                clean_title = raw_title.split(" - ")[0] if " - " in raw_title else raw_title
                
                # タイトルの日本語訳
                jp_title = translate_to_japanese(clean_title)
                
                # RSSのdescriptionからテキスト抽出
                raw_snippet = clean_html(entry.get('summary', entry.get('description', '')))
                
                # タイトルと重複・または短すぎる場合は直接記事URLからメタ概要文（リード文）を取得
                if len(raw_snippet) < 30 or clean_title.lower() in raw_snippet.lower():
                    meta_desc = get_article_summary(entry.link, clean_title)
                    if meta_desc:
                        raw_snippet = meta_desc
                
                # 最終的な要約文の作成と日本語訳
                if raw_snippet and len(raw_snippet) >= 20 and clean_title.lower() not in raw_snippet.lower():
                    short_snippet = raw_snippet[:180]
                    jp_summary = translate_to_japanese(short_snippet)
                else:
                    jp_summary = f"【{src['name']}速報】{jp_title}に関する現地最新レポート記事です。"

                global_news.append({
                    "source": src["name"],
                    "title": f"📌 [AI和訳] {jp_title}",
                    "url": entry.link,
                    "orig": raw_title,
                    "summary": jp_summary,
                    "time": "最新"
                })

    output_data = {
        "domestic": domestic_news[:8],
        "global": global_news[:8]
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated news.json with rich summaries (Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
