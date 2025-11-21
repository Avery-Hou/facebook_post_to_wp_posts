"""
JetEngine Gallery 字段帮助函数

JetEngine 的 gallery 字段需要特殊处理
"""
import requests
from typing import List


def update_jetengine_gallery(wp_api, post_id: int, field_name: str, image_ids: List[int], post_type: str = 'news') -> bool:
    """
    更新 JetEngine gallery 字段

    JetEngine gallery 字段的格式通常是序列化的PHP数组或特定格式

    Args:
        wp_api: WordPress API 客户端
        post_id: 文章ID
        field_name: 字段名 (如 'news-album')
        image_ids: 图片ID列表
        post_type: 文章类型 (如 'news' 或 'news-en')

    Returns:
        是否成功
    """
    # 方法1: 尝试使用 REST API 的 meta 字段
    print(f"尝试方法1: REST API meta 字段 (post_type: {post_type})")
    if try_rest_api_meta(wp_api, post_id, field_name, image_ids, post_type):
        return True

    # 方法2: 使用 JetEngine 的自定义端点（如果存在）
    print(f"尝试方法2: JetEngine 自定义端点")
    if try_jetengine_endpoint(wp_api, post_id, field_name, image_ids):
        return True

    # 方法3: 直接使用 PHP 序列化格式
    print(f"尝试方法3: PHP 序列化格式 (post_type: {post_type})")
    if try_serialized_format(wp_api, post_id, field_name, image_ids, post_type):
        return True

    return False


def try_rest_api_meta(wp_api, post_id: int, field_name: str, image_ids: List[int], post_type: str = 'news') -> bool:
    """
    尝试使用标准 REST API 的 meta 字段
    """
    try:
        url = f"{wp_api.api_base}/{post_type}/{post_id}"
        print(f"  嘗試更新 URL: {url}")
        print(f"  字段名: {field_name}")
        print(f"  圖片 IDs: {image_ids}")

        # JetEngine gallery 可能需要特定格式
        # 尝试多种格式
        formats_to_try = [
            image_ids,  # 数组
            ','.join(map(str, image_ids)),  # 逗号分隔
            [str(id) for id in image_ids],  # 字符串数组
        ]

        for i, format_value in enumerate(formats_to_try):
            print(f"\n  嘗試格式 {i+1}/{len(formats_to_try)}: {type(format_value).__name__}")
            print(f"  值: {format_value}")

            data = {
                'meta': {
                    field_name: format_value
                }
            }

            response = requests.post(url, json=data, auth=wp_api.auth, timeout=30)
            print(f"  響應狀態碼: {response.status_code}")

            if response.status_code in [200, 201]:
                result = response.json()
                saved_value = result.get('meta', {}).get(field_name)

                print(f"  返回的 meta 數據: {result.get('meta', {})}")
                print(f"  保存的 {field_name} 值: {saved_value}")

                # 验证是否保存成功
                if saved_value:
                    print(f"  ✓ 使用格式成功: {type(format_value).__name__}")
                    return True
                else:
                    print(f"  ✗ 保存的值為空或 None")
            else:
                print(f"  ✗ 請求失敗: {response.text[:200]}")

    except Exception as e:
        print(f"  REST API 失败: {e}")
        import traceback
        traceback.print_exc()

    return False


def try_jetengine_endpoint(wp_api, post_id: int, field_name: str, image_ids: List[int]) -> bool:
    """
    尝试使用 JetEngine 的自定义端点
    """
    try:
        # JetEngine 可能有自定义的 REST API 端点
        url = f"{wp_api.site_url}/wp-json/jet-engine/v1/update-meta"

        data = {
            'post_id': post_id,
            'meta_key': field_name,
            'meta_value': image_ids
        }

        response = requests.post(url, json=data, auth=wp_api.auth, timeout=30)

        if response.status_code in [200, 201]:
            print(f"  ✓ JetEngine 端点成功")
            return True

    except Exception as e:
        print(f"  JetEngine 端点失败: {e}")

    return False


def try_serialized_format(wp_api, post_id: int, field_name: str, image_ids: List[int], post_type: str = 'news') -> bool:
    """
    尝试使用 PHP 序列化格式

    JetEngine 可能将 gallery 存储为序列化的 PHP 数组
    """
    try:
        url = f"{wp_api.api_base}/{post_type}/{post_id}"

        # PHP 序列化的数组格式
        # 例如: a:3:{i:0;i:456;i:1;i:457;i:2;i:458;}
        serialized = php_serialize_array(image_ids)

        data = {
            'meta': {
                field_name: serialized
            }
        }

        response = requests.post(url, json=data, auth=wp_api.auth, timeout=30)

        if response.status_code in [200, 201]:
            result = response.json()
            saved_value = result.get('meta', {}).get(field_name)

            if saved_value:
                print(f"  ✓ PHP 序列化格式成功")
                print(f"  保存的值: {saved_value}")
                return True

    except Exception as e:
        print(f"  序列化格式失败: {e}")

    return False


def php_serialize_array(arr: List[int]) -> str:
    """
    简单的 PHP 数组序列化

    将 Python 列表转换为 PHP 序列化格式
    例如: [456, 457, 458] -> a:3:{i:0;s:3:"456";i:1;s:3:"457";i:2;s:3:"458";}
    """
    parts = [f'a:{len(arr)}:{{']

    for i, value in enumerate(arr):
        value_str = str(value)
        parts.append(f'i:{i};s:{len(value_str)}:"{value_str}";')

    parts.append('}')

    return ''.join(parts)


def get_jetengine_gallery(wp_api, post_id: int, field_name: str, post_type: str = 'news') -> List[int]:
    """
    获取 JetEngine gallery 字段的值

    Args:
        wp_api: WordPress API 客户端
        post_id: 文章ID
        field_name: 字段名
        post_type: 文章类型 (如 'news' 或 'news-en')

    Returns:
        图片ID列表
    """
    try:
        url = f"{wp_api.api_base}/{post_type}/{post_id}"
        response = requests.get(url, auth=wp_api.auth, timeout=30)
        response.raise_for_status()

        result = response.json()
        meta = result.get('meta', {})
        value = meta.get(field_name)

        # 处理不同的返回格式
        if isinstance(value, list):
            return [int(x) if isinstance(x, (int, str)) and str(x).isdigit() else 0 for x in value]
        elif isinstance(value, str):
            # 可能是逗号分隔
            if ',' in value:
                return [int(x.strip()) for x in value.split(',') if x.strip().isdigit()]
            # 可能是单个值
            elif value.isdigit():
                return [int(value)]

        return []

    except Exception as e:
        print(f"获取 gallery 字段失败: {e}")
        return []
