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

# 除外キーワード（用具、ショップ、一般技術指導、ローカル教室など）
STRICT_EXCLUDE = [
    "セール", "限定", "特価", "割引", "ラバー", "ラケット", "ギア", "シューズ", 
    "新発売", "ショップ", "入荷", "試打", "レビュー", "比較", "打ち方", "コツ",
    "レッスン", "卓球場", "初心者", "教室"
]

# 主要選手・主要大会キーワード（優先取得）
MAJOR_KEYWORDS = [
    "張本智和", "張本美和", "早田ひな", "松島輝空", "平野美宇", "伊藤美誠", 
    "戸上隼輔", "大藤沙月", "木原美悠", "篠塚大登", "宇田幸矢", "田中佑汰",
    "佐藤瞳", "橋本帆乃香", "長﨑美柚", "日本代表", "WTT", "Tリーグ", "全日本", 
    "世界卓球", "優勝", "決勝", "メダル", "代表", "選考", "王楚欽", "孫穎莎"
]

def is_excluded(title):
    if not isinstance(title, str):
        return False
    title_upper = title.upper()
    return any(k.upper() in title_upper for k in STRICT_EXCLUDE)

def calculate_priority_score(title):
    if not isinstance(title, str):
        return 0
    score = 0
    for k in MAJOR_KEYWORDS:
        if k in title:
            score += 10
    return score

def clean_html(raw_html):
    if not raw_html or not isinstance(raw_html, str):
        return ""
    clean_text = re.sub(r'<[^>]+>', '', raw_html)
    return html.unescape(clean_text).strip()

def is_google_boilerplate(text):
    if not text or not isinstance(text, str):
        return True
    boilerplate_keywords = [
        "Google ニュース",
        "Google News",
        "包括的な最新ニュース報道",
        "世界中の情報源から集められた"
    ]
    return any(b in text for b in boilerplate_keywords)

