# 每日美國新聞 AI 摘要（雲端自動推播至 Discord）

透過 **GitHub Actions** 每天在雲端自動執行（關電腦也會準時跑），抓取美國主流財經／科技新聞並串接 **Google Gemini API（啟用 Google Search 聯網搜尋）**，產出白話繁體中文日報後自動推播到你的 Discord 專屬頻道（例如 `#美股日報`）。

## 自動執行時間（臺灣時間）
- 每天中午 **12:00**（UTC `04:00`）
- 每天晚上 **21:30**（UTC `13:30`）

---

## 3 步驟快速啟用（約 3 分鐘）

### 步驟 1：取得兩個金鑰
1. **Google Gemini API Key（免費額度即可）**
   - 前往 [Google AI Studio](https://aistudio.google.com/apikey) → 點 **Create API key** → 複製金鑰。
2. **Discord 頻道 Webhook 網址**
   - 打開你的 Discord 伺服器，新建一個文字頻道（例如 `#美股日報`）。
   - 點該頻道右邊的 **齒輪（編輯頻道）** → **整合（Integrations）** → **Webhook** → **新 Webhook** → 點 **複製 Webhook 網址**。

### 步驟 2：上傳到你的 GitHub 並填入 Secrets
1. 在 GitHub 建立一個新專案（例如 `us-news-daily`，公開或私人皆可），把這個資料夾的所有檔案上傳上去。
2. 進入該 GitHub 專案的 **Settings** → 左側 **Secrets and variables** → **Actions** → 點 **New repository secret**，新增這兩個：
   - Name：`GEMINI_API_KEY` → Value：貼上你的 Gemini API Key
   - Name：`DISCORD_WEBHOOK_URL` → Value：貼上你的 Discord Webhook 網址

### 步驟 3：手動測試跑一次
1. 進入專案上方的 **Actions** 分頁。
2. 點左側的 **Daily US News AI Digest** → 點右邊的 **Run workflow** 按鈕。
3. 等約 1～2 分鐘，打開你的 Discord `#美股日報` 頻道就能看到完整日報囉！
