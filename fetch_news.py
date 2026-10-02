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

# セール・ギア関連（絶対除外）
STRICT_EXCLUDE = [
    "セール", "限定", "特価", "割引", "ラバー", "ラケット", "ギア", "シューズ", 
    "新発売", "ショップ", "入荷", "試打", "レビュー", "比較"
]

# ジュニア・育成系キーワード（※バンビは日本の卓球の礎となる重要カテゴリーのため除外対象から外しています）
JUNIOR_KEYWORDS = ["U12", "U-12", "U15", "U-15", "ホープス", "カブ", "小学生", "I2U"]

# 主要大会・重要結果を示すキーワード（ジュニア系でもこれらがあれば通す）
MAJOR_RESULT_KEYWORDS = ["全日本", "全国", "優勝", "決定", "日本一", "決勝", "代表", "メダル", "王者", "制覇", "バンビ"]

def is_excluded(title):
    title_upper = title.upper()
    # セール・ギア商品は完全除外
    if any(k.upper() in title_upper for k in STRICT_EXCLUDE):
        return True
    
    # バンビが含まれている場合は絶対に除外せず優先保持
    if "バンビ" in title or "BAMBI" in title_upper:
        return False

    # その他のジュニア・i2U関連キーワードが含まれる場合
    if any(k.upper() in title_upper for k in JUNIOR_KEYWORDS):
        # 「全日本」「全国」「優勝」「日本一」など重要な結果ニュースなら残す
        if any(m in title for m in MAJOR_RESULT_KEYWORDS):
            return False
        # 単なるローカル大会や日常の記事は除外
        return True
        
    return False

def clean_html(raw_html):
    if not raw_html:
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return html.unescape(clean_text).strip()

def translate_to_japanese(text):
    if not text:
        return text
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result and isinstance(result, list) and len(result) > 0 and result:
                translated = "".join([item for item in result if item and isinstance(item, list) and len(item) > 0 and item])
                return translated if translated else text
            return text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def get_article_summary(link, default_title):
    if not link:
        return ""
    try:
        req = urllib.request.Request(link, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as resp:
            content_type = resp.headers.get_content_charset() or 'utf-8'
            html_text = resp.read().decode(content_type, errors='ignore')
            
            pattern = r'<meta\s+(?:name|property)=["\'](?:og:)?description["\']\s+content=["\']([^"\']+)["\']'
            match = re.search(pattern, html_text, re.IGNORECASE)
            if not match:
                pattern2 = r'content=["\']([^"\']+)["\']\s+(?:name|property)=["\'](?:og:)?description["\']'
                match = re.search(pattern2, html_text, re.IGNORECASE)
            
            if match:
                desc = clean_html(match.group(1))
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

    # --- 1. 国内ニュース取得 ---
    domestic_sources = [
        {"name": "Rallys", "url": "https://rallys.online/feed/"},
        {"name": "卓球王国", "url": "https://world-tt.com/blog/news/feed/"},
        {"name": "選手ニュース", "url": "https://news.google.com/rss/search?q=%E5%8D%93%E7%90%83+%E2%80%9C%E9%81%B8%E6%89%8B%E2%80%9D+OR+%E2%80%9C%E3%82%A4%E3%83%B3%E3%82%BF%E3%83%93%E3%83%A5%E3%83%BC%E2%80%9D&hl=ja&gl=JP&ceid=JP:ja"}
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
                clean_title = raw_title.split(" - ") if " - " in raw_title else raw_title
                
                jp_title = translate_to_japanese(clean_title)
                raw_snippet = clean_html(entry.get('summary', entry.get('description', '')))
                
                if len(raw_snippet) < 30 or clean_title.lower() in raw_snippet.lower():
                    meta_desc = get_article_summary(entry.link, clean_title)
                    if meta_desc:
                        raw_snippet = meta_desc
                
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

    print(f"Successfully generated news.json (Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
