"""
Facebook 貼文發布到 WordPress 工具 - Flask Web 應用
"""
from flask import Flask, render_template, request, jsonify
import os
import sys
import shutil
import random
from datetime import datetime
from wordpress_api import WordPressAPI
from facebook_scraper import scrape_facebook_post, FacebookPageScraper
from jetengine_helper import update_jetengine_gallery
from translator import ContentTranslator

# 確保輸出立即刷新到日誌（重要！）
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 嘗試導入配置
try:
    import config
except ImportError:
    print("錯誤: 找不到 config.py 文件")
    print("請確保 config.py 文件存在並包含必要的配置信息")
    exit(1)


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 初始化 WordPress API 客戶端
wp_api = WordPressAPI(
    config.WORDPRESS_URL,
    config.WORDPRESS_USERNAME,
    config.WORDPRESS_PASSWORD
)


@app.route('/')
def index():
    """
    首頁 - 顯示表單
    """
    return render_template('index.html')


@app.route('/api/tags')
def get_tags():
    """
    獲取文章標籤列表
    """
    try:
        tags = wp_api.get_taxonomies(config.TAG_TAXONOMY, config.POST_TYPE)
        return jsonify({
            'success': True,
            'data': [{'id': tag['id'], 'name': tag['name']} for tag in tags]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories')
def get_categories():
    """
    獲取文章分類列表
    """
    try:
        categories = wp_api.get_taxonomies(config.CATEGORY_TAXONOMY, config.POST_TYPE)
        return jsonify({
            'success': True,
            'data': [{'id': cat['id'], 'name': cat['name']} for cat in categories]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/tags-en')
def get_tags_en():
    """
    獲取英文版文章標籤列表
    """
    try:
        tags = wp_api.get_taxonomies(config.TAG_TAXONOMY_EN, config.POST_TYPE_EN)
        return jsonify({
            'success': True,
            'data': [{'id': tag['id'], 'name': tag['name']} for tag in tags]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories-en')
def get_categories_en():
    """
    獲取英文版文章分類列表
    """
    try:
        categories = wp_api.get_taxonomies(config.CATEGORY_TAXONOMY_EN, config.POST_TYPE_EN)
        return jsonify({
            'success': True,
            'data': [{'id': cat['id'], 'name': cat['name']} for cat in categories]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/publish', methods=['POST'])
def publish_post():
    """
    發布文章（支援中英文多語言）
    """
    try:
        data = request.json

        # 獲取表單數據
        fb_url = data.get('fb_url')
        tag_ids = data.get('tags', [])  # 中文版標籤
        category_ids = data.get('categories', [])  # 中文版分類
        tag_ids_en = data.get('tags_en', [])  # 英文版標籤
        category_ids_en = data.get('categories_en', [])  # 英文版分類
        languages = data.get('languages', ['zh'])  # 預設中文
        publish_date = data.get('publish_date')
        publish_time = data.get('publish_time', '20:00')

        # 驗證必填字段
        if not fb_url:
            return jsonify({
                'success': False,
                'error': '請輸入 Facebook 貼文URL'
            }), 400

        if not languages or len(languages) == 0:
            return jsonify({
                'success': False,
                'error': '請至少選擇一種發布語言'
            }), 400

        # 處理發布日期時間
        if not publish_date:
            publish_datetime = datetime.now()
        else:
            # 合併日期和時間
            datetime_str = f"{publish_date} {publish_time}"
            try:
                publish_datetime = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': '日期或時間格式錯誤'
                }), 400

        publish_iso = publish_datetime.isoformat()

        # 從 Facebook 爬取貼文
        print(f"正在從 Facebook 爬取貼文: {fb_url}")
        post_content, image_files = scrape_facebook_post(fb_url)

        if not post_content:
            return jsonify({
                'success': False,
                'error': '無法獲取貼文內容，請確認URL是否正確且為公開貼文'
            }), 400

        # 調試：檢查抓取到的內容
        print(f"\n=== 抓取到的內容調試 ===")
        print(f"內容長度: {len(post_content)} 字符")
        print(f"UTF-8 字節數: {len(post_content.encode('utf-8'))}")
        print(f"內容前 200 字符: {post_content[:200]}")
        # 檢查是否包含常見 emoji
        common_emojis = ['😊', '😂', '🎉', '✅', '❤️', '👍', '🌟', '✨', '⭐']
        found_emojis = [e for e in common_emojis if e in post_content]
        if found_emojis:
            print(f"✅ 發現 emoji: {found_emojis}")
        else:
            print(f"⚠️  未發現常見 emoji")
        print(f"======================\n")

        # 使用貼文內容的第一行作為標題
        first_line = post_content.split('\n')[0].strip() if post_content else ""
        title = first_line[:100] if len(first_line) > 100 else first_line
        if not title:
            title = f"Facebook 貼文 - {publish_datetime.strftime('%Y-%m-%d')}"

        # 上傳圖片到 WordPress（只上傳一次，中英文共用）
        print(f"正在上傳 {len(image_files)} 張圖片...")
        image_ids = []
        for image_file in image_files:
            media_id = wp_api.upload_media(image_file, title=os.path.basename(image_file))
            if media_id:
                image_ids.append(media_id)
                print(f"  - 已上傳: {os.path.basename(image_file)} (ID: {media_id})")

        # 隨機選擇一張圖片作為特色圖片
        featured_media_id = None
        if image_ids:
            featured_media_id = random.choice(image_ids)
            print(f"設置特色圖片: {featured_media_id} (從 {len(image_ids)} 張圖片中隨機選擇)")

        # 儲存發佈結果
        published_posts = []

        # 發布中文版本
        if 'zh' in languages:
            print("\n===== 發布中文版本 =====")
            print(f"正在發布中文文章: {title}")

            # 準備自定義字段
            custom_fields = {}
            if image_ids:
                custom_fields[config.CUSTOM_FIELD_ALBUM] = image_ids

            post_id = wp_api.create_post(
                title=title,
                content=post_content,
                tags=tag_ids,
                categories=category_ids,
                publish_date=publish_iso,
                custom_fields=custom_fields,
                featured_media=featured_media_id,
                post_type=config.POST_TYPE,
                tag_taxonomy=config.TAG_TAXONOMY,
                category_taxonomy=config.CATEGORY_TAXONOMY
            )

            # 使用 JetEngine helper 再次確保 gallery 字段正確設置
            if post_id and image_ids:
                print(f"使用 JetEngine helper 更新 gallery 字段...")
                gallery_success = update_jetengine_gallery(
                    wp_api,
                    post_id,
                    config.CUSTOM_FIELD_ALBUM,
                    image_ids,
                    config.POST_TYPE
                )
                if gallery_success:
                    print(f"✓ JetEngine gallery 字段設置成功")

            if post_id:
                post_url = f"{config.WORDPRESS_URL}/?p={post_id}"
                published_posts.append({
                    'language': 'zh',
                    'language_name': '中文',
                    'post_id': post_id,
                    'post_url': post_url,
                    'title': title
                })
                print(f"✓ 中文版本發布成功 (ID: {post_id})")
            else:
                print(f"✗ 中文版本發布失敗")

        # 發布英文版本
        if 'en' in languages:
            print("\n===== 發布英文版本 =====")

            # 檢查是否設定了 OpenAI API Key
            if not config.OPENAI_API_KEY:
                print("⚠ 警告：未設定 OpenAI API Key，跳過英文版本發布")
            else:
                try:
                    # 初始化翻譯器
                    translator = ContentTranslator()

                    # 翻譯標題和內容
                    print("正在翻譯文章...")
                    translation_result = translator.translate_post(title, post_content)

                    if translation_result['success']:
                        en_title = translation_result['title']
                        en_content = translation_result['content']

                        print(f"正在發布英文文章: {en_title}")

                        # 準備自定義字段（使用相同的圖片）
                        custom_fields_en = {}
                        if image_ids:
                            custom_fields_en[config.CUSTOM_FIELD_ALBUM_EN] = image_ids

                        post_id_en = wp_api.create_post(
                            title=en_title,
                            content=en_content,
                            tags=tag_ids_en,  # 使用英文版的標籤 ID
                            categories=category_ids_en,  # 使用英文版的分類 ID
                            publish_date=publish_iso,
                            custom_fields=custom_fields_en,
                            featured_media=featured_media_id,  # 使用相同的特色圖片
                            post_type=config.POST_TYPE_EN,
                            tag_taxonomy=config.TAG_TAXONOMY_EN,
                            category_taxonomy=config.CATEGORY_TAXONOMY_EN
                        )

                        # 使用 JetEngine helper 再次確保 gallery 字段正確設置
                        if post_id_en and image_ids:
                            print(f"使用 JetEngine helper 更新英文版 gallery 字段...")
                            gallery_success = update_jetengine_gallery(
                                wp_api,
                                post_id_en,
                                config.CUSTOM_FIELD_ALBUM_EN,
                                image_ids,
                                config.POST_TYPE_EN
                            )
                            if gallery_success:
                                print(f"✓ 英文版 JetEngine gallery 字段設置成功")

                        if post_id_en:
                            post_url_en = f"{config.WORDPRESS_URL}/?p={post_id_en}"
                            published_posts.append({
                                'language': 'en',
                                'language_name': '英文',
                                'post_id': post_id_en,
                                'post_url': post_url_en,
                                'title': en_title
                            })
                            print(f"✓ 英文版本發布成功 (ID: {post_id_en})")
                        else:
                            print(f"✗ 英文版本發布失敗")
                    else:
                        print(f"✗ 翻譯失敗: {translation_result.get('error')}")

                except Exception as e:
                    print(f"✗ 英文版本發布出錯: {e}")
                    import traceback
                    traceback.print_exc()

        # 清理臨時文件
        temp_dir = 'temp_fb_downloads'
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        # 返回結果
        if published_posts:
            return jsonify({
                'success': True,
                'published_posts': published_posts,
                'image_count': len(image_ids),
                'message': f'成功發布 {len(published_posts)} 個版本的文章！'
            })
        else:
            return jsonify({
                'success': False,
                'error': '所有語言版本均發布失敗，請檢查WordPress配置和權限'
            }), 500

    except Exception as e:
        print(f"發布文章時出錯: {e}")
        import traceback
        traceback.print_exc()

        # 清理臨時文件
        temp_dir = 'temp_fb_downloads'
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/batch/scrape', methods=['POST'])
def batch_scrape_posts():
    """
    批次抓取粉絲團貼文
    """
    try:
        data = request.json

        # 獲取表單數據
        page_url = data.get('page_url')
        since_date = data.get('since_date')

        # 驗證必填字段
        if not page_url:
            return jsonify({
                'success': False,
                'error': '請輸入粉絲團 URL'
            }), 400

        if not since_date:
            return jsonify({
                'success': False,
                'error': '請選擇日期'
            }), 400

        # 驗證日期格式
        try:
            datetime.strptime(since_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({
                'success': False,
                'error': '日期格式錯誤'
            }), 400

        print(f"正在批次抓取粉絲團貼文...")
        print(f"粉絲團 URL: {page_url}")
        print(f"起始日期: {since_date}")

        # 使用 FacebookPageScraper 抓取貼文
        with FacebookPageScraper(headless=True) as scraper:
            posts = scraper.scrape_page_posts(page_url, since_date)

        if not posts:
            return jsonify({
                'success': False,
                'error': '未找到符合條件的貼文，請確認粉絲團URL是否正確且為公開'
            }), 400

        print(f"成功抓取 {len(posts)} 個貼文")

        # 格式化返回數據
        formatted_posts = []
        for post in posts:
            formatted_posts.append({
                'url': post['url'],
                'title': post['title'],
                'content': post['content'][:100] + '...' if len(post['content']) > 100 else post['content'],
                'full_content': post['content'],
                'date': post['date'],
                'image_count': post['image_count'],
                'images': post['images'][:5]  # 最多返回5張圖片URL用於預覽
            })

        return jsonify({
            'success': True,
            'posts': formatted_posts,
            'total_count': len(formatted_posts),
            'message': f'成功抓取 {len(formatted_posts)} 個貼文'
        })

    except Exception as e:
        print(f"批次抓取貼文時出錯: {e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # 使用端口 8081 避免與 macOS AirPlay Receiver 衝突
    PORT = 8081

    print("=" * 60)
    print("Facebook 貼文發布到 WordPress 工具")
    print("=" * 60)
    print(f"WordPress 網站: {config.WORDPRESS_URL}")
    print(f"訪問地址: http://localhost:{PORT}")
    print("=" * 60)
    print("\n提示:")
    print("1. 請確保已安裝 ChromeDriver")
    print("2. 如果端口被占用，可以修改 app.py 中的 PORT 變量")
    print("3. 只支持公開的 Facebook 貼文\n")

    app.run(debug=True, host='0.0.0.0', port=PORT)
