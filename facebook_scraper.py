"""
Facebook 貼文爬蟲模塊

使用 Selenium 從 Facebook 公開貼文獲取內容和圖片
"""
import os
import time
import requests
from typing import Tuple, List, Optional, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


class FacebookScraper:
    def __init__(self, headless: bool = True):
        """
        初始化 Facebook 爬蟲

        Args:
            headless: 是否使用無頭模式（不顯示瀏覽器窗口）
        """
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """初始化 Chrome WebDriver"""
        if self.driver is not None:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        import os
        import shutil

        # 方法1: 優先使用系統 PATH 中的 chromedriver
        try:
            system_chromedriver = shutil.which('chromedriver')
            if system_chromedriver and os.path.isfile(system_chromedriver):
                print(f"使用系統 ChromeDriver: {system_chromedriver}")
                service = Service(system_chromedriver)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                return
        except Exception as e:
            print(f"使用系統 chromedriver 失敗: {e}")

        # 方法2: 使用 webdriver-manager
        try:
            print("嘗試使用 webdriver-manager...")
            driver_path = ChromeDriverManager().install()

            # 修復路徑問題：webdriver-manager 可能返回錯誤的路徑
            if not os.path.isfile(driver_path) or not os.access(driver_path, os.X_OK):
                # 嘗試在同一目錄下找到真正的 chromedriver 可執行文件
                driver_dir = os.path.dirname(driver_path)
                possible_names = ['chromedriver', 'chromedriver.exe']

                for name in possible_names:
                    possible_path = os.path.join(driver_dir, name)
                    if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                        driver_path = possible_path
                        break
                else:
                    # 在父目錄的 chromedriver 中查找
                    parent_dir = os.path.dirname(driver_dir)
                    for name in possible_names:
                        possible_path = os.path.join(parent_dir, name)
                        if os.path.isfile(possible_path) and os.access(possible_path, os.X_OK):
                            driver_path = possible_path
                            break

            print(f"使用 ChromeDriver: {driver_path}")
            service = Service(driver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            print(f"初始化 Chrome WebDriver 失敗: {e}")
            print("請確保已安裝 Google Chrome 瀏覽器和 ChromeDriver")
            print("macOS 安裝方法: brew install chromedriver")
            raise

    def scrape_post(self, post_url: str, download_dir: str = 'temp_fb_downloads') -> Tuple[str, List[str]]:
        """
        爬取 Facebook 貼文內容和圖片

        Args:
            post_url: Facebook 貼文URL
            download_dir: 圖片下載目錄

        Returns:
            (貼文內容文本, 圖片文件路徑列表)
        """
        try:
            self._init_driver()

            print(f"正在訪問 Facebook 貼文: {post_url}")
            self.driver.get(post_url)

            # 等待頁面加載
            time.sleep(3)

            # 點擊"查看更多"按鈕（如果存在）
            try:
                see_more_buttons = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'x1i10hfl') and contains(text(), '查看更多')]")
                if not see_more_buttons:
                    see_more_buttons = self.driver.find_elements(By.XPATH, "//div[contains(text(), 'See more')]")
                if not see_more_buttons:
                    see_more_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button' and contains(text(), '更多')]")

                if see_more_buttons:
                    see_more_buttons[0].click()
                    time.sleep(1)
            except Exception as e:
                print(f"未找到'查看更多'按鈕: {e}")

            # 獲取貼文內容
            post_text = self._extract_post_text()
            print(f"已提取貼文內容 ({len(post_text)} 字)")

            # 獲取圖片
            image_urls = self._extract_image_urls()
            print(f"找到 {len(image_urls)} 張圖片")

            # 下載圖片
            image_files = []
            if image_urls:
                os.makedirs(download_dir, exist_ok=True)
                image_files = self._download_images(image_urls, download_dir)
                print(f"已下載 {len(image_files)} 張圖片")

            return post_text, image_files

        except Exception as e:
            print(f"爬取貼文時出錯: {e}")
            import traceback
            traceback.print_exc()
            return "", []

    def _extract_post_text(self) -> str:
        """提取貼文文本內容（包含 emoji）"""
        # 嘗試多種可能的選擇器
        selectors = [
            "//div[@data-ad-preview='message']",
            "//div[contains(@class, 'xdj266r')]",
            "//div[@data-ad-comet-preview='message']",
            "//div[contains(@class, 'x11i5rnm')]",
        ]

        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                if elements and len(elements) > 0:
                    element = elements[0]

                    # Facebook 將 emoji 渲染為圖片，需要特殊處理
                    # 使用 JavaScript 重建包含 emoji 的完整文本
                    text_with_emoji = self.driver.execute_script("""
                        function getTextWithEmoji(element) {
                            let text = '';

                            function processNode(node) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    text += node.textContent;
                                } else if (node.nodeType === Node.ELEMENT_NODE) {
                                    // 如果是 emoji 圖片，使用 alt 屬性
                                    if (node.tagName === 'IMG' && node.src && node.src.includes('emoji.php')) {
                                        text += node.alt || '';
                                    } else {
                                        // 遞歸處理子節點
                                        for (let child of node.childNodes) {
                                            processNode(child);
                                        }
                                        // 處理某些需要換行的元素
                                        if (['DIV', 'P', 'BR'].includes(node.tagName)) {
                                            text += '\\n';
                                        }
                                    }
                                }
                            }

                            processNode(element);
                            return text;
                        }

                        return getTextWithEmoji(arguments[0]);
                    """, element)

                    if text_with_emoji and len(text_with_emoji.strip()) > 10:
                        # 清理多餘的換行
                        text_with_emoji = '\n'.join(line.strip() for line in text_with_emoji.split('\n') if line.strip())
                        return text_with_emoji.strip()

            except Exception as e:
                print(f"  提取文本失敗: {e}")
                continue

        # 如果上述方法都失敗，嘗試舊方法
        print("  使用備用方法提取文本...")
        text_elements = []
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector + "//span")
                if elements:
                    text_elements.extend(elements)
                    break
            except Exception:
                continue

        post_text = ""
        for element in text_elements:
            try:
                text = element.text.strip()
                if text and len(text) > 10:
                    post_text += text + "\n\n"
            except Exception:
                continue

        return post_text.strip()

    def _extract_image_urls(self) -> List[str]:
        """提取圖片URL"""
        image_urls = []
        seen_urls = set()

        try:
            # 等待圖片加載
            time.sleep(2)

            # 方法1: 查找所有 img 標籤
            img_elements = self.driver.find_elements(By.TAG_NAME, 'img')
            print(f"找到 {len(img_elements)} 個 img 元素")

            for img in img_elements:
                try:
                    src = img.get_attribute('src')
                    if not src:
                        continue

                    # 過濾條件：
                    # 1. 必須包含 scontent (Facebook CDN)
                    # 2. 排除小尺寸頭像和圖標
                    # 3. 排除表情符號
                    if 'scontent' in src:
                        # 排除條件
                        exclude_patterns = [
                            'p50x50', 'p40x40', 'p32x32', 'p16x16',  # 小頭像
                            's50x50', 's40x40', 's32x32',  # 小圖標
                            'emoji', 'static',  # 表情符號和靜態資源
                            'safe_image',  # 安全圖片
                        ]

                        if not any(pattern in src for pattern in exclude_patterns):
                            # 獲取原始 URL（移除查詢參數）
                            base_url = src.split('?')[0]

                            # 檢查圖片尺寸（盡量獲取大圖）
                            width = img.get_attribute('width')
                            height = img.get_attribute('height')

                            # 只取較大的圖片 (寬度或高度 > 200)
                            try:
                                if width and height:
                                    w = int(width) if width.isdigit() else 0
                                    h = int(height) if height.isdigit() else 0
                                    if w < 200 and h < 200:
                                        continue
                            except:
                                pass

                            if base_url not in seen_urls:
                                seen_urls.add(base_url)
                                image_urls.append(src)  # 保留完整 URL（含參數）以獲得更好的質量
                                print(f"  找到圖片: {base_url[:80]}...")
                except Exception as e:
                    continue

            # 方法2: 查找高清圖片（data-src 或其他屬性）
            try:
                for img in img_elements:
                    for attr in ['data-src', 'data-original', 'data-lazy-src']:
                        src = img.get_attribute(attr)
                        if src and 'scontent' in src:
                            base_url = src.split('?')[0]
                            if base_url not in seen_urls:
                                seen_urls.add(base_url)
                                image_urls.append(src)
                                print(f"  找到高清圖片: {base_url[:80]}...")
            except Exception as e:
                print(f"提取高清圖片失敗: {e}")

            # 方法3: 查找背景圖片
            try:
                divs_with_bg = self.driver.find_elements(By.XPATH, "//*[contains(@style, 'background-image')]")
                for div in divs_with_bg:
                    style = div.get_attribute('style')
                    if style and 'scontent' in style:
                        # 從 style 中提取 URL
                        import re
                        urls = re.findall(r'url\(["\']?(https://scontent[^"\')\s]+)', style)
                        for url in urls:
                            base_url = url.split('?')[0]
                            if base_url not in seen_urls:
                                seen_urls.add(base_url)
                                image_urls.append(url)
                                print(f"  找到背景圖片: {base_url[:80]}...")
            except Exception as e:
                print(f"提取背景圖片失敗: {e}")

        except Exception as e:
            print(f"提取圖片失敗: {e}")

        print(f"總共找到 {len(image_urls)} 張圖片")
        return image_urls

    def _download_images(self, image_urls: List[str], download_dir: str) -> List[str]:
        """
        下載圖片到本地

        Args:
            image_urls: 圖片URL列表
            download_dir: 下載目錄

        Returns:
            本地文件路徑列表
        """
        downloaded_files = []

        for i, url in enumerate(image_urls):
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # 確定文件擴展名
                content_type = response.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = 'jpg'
                elif 'png' in content_type:
                    ext = 'png'
                else:
                    ext = 'jpg'  # 默認

                filename = f"fb_image_{i+1}.{ext}"
                filepath = os.path.join(download_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                downloaded_files.append(filepath)
                print(f"  - 已下載: {filename}")

            except Exception as e:
                print(f"下載圖片失敗 {url}: {e}")
                continue

        return downloaded_files

    def close(self):
        """關閉瀏覽器"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        """Context manager 入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 出口"""
        self.close()


def scrape_facebook_post(post_url: str, download_dir: str = 'temp_fb_downloads') -> Tuple[str, List[str]]:
    """
    便捷函數：爬取 Facebook 貼文

    Args:
        post_url: Facebook 貼文URL
        download_dir: 圖片下載目錄

    Returns:
        (貼文內容文本, 圖片文件路徑列表)
    """
    with FacebookScraper() as scraper:
        return scraper.scrape_post(post_url, download_dir)


class FacebookPageScraper:
    """Facebook 粉絲團爬蟲 - 批次抓取貼文
    
    需要先登入 Facebook（使用 login_and_save_cookies）取得 cookies，
    批次抓取時載入 cookies 後即可正常瀏覽粉絲頁並提取貼文 URL。
    """

    COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'facebook_cookies.json')

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.base_scraper = FacebookScraper(headless=headless)

    def _init_driver(self):
        """初始化 Chrome WebDriver（啟用效能日誌以攔截 GraphQL 回應）"""
        import shutil

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36')
        # 啟用效能日誌以攔截 GraphQL API 回應
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        system_chromedriver = shutil.which('chromedriver')
        if not system_chromedriver:
            raise RuntimeError("找不到 chromedriver")

        print(f"使用系統 ChromeDriver: {system_chromedriver}")
        service = Service(system_chromedriver)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # 反自動化偵測
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
        })

        # 啟用 Network 監聽（用於讀取 response body）
        self.driver.execute_cdp_cmd('Network.enable', {})

        # 同步更新 base_scraper 的 driver
        self.base_scraper.driver = self.driver

    def _load_cookies(self) -> bool:
        """從檔案載入 Facebook cookies"""
        import json
        if not os.path.exists(self.COOKIES_FILE):
            print("⚠️ 找不到 Facebook cookies 檔案，請先登入")
            return False
        try:
            with open(self.COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            
            # 先訪問 facebook.com 才能設定 cookies
            self.driver.get('https://www.facebook.com/')
            time.sleep(2)
            
            for cookie in cookies:
                # Selenium 不支援某些屬性
                for key in ['sameSite', 'storeId', 'id']:
                    cookie.pop(key, None)
                # 確保 domain 正確
                if 'domain' not in cookie or not cookie['domain']:
                    cookie['domain'] = '.facebook.com'
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            
            print(f"✅ 已載入 {len(cookies)} 個 cookies")
            return True
        except Exception as e:
            print(f"❌ 載入 cookies 失敗: {e}")
            return False

    @classmethod
    def login_and_save_cookies(cls) -> bool:
        """
        開啟非無頭瀏覽器讓使用者登入 Facebook，登入成功後儲存 cookies。
        此方法會開啟一個 Chrome 視窗，使用者需手動登入。
        """
        import json
        import shutil

        print("正在開啟 Chrome 瀏覽器...")
        print("請在瀏覽器中登入 Facebook，登入完成後系統會自動儲存 cookies。")

        chrome_options = Options()
        # 非無頭模式 - 使用者可以看到並操作瀏覽器
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1200,800')

        system_chromedriver = shutil.which('chromedriver')
        if not system_chromedriver:
            print("❌ 找不到 chromedriver")
            return False

        service = Service(system_chromedriver)
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            driver.get('https://www.facebook.com/login')
            print("⏳ 等待登入... (完成後會自動偵測)")
            print("  偵測方式：等待 c_user cookie 出現（代表真正登入成功）")

            # 等待使用者登入 — 用 cookie 偵測而非 URL 偵測
            # 登入成功後 Facebook 會設定 c_user cookie
            max_wait = 300  # 最多等 5 分鐘
            logged_in = False
            for i in range(max_wait):
                time.sleep(1)
                # 檢查是否已有登入 session cookie
                browser_cookies = driver.get_cookies()
                cookie_names = [c.get('name', '') for c in browser_cookies]
                if 'c_user' in cookie_names:
                    # 再等幾秒確保所有 cookies 完全設定
                    print("  偵測到 c_user cookie，等待其餘 cookies 設定完成...")
                    time.sleep(5)
                    logged_in = True
                    break
                if i % 30 == 0 and i > 0:
                    print(f"  仍在等待登入... ({i}秒)")

            if not logged_in:
                print("❌ 登入逾時（未偵測到 c_user cookie）")
                return False

            # 儲存 cookies
            cookies = driver.get_cookies()
            cookie_names = [c.get('name', '') for c in cookies]
            print(f"  取得 cookies: {cookie_names}")

            with open(cls.COOKIES_FILE, 'w') as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            print(f"✅ 登入成功！已儲存 {len(cookies)} 個 cookies 到 {cls.COOKIES_FILE}")
            return True

        except Exception as e:
            print(f"❌ 登入過程出錯: {e}")
            return False
        finally:
            driver.quit()

    @classmethod
    def check_login_status(cls) -> bool:
        """檢查是否已有有效的 cookies 檔案（必須含 c_user）"""
        import json
        if not os.path.exists(cls.COOKIES_FILE):
            return False
        try:
            with open(cls.COOKIES_FILE, 'r') as f:
                cookies = json.load(f)
            # 檢查是否有關鍵的登入 session cookie
            cookie_names = [c.get('name', '') for c in cookies]
            # c_user 是 Facebook 登入後才會出現的 cookie
            return 'c_user' in cookie_names
        except Exception:
            return False

    def scrape_page_posts(self, page_url: str, since_date: str) -> List[Dict]:
        """
        爬取粉絲團指定日期之後的所有貼文

        策略（攔截 GraphQL API 回應）：
        1. 啟用 Chrome Performance Logs
        2. 載入 cookies → 訪問粉絲頁 → 持續滾動
        3. 從 GraphQL API 回應中提取 pfbid + post_id + creation_time + message
        4. 用 creation_time 過濾日期
        5. 逐一訪問每個 permalink 抓取完整內容和圖片
        """
        try:
            self._init_driver()

            from datetime import datetime, timedelta
            import re
            import json as json_mod
            import urllib.parse
            target_date = datetime.strptime(since_date, '%Y-%m-%d')
            target_ts = int(target_date.timestamp())

            # 載入 cookies
            if not self._load_cookies():
                print("❌ 無法載入 Facebook cookies，請先使用「登入 Facebook」功能")
                return []

            # 從 URL 提取 page_id
            parsed = urllib.parse.urlparse(page_url)
            params = urllib.parse.parse_qs(parsed.query)
            page_id = params.get('id', [None])[0]
            if not page_id:
                path = parsed.path.strip('/')
                if path.isdigit():
                    page_id = path

            print(f"\n正在訪問粉絲團: {page_url}")
            print(f"目標日期: {since_date}")
            print(f"粉絲頁 ID: {page_id or '未知（將從頁面提取）'}")
            self.driver.get(page_url)
            time.sleep(6)

            page_title = self.driver.title
            print(f"頁面標題: {page_title}")

            # 如果 URL 是 slug 格式（如 /euxin.babycare），嘗試從頁面提取數字 page_id
            if not page_id:
                try:
                    source_snippet = self.driver.page_source[:50000]  # 只看前 50KB
                    # Facebook 在頁面中嵌入 "pageID":"12345" 或 "page_id":"12345" 等
                    import re as re_mod
                    patterns = [
                        r'"pageID"\s*:\s*"(\d{10,})"',
                        r'"page_id"\s*:\s*"(\d{10,})"',
                        r'"userID"\s*:\s*"(\d{10,})"',
                        r'"ownerID"\s*:\s*"(\d{10,})"',
                        r'"profileID"\s*:\s*"(\d{10,})"',
                        r'"id"\s*:\s*"(\d{10,})"[^}]*"__typename"\s*:\s*"Page"',
                    ]
                    for pat in patterns:
                        m = re_mod.search(pat, source_snippet)
                        if m:
                            page_id = m.group(1)
                            print(f"  \ud83d\udd0d 從頁面提取到 page_id: {page_id}")
                            break
                    if not page_id:
                        # 備用：找第一個出現的 actors[0].id
                        actor_match = re_mod.search(r'"actors"\s*:\s*\[\s*\{\s*[^}]*"id"\s*:\s*"(\d{10,})"', source_snippet)
                        if actor_match:
                            page_id = actor_match.group(1)
                            print(f"  \ud83d\udd0d 從 actors 提取到 page_id: {page_id}")
                except Exception as e:
                    print(f"  \u26a0\ufe0f 提取 page_id 失敗: {e}")

            # 檢查是否仍在登入頁
            if 'login' in self.driver.current_url.lower():
                print("❌ cookies 已失效，請重新登入")
                return []

            # 關閉可能的彈窗
            try:
                close_btns = self.driver.find_elements(By.XPATH,
                    "//div[@aria-label='關閉' or @aria-label='Close']")
                if close_btns:
                    close_btns[0].click()
                    time.sleep(1)
            except:
                pass

            # Step 1: 滾動頁面並從 GraphQL 回應中收集貼文資料
            post_map = {}  # post_id -> {pfbid, post_id, creation_time, full_message, ...}
            scroll_count = 0
            max_scrolls = 100
            no_new_count = 0
            found_old_post = False
            scrolls_after_old = 0  # 找到舊貼文後的額外滾動次數

            print("\n開始滾動並攔截 GraphQL 回應...")
            print("=" * 60)

            # Step 0: 從頁面原始碼提取 SSR 嵌入的貼文（最新 1-2 篇可能不在 GraphQL XHR 中）
            ssr_posts = self._extract_posts_from_page_source(page_id)
            for key, info in ssr_posts.items():
                post_map[key] = info
                ct = info.get('creation_time')
                if ct and ct < target_ts:
                    found_old_post = True
            if ssr_posts:
                print(f"  SSR 嵌入: 找到 {len(ssr_posts)} 個貼文")

            # 先處理初始頁面載入的 GraphQL 回應（也包含貼文資料）
            initial_posts = self._extract_posts_from_perf_logs(page_id)
            for key, info in initial_posts.items():
                post_map[key] = info
                ct = info.get('creation_time')
                if ct and ct < target_ts:
                    found_old_post = True
            if initial_posts:
                print(f"  初始載入: 找到 {len(initial_posts)} 個貼文")

            while scroll_count < max_scrolls:
                # 滾動
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(4)

                # 從 performance logs 提取 GraphQL 回應
                new_posts = self._extract_posts_from_perf_logs(page_id)

                new_found = 0
                for key, info in new_posts.items():
                    if key in post_map:
                        continue
                    post_map[key] = info
                    new_found += 1

                    # 檢查日期是否早於目標
                    ct = info.get('creation_time')
                    if ct and ct < target_ts:
                        found_old_post = True

                scroll_count += 1
                if new_found > 0:
                    no_new_count = 0
                    print(f"  滾動 #{scroll_count}: 新增 {new_found} 個，累計 {len(post_map)} 個")
                else:
                    no_new_count += 1

                if no_new_count >= 5:
                    print(f"  連續 {no_new_count} 次無新內容，停止滾動")
                    break

                # 如果已找到早於目標日期的貼文，再多滾動 3 次就停
                if found_old_post:
                    scrolls_after_old += 1
                    if scrolls_after_old >= 3:
                        print(f"  已找到早於 {since_date} 的貼文，額外滾動 {scrolls_after_old} 次後停止")
                        break

            # 過濾出日期範圍內的貼文
            filtered_posts = []
            no_date_posts = []
            for key, info in post_map.items():
                ct = info.get('creation_time')
                if ct:
                    if ct >= target_ts:
                        filtered_posts.append(info)
                    else:
                        post_date = datetime.fromtimestamp(ct).strftime('%Y-%m-%d')
                        print(f"  ⏰ 跳過早於 {since_date} 的貼文: {post_date} - {info.get('message_preview', '')[:30]}")
                else:
                    # 沒有日期的貼文也納入（可能是最新的貼文，creation_time 路徑變了）
                    no_date_posts.append(info)
                    print(f"  ⚠️ 無日期貼文納入結果: post_id={info.get('post_id', '?')} - {info.get('message_preview', '')[:40]}")

            # 無日期的貼文也加入過濾結果
            filtered_posts.extend(no_date_posts)

            # 依日期排序（新到舊，無日期的放最前）
            filtered_posts.sort(key=lambda x: x.get('creation_time', 9999999999), reverse=True)

            print(f"\n{'='*60}")
            print(f"🔍 共找到 {len(post_map)} 個粉絲頁貼文（SSR: {len(ssr_posts)}, GraphQL: {len(post_map) - len(ssr_posts)}），日期範圍內 {len(filtered_posts)} 個（含 {len(no_date_posts)} 個無日期）")
            print(f"{'='*60}")

            if not filtered_posts:
                # 計算最新貼文日期，供前端顯示更友善的錯誤訊息
                newest_date = None
                for info in post_map.values():
                    ct = info.get('creation_time')
                    if ct:
                        if newest_date is None or ct > newest_date:
                            newest_date = ct
                if newest_date:
                    newest_date_str = datetime.fromtimestamp(newest_date).strftime('%Y-%m-%d')
                    print(f"ℹ️ 粉絲頁最新貼文日期: {newest_date_str}，但您設定的起始日期為 {since_date}")
                # 回傳空 list 但附帶 metadata（透過 instance attribute）
                self._last_scrape_meta = {
                    'found_total': len(post_map),
                    'newest_date': datetime.fromtimestamp(newest_date).strftime('%Y-%m-%d') if newest_date else None,
                    'since_date': since_date,
                }
                return []

            # Step 2: 處理每篇貼文
            # 內容直接使用 GraphQL 的 message，僅訪問 URL 來抓取完整圖片
            detailed_posts = []
            for i, info in enumerate(filtered_posts):
                pfbid = info['pfbid']
                post_id = info.get('post_id', '')
                ct = info.get('creation_time')
                post_date = datetime.fromtimestamp(ct).strftime('%Y-%m-%d') if ct else None
                content = info.get('full_message', '')
                graphql_images = info.get('image_urls', [])

                # 構建 permalink URL
                if page_id:
                    post_url = f"https://www.facebook.com/permalink.php?story_fbid={pfbid}&id={page_id}"
                else:
                    post_url = f"https://www.facebook.com/permalink.php?story_fbid={pfbid}"

                print(f"\n[{i+1}/{len(filtered_posts)}] 處理: post_id={post_id}")
                if post_date:
                    print(f"  📅 日期: {post_date}")
                print(f"  📝 GraphQL 內容: {content[:50]}... ({len(content)} 字)")
                print(f"  🖼️ GraphQL 圖片: {len(graphql_images)} 張")

                if not content or len(content.strip()) < 5:
                    print(f"  ⚠️ GraphQL 無內容，跳過")
                    continue

                # 使用 GraphQL 提供的圖片（已確認為該貼文的圖片）
                # 註：不再訪問頁面抓圖，因為 _extract_image_urls() 會抓到整個頁面的所有圖片（含推薦貼文等不相關的）
                image_urls = graphql_images
                print(f"  🖼️ 使用 GraphQL 圖片: {len(image_urls)} 張")

                # 標題：取內容第一行
                lines = [l.strip() for l in content.split('\n') if l.strip()]
                title = lines[0][:80] if lines else "無標題"

                detailed_posts.append({
                    'url': post_url,
                    'title': title,
                    'content': content,
                    'date': post_date or 'Unknown',
                    'images': image_urls,
                    'image_count': len(image_urls)
                })
                print(f"  ✅ {title[:40]}... ({len(content)} 字, {len(image_urls)} 張圖)")

            print(f"\n{'='*60}")
            print(f"🎉 完成！成功 {len(detailed_posts)}/{len(filtered_posts)} 篇")
            print(f"{'='*60}")

            return detailed_posts

        except Exception as e:
            print(f"❌ 爬取粉絲團貼文時出錯: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_posts_from_page_source(self, page_id: Optional[str] = None) -> Dict:
        """
        從頁面 HTML 原始碼中提取 SSR（伺服器端渲染）嵌入的貼文資料。
        Facebook SPA 會將最新 1-2 篇貼文直接渲染在 HTML 中（不透過 GraphQL XHR），
        因此 Performance Logs 攔截不到。此方法從 page_source 的 JSON 片段中提取這些貼文。
        
        Returns:
            {post_id: {pfbid, post_id, creation_time, full_message, image_urls}}
        """
        import json as json_mod
        import re

        posts = {}
        try:
            source = self.driver.page_source
            if not source or '"post_id"' not in source:
                return posts

            print(f"  📄 頁面原始碼大小: {len(source):,} bytes，嘗試提取 SSR 嵌入貼文...")

            # 策略: 找出 HTML 中所有包含 "post_id" 的 JSON 物件
            # Facebook 把資料放在 <script> 標籤或 data-sjs 屬性中
            # 方法1: 從 <script ...>...</script> 中提取
            script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
            json_candidates = []

            for m in script_pattern.finditer(source):
                script_content = m.group(1).strip()
                if '"post_id"' not in script_content:
                    continue
                # 有些 script 內容是 JSON，有些是 JS 賦值
                # 嘗試直接解析，或提取 JSON 部分
                # 常見模式: require("ScheduledServerJS").handle({"require":[...]})
                # 或 __d("...", ["require"], function(...) {}, ...)
                for line in script_content.split('\n'):
                    line = line.strip()
                    if '"post_id"' not in line:
                        continue
                    # 嘗試找到最外層的 JSON 物件
                    json_candidates.append(line)

            # 方法2: 從 data-sjs 屬性提取（某些 Facebook 頁面用此方式）
            sjs_pattern = re.compile(r'data-sjs="([^"]*)"')
            for m in sjs_pattern.finditer(source):
                raw = m.group(1)
                if '"post_id"' in raw or 'post_id' in raw:
                    # HTML entity decode
                    import html
                    decoded = html.unescape(raw)
                    json_candidates.append(decoded)

            # 方法3: 尋找大型 JSON 物件（通常以 {"require": 或 {"__bbox": 開頭）
            # 這些出現在 script type="application/json" 標籤中
            json_script_pattern = re.compile(
                r'<script[^>]*type="application/json"[^>]*data-sjs[^>]*>(.*?)</script>', re.DOTALL)
            for m in json_script_pattern.finditer(source):
                content = m.group(1).strip()
                if '"post_id"' in content:
                    json_candidates.append(content)

            # 嘗試從每個候選 JSON 中解析貼文
            for raw_json in json_candidates:
                # 嘗試多種方式解析 JSON
                parsed_objects = []

                # 直接解析
                try:
                    obj = json_mod.loads(raw_json)
                    parsed_objects.append(obj)
                except:
                    pass

                # 嘗試找到 JSON 物件的起始位置
                if not parsed_objects:
                    for start_char in ['{', '[']:
                        idx = raw_json.find(start_char)
                        if idx >= 0:
                            try:
                                obj = json_mod.loads(raw_json[idx:])
                                parsed_objects.append(obj)
                                break
                            except:
                                # 可能尾部有多餘字元，嘗試找配對的括號
                                pass

                # 嘗試用正則提取所有 JSON 物件
                if not parsed_objects:
                    # 找所有 { 開頭的物件，嘗試逐一解析
                    brace_positions = [i for i, c in enumerate(raw_json) if c == '{']
                    for pos in brace_positions[:50]:  # 限制嘗試次數
                        depth = 0
                        end = pos
                        for j in range(pos, min(pos + 500000, len(raw_json))):
                            if raw_json[j] == '{':
                                depth += 1
                            elif raw_json[j] == '}':
                                depth -= 1
                                if depth == 0:
                                    end = j + 1
                                    break
                        if end > pos:
                            snippet = raw_json[pos:end]
                            if '"post_id"' in snippet and len(snippet) > 200:
                                try:
                                    obj = json_mod.loads(snippet)
                                    parsed_objects.append(obj)
                                except:
                                    pass

                for obj in parsed_objects:
                    story_nodes = []
                    self._find_story_nodes(obj, story_nodes)
                    for sn in story_nodes:
                        post_info = self._parse_story_node(sn, page_id)
                        if post_info:
                            key = post_info['post_id']
                            if key not in posts:
                                posts[key] = post_info

            if posts:
                print(f"  ✅ 從頁面原始碼提取到 {len(posts)} 篇 SSR 嵌入貼文")
                for pid, info in posts.items():
                    ct = info.get('creation_time')
                    if ct:
                        from datetime import datetime
                        dt = datetime.fromtimestamp(ct).strftime('%Y-%m-%d %H:%M')
                        print(f"     - post_id={pid}, 日期={dt}, 內容={info.get('message_preview', '')[:40]}")
                    else:
                        print(f"     - post_id={pid}, 日期=未知, 內容={info.get('message_preview', '')[:40]}")
            else:
                print(f"  ℹ️ 頁面原始碼中未找到可解析的 SSR 嵌入貼文")

        except Exception as e:
            print(f"  ⚠️ 提取 SSR 嵌入貼文時出錯: {e}")
            import traceback
            traceback.print_exc()

        return posts

    def _drain_perf_logs(self):
        """清空已有的 performance logs"""
        try:
            self.driver.get_log('performance')
        except:
            pass

    def _extract_posts_from_perf_logs(self, page_id: Optional[str] = None) -> Dict:
        """
        從 Chrome Performance Logs 中提取 GraphQL 回應的貼文資料
        正確解析 JSON 結構，只提取屬於目標粉絲頁的貼文

        Returns:
            {post_id: {pfbid, post_id, creation_time, full_message, image_urls}}
        """
        import json as json_mod
        import re
        posts = {}

        try:
            logs = self.driver.get_log('performance')
        except:
            return posts

        graphql_request_ids = []
        for entry in logs:
            try:
                log_data = json_mod.loads(entry['message'])
                msg = log_data.get('message', {})
                method = msg.get('method', '')

                if method == 'Network.responseReceived':
                    url = msg.get('params', {}).get('response', {}).get('url', '')
                    if 'graphql' in url.lower():
                        req_id = msg.get('params', {}).get('requestId', '')
                        graphql_request_ids.append(req_id)
            except:
                continue

        for req_id in graphql_request_ids:
            try:
                body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': req_id})
                body_text = body.get('body', '')

                # 跳過不含 post_id 的回應
                if '"post_id"' not in body_text:
                    continue

                # Facebook 回應可能是多行 JSON（各行獨立）
                for line in body_text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json_mod.loads(line)
                    except:
                        continue

                    # 從 JSON 中提取 story 節點
                    story_nodes = []
                    self._find_story_nodes(data, story_nodes)

                    for node in story_nodes:
                        post_info = self._parse_story_node(node, page_id)
                        if post_info:
                            key = post_info['post_id']
                            if key not in posts:
                                posts[key] = post_info

            except Exception:
                continue

        return posts

    def _find_story_nodes(self, obj, results, depth=0):
        """
        遞歸遍歷 JSON，找出所有含 post_id 的 story 節點

        Facebook GraphQL 回應有兩種格式：
        A) data.node.timeline_list_feed_units.edges[].node（含多篇貼文）
        B) data.node（單篇貼文，每行一個 JSON）
        """
        if depth > 20 or not isinstance(obj, (dict, list)):
            return

        if isinstance(obj, dict):
            # 如果這個 dict 有 post_id 且有 comet_sections，就是一個 story 節點
            if 'post_id' in obj and 'comet_sections' in obj:
                results.append(obj)
                return  # 不再往下找（避免重複）

            # 特別處理 timeline_list_feed_units.edges
            edges = None
            tl = obj.get('timeline_list_feed_units')
            if isinstance(tl, dict):
                edges = tl.get('edges')
            if isinstance(edges, list):
                for edge in edges:
                    if isinstance(edge, dict):
                        node = edge.get('node')
                        if isinstance(node, dict) and 'post_id' in node:
                            results.append(node)
                return

            # 否則繼續往下搜尋
            for v in obj.values():
                self._find_story_nodes(v, results, depth + 1)

        elif isinstance(obj, list):
            for item in obj:
                self._find_story_nodes(item, results, depth + 1)

    def _parse_story_node(self, node: dict, page_id: Optional[str] = None) -> Optional[Dict]:
        """
        從一個 story 節點中提取貼文資料

        路徑：
        - post_id: node.post_id
        - message: node.comet_sections.content.story.message.text
        - creation_time: node.comet_sections.context_layout.story.comet_sections.metadata[0].story.creation_time
        - actors: node.comet_sections.content.story.actors[0].id
        - pfbid: regex from serialized node
        - images: node.attachments[0].styles.attachment.all_subattachments.nodes[i].media.image.uri
        """
        import re

        post_id = str(node.get('post_id', ''))
        if not post_id:
            return None

        comet = node.get('comet_sections', {})

        # ---- 提取 message ----
        message = ''
        try:
            content_story = comet.get('content', {}).get('story', {})
            msg_obj = content_story.get('message')
            if isinstance(msg_obj, dict):
                message = msg_obj.get('text', '')
            # 備用路徑: message_container
            if not message:
                msg_container = content_story.get('comet_sections', {}).get(
                    'message_container', {}).get('story', {}).get('message')
                if isinstance(msg_container, dict):
                    message = msg_container.get('text', '')
        except:
            pass

        # ---- 提取 creation_time ----
        creation_time = None
        try:
            ctx = comet.get('context_layout', {}).get('story', {}).get('comet_sections', {})
            metadata = ctx.get('metadata', [])
            if isinstance(metadata, list) and metadata:
                creation_time = metadata[0].get('story', {}).get('creation_time')
                if creation_time:
                    creation_time = int(creation_time)
        except:
            pass

        # 備用路徑1: comet_sections.context_layout.story.comet_sections.timestamp
        if not creation_time:
            try:
                ctx = comet.get('context_layout', {}).get('story', {}).get('comet_sections', {})
                ts_obj = ctx.get('timestamp', {})
                if isinstance(ts_obj, dict):
                    ct_val = ts_obj.get('story', {}).get('creation_time')
                    if ct_val:
                        creation_time = int(ct_val)
            except:
                pass

        # 備用路徑2: 直接從 node 中搜尋 creation_time
        if not creation_time:
            try:
                ct_val = self._find_creation_time(node)
                if ct_val:
                    creation_time = int(ct_val)
            except:
                pass

        # ---- 提取 owner/actors ----
        owner_id = None
        try:
            content_story = comet.get('content', {}).get('story', {})
            actors = content_story.get('actors', [])
            if isinstance(actors, list) and actors:
                owner_id = str(actors[0].get('id', ''))
        except:
            pass
        # 備用: context_layout.actor_photo
        if not owner_id:
            try:
                ctx = comet.get('context_layout', {}).get('story', {}).get('comet_sections', {})
                ap_actors = ctx.get('actor_photo', {}).get('story', {}).get('actors', [])
                if isinstance(ap_actors, list) and ap_actors:
                    owner_id = str(ap_actors[0].get('id', ''))
            except:
                pass

        # ---- 過濾: 只保留屬於目標粉絲頁的貼文 ----
        if page_id and owner_id and owner_id != page_id:
            return None

        # ---- 提取 pfbid ----
        pfbid = ''
        try:
            node_str = str(node)  # 比 json.dumps 快
            pfbids = re.findall(r'pfbid\w{20,}', node_str)
            if pfbids:
                pfbid = pfbids[0]
        except:
            pass

        # ---- 提取圖片 URL ----
        image_urls = []
        try:
            # 優先從 node.attachments 提取
            atts = node.get('attachments', [])
            if not atts:
                # 備用: content.story.attachments
                atts = comet.get('content', {}).get('story', {}).get('attachments', [])

            if atts:
                attachment_obj = atts[0].get('styles', {}).get('attachment', {})
                subs = attachment_obj.get('all_subattachments', {}).get('nodes', [])

                if subs:
                    # 多圖貼文：從 all_subattachments 提取
                    for sub in subs:
                        media = sub.get('media', {})
                        uri = self._extract_best_image_uri(media)
                        if uri:
                            image_urls.append(uri)
                else:
                    # 單圖貼文：直接從 attachment.media 提取
                    media = attachment_obj.get('media', {})
                    if media:
                        uri = self._extract_best_image_uri(media)
                        if uri:
                            image_urls.append(uri)

                # 備用：遍歷所有 attachments
                if not image_urls and len(atts) > 1:
                    for att in atts:
                        att_media = att.get('styles', {}).get('attachment', {}).get('media', {})
                        if att_media:
                            uri = self._extract_best_image_uri(att_media)
                            if uri:
                                image_urls.append(uri)
        except:
            pass

        return {
            'pfbid': pfbid,
            'post_id': post_id,
            'creation_time': creation_time,
            'full_message': message,
            'message_preview': message[:60] if message else '',
            'image_urls': image_urls,
            'owner_id': owner_id,
        }

    def _find_creation_time(self, obj, depth=0):
        """
        遞迴搜尋 JSON 物件中的 creation_time 欄位
        只匹配合理的 Unix 時間戳（> 1000000000，即 2001 年之後）
        """
        if depth > 15 or not isinstance(obj, (dict, list)):
            return None
        if isinstance(obj, dict):
            if 'creation_time' in obj:
                val = obj['creation_time']
                try:
                    val_int = int(val)
                    if val_int > 1000000000:  # 合理的 Unix timestamp
                        return val_int
                except (ValueError, TypeError):
                    pass
            for v in obj.values():
                result = self._find_creation_time(v, depth + 1)
                if result:
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = self._find_creation_time(item, depth + 1)
                if result:
                    return result
        return None

    def _extract_best_image_uri(self, media: dict) -> Optional[str]:
        """
        從 media 物件中提取最佳解析度的圖片 URI
        優先順序: viewer_image > photo_image > image > thumbnailImage
        """
        # 優先用高解析度的 viewer_image
        for key in ['viewer_image', 'photo_image', 'image', 'thumbnailImage']:
            img = media.get(key)
            if isinstance(img, dict) and 'uri' in img:
                return img['uri']
        return None

    def close(self):
        """關閉瀏覽器"""
        self.base_scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
