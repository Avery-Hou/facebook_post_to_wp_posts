import os
from dotenv import load_dotenv

load_dotenv()

# WordPress 配置
WORDPRESS_URL = os.getenv("WORDPRESS_URL", "https://xinbaby.com.tw")
WORDPRESS_USERNAME = os.getenv("WORDPRESS_USERNAME", "wpadmin")
WORDPRESS_PASSWORD = os.getenv("WORDPRESS_PASSWORD", "")

# 文章配置
POST_TYPE = "news"
TAG_TAXONOMY = "news-tag"
CATEGORY_TAXONOMY = "news-type"
CUSTOM_FIELD_ALBUM = "news-album"

# 英文版文章配置
POST_TYPE_EN = "news-en"
TAG_TAXONOMY_EN = "news-tag-en"
CATEGORY_TAXONOMY_EN = "news-type-en"
CUSTOM_FIELD_ALBUM_EN = "news-album"

# OpenAI API 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # 請在 .env 檔案中設定您的 OpenAI API Key
