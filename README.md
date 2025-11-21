# Facebook 貼文發布到 WordPress 工具

這是一個本機版的 Python 工具，可以將 Facebook 粉絲團的公開貼文內容和圖片抓取下來，並自動發布到 WordPress 網站。

## ✨ 功能特色

### 單篇發布
- 📱 從 Facebook 公開貼文抓取內容和圖片
- 🖼️ 自動下載貼文中的所有附圖
- 🎲 隨機選擇一張圖片作為特色圖片（Featured Image）
- 📚 將所有圖片上傳到 WordPress 的 custom field（news-album gallery）
- 🏷️ 支援選擇 WordPress 文章標籤和分類
- 📅 自訂文章發布日期和時間

### 🚀 批次抓取（新功能）
- 🔄 **智能自動滾動**: 自動滾動粉絲團頁面直到指定日期
- 📅 **日期過濾**: 只抓取設定日期之後的貼文
- 📊 **批量預覽**: 抓取完成後可預覽所有符合條件的貼文
- ⏱️ **自動停止**: 遇到早於設定日期的貼文時智能停止
- � **適合場景**: 定期同步粉絲團內容、歷史資料導入

### 用戶界面
- �🌐 簡潔的 Web 界面操作
- 📋 分頁設計：單篇發布 + 批次抓取
- 💡 智能提示和進度顯示

## 系統需求

- Python 3.8 或更高版本
- Google Chrome 瀏覽器
- ChromeDriver（Selenium 需要）
- WordPress 網站（需要有 REST API 權限）

## 安裝步驟

### 1. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

### 2. 安裝 ChromeDriver

**macOS (使用 Homebrew):**
```bash
brew install chromedriver
```

