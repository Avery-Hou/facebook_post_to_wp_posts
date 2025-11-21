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
    """Facebook 粉絲團爬蟲 - 批次抓取貼文"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.base_scraper = FacebookScraper(headless=headless)

    def _init_driver(self):
        """初始化 Chrome WebDriver"""
        self.base_scraper._init_driver()
        self.driver = self.base_scraper.driver

    def scrape_page_posts(self, page_url: str, since_date: str) -> List[Dict]:
        """
        爬取粉絲團指定日期之後的所有貼文
        自動滾動直到所有貼文的日期都早於設定日期

        Args:
            page_url: 粉絲團 URL
            since_date: 起始日期 (格式: YYYY-MM-DD)

        Returns:
            貼文列表，每個貼文包含：
            {
                'url': 貼文URL,
                'title': 貼文標題（第一行）,
                'content': 貼文完整內容,
                'date': 貼文日期,
                'images': 圖片URL列表,
                'image_count': 圖片數量
            }
        """
        try:
            self._init_driver()

            from datetime import datetime
            target_date = datetime.strptime(since_date, '%Y-%m-%d')

            print(f"正在訪問粉絲團: {page_url}")
            print(f"目標日期: {since_date} (將抓取此日期之後的所有貼文)")
            self.driver.get(page_url)
            time.sleep(10)  # 增加等待時間確保頁面完全載入
            
            # 檢查是否成功載入頁面
            page_title = self.driver.title
            print(f"頁面標題: {page_title}")
            
            # 嘗試處理登入提示或其他彈窗
            try:
                # 查找並關閉可能的彈窗
                close_buttons = self.driver.find_elements(By.XPATH, 
                    "//div[@role='button' and contains(@aria-label, 'Close')] | //button[contains(@aria-label, 'Close')]")
                if close_buttons:
                    close_buttons[0].click()
                    time.sleep(2)
                    print("已關閉彈窗")
            except:
                pass

            detailed_posts = []
            seen_urls = set()
            scroll_count = 0
            max_scrolls = 200  # 增加最大滾動次數
            consecutive_old_posts = 0  # 連續發現過期貼文的滾動次數
            no_new_content_count = 0  # 連續沒有新內容的次數
            
            print("開始自動滾動並提取貼文...")
            print("=" * 60)

            while scroll_count < max_scrolls:
                current_scroll_found_new = False
                current_scroll_found_old = False
                current_posts_in_scroll = 0

                # 查找頁面上所有的時間元素和連結
                try:
                    # 使用更全面的貼文選擇器，包括個人檔案頁面的結構
                    post_selectors = [
                        "//div[@role='article']",  # 標準貼文容器
                        "//div[contains(@class, 'x1yztbdb')]",  # 另一種貼文容器
                        "//div[contains(@class, 'x1n2onr6')]",  # 第三種貼文容器
                        "//div[@data-pagelet='FeedUnit']",  # 動態消息單元
                        "//div[contains(@class, 'story_body_container')]",  # 故事內容容器
                        "//div[contains(@class, 'userContentWrapper')]",  # 用戶內容包裝器
                    ]
                    
                    post_elements = []
                    for selector in post_selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            post_elements.extend(elements)
                        except:
                            continue
                    
                    # 去除重複元素
                    unique_elements = list(set(post_elements))
                    post_elements = unique_elements

                    print(f"\n滾動 #{scroll_count + 1} - 檢查 {len(post_elements)} 個貼文元素")
                    
                    # 如果找不到貼文元素，嘗試其他方法
                    if len(post_elements) == 0:
                        print("    ⚠️ 使用標準選擇器找不到貼文，嘗試備用方法...")
                        # 查找包含連結的所有div
                        all_divs = self.driver.find_elements(By.XPATH, "//div[.//a[contains(@href, '/posts/') or contains(@href, '/permalink.php') or contains(@href, '/story.php')]]")
                        post_elements = all_divs[:50]  # 限制數量避免過多
                        print(f"    🔄 備用方法找到 {len(post_elements)} 個可能的貼文元素")

                    for post_elem in post_elements:
                        try:
                            # 更全面的連結搜尋策略
                            link_selectors = [
                                ".//a[contains(@href, '/posts/')]",
                                ".//a[contains(@href, '/permalink.php')]", 
                                ".//a[contains(@href, '/story.php')]",
                                ".//a[contains(@href, '/photo.php')]",  # 照片貼文
                                ".//a[contains(@href, 'fbid=')]",  # 另一種照片格式
                                ".//a[@role='link' and @href]",  # 通用連結
                            ]
                            
                            links = []
                            for link_selector in link_selectors:
                                try:
                                    found_links = post_elem.find_elements(By.XPATH, link_selector)
                                    links.extend(found_links)
                                    if links:  # 如果找到連結就停止
                                        break
                                except:
                                    continue

                            if not links:
                                continue

                            post_url = links[0].get_attribute('href')
                            if not post_url:
                                continue

                            # 清理和標準化URL
                            original_url = post_url
                            if '?' in post_url:
                                post_url = post_url.split('?')[0]
                            
                            # 處理不同的URL格式
                            if '/photo.php' in post_url or 'fbid=' in original_url:
                                # 對於照片連結，保留原始URL
                                post_url = original_url

                            # 檢查是否已處理過
                            if post_url in seen_urls:
                                continue

                            print(f"    🔍 檢查連結: {post_url[:80]}...")

                            # 嘗試在當前元素內查找時間
                            time_elems = post_elem.find_elements(By.TAG_NAME, 'time')
                            post_date_str = None

                            if time_elems:
                                datetime_attr = time_elems[0].get_attribute('datetime')
                                if datetime_attr:
                                    try:
                                        # 處理 ISO 格式的時間
                                        dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                        post_date_str = dt.strftime('%Y-%m-%d')

                                        # 檢查日期是否早於目標日期
                                        post_datetime = datetime.strptime(post_date_str, '%Y-%m-%d')
                                        if post_datetime < target_date:
                                            print(f"    ⏰ 發現過期貼文: {post_date_str} < {since_date}")
                                            current_scroll_found_old = True
                                            seen_urls.add(post_url)  # 標記為已見但不處理
                                            continue
                                    except Exception as e:
                                        print(f"    ⚠️ 解析日期失敗: {e}")

                            # 標記為已見過
                            seen_urls.add(post_url)
                            current_posts_in_scroll += 1

                            print(f"    ✅ 發現符合條件的貼文: {post_url[:60]}... (日期: {post_date_str or '未知'})")

                            # 立即提取詳細資訊
                            detailed_post = self._extract_post_details(post_url, target_date, since_date)
                            if detailed_post:
                                detailed_posts.append(detailed_post)
                                current_scroll_found_new = True

                        except Exception as e:
                            continue

                    print(f"    📊 本次滾動統計: 新貼文 {current_posts_in_scroll} 個")

                except Exception as e:
                    print(f"    ❌ 提取貼文時出錯: {e}")

                # 判斷停止條件
                if current_scroll_found_old and not current_scroll_found_new:
                    consecutive_old_posts += 1
                    print(f"    🔄 連續第 {consecutive_old_posts} 次滾動只發現過期貼文")
                else:
                    consecutive_old_posts = 0

                # 如果連續 5 次滾動都只發現過期貼文，很可能已經到達目標日期之前
                if consecutive_old_posts >= 5:
                    print(f"\n🛑 已連續 {consecutive_old_posts} 次滾動只發現過期貼文，停止抓取")
                    break

                # 滾動頁面
                print(f"    📜 向下滾動...")
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                
                # 使用更積極的滾動策略
                try:
                    if scroll_count % 5 == 0:
                        # 每5次使用平滑滾動
                        self.driver.execute_script("window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});")
                    elif scroll_count % 3 == 0:
                        # 每3次滾動到頁面的不同位置
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
                        time.sleep(1)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    else:
                        # 其他時候使用快速滾動
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    # 嘗試觸發懶載入
                    self.driver.execute_script("""
                        // 觸發scroll事件
                        window.dispatchEvent(new Event('scroll'));
                        // 觸發resize事件
                        window.dispatchEvent(new Event('resize'));
                    """)
                    
                except Exception as e:
                    print(f"    ⚠️ 滾動失敗: {e}")

                time.sleep(8)  # 增加等待時間讓內容充分載入

                # 檢查是否有新內容載入
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_new_content_count += 1
                    print(f"    ⏸️ 第 {no_new_content_count} 次未發現新內容")
                    
                    # 嘗試觸發更多內容載入
                    if no_new_content_count <= 3:
                        print(f"    🔄 嘗試觸發更多內容載入...")
                        # 向上滾動一點再向下滾動
                        self.driver.execute_script("window.scrollBy(0, -200);")
                        time.sleep(2)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(4)
                        
                        # 再次檢查
                        final_height = self.driver.execute_script("return document.body.scrollHeight")
                        if final_height and final_height > new_height:
                            no_new_content_count = 0  # 重置計數
                            print(f"    ✅ 成功載入更多內容")
                    
                    # 如果連續多次沒有新內容，停止
                    if no_new_content_count >= 4:
                        print(f"    🏁 頁面已到底部，沒有更多內容")
                        break
                else:
                    no_new_content_count = 0  # 重置計數

                scroll_count += 1
                
                # 每 10 次滾動顯示進度
                if scroll_count % 10 == 0:
                    print(f"\n📈 進度報告 - 已滾動 {scroll_count} 次，已抓取 {len(detailed_posts)} 個貼文")

            print("=" * 60)
            print(f"🎉 抓取完成！總共成功提取 {len(detailed_posts)} 個符合條件的貼文")
            print(f"📊 滾動次數: {scroll_count}")
            print(f"📅 目標日期: {since_date}")
            return detailed_posts

        except Exception as e:
            print(f"❌ 爬取粉絲團貼文時出錯: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extract_post_details(self, post_url: str, target_date, since_date: str) -> Optional[Dict]:
        """
        提取單個貼文的詳細資訊
        
        Args:
            post_url: 貼文URL
            target_date: 目標日期的 datetime 物件
            since_date: 起始日期字串
            
        Returns:
            貼文詳細資訊字典，如果不符合條件則返回 None
        """
        try:
            from datetime import datetime

            print(f"      🔍 正在提取貼文詳情: {post_url[:70]}...")
            self.driver.get(post_url)
            time.sleep(4)  # 增加等待時間確保頁面載入完成

            # 點擊"查看更多"按鈕以獲取完整內容
            try:
                see_more_buttons = self.driver.find_elements(By.XPATH, 
                    "//div[contains(text(), '查看更多') or contains(text(), 'See more') or contains(text(), '更多')]")
                if see_more_buttons:
                    see_more_buttons[0].click()
                    time.sleep(2)
                    print(f"      📖 已展開完整內容")
            except:
                pass

            # 提取貼文內容
            content = self._extract_post_content()
            if not content or len(content.strip()) < 10:
                print(f"      ⚠️ 跳過：內容太短或無法提取內容")
                return None
                
            # 檢查是否是登入頁面或錯誤頁面
            login_indicators = ['忘記帳號', '建立新帳號', '登入', 'Log in', 'Sign up', 'Create account', 
                              'Forgotten password', '密碼', 'Password', 'Email', '電子郵件']
            if any(indicator in content for indicator in login_indicators):
                print(f"      ⚠️ 跳過：偵測到登入頁面或錯誤頁面")
                return None

            # 提取貼文日期（更準確的日期提取）
            post_date = self._extract_post_date()

            # 雙重檢查日期 - 確保貼文不早於目標日期
            if post_date:
                try:
                    post_datetime = datetime.strptime(post_date, '%Y-%m-%d')
                    if post_datetime < target_date:
                        print(f"      ⏰ 跳過：貼文日期 {post_date} 早於設定日期 {since_date}")
                        return None
                    else:
                        print(f"      ✅ 日期檢查通過：{post_date}")
                except Exception as e:
                    print(f"      ⚠️ 日期解析警告: {e}")

            # 提取圖片
            image_urls = self._extract_images()

            # 提取標題（使用第一行內容，限制長度）
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            title = ""
            if lines:
                title = lines[0][:80]  # 限制標題長度
                if len(lines[0]) > 80:
                    title += "..."

            # 建立貼文資料
            detailed_post = {
                'url': post_url,
                'title': title if title else "無標題",
                'content': content,
                'date': post_date or 'Unknown',
                'images': image_urls,
                'image_count': len(image_urls)
            }

            print(f"      🎉 提取成功 - 標題: {title[:40]}{'...' if len(title) > 40 else ''}")
            print(f"      📊 統計: {len(image_urls)} 張圖片, {len(content)} 字")
            return detailed_post

        except Exception as e:
            print(f"      ❌ 提取失敗: {e}")
            return None

    def _extract_post_content(self) -> str:
        """
        提取貼文內容 - 使用多種策略確保準確提取
        """
        try:
            content = ""
            
            # 等待頁面載入
            time.sleep(3)
            
            print(f"      📄 開始提取內容，當前URL: {self.driver.current_url[:60]}...")
            
            # 首先嘗試點擊"查看更多"以展開內容
            try:
                see_more_selectors = [
                    "//div[contains(text(), '查看更多')]",
                    "//div[contains(text(), 'See more')]", 
                    "//div[contains(text(), '更多')]",
                    "//span[contains(text(), '查看更多')]",
                    "//span[contains(text(), 'See more')]",
                    "//div[@role='button' and contains(text(), '更多')]"
                ]
                
                for selector in see_more_selectors:
                    try:
                        see_more_buttons = self.driver.find_elements(By.XPATH, selector)
                        if see_more_buttons:
                            see_more_buttons[0].click()
                            time.sleep(2)
                            print(f"      📖 已點擊展開內容")
                            break
                    except:
                        continue
            except:
                pass
            
            # 策略1: 使用特定的文本容器類別
            content_selectors = [
                # Facebook 新版介面的文本選擇器
                "//div[contains(@class, 'xdj266r')]//span",  
                "//div[contains(@class, 'x1iorvi4')]//span", 
                "//div[contains(@class, 'x1y1aw1k')]//span",
                "//div[contains(@class, 'x126k92a')]//span",
                
                # 舊版和備用選擇器
                "//div[@data-ad-preview='message']//span",   
                "//div[@data-testid='post_message']//span",
                "//div[contains(@class, 'userContent')]//span",
                "//div[contains(@class, '_5pbx')]//span",
                
                # 更廣泛的搜尋
                "//div[contains(@dir, 'auto')]//span",
                "//p//span",
                "//div//span[string-length(text()) > 10]"
            ]
            
            for selector in content_selectors:
                try:
                    text_elements = self.driver.find_elements(By.XPATH, selector)
                    temp_content = ""
                    
                    for element in text_elements:
                        try:
                            text = element.text.strip()
                            # 過濾掉太短或明顯不是內容的文字
                            if text and len(text) > 3 and not text.isdigit():
                                # 排除 UI 元素
                                ui_elements = ['讚', '留言', '分享', 'Like', 'Comment', 'Share', 
                                             '更多', 'More', '查看更多', 'See more', '回覆', 'Reply']
                                if not any(ui in text for ui in ui_elements):
                                    # 避免重複內容
                                    if text not in temp_content:
                                        temp_content += text + "\n"
                        except:
                            continue
                    
                    if temp_content and len(temp_content.strip()) > len(content):
                        content = temp_content.strip()
                        print(f"      ✅ 使用選擇器成功提取: {len(content)} 字")
                        if len(content) > 50:  # 如果找到足夠的內容就停止
                            break
                        
                except Exception as e:
                    continue
                    
            # 策略2: 如果上面的方法沒有找到足夠的內容，嘗試更廣泛的搜尋
            if len(content) < 30:
                print(f"      🔄 內容不足，嘗試廣泛搜尋...")
                try:
                    # 查找所有可能包含文本的元素
                    broad_selectors = [
                        "//div[contains(@dir, 'auto')]",
                        "//div[contains(@class, 'text')]",
                        "//p[string-length(text()) > 15]",
                        "//div[string-length(text()) > 20 and string-length(text()) < 2000]"
                    ]
                    
                    for selector in broad_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for div in elements:
                            try:
                                text = div.text.strip()
                                if text and len(text) > 20 and len(text) < 5000:
                                    # 檢查是否看起來像貼文內容
                                    content_indicators = ['。', '！', '？', '.', '!', '?', '，', ',']
                                    if any(char in text for char in content_indicators):
                                        # 排除明顯的導航或UI文字
                                        exclude_phrases = ['登入', 'Log in', 'Sign up', '註冊', 'Facebook', 
                                                          'Cookie', '隱私', 'Privacy', '條款', 'Terms']
                                        if not any(phrase in text for phrase in exclude_phrases):
                                            if len(text) > len(content):
                                                content = text
                                                print(f"      ✅ 廣泛搜尋找到內容: {len(content)} 字")
                            except:
                                continue
                        
                        if len(content) > 50:
                            break
                            
                except Exception as e:
                    print(f"      ⚠️ 廣泛搜尋失敗: {e}")

            # 策略3: 最後嘗試獲取頁面的主要文本內容
            if len(content) < 20:
                try:
                    print(f"      🔍 嘗試獲取頁面主要內容...")
                    # 獲取頁面主體中的所有文本，然後過濾
                    body_text = self.driver.find_element(By.TAG_NAME, "body").text
                    lines = body_text.split('\n')
                    
                    # 查找看起來像貼文內容的行
                    for line in lines:
                        line = line.strip()
                        if (len(line) > 30 and len(line) < 1000 and 
                            any(char in line for char in ['。', '.', '！', '!', '？', '?'])):
                            # 排除UI元素和導航文字
                            ui_words = ['讚', '留言', '分享', 'Like', 'Comment', 'Share', 'Facebook', 
                                       '登入', 'Log in', '首頁', 'Home', '搜尋', 'Search']
                            if not any(word in line for word in ui_words):
                                if len(line) > len(content):
                                    content = line
                                    print(f"      ✅ 頁面掃描找到內容: {len(content)} 字")
                except Exception as e:
                    print(f"      ⚠️ 頁面掃描失敗: {e}")

            # 清理內容
            if content:
                # 移除多餘的空行和空白
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                content = '\n\n'.join(lines)
                
                # 移除明顯的 UI 元素文字
                ui_texts = ['讚', '留言', '分享', '更多', '查看更多', 'See more', 'Like', 'Comment', 'Share']
                for ui_text in ui_texts:
                    content = content.replace(ui_text, '')
                
                content = content.strip()

            print(f"      � 最終內容提取結果: {len(content)} 字")
            if content:
                print(f"      📝 內容預覽: {content[:100]}...")
            
            return content

        except Exception as e:
            print(f"      ❌ 提取貼文內容失敗: {e}")
            return ""

    def _extract_post_date(self) -> str:
        """提取貼文日期"""
        try:
            # 查找時間元素
            time_elements = self.driver.find_elements(By.TAG_NAME, 'time')
            if time_elements:
                # 優先使用 datetime 屬性
                datetime_attr = time_elements[0].get_attribute('datetime')
                if datetime_attr:
                    # 轉換 ISO 格式到 YYYY-MM-DD
                    from datetime import datetime
                    dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d')

                # 或使用顯示的文本
                date_text = time_elements[0].text
                if date_text:
                    return date_text

            return None
        except Exception as e:
            print(f"提取日期失敗: {e}")
            return None

    def _extract_images(self) -> List[str]:
        """提取圖片URL"""
        try:
            image_urls = []
            seen_urls = set()

            img_elements = self.driver.find_elements(By.TAG_NAME, 'img')

            for img in img_elements:
                try:
                    src = img.get_attribute('src')
                    if not src or 'scontent' not in src:
                        continue

                    # 過濾小圖
                    exclude_patterns = ['p50x50', 'p40x40', 's50x50', 'emoji', 'static']
                    if any(pattern in src for pattern in exclude_patterns):
                        continue

                    base_url = src.split('?')[0]
                    if base_url not in seen_urls:
                        seen_urls.add(base_url)
                        image_urls.append(src)

                except:
                    continue

            return image_urls[:10]  # 最多10張圖

        except Exception as e:
            print(f"提取圖片失敗: {e}")
            return []

    def close(self):
        """關閉瀏覽器"""
        self.base_scraper.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
