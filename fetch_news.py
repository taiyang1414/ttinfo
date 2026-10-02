import os
import json
import feedparser
import urllib.parse
import urllib.request
from datetime import datetime

# ==========================================
# 1. 取得元ニュースフィードの設定 (RSS / Feed)
# ==========================================
DOMESTIC_FEEDS = [
    {"name": "Rallys", "badge": "Rallys", "url": "https://rallys.online/feed/"},
    {"name": "卓球王国", "badge": "卓球王国", "url": "https://world-tt.com/blog/news/feed"},
]

GLOBAL_FEEDS = [
    {"name": "WTT Official", "badge": "🌍 WTT", "url": "https://www.worldtabletennis.com/rss/news"},
    {"name": "MyTischtennis (DE)", "badge": "🇩🇪 ドイツ", "url": "https://www.mytischtennis.de/rss/"},
    {"name": "NAVER Sports (KR)", "badge": "🇰🇷 韓国", "url": "https://sports.news.naver.com/rss/news.xml"},
]

# ==========================================
# 2. AI自動翻訳関数 (Gemini API 使用)
# ==========================================
def translate_and_summarize_with_ai(title, source_name):
    """
    海外ニュースの見出しをAIで日本語化し、1行要約を作成する関数
    環境変数 GEMINI_API_KEY が設定されている場合に使用
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # APIキーがない場合はフォールバック表示
        return f"[AI和訳] {title}", "（自動翻訳を準備中...）"

    prompt = f"""
以下の海外卓球ニュースの見出し（ソース: {source_name}）を読み、以下の2点を日本語で返してください。
1. 自然で魅力的な日本語の見出し（「📌 [AI和訳] 」から始めてください）
2. 1行の分かりやすい概要（50文字程度）

出力フォーマット（JSON形式）:
{{
  "title_ja": "📌 [AI和訳] 日本語見出し",
  "summary_ja": "日本語での1行要約"
}}

対象ニュースタイトル:
"{title}"
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req) as response:
            res_body = json.loads(response.read().decode('utf-8'))
            res_text = res_body['candidates'][0]['content']['parts'][0]['text']
            parsed = json.loads(res_text)
            return parsed.get("title_ja", f"[AI和訳] {title}"), parsed.get("summary_ja", "要約を取得しました。")
    except Exception as e:
        print(f"AI Translation Error for '{title}': {e}")
        return f"📌 [AI和訳] {title}", "原文の最新ニュースです。"

# ==========================================
# 3. ニュース収集メイン処理
# ==========================================
def fetch_all_news():
    print("🔄 ニュースの自動取得を開始します...")
    
    # --- 国内ニュース取得 ---
    domestic_items = []
    for feed_info in DOMESTIC_FEEDS:
        parsed = feedparser.parse(feed_info["url"])
        for entry in parsed.entries[:5]: # 各サイト上位5件
            domestic_items.append({
                "source": feed_info["badge"],
                "time": getattr(entry, "published", "最新"),
                "title": entry.title,
                "url": entry.link
            })

    # --- 海外ニュース取得 & AI翻訳 ---
    global_items = []
    for feed_info in GLOBAL_FEEDS:
        parsed = feedparser.parse(feed_info["url"])
        for entry in parsed.entries[:3]: # 各サイト上位3件
            orig_title = entry.title
            title_ja, summary_ja = translate_and_summarize_with_ai(orig_title, feed_info["name"])
            
            global_items.append({
                "source": feed_info["badge"],
                "time": getattr(entry, "published", "最新"),
                "title": title_ja,
                "url": entry.link,
                "orig": orig_title,
                "summary": summary_ja
            })

    output_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "domestic": domestic_items,
        "global": global_items
    }

    # 出力先フォルダ 'data' の作成
    os.makedirs("data", exist_ok=True)
    
    # data/news.json に書き出し
    with open("data/news.json", "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print("✅ `data/news.json` の作成が完了しました！")

if __name__ == "__main__":
    fetch_all_news()