**其他系統:**
請從 [ChromeDriver 官網](https://chromedriver.chromium.org/downloads) 下載對應版本

### 3. 配置 WordPress 連接

編輯 `config.py` 文件，填入你的 WordPress 網站資訊：

```python
# WordPress 配置
WORDPRESS_URL = "https://xinbaby.com.tw"
WORDPRESS_USERNAME = "your_username"
WORDPRESS_PASSWORD = "your_app_password"

# 文章配置
POST_TYPE = "news"
TAG_TAXONOMY = "news-tag"
CATEGORY_TAXONOMY = "news-type"
CUSTOM_FIELD_ALBUM = "news-album"
```

**注意:** WordPress 密碼建議使用 [Application Password](https://make.wordpress.org/core/2020/11/05/application-passwords-integration-guide/)，不要使用主密碼。

## 使用方法

### 1. 啟動應用

```bash
python app.py
```

或使用啟動腳本（推薦）：

```bash
./start.sh
```

### 2. 打開瀏覽器

訪問 `http://localhost:8081`

### 3. 選擇功能

#### 📄 單篇發布

適合發布單個 Facebook 貼文：

1. **Facebook 貼文 URL**: 輸入要抓取的 Facebook 貼文完整網址
   - 範例: `https://www.facebook.com/pagename/posts/123456789`
   - 必須是公開貼文

2. **文章標籤**: 從下拉選單選擇（可選）
   - 下拉選單會自動從 WordPress 載入 `news-tag` taxonomy

3. **文章分類**: 從下拉選單選擇（可選）
   - 下拉選單會自動從 WordPress 載入 `news-type` taxonomy

4. **發布日期**: 選擇文章發布日期（預設為當天）

5. **發布時間**: 選擇文章發布時間（預設為 20:00）

6. 點擊「🚀 發布到 WordPress」

#### 🔄 批次抓取（推薦）

適合批量抓取粉絲團貼文：

1. **粉絲團 URL**: 輸入 Facebook 粉絲團頁面網址
   - 範例: `https://www.facebook.com/yourpage`
   - 必須是公開粉絲團

2. **起始日期**: 選擇要抓取的起始日期
   - 系統會抓取此日期**之後**的所有貼文
   - 建議先選擇較近的日期測試

3. 點擊「🔍 開始抓取貼文」

4. **智能滾動過程**:
   - 🔄 系統自動滾動頁面
   - 📅 檢查每個貼文的日期
   - ⏹️ 遇到早於設定日期的貼文時停止
   - 📊 顯示抓取進度

5. **預覽結果**:
   - 查看所有符合條件的貼文
   - 包含標題、日期、內容預覽、圖片數量
   - 可以選擇性發布到 WordPress

### 4. 系統處理流程

無論使用哪種方式，系統都會：
- 自動打開 Chrome 瀏覽器（無頭模式）
- 訪問 Facebook 頁面
- 抓取貼文內容和圖片
- 下載圖片到本機臨時目錄
- 上傳圖片到 WordPress
- 創建新文章並設置：
  - 標題（使用貼文前 50 字）
  - 內容（貼文完整文本）
  - 特色圖片（隨機選擇一張）
  - 相冊字段（所有圖片）
  - 標籤和分類
  - 發布日期和時間

### 5. 停止應用

如果需要停止應用，使用停止腳本：

```bash
./stop.sh
```

這會優雅地停止應用並釋放端口，避免端口佔用問題。

## 項目結構

```
facebook_post_to_wp_posts/
├── app.py                    # Flask 應用主程式
├── config.py                 # 配置文件
├── wordpress_api.py          # WordPress API 客戶端
├── facebook_scraper.py       # Facebook 貼文爬蟲
├── jetengine_helper.py       # JetEngine Gallery 字段處理
├── requirements.txt          # Python 依賴
├── README.md                 # 使用說明
├── templates/
│   └── index.html           # Web 界面
└── static/                   # 靜態資源（如有）
```

## 技術說明

### WordPress REST API

本工具使用 WordPress REST API 進行以下操作：

- **獲取 Taxonomies**: `GET /wp-json/wp/v2/{taxonomy}`
- **上傳媒體**: `POST /wp-json/wp/v2/media`
- **創建文章**: `POST /wp-json/wp/v2/{post_type}`
- **更新 Meta**: `POST /wp-json/wp/v2/{post_type}/{id}`

### JetEngine Gallery 字段

`news-album` 字段使用 JetEngine 的 gallery 類型，程式會嘗試多種方法來設置該字段：

1. REST API meta 字段（多種格式）
2. JetEngine 自定義端點（如果存在）
3. PHP 序列化格式

### Facebook 爬蟲

使用 Selenium WebDriver 來模擬瀏覽器訪問 Facebook：

- 支援無頭模式（不顯示瀏覽器窗口）
- 自動點擊"查看更多"按鈕以獲取完整內容
- 智能識別貼文圖片（過濾頭像、圖標等）
- 支援多張圖片的貼文

## 注意事項

### 一般使用
1. **只支援公開貼文**: 需要登入才能看到的貼文無法抓取

2. **Facebook 反爬蟲**: Facebook 可能會偵測並阻止自動化訪問，建議：
   - 不要頻繁使用，建議間隔至少 30 分鐘
   - 如遇到問題，可以手動登入 Facebook 後再執行

3. **ChromeDriver 版本**: 確保 ChromeDriver 版本與你的 Chrome 瀏覽器版本相符

4. **網路連接**: 需要穩定的網路連接來訪問 Facebook 和 WordPress

5. **臨時文件**: 圖片會暫存在 `temp_fb_downloads` 目錄，處理完成後會自動刪除

### 批次抓取特別注意
6. **處理時間**: 批次抓取可能需要 2-5 分鐘，取決於：
   - 設定日期範圍的大小
   - 粉絲團貼文的數量
   - 網路連接速度

7. **資源消耗**: 批次抓取會消耗較多系統資源，建議：
   - 關閉不必要的程式
   - 確保足夠的磁碟空間
   - 避免同時執行其他大型任務

8. **使用頻率**: 不建議對同一粉絲團頻繁執行批次抓取

9. **測試建議**: 首次使用建議：
   - 選擇較短的日期範圍（如最近 3-7 天）
   - 先測試小型粉絲團
   - 確認功能正常後再擴大範圍

## 疑難排解

### ChromeDriver 錯誤

如果出現 ChromeDriver 相關錯誤：

```bash
# macOS
brew upgrade chromedriver

# 檢查 Chrome 和 ChromeDriver 版本是否匹配
chromedriver --version
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --version
```

### 無法抓取貼文內容

- 確認 URL 是否正確
- 確認貼文是否為公開
- 嘗試在瀏覽器中手動打開該 URL

### WordPress 連接失敗

- 確認 `config.py` 中的配置是否正確
- 確認 WordPress REST API 是否啟用
- 確認用戶權限是否足夠
- 測試 Application Password 是否有效

### 圖片上傳失敗

- 檢查 WordPress 的上傳文件大小限制
- 確認 WordPress 媒體庫權限設置

## 授權

本專案僅供學習和個人使用。請遵守 Facebook 的使用條款和服務協議。

## 支援

如有問題或建議，請聯繫開發團隊。
