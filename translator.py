"""
OpenAI 翻譯模組
使用 OpenAI API 將中文內容翻譯成英文（以幼兒園主任的角色）
"""
from openai import OpenAI
from typing import Optional
import config


class ContentTranslator:
    def __init__(self, api_key: str = None):
        """
        初始化翻譯器

        Args:
            api_key: OpenAI API Key，如果未提供則使用 config.OPENAI_API_KEY
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API Key 未設定，請在 config.py 中設定 OPENAI_API_KEY")

        self.client = OpenAI(api_key=self.api_key)

    def translate_to_english(self, chinese_text: str, text_type: str = "content") -> Optional[str]:
        """
        將中文內容翻譯成英文

        Args:
            chinese_text: 要翻譯的中文內容
            text_type: 文本類型，可以是 "title" 或 "content"

        Returns:
            翻譯後的英文內容，失敗返回 None
        """
        if not chinese_text or not chinese_text.strip():
            return ""

        try:
            # 根據文本類型設定不同的提示詞
            if text_type == "title":
                system_prompt = """你是一位專業且親切的幼兒園主任，負責將幼兒園的中文公告標題翻譯成英文。
請注意：
1. 保持標題的簡潔性和吸引力
2. 使用適合家長閱讀的友善語氣
3. 保留原文的重點信息
4. 只返回翻譯結果，不要加任何說明"""

                user_prompt = f"請將以下幼兒園公告標題翻譯成英文：\n\n{chinese_text}"

            else:  # content
                system_prompt = """你是一位專業且親切的幼兒園主任，負責將幼兒園的中文公告內容翻譯成英文。
請注意：
1. 使用溫暖、專業且易懂的語氣
2. 保持原文的段落結構和格式
3. 適當使用家長能理解的教育專業術語
4. 保持親切友善的語調，讓家長感到被重視
5. 只返回翻譯結果，不要加任何說明或註解"""

                user_prompt = f"請將以下幼兒園公告內容翻譯成英文：\n\n{chinese_text}"

            # 調用 OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # 使用 GPT-4o mini 模型，性價比高
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # 適度的創造性
                max_tokens=2000
            )

            # 獲取翻譯結果
            translated_text = response.choices[0].message.content.strip()

            print(f"✓ 翻譯完成 ({text_type})")
            return translated_text

        except Exception as e:
            print(f"翻譯失敗 ({text_type}): {e}")
            import traceback
            traceback.print_exc()
            return None

    def translate_post(self, title: str, content: str) -> dict:
        """
        翻譯整篇文章（標題和內容）

        Args:
            title: 文章標題
            content: 文章內容

        Returns:
            包含翻譯結果的字典 {'title': ..., 'content': ..., 'success': ...}
        """
        print("開始翻譯文章...")

        translated_title = self.translate_to_english(title, "title")
        if not translated_title:
            return {
                'success': False,
                'error': '標題翻譯失敗'
            }

        translated_content = self.translate_to_english(content, "content")
        if not translated_content:
            return {
                'success': False,
                'error': '內容翻譯失敗'
            }

        print("✓ 文章翻譯完成")
        return {
            'success': True,
            'title': translated_title,
            'content': translated_content
        }