def translate_to_japanese(text):
    if not text or not isinstance(text, str):
        return text if isinstance(text, str) else ""
    try:
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={urllib.parse.quote(text)}"
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result and isinstance(result, list) and len(result) > 0 and result:
                translated = "".join([item for item in result if item and isinstance(item, list) and len(item) > 0 and isinstance(item, str)])
                return translated if translated else text
            return text
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def get_article_summary(link, default_title):
    if not link or not isinstance(link, str):
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
                if len(desc) > 20 and isinstance(default_title, str) and desc.lower() not in default_title.lower():
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
    raw_domestic_candidates = []
    global_news = []

    # --- 1. 国内主要ニュース取得 (主要選手・代表動向優先クエリ) ---
    major_player_query = '卓球 (張本 OR 松島輝空 OR 早田ひな OR 平野美宇 OR 伊藤美誠 OR 戸上隼輔 OR 大藤沙月 OR 木原美悠 OR 篠塚大登 OR 日本代表 OR WTT OR Tリーグ)'
    encoded_query = urllib.parse.quote(major_player_query)
    
    domestic_sources = [
        {"name": "主要選手ニュース", "url": f"https://news.google.com/rss/search?q={encoded_query}&hl=ja&gl=JP&ceid=JP:ja"},
        {"name": "Rallys", "url": "https://rallys.online/feed/"},
        {"name": "卓球王国", "url": "https://world-tt.com/blog/news/feed/"}
    ]

    for src in domestic_sources:
        feed = fetch_feed(src["url"])
        if feed and feed.entries:
            for entry in feed.entries:
                title = entry.title if hasattr(entry, 'title') and isinstance(entry.title, str) else ''
                if is_excluded(title):
                    continue
                
                score = calculate_priority_score(title)
                if src["name"] == "主要選手ニュース":
                    score += 15

                raw_domestic_candidates.append({
                    "source": src["name"],
                    "title": title,
                    "url": entry.link if hasattr(entry, 'link') and isinstance(entry.link, str) else '',
                    "score": score,
                    "time": "最新"
                })

    # 重複除外 ＆ 優先度スコア順にソート
    seen_titles = set()
    domestic_news = []
    raw_domestic_candidates.sort(key=lambda x: x["score"], reverse=True)

    for item in raw_domestic_candidates:
        short_title = item["title"][:20]
        if short_title in seen_titles:
            continue
        seen_titles.add(short_title)

        domestic_news.append({
            "source": item["source"],
            "title": item["title"],
            "url": item["url"],
            "time": item["time"]
        })
        if len(domestic_news) >= 8:
            break

    # --- 2. 海外ニュース取得 ＆ AI自動要約 ---
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
                raw_title = entry.title if hasattr(entry, 'title') and isinstance(entry.title, str) else ''
                clean_title = raw_title.split(" - ")[0] if " - " in raw_title else raw_title
                
                jp_title = translate_to_japanese(clean_title)
                raw_snippet = clean_html(entry.get('summary', entry.get('description', '')))
                
                if len(raw_snippet) < 20 or is_google_boilerplate(raw_snippet) or clean_title.lower() in raw_snippet.lower():
                    meta_desc = get_article_summary(entry.link if hasattr(entry, 'link') and isinstance(entry.link, str) else '', clean_title)
                    if meta_desc and not is_google_boilerplate(meta_desc):
                        raw_snippet = meta_desc
                    else:
                        raw_snippet = ""
                
                if raw_snippet and len(raw_snippet) >= 20 and not is_google_boilerplate(raw_snippet):
                    short_snippet = raw_snippet[:180]
                    jp_summary = translate_to_japanese(short_snippet)
                    if is_google_boilerplate(jp_summary):
                        jp_summary = f"【{src['name']}速報】「{jp_title}」に関する現地メディアの最新トピックス記事です。"
                else:
                    jp_summary = f"【{src['name']}速報】「{jp_title}」に関する現地メディアの最新トピックス記事です。"

                global_news.append({
                    "source": src["name"],
                    "title": f"📌 [AI和訳] {jp_title}",
                    "url": entry.link if hasattr(entry, 'link') and isinstance(entry.link, str) else '',
                    "orig": raw_title,
                    "summary": jp_summary,
                    "time": "最新"
                })

    # --- 3. 最新ITTF世界ランキング TOP25 ---
    rankings_data = {
        "updated": "2026年第40週",
        "men": [
            {"rank": 1, "name": "王楚欽 (Wang Chuqin)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 2, "name": "林詩棟 (Lin Shidong)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 3, "name": "松島輝空", "flag": "🇯🇵", "tag": "日本最高位"},
            {"rank": 4, "name": "張本智和", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 5, "name": "F.ルブラン (Felix Lebrun)", "flag": "🇫🇷", "tag": "フランス"},
            {"rank": 6, "name": "モーレゴード (Truls Moregard)", "flag": "🇸🇪", "tag": "スウェーデン"},
            {"rank": 7, "name": "梁靖崑 (Liang Jingkun)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 8, "name": "馬龍 (Ma Long)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 9, "name": "樊振東 (Fan Zhendong)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 10, "name": "林昀儒 (Lin Yun-Ju)", "flag": "🇹🇼", "tag": "チャイニーズタイペイ"},
            {"rank": 11, "name": "カルデラノ (Hugo Calderano)", "flag": "🇧🇷", "tag": "ブラジル"},
            {"rank": 12, "name": "チン・チウ (Dang Qiu)", "flag": "🇩🇪", "tag": "ドイツ"},
            {"rank": 13, "name": "戸上隼輔", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 14, "name": "張禹珍 (Jang Woojin)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 15, "name": "カールソン (Kristian Karlsson)", "flag": "🇸🇪", "tag": "スウェーデン"},
            {"rank": 16, "name": "シェルベリ (Anton Kallberg)", "flag": "🇸🇪", "tag": "スウェーデン"},
            {"rank": 17, "name": "オフチャロフ (Dimitrij Ovtcharov)", "flag": "🇩🇪", "tag": "ドイツ"},
            {"rank": 18, "name": "篠塚大登", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 19, "name": "アッサール (Omar Assar)", "flag": "🇪🇬", "tag": "エジプト"},
            {"rank": 20, "name": "安宰賢 (An Jaehyun)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 21, "name": "林鐘勲 (Lim Jonghoon)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 22, "name": "A.ルブラン (Alexis Lebrun)", "flag": "🇫🇷", "tag": "フランス"},
            {"rank": 23, "name": "フランツィスカ (Patrick Franziska)", "flag": "🇩🇪", "tag": "ドイツ"},
            {"rank": 24, "name": "高承睿 (Kao Cheng-Jui)", "flag": "🇹🇼", "tag": "チャイニーズタイペイ"},
            {"rank": 25, "name": "ヨルジッチ (Darko Jorgic)", "flag": "🇸🇮", "tag": "スロベニア"}
        ],
        "women": [
            {"rank": 1, "name": "孫穎莎 (Sun Yingsha)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 2, "name": "王曼昱 (Wang Manyu)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 3, "name": "張本美和", "flag": "🇯🇵", "tag": "日本最高位"},
            {"rank": 4, "name": "王芸迪 (Wang Yidi)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 5, "name": "陳夢 (Chen Meng)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 6, "name": "早田ひな", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 7, "name": "陳幸同 (Chen Xingtong)", "flag": "🇨🇳", "tag": "中国"},
            {"rank": 8, "name": "申裕斌 (Shin Yubin)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 9, "name": "スッチ (Bernadette Szocs)", "flag": "🇷🇴", "tag": "ルーマニア"},
            {"rank": 10, "name": "ディアス (Adriana Diaz)", "flag": "🇵🇷", "tag": "プエルトリコ"},
            {"rank": 11, "name": "鄭怡静 (Cheng I-Ching)", "flag": "🇹🇼", "tag": "チャイニーズタイペイ"},
            {"rank": 12, "name": "大藤沙月", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 13, "name": "佐藤瞳", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 14, "name": "ポルカノバ (Sofia Polcanova)", "flag": "🇦🇹", "tag": "オーストリア"},
            {"rank": 15, "name": "橋本帆乃香", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 16, "name": "ミッテルハム (Nina Mittelham)", "flag": "🇩🇪", "tag": "ドイツ"},
            {"rank": 17, "name": "パバド (Prithika Pavade)", "flag": "🇫🇷", "tag": "フランス"},
            {"rank": 18, "name": "長﨑美柚", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 19, "name": "木原美悠", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 20, "name": "メシュレフ (Dina Meshref)", "flag": "🇪🇬", "tag": "エジプト"},
            {"rank": 21, "name": "田志希 (Jeon Jihee)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 22, "name": "朱芊曦 (Joo Cheonhui)", "flag": "🇰🇷", "tag": "韓国"},
            {"rank": 23, "name": "シャン・シャオナ (Shan Xiaona)", "flag": "🇩🇪", "tag": "ドイツ"},
            {"rank": 24, "name": "伊藤美誠", "flag": "🇯🇵", "tag": "日本"},
            {"rank": 25, "name": "平野美宇", "flag": "🇯🇵", "tag": "日本"}
        ]
    }

    output_data = {
        "rankings": rankings_data,
        "domestic": domestic_news[:8],
        "global": global_news[:8]
    }

    os.makedirs("data", exist_ok=True)
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated news.json with Top 25 Rankings & Major Player News (Domestic: {len(domestic_news)}, Global: {len(global_news)})")

if __name__ == "__main__":
    main()
