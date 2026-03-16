"""
WordPress API 集成模块
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Optional


class WordPressAPI:
    def __init__(self, site_url: str, username: str, password: str):
        """
        初始化 WordPress API 客户端

        Args:
            site_url: WordPress 网站URL
            username: WordPress 用户名
            password: WordPress 应用程序密码（会自动去除空格）
        """
        self.site_url = site_url.rstrip('/')
        # 去除应用程序密码中的空格
        clean_password = password.replace(' ', '')
        self.auth = HTTPBasicAuth(username, clean_password)
        self.api_base = f"{self.site_url}/wp-json/wp/v2"

    def get_taxonomies(self, taxonomy: str, post_type: str = 'news') -> List[Dict]:
        """
        获取指定分类法的术语列表

        Args:
            taxonomy: 分类法名称 (如 'news-tag', 'news-type')
            post_type: 文章类型

        Returns:
            术语列表
        """
        url = f"{self.site_url}/wp-json/wp/v2/{taxonomy}"
        params = {
            'post_type': post_type,
            'per_page': 100  # 获取更多项目
        }

        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"获取分类法 {taxonomy} 失败: {e}")
            return []

    def upload_media(self, file_path: str, title: str = None) -> Optional[int]:
        """
        上传媒体文件到 WordPress

        Args:
            file_path: 本地文件路径
            title: 媒体标题

        Returns:
            媒体ID，失败返回 None
        """
        url = f"{self.api_base}/media"

        try:
            import os
            filename = os.path.basename(file_path)

            # 确定MIME类型
            if filename.lower().endswith(('.jpg', '.jpeg')):
                mime_type = 'image/jpeg'
            elif filename.lower().endswith('.png'):
                mime_type = 'image/png'
            elif filename.lower().endswith('.gif'):
                mime_type = 'image/gif'
            else:
                mime_type = 'application/octet-stream'

            # 使用 files 参数上传（multipart/form-data）
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, mime_type)
                }

                # 使用data参数传递额外信息（如果需要）
                data = {}
                if title:
                    data['title'] = title

                response = requests.post(
                    url,
                    files=files,
                    data=data if data else None,
                    auth=self.auth,
                    timeout=60
                )

            # 检查响应
            if response.status_code != 201:
                print(f"上传失败，状态码: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None

            result = response.json()
            media_id = result.get('id')

            return media_id

        except requests.exceptions.HTTPError as e:
            print(f"上传媒体文件失败 {file_path}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            return None
        except Exception as e:
            print(f"上传媒体文件失败 {file_path}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def post_exists_by_title(self, title: str, post_type: str = 'news') -> Optional[int]:
        """
        檢查指定 post_type 中是否已存在相同標題的文章

        Args:
            title: 文章標題
            post_type: 文章類型

        Returns:
            若已存在則回傳文章 ID，否則回傳 None
        """
        url = f"{self.api_base}/{post_type}"
        params = {
            'search': title,
            'per_page': 10,
            'status': 'publish,draft,pending,private',
        }

        try:
            response = requests.get(url, params=params, auth=self.auth, timeout=30)
            response.raise_for_status()
            posts = response.json()

            for post in posts:
                existing_title = post.get('title', {}).get('rendered', '')
                # WordPress 會將 HTML entities 編碼，需要解碼後比對
                import html as html_mod
                existing_title_decoded = html_mod.unescape(existing_title).strip()
                if existing_title_decoded == title.strip():
                    return post.get('id')

            return None
        except Exception as e:
            print(f"檢查文章標題是否重複時出錯: {e}")
            return None

    def create_post(self,
                    title: str,
                    content: str,
                    tags: List[int],
                    categories: List[int],
                    publish_date: str,
                    custom_fields: Dict = None,
                    featured_media: int = None,
                    post_type: str = 'news',
                    tag_taxonomy: str = 'news-tag',
                    category_taxonomy: str = 'news-type') -> Optional[int]:
        """
        创建文章

        Args:
            title: 文章标题
            content: 文章内容
            tags: 标签ID列表
            categories: 分类ID列表
            publish_date: 发布日期 (ISO 8601 格式)
            custom_fields: 自定义字段字典
            featured_media: 特色图片媒体ID
            post_type: 文章类型
            tag_taxonomy: 標籤分類法名稱
            category_taxonomy: 分類法名稱

        Returns:
            文章ID，失败返回 None
        """
        url = f"{self.api_base}/{post_type}"

        data = {
            'title': title,
            'content': content,
            'status': 'publish',
            'date': publish_date,
        }

        # 添加标签和分类（根據傳入的 taxonomy 名稱）
        if tags:
            data[tag_taxonomy] = tags
        if categories:
            data[category_taxonomy] = categories

        # 添加自定义字段
        if custom_fields:
            data['meta'] = custom_fields

        # 添加特色图片
        if featured_media:
            data['featured_media'] = featured_media

        try:
            # 確保請求使用 UTF-8 編碼（支持 emoji）
            # 使用 ensure_ascii=False 確保 emoji 不被轉義
            import json as json_module
            json_data = json_module.dumps(data, ensure_ascii=False)

            headers = {
                'Content-Type': 'application/json; charset=utf-8'
            }

            response = requests.post(
                url,
                data=json_data.encode('utf-8'),
                auth=self.auth,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            post_id = result.get('id')

            # 調試：檢查返回的 meta 數據
            if post_id and custom_fields:
                returned_meta = result.get('meta', {})
                print(f"\n調試信息 - 文章創建後的 meta 數據:")
                for field_name, field_value in custom_fields.items():
                    returned_value = returned_meta.get(field_name)
                    print(f"  字段: {field_name}")
                    print(f"  發送的值: {field_value}")
                    print(f"  返回的值: {returned_value}")
                    if returned_value != field_value:
                        print(f"  ⚠️  警告: 返回值與發送值不一致！")
                    else:
                        print(f"  ✓ 值匹配")

            return post_id

        except requests.exceptions.RequestException as e:
            print(f"创建文章失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应内容: {e.response.text}")
            return None
