#!/usr/bin/env python3
"""
Facebook 粉絲團可訪問性檢查工具

檢查指定的 Facebook 粉絲團是否可以在未登入狀態下訪問
"""

import sys
from facebook_scraper import FacebookPageScraper


def check_page_accessibility(page_url: str):
    """檢查粉絲團頁面的可訪問性"""
    print("=" * 60)
    print("Facebook 粉絲團可訪問性檢查")
    print("=" * 60)
    print(f"檢查 URL: {page_url}")
    
    try:
        with FacebookPageScraper(headless=False) as scraper:
            scraper._init_driver()
            
            print("正在載入頁面...")
            scraper.driver.get(page_url)
            
            import time
            time.sleep(5)
            
            # 獲取頁面標題
            page_title = scraper.driver.title
            print(f"頁面標題: {page_title}")
            
            # 檢查是否出現登入要求
            login_indicators = [
                "Log In",
                "Sign Up", 
                "登入",
                "註冊",
                "You must log in",
                "Create an account",
                "忘記帳號"
            ]
            
            page_source = scraper.driver.page_source
            needs_login = any(indicator in page_source for indicator in login_indicators)
            
            if needs_login:
                print("❌ 此頁面需要登入才能查看")
                print("   建議使用完全公開的粉絲團頁面")
                print("   範例: https://www.facebook.com/Microsoft")
                print("   範例: https://www.facebook.com/Apple")
            else:
                print("✅ 此頁面可以在未登入狀態下訪問")
                
                # 嘗試找到一些貼文
                post_elements = scraper.driver.find_elements(
                    scraper.driver.find_element("xpath", "//div[@role='article']")
                )
                print(f"   找到 {len(post_elements)} 個可能的貼文元素")
            
            print("\n等待 10 秒讓您檢查頁面...")
            time.sleep(10)
            
    except Exception as e:
        print(f"❌ 檢查過程中出現錯誤: {e}")
    
    print("檢查完成")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("請輸入 Facebook 粉絲團 URL: ").strip()
    
    if not url:
        print("未提供 URL")
        sys.exit(1)
    
    check_page_accessibility(url)
