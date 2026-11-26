import os
import sys
import time
from datetime import datetime, timezone, timedelta
import requests
import feedparser
from google import genai
from google.genai import types

# 臺灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

HOLDINGS_URL = "https://raw.githubusercontent.com/alex4236701/sec-radar/main/holdings.txt"
TICKERS_URL = "https://raw.githubusercontent.com/alex4236701/sec-radar/main/tickers.txt"

# 實測可用的美國主流財經與科技 RSS（提供最新頭條作為搜尋種子）
RSS_FEEDS = [
    ("WSJ Markets", "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),
    ("WSJ US Business", "https://feeds.content.dowjones.io/public/rss/WSJcomUSBusiness"),
    ("WSJ Tech", "https://feeds.content.dowjones.io/public/rss/RSSWSJD"),
    ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("NYT Tech", "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"),
    ("Reuters Markets", "https://news.google.com/rss/search?q=site:reuters.com/markets+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Reuters Tech", "https://news.google.com/rss/search?q=site:reuters.com/technology+when:1d&hl=en-US&gl=US&ceid=US:en"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Tech", "https://feeds.bloomberg.com/technology/news.rss"),
    ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("CNBC Tech", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
]


def fetch_ticker_list(url: str) -> list[str]:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        tickers = []
        for line in resp.text.splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#"):
                tickers.append(clean)
        return tickers
    except Exception as e:
        print(f"[WARN] 無法讀取 {url}: {e}")
        return []


def fetch_rss_headlines(max_per_feed: int = 5) -> str:
    lines = []
    headers = {"User-Agent": "Mozilla/5.0"}
    for name, url in RSS_FEEDS:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                continue
            feed = feedparser.parse(resp.content)
            entries = feed.entries[:max_per_feed]
            if entries:
                lines.append(f"[{name}]")
                for entry in entries:
                    title = getattr(entry, "title", "").strip()
                    if title:
                        lines.append(f"- {title}")
        except Exception as e:
            print(f"[WARN] RSS 讀取失敗 ({name}): {e}")
    return "\n".join(lines)


def build_prompt(session_label: str, now_tw: str, holdings: list[str], tickers: list[str], rss_context: str) -> str:
    holdings_str = ", ".join(holdings) if holdings else "（無）"
    tickers_str = ", ".join(tickers) if tickers else "（無）"

    return f"""請透過 Google 搜尋查證最新資訊，整理今日（臺灣時間 {now_tw}，{session_label}）的完整版「每日美國新聞 AI 摘要」，一律使用白話繁體中文（臺灣用語）。

【最新外媒 RSS 頭條參考（請搭配 Google 搜尋補充完整細節與最新數字）】
{rss_context}

【搜尋策略（確保內容充實、不漏新聞）】
請涵蓋最新 24 小時內的美國新聞（優先參考 WSJ 華爾街日報、紐約時報、路透社、彭博、CNBC）：
1. 美股四大指數（道瓊、標普 500、那斯達克、費半）最新收盤／期指走勢、美債殖利率與油金美元動向。
2. 美國總體經濟數據、聯準會（Fed）官員談話、關稅／貿易與重大地緣政治。
3. 科技、AI、半導體、雲端巨頭與資料中心能源／基建動態（優先深度涵蓋）。
4. 其他重要產業（工業、醫療、消費、金融與房地產重大事件，雖不投資金融與房產仍須涵蓋以利理解大局），避免與台股盤後細節過度重疊。

【持股與觀察名單整合】
- 持股清單（共 {len(holdings)} 檔）：{holdings_str}
  （僅用於在新聞中出現時標記「★ 持股」，不額外展開一般個股新聞）
- 觀察名單（共 {len(tickers)} 檔）：{tickers_str}
  （搜尋並整理名單內公司最近 24 小時值得通知的重大消息與事件，包含財報財測、大單合約、併購、產品發布、監管動態、大幅漲跌原因等，自動過濾無關雜訊）

【寫作深度與白話規範】
- 不要為了縮短篇幅而刪減細節，請透過拆段提升閱讀性。
- 每則 S／A 級新聞必須交代完整脈絡：發生什麼事、關鍵數字或時間點、對市場或產業的具體影響。
- 切勿直接丟出外國公司、基金、券商或機構的裸名稱，必須用白話說明它們是誰、扮演什麼角色；必要時補充地名說明。

【固定版面格式（適合 Discord 閱讀，請勿使用複雜表格）】
# 每日美國新聞 AI 摘要（{now_tw}｜{session_label}）

## 1. 30 秒總覽
先附美股主要指數與美債／匯率一句話行情，再用 4～5 個要點濃縮今日全貌。
---
## 2. 市場預警指標
逐項查詢並附上具體數值、與近期相比的變化，以及白話判讀：
- CNN 恐慌與貪婪指數（CNN Fear & Greed Index）
- VIX 波動率指數（CBOE VIX）
- 美元指數（DXY）
- 美國信用利差（CDS spreads／高收益債利差）
- CME FedWatch（芝加哥商業交易所聯準會利率觀察工具）顯示的下一次聯準會會議升息／維持不變／降息機率
---
## 3. 重點新聞（採 S／A／B 重要度分級，總計至少 10～14 則）
- 【S 級｜必看重大事件】（3～4 則）：詳盡拆解背景、關鍵數據與後續影響。
- 【A 級｜重要產業與市場動態】（4～6 則）：涵蓋 AI／半導體、總經政策、大型企業動向。
- 【B 級｜值得留意的次要趨勢】（3～4 則）：補充產業鏈、債市、原物料或地緣動向。
- 控制粗體使用次數，每則結尾以統一格式標註「來源：媒體名稱」。
---
## 4. 觀察名單今日重大消息與事件
根據上述觀察名單，整理最近 24 小時內有值得通知之重大事件或消息的公司，逐家以白話說明重點與來源；若今日無重大事件則明確註明。
"""


def generate_digest(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("缺少環境變數 GEMINI_API_KEY")

    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(api_key=api_key)

    print(f"[INFO] 呼叫 Gemini 模型：{model_name}（啟用 Google Search 聯網搜尋）...")
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3,
        ),
    )
    text = response.text
    if not text:
        raise RuntimeError("Gemini 回傳內容為空")
    return text.strip()


def split_for_discord(text: str, limit: int = 1900) -> list[str]:
    """將長文章依照段落安全切分成符合 Discord 2000 字上限的片段"""
    chunks = []
    current = ""
    for para in text.split("\n\n"):
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            # 若單一段落仍超過 limit，按行再切
            if len(para) <= limit:
                current = para
            else:
                sub = ""
                for line in para.splitlines():
                    line_cand = f"{sub}\n{line}" if sub else line
                    if len(line_cand) <= limit:
                        sub = line_cand
                    else:
                        if sub:
                            chunks.append(sub)
                        # 極端情況：單行超過 limit 直接硬切
                        while len(line) > limit:
                            chunks.append(line[:limit])
                            line = line[limit:]
                        sub = line
                current = sub
    if current:
        chunks.append(current)
    return chunks


def send_to_discord(content: str) -> None:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("缺少環境變數 DISCORD_WEBHOOK_URL")

    chunks = split_for_discord(content, limit=1900)
    print(f"[INFO] 準備推播至 Discord，共分成 {len(chunks)} 則訊息...")
    for idx, chunk in enumerate(chunks, start=1):
        resp = requests.post(
            webhook_url,
            json={"content": chunk},
            timeout=15,
        )
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"Discord 推播失敗（第 {idx} 段）：HTTP {resp.status_code} - {resp.text}")
        # 避免觸發 Discord Rate Limit
        if idx < len(chunks):
            time.sleep(1.2)
    print("[INFO] Discord 推播完成！")


def main() -> None:
    now = datetime.now(TW_TZ)
    now_str = now.strftime("%Y/%m/%d %H:%M")
    session_label = "中午 12:00 場次" if now.hour < 17 else "晚上 21:30 場次"

    print(f"[INFO] 開始執行每日美國新聞 AI 摘要（{now_str}｜{session_label}）")
    holdings = fetch_ticker_list(HOLDINGS_URL)
    tickers = fetch_ticker_list(TICKERS_URL)
    print(f"[INFO] 讀取清單成功：持股 {len(holdings)} 檔、觀察名單 {len(tickers)} 檔")

    rss_context = fetch_rss_headlines(max_per_feed=5)
    prompt = build_prompt(session_label, now_str, holdings, tickers, rss_context)

    digest = generate_digest(prompt)
    print(f"[INFO] 摘要生成成功，總字數：{len(digest)}")

    send_to_discord(digest)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] 執行失敗：{exc}", file=sys.stderr)
        sys.exit(1)
