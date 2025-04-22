import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load config from config.json
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Configuration variables
GEMINI_API_KEY = config.get('gemini_api_key') or os.getenv('GEMINI_API_KEY')
COUPANG_API_KEY = config.get('coupang_api_key') or os.getenv('COUPANG_API_KEY')
ENABLE_AI_FILTERING = config.get('enable_ai_filtering', True)

# Coupang Partners configuration
COUPANG_PARTNERS_ACCESS_KEY = os.getenv('COUPANG_PARTNERS_ACCESS_KEY')
COUPANG_PARTNERS_SECRET_KEY = os.getenv('COUPANG_PARTNERS_SECRET_KEY')
COUPANG_PARTNERS_VENDOR_ID = os.getenv('COUPANG_PARTNERS_VENDOR_ID')
IMAGE_SIZE = os.getenv('IMAGE_SIZE', '200x200')

# YouTube configuration
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Blogger configuration
BLOGGER_BLOGS = {
    1: {
        'name': '전기방식프로',
        'id': '3529026030573801112'
    }
}

# 기본 블로그 설정 (전기방식프로)
DEFAULT_BLOG_NUMBER = 1
BLOGGER_BLOG_ID = BLOGGER_BLOGS[DEFAULT_BLOG_NUMBER]['id']
WORK_DIR = os.getenv('WORK_DIR')

def get_blog_list_text():
    """블로그 목록을 문자열로 반환합니다."""
    return '\n'.join([f"{num}. {blog['name']} (ID: {blog['id']})" 
                     for num, blog in BLOGGER_BLOGS.items()])

def set_blog_id(blog_number):
    """블로그 번호로 블로그 ID를 설정합니다."""
    global BLOGGER_BLOG_ID
    if blog_number in BLOGGER_BLOGS:
        BLOGGER_BLOG_ID = BLOGGER_BLOGS[blog_number]['id']
        return True
    return False

# Export all variables
__all__ = [
    'GEMINI_API_KEY',
    'COUPANG_API_KEY',
    'ENABLE_AI_FILTERING',
    'COUPANG_PARTNERS_ACCESS_KEY',
    'COUPANG_PARTNERS_SECRET_KEY',
    'COUPANG_PARTNERS_VENDOR_ID',
    'IMAGE_SIZE',
    'YOUTUBE_API_KEY',
    'BLOGGER_BLOG_ID',
    'WORK_DIR',
    'BLOGGER_BLOGS',
    'DEFAULT_BLOG_NUMBER',
    'get_blog_list_text',
    'set_blog_id'
] 