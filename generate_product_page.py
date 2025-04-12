import os
import json
import requests
from urllib.parse import quote_plus
import time
from datetime import datetime
import re
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import base64
from io import BytesIO
import sys
import random
import textwrap
import math
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from collections import defaultdict
import google.generativeai as genai
import mimetypes
import urllib.parse

def create_dummy_image(file_path, text="이미지 없음"):
    """더미 이미지 생성 함수"""
    try:
        # 이미지 크기 설정
        width = 300
        height = 300
        
        # 새 이미지 생성 (흰색 배경)
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        try:
            # 폰트 설정 (나눔고딕 사용)
            font_path = "C:/Windows/Fonts/NanumGothic.ttf"  # Windows 기본 설치 폰트
            font_size = 20
            font = ImageFont.truetype(font_path, font_size)
        except:
            # 폰트 로드 실패시 기본 폰트 사용
            font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 텍스트 위치 계산 (중앙 정렬)
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # 텍스트 그리기
        draw.text((x, y), text, font=font, fill='black')
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 이미지 저장
        image.save(file_path, 'JPEG', quality=95)
        print(f"✅ 더미 이미지 생성 완료: {os.path.basename(file_path)}")
        return True
        
    except Exception as e:
        print(f"⚠️ 더미 이미지 생성 실패: {str(e)}")
        return False

def download_image(url, file_path):
    """이미지 다운로드 함수"""
    try:
        # URL이 placeholder인 경우 더미 이미지 생성
        if 'placeholder.com' in url:
            return create_dummy_image(file_path, "이미지 없음")
        
        # 이미지 다운로드를 위한 헤더 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.coupang.com/'
        }
        
        # URL이 상대 경로인 경우 절대 경로로 변환
        if not url.startswith(('http://', 'https://')):
            url = f"https:{url}" if url.startswith('//') else f"https://{url}"
        
        # 이미지 다운로드 시도
        max_retries = 3
        retry_delay = 2  # 초
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, stream=True, timeout=10)
                response.raise_for_status()
                
                # Content-Type 확인
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    print(f"⚠️ 잘못된 Content-Type: {content_type}")
                    return create_dummy_image(file_path, "유효하지 않은 이미지")
                
                # 이미지 저장
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 파일 크기 확인
                file_size = os.path.getsize(file_path)
                if file_size < 100:  # 100바이트 미만이면 유효하지 않은 이미지로 간주
                    print(f"⚠️ 파일 크기가 너무 작음: {file_size} bytes")
                    return create_dummy_image(file_path, "유효하지 않은 이미지")
                
                print(f"✅ 이미지 다운로드 완료: {os.path.basename(file_path)}")
                print(f"   크기: {file_size:,} bytes")
                return True
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ 다운로드 시도 {attempt + 1}/{max_retries} 실패. {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
                else:
                    print(f"⚠️ 네트워크 오류: {str(e)}")
                    return create_dummy_image(file_path, "네트워크 오류")
        
        return create_dummy_image(file_path, "다운로드 실패")
        
    except Exception as e:
        print(f"⚠️ 이미지 다운로드 실패: {str(e)}")
        return create_dummy_image(file_path, "다운로드 실패")

def normalize_text(text):
    """텍스트 정규화 함수: 공백을 단일 공백으로 변경하고 특수문자 제거"""
    # 모든 공백 문자를 단일 공백으로 변경
    text = ' '.join(text.split())
    # 특수문자 제거 (단, 숫자와 L은 유지)
    text = re.sub(r'[^\w\s]|_', '', text)
    # 중요하지 않은 단어 제거
    text = re.sub(r'\b(방문설치|설치|무료배송)\b', '', text, flags=re.IGNORECASE)
    return text.strip().lower()

# Gemini API 관련 함수
def get_gemini_api_key():
    """Gemini API 키를 .env 파일, 환경 변수 또는 config 파일에서 로드"""
    # .env 파일 로드 시도
    load_dotenv()
    
    # 환경 변수에서 API 키 가져오기
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # 환경 변수에 없는 경우 config 파일에서 로드 시도
    if not api_key:
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    api_key = config.get("gemini_api_key", "")
            except Exception as e:
                print(f"설정 파일 로드 중 오류: {e}")
    
    return api_key

def encode_image_to_base64(image_url):
    """이미지 URL에서 이미지를 다운로드하고 Base64로 인코딩"""
    try:
        response = requests.get(image_url)
        response.raise_for_status()
        image_bytes = BytesIO(response.content)
        encoded_string = base64.b64encode(image_bytes.getvalue()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print(f"이미지 인코딩 중 오류: {e}")
        return None

def analyze_product_with_gemini(product_name, image_url):
    """Gemini API를 사용하여 제품 이름과 이미지를 분석"""
    api_key = get_gemini_api_key()
    if not api_key:
        print("Gemini API 키가 없습니다. 환경 변수 GEMINI_API_KEY를 설정하거나 config.json 파일에 추가하세요.")
        return None
    
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}"
    
    # 이미지가 없는 경우
    if not image_url:
        prompt = f"""다음 제품 이름을 분석하여 정확한 제품 분류를 해주세요:
        제품 이름: {product_name}
        
        다음 형식으로 JSON으로 응답해주세요:
        {{
            "brand": "제품 브랜드",
            "product_type": "제품 유형 (예: 전자제품, 의류, 신발, 가전제품, 가구, 식품, 화장품 등)",
            "product_category": "제품 카테고리 (예: 노트북, 티셔츠, 운동화, 냉장고, 소파, 과자, 립스틱 등)",
            "confidence": "확신도 (0-1 사이의 숫자)",
            "is_relevant": true/false,
            "description": "제품에 대한 간략한 설명"
        }}
        
        특히 다음 사항에 주의해주세요:
        1. 정확한 브랜드와 제품 유형 구분
        2. 최대한 구체적인 카테고리 분류
        3. 제품 특성에 맞는 정확한 설명
        """
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
    else:
        # 이미지가 있는 경우, 이미지 인코딩
        encoded_image = encode_image_to_base64(image_url)
        if not encoded_image:
            return None
        
        prompt = f"""다음 제품 이름과 이미지를 분석하여 정확한 제품 분류를 해주세요:
        제품 이름: {product_name}
        
        다음 형식으로 JSON으로 응답해주세요:
        {{
            "brand": "제품 브랜드",
            "product_type": "제품 유형 (예: 전자제품, 의류, 신발, 가전제품, 가구, 식품, 화장품 등)",
            "product_category": "제품 카테고리 (예: 노트북, 티셔츠, 운동화, 냉장고, 소파, 과자, 립스틱 등)",
            "confidence": "확신도 (0-1 사이의 숫자)",
            "is_relevant": true/false,
            "description": "제품에 대한 간략한 설명"
        }}
        
        특히 다음 사항에 주의해주세요:
        1. 정확한 브랜드와 제품 유형 구분
        2. 최대한 구체적인 카테고리 분류
        3. 제품 특성에 맞는 정확한 설명
        4. 이미지가 제품명과 일치하는지 확인하고 불일치하면 is_relevant를 false로 설정
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}}
                ]
            }]
        }
    
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # 응답에서 JSON 추출
        text_response = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
        
        # JSON 문자열 찾기
        json_match = re.search(r'({[\s\S]*})', text_response)
        if json_match:
            json_str = json_match.group(1)
            try:
                analysis = json.loads(json_str)
                return analysis
            except json.JSONDecodeError:
                print(f"JSON 파싱 오류: {json_str}")
                return None
        
        return None
        
    except Exception as e:
        print(f"Gemini API 호출 중 오류: {e}")
        return None

def filter_products(search_results, keyword, search_type='exact'):
    """검색 결과를 필터링하는 함수"""
    filtered_products = []
    
    # 디버깅 로깅 활성화
    debug_mode = True
    
    print(f"\n{'='*50}")
    print(f"검색어: '{keyword}'")
    print(f"검색 방식: {search_type}")
    print(f"{'='*50}")
    
    # 모든 상품을 처리
    for idx, item in enumerate(search_results):
        original_name = item.get('name', '')
        category = item.get('category', '')
        
        # 디버깅 정보
        if idx < 5 or debug_mode:
            print(f"\n상품 #{idx+1}: {original_name}")
            print(f"  카테고리: {category}")
        
        # 모든 상품을 포함
        filtered_products.append(item)
        if idx < 5 or debug_mode:
            print(f"  ✅ 상품 포함됨")
    
    # 결과 개수 출력
    print(f"\n{'='*50}")
    print(f"검색 결과: 총 {len(filtered_products)}개 상품")
    print(f"{'='*50}")
    
    # 결과가 없으면 빈 목록 반환
    if not filtered_products:
        return []
    
    # 상품 데이터 변환
    processed_products = []
    for item in filtered_products:
        try:
            # URL이 상대 경로인 경우 절대 경로로 변환
            product_url = item.get('productUrl', '')
            if product_url and not product_url.startswith(('http://', 'https://')):
                product_url = f"https://www.coupang.com{product_url}"
            
            # 이미지 URL 처리
            print(f"\n상품 정보:")
            print(f"  상품명: {item.get('productName', '')}")
            print(f"  상품 ID: {item.get('productId', '')}")
            
            # 1. productImage 필드 확인
            image_url = item.get('productImage', '')
            if image_url:
                print(f"  ✅ productImage 필드에서 이미지 URL 찾음: {image_url}")
            
            # 2. imageUrl 필드 확인
            if not image_url:
                image_url = item.get('imageUrl', '')
                if image_url:
                    print(f"  ✅ imageUrl 필드에서 이미지 URL 찾음: {image_url}")
            
            # 3. CDN URL 생성 시도
            if not image_url:
                product_id = item.get('productId', '')
                if product_id:
                    print(f"  🔍 CDN URL 생성 시도 (상품 ID: {product_id})")
                    # 쿠팡 CDN URL 패턴 시도
                    cdn_patterns = [
                        f"https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                        f"https://thumbnail6.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                        f"https://thumbnail7.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                        f"https://thumbnail8.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                        f"https://thumbnail9.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg"
                    ]
                    
                    # 각 CDN 패턴 시도
                    for pattern in cdn_patterns:
                        try:
                            response = requests.head(pattern)
                            if response.status_code == 200:
                                image_url = pattern
                                print(f"  ✅ CDN URL 찾음: {pattern}")
                                break
                            else:
                                print(f"  ❌ CDN URL 실패 ({response.status_code}): {pattern}")
                        except Exception as e:
                            print(f"  ❌ CDN URL 요청 실패: {str(e)}")
            
            if image_url:
                # 이미지 URL이 상대 경로인 경우 절대 경로로 변환
                if not image_url.startswith(('http://', 'https://')):
                    image_url = f"https:{image_url}" if image_url.startswith('//') else f"https://{image_url}"
                
                # 이미지 URL이 쿠팡 CDN URL인 경우
                if 'thumbnail' in image_url:
                    # 이미지 크기 조정 (212x212)
                    image_url = image_url.replace('492x492ex', '212x212ex')
                
                print(f"  ✅ 최종 이미지 URL: {image_url}")
            else:
                print(f"  ⚠️ 이미지 URL을 찾을 수 없음")
                print(f"  상품 ID: {product_id}")
                print(f"  상품명: {item.get('productName', '')}")
            
            processed_product = {
                'id': str(item.get('productId', '')).replace('/', '_'),
                'name': item.get('name', '').strip(),
                'price': item.get('price', '0'),
                'product_url': product_url,
                'productImage': item.get('productImage', ''),
                'image_url': image_url,
                'category': item.get('category', ''),
                'rocket_delivery': item.get('rocketDelivery', False),
                'rating': item.get('rating', '0'),
                'review_count': item.get('reviewCount', '0')
            }
            processed_products.append(processed_product)
            print(f"✅ 상품 처리 완료: {processed_product['name']}")
        except Exception as e:
            print(f"⚠️ 상품 처리 중 오류 발생: {str(e)}")
            continue
    
    return processed_products

def test_html_generation():
    """HTML 생성 테스트 함수"""
    print("\n=== HTML 생성 테스트 시작 ===")
    
    # 테스트 케이스 1: 기본 테스트
    print("\n테스트 케이스 1: 기본 상품")
    test_products = [{
        'name': '테스트 상품 1',
        'product_url': 'https://www.coupang.com/vp/products/1234567',
        'image_url': 'https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg',
        'price': 10000,
        'rating': '4.5',
        'review_count': '10'
    }]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result1 = generate_html(test_products, timestamp)
    print(f"테스트 1 결과: {'성공' if result1 else '실패'}")
    
    # 테스트 케이스 2: 여러 상품
    print("\n테스트 케이스 2: 여러 상품")
    test_products = [
        {
            'name': '테스트 상품 1',
            'product_url': 'https://www.coupang.com/vp/products/1234567',
            'image_url': 'https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg',
            'price': 10000,
            'rating': '4.5',
            'review_count': '10'
        },
        {
            'name': '테스트 상품 2',
            'product_url': 'https://www.coupang.com/vp/products/7654321',
            'image_url': 'https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg',
            'price': 20000,
            'rating': '4.8',
            'review_count': '20'
        }
    ]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result2 = generate_html(test_products, timestamp)
    print(f"테스트 2 결과: {'성공' if result2 else '실패'}")
    
    # 테스트 케이스 3: 특수문자가 포함된 상품명
    print("\n테스트 케이스 3: 특수문자 포함 상품명")
    test_products = [{
        'name': '테스트 상품!@#$%^&*()',
        'product_url': 'https://www.coupang.com/vp/products/9876543',
        'image_url': 'https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg',
        'price': 30000,
        'rating': '4.2',
        'review_count': '15'
    }]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result3 = generate_html(test_products, timestamp)
    print(f"테스트 3 결과: {'성공' if result3 else '실패'}")
    
    # 테스트 케이스 4: 이미지 URL이 없는 경우
    print("\n테스트 케이스 4: 이미지 URL 없음")
    test_products = [{
        'name': '테스트 상품 4',
        'product_url': 'https://www.coupang.com/vp/products/4567890',
        'image_url': '',
        'price': 40000,
        'rating': '4.7',
        'review_count': '25'
    }]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    result4 = generate_html(test_products, timestamp)
    print(f"테스트 4 결과: {'성공' if result4 else '실패'}")
    
    # 모든 테스트 결과 확인
    all_tests_passed = all([result1, result2, result3, result4])
    print(f"\n=== 테스트 결과 ===")
    print(f"전체 테스트: {'성공' if all_tests_passed else '실패'}")
    
    return all_tests_passed

def generate_html(products: List[Dict], timestamp: str) -> str:
    """상품 정보를 HTML로 변환"""
    try:
        # 이미지 저장 디렉토리 생성
        image_dir = os.path.join('coupang_html', 'images')
        os.makedirs(image_dir, exist_ok=True)
        
        # 기본 이미지 생성
        no_image_path = os.path.join(image_dir, 'no-image.jpg')
        if not os.path.exists(no_image_path):
            print("\n기본 이미지 생성 중...")
            create_dummy_image(no_image_path, "이미지 없음")
            print("✅ 기본 이미지 생성 완료")
        
        # 썸네일 디렉토리 생성 
        thumbnail_dir = os.path.join('coupang_html', 'thumbnails')
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        # 페이지 헤더 썸네일 생성
        header_thumbnail_path = os.path.join(thumbnail_dir, f'header_thumbnail_{timestamp}.jpg')
        header_title = "추천 상품 모음"
        
        try:
            # 상품 정보가 있으면 첫 번째 상품의 카테고리 추정
            category = None
            if products and len(products) > 0:
                product_name = products[0].get('name', '').lower()
                if '노트북' in product_name or '컴퓨터' in product_name or '태블릿' in product_name:
                    category = '전자제품'
                    header_title = "프리미엄 전자제품 추천"
                elif '옷' in product_name or '의류' in product_name or '셔츠' in product_name:
                    category = '의류'
                    header_title = "스타일리시한 의류 추천"
                elif '냉장고' in product_name or '세탁기' in product_name or '에어컨' in product_name:
                    category = '가전'
                    header_title = "필수 가전제품 추천"
                elif '운동' in product_name or '스포츠' in product_name:
                    category = '스포츠'
                    header_title = "건강한 스포츠 용품 추천"
                elif '음식' in product_name or '과자' in product_name:
                    category = '식품'
                    header_title = "맛있는 식품 추천"
                elif '책상' in product_name or '의자' in product_name:
                    category = '가구'
                    header_title = "편안한 가구 추천"
            
            # 헤더 썸네일 생성
            print("\n페이지 헤더 썸네일 생성 중...")
            thumbnail_result = generate_thumbnail(
                title=header_title,
                category=category,
                output_path=header_thumbnail_path
            )
            
            if thumbnail_result:
                header_thumbnail_url = os.path.join('thumbnails', os.path.basename(header_thumbnail_path))
                print(f"✅ 헤더 썸네일 생성 완료: {header_thumbnail_url}")
            else:
                header_thumbnail_url = None
                print("⚠️ 헤더 썸네일 생성 실패")
        except Exception as e:
            print(f"⚠️ 헤더 썸네일 생성 중 오류: {str(e)}")
            header_thumbnail_url = None
        
        # CSS 스타일 정의 (한 줄로 작성)
        css_style = "body{font-family:'Noto Sans KR',sans-serif;line-height:1.6;color:#333;background:#f5f5f5;margin:0;padding:0}.container{max-width:1200px;margin:0 auto;padding:20px}.header-banner{width:100%;max-height:300px;object-fit:cover;border-radius:8px;margin-bottom:20px}.product-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px;margin-top:20px}.product-card{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);overflow:hidden;transition:transform .2s}.product-card:hover{transform:translateY(-5px)}.product-image{width:100%;height:200px;object-fit:contain;border-bottom:1px solid #eee;transition:opacity 0.3s}.product-image:hover{opacity:0.8;cursor:pointer}.product-info{padding:12px}.product-title{font-size:.9rem;font-weight:500;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;text-overflow:ellipsis}.product-price{font-size:1rem;font-weight:700;color:#e74c3c}.product-price::after{content:'원';margin-left:2px;font-size:.9em}.product-meta{font-size:.8rem;color:#666;margin-top:8px}.product-link{text-decoration:none;color:inherit}.product-info .product-link{display:inline-block;margin-top:10px;padding:6px 12px;background:#3498db;color:#fff;border-radius:4px;text-align:center;transition:background 0.3s}.product-info .product-link:hover{background:#2980b9}h1.page-title{text-align:center;margin-bottom:30px;color:#2c3e50}.affiliate-disclosure{margin-top:40px;padding-top:20px;border-top:1px solid #eee;color:#888;font-size:0.9em;text-align:center}@media (max-width:768px){.product-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}.product-image{height:160px}.product-info{padding:8px}}"
        
        # HTML 템플릿 정의
        html_template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>추천 상품</title>
    <style>{css_style}</style>
</head>
<body>
    <div class="container">
        <h1 class="page-title">오늘의 추천 상품</h1>
        {header_thumbnail}
        <div class="product-grid">
            {product_cards}
        </div>
        <div class="affiliate-disclosure">
            <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
        </div>
    </div>
</body>
</html>"""

        # 헤더 썸네일 HTML
        header_thumbnail_html = ""
        if header_thumbnail_url:
            header_thumbnail_html = f'<img src="{header_thumbnail_url}" alt="추천 상품" class="header-banner">'

        # 상품 카드 템플릿
        product_card_template = """<div class="product-card">
        <a href="{url}" class="product-link" target="_blank">
            <img src="{image_url}" alt="{title}" class="product-image" onerror="this.src='images/no-image.jpg'">
        </a>
        <div class="product-info">
            <h3 class="product-title">{title}</h3>
            <div class="product-price">{price_formatted}</div>
            <div class="product-meta">평점: {rating} ({review_count}개 리뷰)</div>
            <a href="{url}" class="product-link" target="_blank">상품 보기</a>
        </div>
    </div>"""

        # 상품 카드 HTML 생성
        product_cards = ""
        for idx, product in enumerate(products, 1):
            try:
                # 이미지 파일명 생성 (상품 ID와 타임스탬프 사용)
                product_id = product.get('id', f'product_{idx}')
                image_filename = f"{product_id}_{timestamp}.jpg"
                image_path = os.path.join('images', image_filename)
                full_image_path = os.path.join('coupang_html', image_path)
                
                # 이미지 URL 처리
                image_url = product.get('image_url', '')
                
                # 상품 정보 추출
                title = product.get('name', '제목 없음')
                url = product.get('product_url', '#')
                rating = product.get('rating', '0.0')
                review_count = product.get('review_count', '0')
                
                # 가격 형식화
                try:
                    price = int(product.get('price', 0))
                    price_formatted = f"{price:,}"
                except (ValueError, TypeError):
                    price_formatted = str(product.get('price', '가격 정보 없음'))
                
                # 이미지 다운로드 시도
                if image_url:
                    try:
                        if download_image(image_url, full_image_path):
                            print(f"✅ 이미지 다운로드 완료: {image_filename}")
                        else:
                            print(f"⚠️ 이미지 다운로드 실패: {image_url}")
                            image_path = "images/no-image.jpg"
                    except Exception as e:
                        print(f"⚠️ 이미지 다운로드 중 오류: {str(e)}")
                        image_path = "images/no-image.jpg"
                else:
                    print(f"⚠️ 이미지 URL 없음: {title}")
                    image_path = "images/no-image.jpg"
                
                # 상품 카드 HTML 생성
                product_cards += product_card_template.format(
                    url=url,
                    image_url=image_path,
                    title=title,
                    price_formatted=price_formatted,
                    rating=rating,
                    review_count=review_count
                )
                print(f"✅ 상품 카드 생성 완료: {title}")
                
            except Exception as e:
                print(f"⚠️ 상품 카드 생성 중 오류 발생: {str(e)}")
                continue

        # 최종 HTML 생성
        html_content = html_template.format(
            css_style=css_style,
            header_thumbnail=header_thumbnail_html,
            product_cards=product_cards
        )
        
        # HTML 파일 저장 - 고정된 파일명 사용
        os.makedirs('coupang_html', exist_ok=True)
        output_file = 'coupang_html/product_page.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ HTML 파일이 생성되었습니다: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ HTML 생성 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def process_search_results(search_results):
    """검색 결과에서 상품 정보 추출"""
    processed_products = []
    
    for result in search_results:
        try:
            # 상품 정보 추출
            product = {
                'name': result.get('productName', '제목 없음'),
                'price': result.get('productPrice', 0),
                'url': result.get('productUrl', ''),
                'image_url': result.get('productImage', '') or result.get('imageUrl', '')
            }
            
            # 필수 정보 확인
            if not product['name'] or not product['price'] or not product['url']:
                print(f"⚠️ 필수 정보 누락: {product['name']}")
                continue
                
            # 가격 형식 변환
            if isinstance(product['price'], str):
                # 쉼표 제거 후 정수로 변환
                try:
                    product['price'] = int(product['price'].replace(',', '').replace('원', ''))
                except:
                    product['price'] = 0
            
            # 이미지 URL 처리
            if not product['image_url']:
                product['image_url'] = 'https://via.placeholder.com/300x300?text=No+Image'
            
            # URL 처리: 상대 경로를 절대 경로로 변환
            if product['url'] and not product['url'].startswith(('http://', 'https://')):
                product['url'] = f"https://www.coupang.com{product['url']}"
                
            processed_products.append(product)
            print(f"   ✅ 상품 추가: {product['name']} ({product['price']}원)")
            
        except Exception as e:
            print(f"   ⚠️ 상품 처리 중 오류: {str(e)}")
            continue
    
    return processed_products

def download_image_to_base64(url, default_text="상품 이미지"):
    """이미지 URL에서 이미지를 다운로드하여 Base64 문자열로 반환
    다운로드에 실패하면 로컬에서 기본 이미지 생성"""
    try:
        if not url or url.strip() == "":
            # URL이 없으면 로컬에서 기본 이미지 생성
            return create_base64_placeholder_image(default_text)
        
        # URL이 유효한 경우 다운로드 시도
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                image_data = response.content
                base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # MIME 타입 탐지
                mime_type, _ = mimetypes.guess_type(url)
                if not mime_type:
                    # 기본적으로 JPEG로 가정
                    mime_type = "image/jpeg"
                
                return f"data:{mime_type};base64,{base64_data}"
        except Exception as e:
            print(f"   ⚠️ 이미지 다운로드 실패: {str(e)}")
        
        # 다운로드 실패 시 로컬에서 이미지 생성
        return create_base64_placeholder_image(default_text)
        
    except Exception as e:
        print(f"   ⚠️ 이미지 처리 중 오류: {str(e)}")
        # 어떤 경우든 기본 이미지는 반환
        return create_base64_placeholder_image("이미지 없음")

def create_base64_placeholder_image(text="이미지 없음"):
    """텍스트가 있는 기본 이미지를 생성하고 Base64 문자열로 반환"""
    try:
        # 이미지 크기 설정
        width, height = 200, 200
        
        # 빈 이미지 생성 (흰색 배경)
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 테두리 그리기
        border_color = (220, 220, 220)  # 연한 회색
        for i in range(4):  # 테두리 두께
            draw.rectangle(
                [(i, i), (width - 1 - i, height - 1 - i)],
                outline=border_color
            )
        
        try:
            # 폰트 설정 (나눔고딕 사용, 없으면 기본 폰트)
            font_path = "C:/Windows/Fonts/malgun.ttf"  # 맑은 고딕
            if not os.path.exists(font_path):
                font_path = "C:/Windows/Fonts/NanumGothic.ttf"  # 나눔고딕
            
            font_size = 16
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 줄바꿈 처리 (최대 15자)
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if len(test_line) <= 15:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        # 텍스트가 없으면 기본 텍스트 사용
        if not lines:
            lines = ["이미지 없음"]
        
        # 텍스트 그리기
        line_height = font_size + 4
        total_text_height = len(lines) * line_height
        start_y = (height - total_text_height) // 2
        
        for i, line in enumerate(lines):
            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 텍스트 위치 계산 (중앙 정렬)
            x = (width - text_width) // 2
            y = start_y + i * line_height
            
            # 텍스트 그리기
            draw.text((x, y), line, font=font, fill='black')
        
        # 이미지를 바이트로 변환
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{base64_image}"
    
    except Exception as e:
        print(f"   ⚠️ 기본 이미지 생성 중 오류: {str(e)}")
        # 아무런 이미지도 생성할 수 없는 경우 빈 문자열 반환
        return ""

def generate_product_html(products):
    """상품 정보를 HTML로 변환"""
    try:
        html_content = """
        <div class="products-grid">
        """
        
        for product in products:
            try:
                # Google 이미지 프록시를 사용하여 이미지 URL 변환
                product_image = proxy_image_url(product['image_url'], product['name'])
                
                # 상품 카드 HTML 생성
                product_card = f"""
                <div class="product-card">
                    <div class="product-image">
                        <a href="{product['url']}" target="_blank">
                            <img src="{product_image}" alt="{product['name']}" loading="lazy">
                        </a>
                    </div>
                    <div class="product-info">
                        <h3 class="product-title">{product['name']}</h3>
                        <p class="product-price">{product['price']:,}원</p>
                        <a href="{product['url']}" class="product-link" target="_blank">상품 보기</a>
                    </div>
                </div>
                """
                html_content += product_card
                print(f"   ✅ 상품 카드 생성: {product['name']}")
                
            except Exception as e:
                print(f"   ⚠️ 상품 카드 생성 중 오류: {str(e)}")
                continue
        
        html_content += """
        </div>
        """
        
        return html_content
        
    except Exception as e:
        print(f"❌ HTML 생성 중 오류 발생: {str(e)}")
        return None

def generate_video_html(video_info, summary, products):
    """비디오 정보와 요약, 상품 정보를 HTML로 변환"""
    try:
        # 비디오 정보 추출
        title = video_info.get('title', '제목 없음')
        description = video_info.get('description', '')
        thumbnail_url = video_info.get('thumbnail_url', '')
        
        # 썸네일 URL이 없으면 placeholder 이미지 사용
        if not thumbnail_url:
            thumbnail_url = "https://via.placeholder.com/1280x720?text=No+Thumbnail"
        
        # 요약 내용이 HTML 태그를 포함하는지 확인
        has_html_tags = bool(re.search(r'<[^>]+>', summary))
        
        # HTML 태그가 없으면 단락으로 변환
        if not has_html_tags:
            summary = '<p>' + summary.replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
        
        # BeautifulSoup을 사용하여 요약 내용에서 섹션이나 헤더 찾기
        soup = BeautifulSoup(summary, 'html.parser')
        sections = soup.find_all('div', class_='section')
        headers = soup.find_all(['h2', 'h3']) if not sections else []
        
        # 상품 배치를 위한 분석
        
        # 섹션 또는 헤더를 선택
        target_elements = sections if sections else headers
        if not target_elements:
            # 섹션이나 헤더가 없으면 summary를 그대로 사용
            processed_summary = summary
            # 모든 상품을 균등하게 나눠서 배치할 수 있도록 임의의 포인트 생성
            if products:
                soup = BeautifulSoup(summary, 'html.parser')
                paragraphs = soup.find_all('p')
                if paragraphs:
                    # 단락이 있으면 몇 개의 단락마다 상품을 배치
                    products_per_section = min(2, len(products))  # 섹션당 최대 2개 상품
                    sections_needed = (len(products) + products_per_section - 1) // products_per_section
                    paragraphs_per_section = max(1, len(paragraphs) // sections_needed)
                    
                    product_idx = 0
                    for i in range(0, len(paragraphs), paragraphs_per_section):
                        if product_idx >= len(products):
                            break
                            
                        # 현재 섹션에 추가할 상품 수 결정
                        current_products = products[product_idx:product_idx+products_per_section]
                        product_idx += products_per_section
                        
                        if current_products:
                            # 상품 HTML 생성
                            product_html = generate_product_subset_html(current_products, "관련 추천 상품")
                            product_section = BeautifulSoup(product_html, 'html.parser')
                            
                            # 현재 단락 뒤에 상품 추가
                            if i < len(paragraphs):
                                paragraphs[i].insert_after(product_section)
                    
                    processed_summary = str(soup)
                else:
                    # 단락이 없으면 전체 상품을 하나의 섹션으로 추가
                    additional_products_html = generate_product_subset_html(products, "추천 상품")
                    processed_summary = summary + additional_products_html
            else:
                processed_summary = summary
        else:
            # 각 상품에 가장 적합한 섹션 찾기
            section_products = defaultdict(list)
            
            # 상품 특성 추출
            for i, product in enumerate(products):
                product_name = product.get('name', '').lower()
                product_keywords = set(re.findall(r'\w+', product_name))
                
                best_match_score = -1
                best_match_idx = 0
                
                # 각 섹션과의 매칭 점수 계산
                for idx, section in enumerate(target_elements):
                    section_text = section.get_text().lower()
                    section_keywords = set(re.findall(r'\w+', section_text))
                    
                    # 공통 키워드 수 계산
                    common_keywords = product_keywords.intersection(section_keywords)
                    match_score = len(common_keywords)
                    
                    # 상품 키워드 중 공통 키워드 비율 계산
                    if product_keywords:
                        match_ratio = len(common_keywords) / len(product_keywords)
                        match_score = match_score * (1 + match_ratio)
                    
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_match_idx = idx
                
                # 가장 적합한 섹션에 상품 추가
                section_products[best_match_idx].append(product)
            
            # 요약에 상품 삽입
            str_summary = str(soup)
            soup = BeautifulSoup(str_summary, 'html.parser')
            target_elements = soup.find_all('div', class_='section') if sections else soup.find_all(['h2', 'h3'])
            
            # 모든 상품을 적절히 배치했는지 확인하기 위한 집합
            used_products = set()
            
            # 역순으로 처리하여 인덱스 문제 방지
            for idx in sorted(section_products.keys(), reverse=True):
                if idx < len(target_elements) and section_products[idx]:
                    prods = section_products[idx]
                    
                    # 섹션당 최대 2개의 상품만 사용
                    current_section_products = prods[:2]
                    
                    # 상품 섹션 HTML 생성
                    product_html = generate_product_subset_html(current_section_products, "관련 추천 상품")
                    
                    # 상품 섹션 삽입
                    product_section = BeautifulSoup(product_html, 'html.parser')
                    target_elements[idx].insert_after(product_section)
                    
                    # 사용된 상품 추적
                    for product in current_section_products:
                        used_products.add(tuple(sorted(product.items())))
            
            # 처리된 HTML 가져오기
            processed_summary = str(soup)
            
            # 남은 상품들 (미사용 상품) 확인
            remaining_products = []
            for product in products:
                product_tuple = tuple(sorted(product.items()))
                if product_tuple not in used_products:
                    remaining_products.append(product)
            
            # 남은 상품들이 있으면 추가
            if remaining_products:
                additional_products_html = generate_product_subset_html(remaining_products, "더 많은 추천 상품")
                processed_summary = processed_summary + additional_products_html
        
        # 전체 HTML 구성
        html = f"""<!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .thumbnail {{
                    width: 100%;
                    max-height: 350px;
                    object-fit: contain;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                h1 {{
                    font-size: 28px;
                    margin-bottom: 10px;
                    color: #1a1a1a;
                }}
                h2 {{
                    font-size: 22px;
                    margin-top: 30px;
                    margin-bottom: 15px;
                    color: #333;
                    border-bottom: 1px solid #eee;
                    padding-bottom: 10px;
                }}
                h3 {{
                    font-size: 18px;
                    margin-top: 25px;
                    color: #444;
                }}
                p {{
                    margin-bottom: 15px;
                }}
                .content {{
                    background: #fff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .section {{
                    margin-bottom: 25px;
                }}
                .meta {{
                    color: #666;
                    font-size: 14px;
                    margin-bottom: 20px;
                }}
                .product-section {{
                    margin: 20px 0;
                    padding: 12px;
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    max-width: 100%;
                }}
                .product-section h3 {{
                    margin-top: 0;
                    color: #333;
                    font-size: 16px;
                }}
                .products-grid, .product-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin: 15px auto;
                    max-width: 100%;
                }}
                .product-card {{
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                    width: 100%;
                    max-width: 300px;
                    margin: 0 auto;
                    display: flex;
                    flex-direction: column;
                }}
                .product-card:hover {{
                    transform: translateY(-3px);
                }}
                .product-image {{
                    width: 100%;
                    height: 120px;
                    text-align: center;
                    overflow: hidden;
                    border-bottom: 1px solid #eee;
                }}
                .product-image img {{
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }}
                .product-info {{
                    padding: 10px;
                }}
                .product-title {{
                    font-size: 13px;
                    margin: 0 0 8px 0;
                    color: #333;
                    line-height: 1.3;
                    max-height: 2.6em;
                    overflow: hidden;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                }}
                .product-price {{
                    font-size: 14px;
                    font-weight: bold;
                    color: #e44d26;
                    margin: 0 0 8px 0;
                }}
                .product-link {{
                    display: inline-block;
                    margin: 0;
                    padding: 6px 12px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: background-color 0.2s;
                    text-align: center;
                    font-size: 12px;
                }}
                .product-link:hover {{
                    background-color: #0056b3;
                }}
                .affiliate-disclosure {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #888;
                    font-size: 0.9em;
                    text-align: center;
                }}
                @media (max-width: 768px) {{
                    .product-grid {{
                        grid-template-columns: repeat(2, 1fr);
                    }}
                }}
                @media (max-width: 480px) {{
                    .product-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="{thumbnail_url}" alt="{title}" class="thumbnail">
                <h1>{title}</h1>
                <div class="meta">영상 요약</div>
                <div class="content">
                    {processed_summary}
                </div>
                <div class="affiliate-disclosure">
                    <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
                </div>
            </div>
        </body>
        </html>"""
        
        return html
    except Exception as e:
        print(f"❌ HTML 생성 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_specific_search(query, search_type='expanded'):
    """특정 검색어로 테스트하는 함수"""
    print(f"\n=== 검색어 '{query}', 검색방식 '{search_type}' 테스트 시작 ===")
    
    try:
        # 검색 실행
        result = process_search_results(keyword=query, search_type=search_type, max_products=5)
        
        if result:
            print(f"✅ 검색 테스트 성공: '{query}' ({search_type})")
            print(f"   생성된 HTML 파일: {result}")
            
            # HTML 파일 열기 옵션
            open_file = input("\nHTML 파일을 열어보시겠습니까? (y/n): ").lower().strip()
            if open_file == 'y':
                try:
                    import webbrowser
                    file_url = f"file://{os.path.abspath(result)}"
                    webbrowser.open(file_url)
                    print(f"✅ 파일을 브라우저에서 열었습니다: {file_url}")
                except Exception as e:
                    print(f"❌ 파일 열기 실패: {str(e)}")
            
            return True
        else:
            print(f"❌ 검색 테스트 실패: '{query}' ({search_type}) - 결과 없음")
            return False
    
    except Exception as e:
        print(f"❌ 검색 테스트 중 오류 발생: {str(e)}")
        return False

def run_e2e_tests():
    """종합적인 E2E 테스트를 실행하는 함수"""
    print("\n===== 종합 E2E 테스트 시작 =====")
    
    # 테스트할 검색어 목록과 검색 타입
    test_queries = [
        "e22",
        "테니스 라켓",
        "윌슨 테니스",
        "헤드 테니스 라켓"
    ]
    
    search_types = ['exact', 'similar', 'expanded']
    
    results = {}
    total_tests = len(test_queries) * len(search_types)
    success_count = 0
    
    print(f"\n총 {total_tests}개의 테스트를 실행합니다.\n")
    
    # 각 검색어와 검색 타입 조합으로 테스트
    for query in test_queries:
        results[query] = {}
        
        for search_type in search_types:
            test_name = f"검색어: '{query}', 검색방식: '{search_type}'"
            print(f"\n--- 테스트: {test_name} ---")
            
            try:
                result = process_search_results(keyword=query, search_type=search_type, max_products=3)
                
                if result:
                    print(f"✅ 성공: {test_name}")
                    print(f"   생성된 파일: {result}")
                    results[query][search_type] = True
                    success_count += 1
                else:
                    print(f"❌ 실패: {test_name} - 결과 없음")
                    results[query][search_type] = False
            except Exception as e:
                print(f"❌ 오류 발생: {test_name} - {str(e)}")
                results[query][search_type] = False
                
    # 테스트 결과 요약
    print("\n===== E2E 테스트 결과 요약 =====")
    print(f"성공: {success_count}/{total_tests} ({success_count/total_tests*100:.1f}%)")
    
    # 상세 결과 출력
    print("\n검색어별 결과:")
    for query in test_queries:
        query_success = sum(1 for v in results[query].values() if v)
        print(f"- '{query}': {query_success}/{len(search_types)} 성공")
        
    print("\n검색 방식별 결과:")
    for search_type in search_types:
        type_success = sum(1 for q in test_queries if results[q].get(search_type, False))
        print(f"- '{search_type}': {type_success}/{len(test_queries)} 성공")
    
    # 전체 테스트 통과 여부
    overall_success = success_count > 0  # 하나 이상의 테스트가 성공했는지 확인
    print(f"\n전체 E2E 테스트: {'성공' if overall_success else '실패'}")
    
    return overall_success

def run_test_suite():
    """테스트 스위트 실행 함수 - 모든 테스트를 관리"""
    print("\n======== 테스트 스위트 시작 ========")
    
    # 테스트 옵션 메뉴
    print("\n테스트 옵션을 선택하세요:")
    print("1. 기본 HTML 생성 테스트")
    print("2. E2E 테스트 (다양한 검색어)")
    print("3. 특정 검색어 테스트")
    print("4. 모든 테스트 실행")
    print("5. 썸네일 생성 테스트")
    print("6. 종료")
    
    mode = input("\n옵션 선택 (1-6): ").strip()
    
    if mode == '1':
        # HTML 생성 테스트
        print("\nHTML 생성 테스트 실행...")
        if test_html_generation():
            print("✅ HTML 생성 테스트 성공")
            return True
        else:
            print("❌ HTML 생성 테스트 실패")
            return False
    
    elif mode == '2':
        # E2E 테스트
        print("\nE2E 테스트 실행...")
        if run_e2e_tests():
            print("✅ E2E 테스트 성공")
            return True
        else:
            print("❌ E2E 테스트 실패")
            return False
    
    elif mode == '3':
        # 특정 검색어 테스트
        query = input("\n테스트할 검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어가 입력되지 않았습니다.")
            return False
        
        print(f"\n검색 방식을 선택하세요:")
        print("1. 완전일치 (exact)")
        print("2. 유사검색 (similar)")
        print("3. 확장검색 (expanded)")
        print("4. 모든 검색 방식")
        
        search_option = input("\n옵션 선택 (1-4): ").strip()
        
        if search_option == '4':
            # 모든 검색 방식으로 테스트
            success_count = 0
            for search_type in ['exact', 'similar', 'expanded']:
                if test_specific_search(query, search_type):
                    success_count += 1
            
            result = success_count > 0
            print(f"\n테스트 결과: {success_count}/3 성공")
            return result
        else:
            # 단일 검색 방식으로 테스트
            search_type = 'exact' if search_option == '1' else 'similar' if search_option == '2' else 'expanded'
            return test_specific_search(query, search_type)
    
    elif mode == '4':
        # 범용 검색
        print("\n=== 범용 검색 ===")
        print("이 모드는 모든 종류의 상품을 검색하고 AI 필터링을 적용합니다.")
        
        # 검색어 입력
        query = input("\n검색할 상품을 입력하세요: ").strip()
        if not query:
            print("검색어가 입력되지 않았습니다.")
            return
        
        # 가격대 선택 (선택 사항)
        print("\n가격대 선택 (선택사항):")
        print("1. 10만원 미만")
        print("2. 10-20만원")
        print("3. 20-30만원")
        print("4. 30만원 이상")
        print("5. 전체 가격대")
        
        price_option = input("\n옵션 선택 (1-5, 기본값: 5): ").strip() or '5'
        
        # 최대 상품 수
        max_products = input("\n표시할 최대 상품 개수 (기본값: 15): ").strip()
        if max_products and max_products.isdigit():
            max_products = int(max_products)
        else:
            max_products = 15
        
        # 검색 방식 - 범용 검색은 기본적으로 확장 검색
        search_type = 'expanded'
        
        # 범용 검색 실행
        print(f"\n검색 실행: '{query}' (최대 {max_products}개 상품)")
        result = process_search_results(keyword=query, search_type=search_type, max_products=max_products)
        
        if result:
            print(f"\n✅ 상품 페이지가 생성되었습니다: {result}")
            
            # HTML 파일 열기 옵션
            open_file = input("\nHTML 파일을 열어보시겠습니까? (y/n): ").lower().strip()
            if open_file == 'y':
                try:
                    import webbrowser
                    file_url = f"file://{os.path.abspath(result)}"
                    webbrowser.open(file_url)
                    print(f"✅ 파일을 브라우저에서 열었습니다: {file_url}")
                except Exception as e:
                    print(f"❌ 파일 열기 실패: {str(e)}")
        else:
            print(f"\n❌ 상품 페이지 생성에 실패했습니다.")
    elif mode == '5':
        # 썸네일 테스트
        print("\n썸네일 생성 테스트 실행...")
        result = test_thumbnail_generation()
        if result:
            print("\n✅ 썸네일 생성 테스트 성공")
            
            # 커스텀 썸네일 생성 옵션
            run_custom = input("\n커스텀 썸네일을 직접 생성해보시겠습니까? (y/n): ").strip().lower()
            if run_custom == 'y':
                title = input("\n썸네일 제목을 입력하세요: ").strip()
                
                print("\n카테고리를 선택하세요:")
                categories = ['전자제품', '의류', '가전', '스포츠', '식품', '가구', '미용', '도서', '생활용품', '악세서리']
                for idx, cat in enumerate(categories, 1):
                    print(f"{idx}. {cat}")
                
                cat_choice = input("\n카테고리 번호 선택 (1-10): ").strip()
                try:
                    cat_idx = int(cat_choice) - 1
                    if 0 <= cat_idx < len(categories):
                        category = categories[cat_idx]
                    else:
                        category = None
                except:
                    category = None
                
                # 배경 이미지 사용 옵션
                use_bg = input("\n배경 이미지를 사용하시겠습니까? (y/n): ").strip().lower()
                bg_image = None
                if use_bg == 'y':
                    bg_path = input("배경 이미지 경로를 입력하세요 (없으면 Enter): ").strip()
                    if bg_path and os.path.exists(bg_path):
                        bg_image = bg_path
                
                # 썸네일 생성 및 저장
                if title:
                    output_dir = os.path.join('coupang_html', 'thumbnails')
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, f"custom_thumbnail_{int(time.time())}.jpg")
                    
                    result = generate_thumbnail(
                        title=title,
                        category=category,
                        image_path=bg_image,
                        output_path=output_file
                    )
                    
                    if result:
                        print(f"\n✅ 커스텀 썸네일 생성 완료: {result}")
                        
                        # 브라우저에서 확인
                        try:
                            import webbrowser
                            file_url = f"file://{os.path.abspath(result)}"
                            webbrowser.open(file_url)
                        except Exception as e:
                            print(f"⚠️ 파일 열기 실패: {str(e)}")
                    else:
                        print("\n❌ 커스텀 썸네일 생성 실패")
            
            return True
        else:
            print("\n❌ 썸네일 생성 테스트 실패")
            return False
    elif mode == '6':
        print("프로그램을 종료합니다.")
        sys.exit(0)
    else:
        print("잘못된 모드를 선택하셨습니다. 프로그램을 종료합니다.")

def generate_thumbnail(title, category=None, image_path=None, output_path=None, size=(1200, 630)):
    """
    내용에 맞는 썸네일 이미지를 생성하는 함수
    
    Args:
        title (str): 썸네일에 표시할 제목
        category (str, optional): 제품 카테고리 (배경 색상 결정에 사용)
        image_path (str, optional): 배경으로 사용할 이미지 경로
        output_path (str, optional): 출력 파일 경로 (지정하지 않으면 BytesIO 객체 반환)
        size (tuple, optional): 이미지 크기 (기본값: 1200x630, 소셜미디어 썸네일 크기)
    
    Returns:
        str or BytesIO: 출력 파일 경로 또는 이미지 데이터
    """
    try:
        print(f"썸네일 생성 시작: '{title}' (카테고리: {category})")
        width, height = size
        
        # 카테고리별 배경색 매핑
        category_colors = {
            '전자제품': (52, 152, 219),  # 파란색
            '의류': (155, 89, 182),     # 보라색
            '가전': (52, 73, 94),       # 짙은 파란색
            '스포츠': (231, 76, 60),    # 빨간색
            '식품': (243, 156, 18),     # 주황색
            '가구': (39, 174, 96),      # 녹색
            '미용': (240, 98, 146),     # 분홍색
            '도서': (149, 165, 166),    # 회색
            '생활용품': (22, 160, 133), # 청록색
            '악세서리': (211, 84, 0),   # 갈색
        }
        
        # 1. 이미지 생성 (배경 이미지 또는 색상)
        if image_path and os.path.exists(image_path):
            # 배경 이미지가 제공된 경우
            print(f"배경 이미지 사용: {image_path}")
            try:
                background = Image.open(image_path).convert('RGBA')
                background = background.resize(size, Image.LANCZOS)
                
                # 배경 이미지를 약간 어둡게 만들어 텍스트가 잘 보이게 함
                enhancer = ImageEnhance.Brightness(background)
                background = enhancer.enhance(0.7)
                
                # 배경 이미지를 약간 흐리게 만들어 텍스트 가독성 높임
                background = background.filter(ImageFilter.GaussianBlur(radius=5))
                
                # 최종 이미지 설정
                image = Image.new('RGBA', size, (0, 0, 0, 0))
                image.paste(background, (0, 0))
                print("배경 이미지 처리 완료")
            except Exception as e:
                print(f"배경 이미지 처리 중 오류: {str(e)}")
                # 오류 발생시 기본 색상 배경으로 대체
                bg_color = category_colors.get(category, (41, 128, 185))
                image = Image.new('RGB', size, bg_color)
                
        else:
            # 배경 이미지가 없는 경우 카테고리별 배경색 사용
            bg_color = category_colors.get(category, (41, 128, 185))  # 기본 파란색
            print(f"배경 색상 사용: {bg_color}")
            
            # 그라데이션 효과 추가
            image = Image.new('RGB', size, bg_color)
            draw = ImageDraw.Draw(image)
            
            # 그라데이션 오버레이 (위에서 아래로)
            for y in range(height):
                # 투명도 계산 (위쪽은 더 투명하게)
                alpha = int(200 * (1 - y / height))
                overlay_color = (255, 255, 255, alpha)
                draw.line([(0, y), (width, y)], fill=overlay_color)
        
        # 최종 그리기 객체 생성
        draw = ImageDraw.Draw(image)
        
        # 2. 제목 텍스트 추가
        # 폰트 로드 시도 - 여러 가능한 폰트 경로를 시도
        font_loaded = False
        title_font = None
        title_font_size = width // 20  # 이미지 폭에 비례한 폰트 크기
        
        # Windows 폰트
        windows_fonts = [
            "C:/Windows/Fonts/NanumGothicBold.ttf",
            "C:/Windows/Fonts/NanumGothic.ttf",
            "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
            "C:/Windows/Fonts/gulim.ttc",   # 굴림
            "C:/Windows/Fonts/Arial.ttf"    # 영문 폰트
        ]
        
        # macOS 폰트
        mac_fonts = [
            "/Library/Fonts/AppleGothic.ttf",
            "/Library/Fonts/Arial.ttf"
        ]
        
        # 모든 폰트 경로 시도
        all_fonts = windows_fonts + mac_fonts
        for font_path in all_fonts:
            try:
                if os.path.exists(font_path):
                    title_font = ImageFont.truetype(font_path, title_font_size)
                    print(f"폰트 로드 성공: {font_path}")
                    font_loaded = True
                    break
            except Exception as e:
                print(f"폰트 로드 실패: {font_path} - {str(e)}")
                continue
        
        # 폰트 로드 실패 시 기본 폰트 사용
        if not font_loaded:
            title_font = ImageFont.load_default()
            title_font_size = 40
            print("기본 폰트 사용")
        
        # 제목 줄바꿈 처리
        max_chars_per_line = 30
        wrapped_title = textwrap.fill(title, width=max_chars_per_line)
        
        # 텍스트 그림자 효과 추가
        shadow_offset = 3
        
        # 중앙 정렬을 위한 텍스트 크기 계산
        bbox = draw.textbbox((0, 0), wrapped_title, font=title_font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
        
        # 그림자 먼저 그리기
        draw.text((text_x + shadow_offset, text_y + shadow_offset), 
                  wrapped_title, font=title_font, fill=(0, 0, 0, 128))
        
        # 실제 텍스트 그리기 (흰색)
        draw.text((text_x, text_y), wrapped_title, font=title_font, fill=(255, 255, 255))
        print("제목 텍스트 추가 완료")
        
        # 3. 카테고리 표시 (있는 경우)
        if category:
            category_font_size = width // 30
            
            # 카테고리 폰트 로드 시도
            category_font = None
            if font_loaded:  # 앞서 제목에서 폰트 로드 성공한 경우 동일 폰트 사용
                try:
                    category_font = ImageFont.truetype(font_path, category_font_size)
                except:
                    category_font = ImageFont.load_default()
            else:
                category_font = ImageFont.load_default()
            
            # 카테고리 텍스트 그리기 (오른쪽 하단)
            category_text = f"#{category}"
            bbox = draw.textbbox((0, 0), category_text, font=category_font)
            cat_text_width = bbox[2] - bbox[0]
            
            cat_x = width - cat_text_width - 20  # 우측 여백
            cat_y = height - category_font_size - 20  # 하단 여백
            
            # 카테고리 배경 (태그 스타일)
            tag_padding = 10
            tag_color = category_colors.get(category, (41, 128, 185))
            draw.rectangle(
                [(cat_x - tag_padding, cat_y - tag_padding), 
                 (cat_x + cat_text_width + tag_padding, cat_y + category_font_size + tag_padding)],
                fill=(255, 255, 255, 200),
                outline=tag_color
            )
            
            # 카테고리 텍스트 (카테고리 색상)
            draw.text((cat_x, cat_y), category_text, font=category_font, fill=tag_color)
            print("카테고리 태그 추가 완료")
        
        # 4. 장식 요소 추가 (모서리 장식)
        corner_size = width // 20
        line_width = 5
        
        # 왼쪽 상단 모서리
        draw.line([(0, corner_size), (0, 0), (corner_size, 0)], 
                  fill=(255, 255, 255), width=line_width)
        
        # 오른쪽 상단 모서리
        draw.line([(width - corner_size, 0), (width, 0), (width, corner_size)], 
                  fill=(255, 255, 255), width=line_width)
        
        # 왼쪽 하단 모서리
        draw.line([(0, height - corner_size), (0, height), (corner_size, height)], 
                  fill=(255, 255, 255), width=line_width)
        
        # 오른쪽 하단 모서리
        draw.line([(width - corner_size, height), (width, height), (width, height - corner_size)], 
                  fill=(255, 255, 255), width=line_width)
        print("장식 요소 추가 완료")
        
        # 5. 결과 저장 또는 반환
        if output_path:
            # 디렉토리 확인 및 생성
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                print(f"디렉토리 생성: {output_dir}")
            
            # PNG 또는 RGBA 형식인 경우 RGB로 변환
            image = image.convert('RGB')
            image.save(output_path, format="JPEG", quality=95)
            print(f"✅ 썸네일 저장 완료: {output_path}")
            
            # 파일 크기 확인
            file_size = os.path.getsize(output_path)
            print(f"   파일 크기: {file_size:,} bytes")
            
            return output_path
        else:
            # BytesIO로 반환
            buffer = BytesIO()
            image = image.convert('RGB')
            image.save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            print(f"✅ 메모리에 썸네일 생성 완료 (크기: {len(buffer.getvalue()):,} bytes)")
            return buffer
        
    except Exception as e:
        print(f"❌ 썸네일 생성 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 오류 시 기본 더미 이미지 반환
        if output_path:
            return create_dummy_image(output_path, text=f"썸네일 생성 실패: {title}")
        else:
            dummy_image = Image.new('RGB', size, (200, 200, 200))
            draw = ImageDraw.Draw(dummy_image)
            font = ImageFont.load_default()
            draw.text((size[0]//2 - 100, size[1]//2), f"썸네일 생성 실패: {title}", font=font, fill=(0, 0, 0))
            
            buffer = BytesIO()
            dummy_image.save(buffer, format="JPEG")
            buffer.seek(0)
            return buffer

def generate_thumbnail_base64(title, category=None, image_path=None, size=(1200, 630)):
    """썸네일을 생성하고 Base64 문자열로 반환하는 함수"""
    try:
        buffer = generate_thumbnail(title, category, image_path, output_path=None, size=size)
        if isinstance(buffer, BytesIO):
            base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/jpeg;base64,{base64_image}"
        else:
            # 파일 경로가 반환된 경우
            with open(buffer, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                return f"data:image/jpeg;base64,{base64_image}"
    except Exception as e:
        print(f"❌ 썸네일 Base64 인코딩 중 오류: {str(e)}")
        return None

def test_thumbnail_generation():
    """썸네일 생성 테스트 함수"""
    print("\n=== 썸네일 생성 테스트 시작 ===\n")
    
    # 출력 디렉토리 생성
    output_dir = os.path.join('coupang_html', 'thumbnails')
    os.makedirs(output_dir, exist_ok=True)
    
    # 테스트 케이스
    test_cases = [
        {
            "title": "프리미엄 노트북 추천 TOP 10",
            "category": "전자제품",
            "filename": "laptop_thumbnail.jpg"
        },
        {
            "title": "여름 필수 아이템 셔츠 모음",
            "category": "의류",
            "filename": "summer_shirt_thumbnail.jpg"
        },
        {
            "title": "요리가 쉬워지는 주방가전 추천",
            "category": "가전",
            "filename": "kitchen_thumbnail.jpg"
        },
        {
            "title": "초보자도 쉽게 시작하는 홈트레이닝 용품",
            "category": "스포츠",
            "filename": "fitness_thumbnail.jpg"
        },
        {
            "title": "맛과 건강을 동시에! 슈퍼푸드 모음",
            "category": "식품",
            "filename": "superfood_thumbnail.jpg"
        }
    ]
    
    # 각 케이스별로 썸네일 생성
    generated_files = []
    for idx, case in enumerate(test_cases, 1):
        try:
            output_path = os.path.join(output_dir, case["filename"])
            
            print(f"\n테스트 케이스 {idx}:")
            print(f"  제목: {case['title']}")
            print(f"  카테고리: {case['category']}")
            
            # 썸네일 생성
            result = generate_thumbnail(
                title=case["title"],
                category=case["category"],
                output_path=output_path
            )
            
            if result:
                print(f"  ✅ 썸네일 생성 성공: {output_path}")
                generated_files.append(output_path)
            else:
                print(f"  ❌ 썸네일 생성 실패")
                
        except Exception as e:
            print(f"  ❌ 테스트 케이스 {idx} 실행 중 오류: {str(e)}")
    
    # 테스트 결과 요약
    print(f"\n=== 썸네일 생성 테스트 결과 ===")
    print(f"총 {len(test_cases)}개 중 {len(generated_files)}개 생성 성공")
    
    if generated_files:
        print("\n생성된 썸네일:")
        for file_path in generated_files:
            print(f"  - {file_path}")
            
        # 생성된 썸네일을 브라우저에서 확인하는 HTML 생성
        try:
            view_html_path = os.path.join(output_dir, 'view_thumbnails.html')
            with open(view_html_path, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>생성된 썸네일 보기</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        h1 { color: #333; }
        .thumbnails { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 20px; }
        .thumbnail-item { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .thumbnail-item img { width: 100%; height: auto; display: block; }
        .thumbnail-info { padding: 15px; }
        .thumbnail-title { font-size: 18px; margin: 0 0 10px 0; }
        .thumbnail-category { display: inline-block; background: #e2e2e2; padding: 5px 10px; border-radius: 4px; font-size: 14px; }
        .debug-info { margin-top: 20px; padding: 10px; background: #eee; border-radius: 4px; font-size: 12px; }
    </style>
</head>
<body>
    <h1>생성된 썸네일</h1>
    <div class="thumbnails">
""")
                
                # 각 썸네일에 대한 항목 추가
                for idx, file_path in enumerate(generated_files):
                    title = test_cases[idx]["title"]
                    category = test_cases[idx]["category"]
                    
                    # 상대 경로 계산 (HTML에서 참조하기 위함)
                    relative_path = os.path.basename(file_path)
                    
                    # 파일 정보 가져오기
                    file_size = os.path.getsize(file_path)
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                    
                    f.write(f"""
        <div class="thumbnail-item">
            <img src="{relative_path}" alt="{title}">
            <div class="thumbnail-info">
                <h2 class="thumbnail-title">{title}</h2>
                <span class="thumbnail-category">{category}</span>
                <div class="debug-info">
                    파일명: {relative_path}<br>
                    크기: {file_size:,} bytes<br>
                    생성시간: {file_time}
                </div>
            </div>
        </div>
""")
                
                f.write("""
    </div>
    <hr>
    <div class="debug-info">
        <h3>디버그 정보</h3>
        <p>이 페이지는 생성된 썸네일을 확인하기 위한 것입니다.</p>
        <p>이미지가 보이지 않는다면 다음 사항을 확인하세요:</p>
        <ul>
            <li>이미지 파일이 실제로 생성되었는지 확인</li>
            <li>이미지 파일 경로가 올바른지 확인</li>
            <li>브라우저 개발자 도구(F12)에서 네트워크 탭을 확인하여 이미지 로딩 오류 확인</li>
        </ul>
    </div>
</body>
</html>""")
            
            print(f"\n✅ 썸네일 뷰어 HTML 생성 완료: {view_html_path}")
            print("  브라우저에서 이 파일을 열어 생성된 썸네일을 확인할 수 있습니다.")
            
            # 생성된 썸네일을 개별적으로 확인하는 HTML 파일 생성
            for idx, file_path in enumerate(generated_files):
                try:
                    title = test_cases[idx]["title"]
                    category = test_cases[idx]["category"]
                    file_name = os.path.basename(file_path)
                    html_name = os.path.splitext(file_name)[0] + ".html"
                    single_html_path = os.path.join(output_dir, html_name)
                    
                    with open(single_html_path, 'w', encoding='utf-8') as f:
                        f.write(f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 썸네일 보기</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; text-align: center; }}
        h1 {{ color: #333; }}
        .thumbnail-container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .thumbnail-container img {{ max-width: 100%; height: auto; display: block; margin: 0 auto; border-radius: 4px; }}
        .debug-info {{ margin-top: 20px; padding: 10px; background: #eee; border-radius: 4px; font-size: 12px; text-align: left; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="thumbnail-container">
        <img src="{file_name}" alt="{title}">
        <p>카테고리: {category}</p>
    </div>
    <div class="debug-info">
        <h3>디버그 정보</h3>
        <p>파일명: {file_name}</p>
        <p>크기: {os.path.getsize(file_path):,} bytes</p>
        <p>생성시간: {datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <p><a href="view_thumbnails.html">모든 썸네일 보기</a></p>
</body>
</html>""")
                    print(f"  ✅ 개별 썸네일 뷰어 생성: {single_html_path}")
                except Exception as e:
                    print(f"  ⚠️ 개별 HTML 생성 실패: {str(e)}")
            
            # 브라우저에서 HTML 파일 열기
            try:
                import webbrowser
                file_url = f"file://{os.path.abspath(view_html_path)}"
                webbrowser.open(file_url)
                print(f"✅ 뷰어를 브라우저에서 열었습니다.")
            except Exception as e:
                print(f"⚠️ 브라우저에서 뷰어 열기 실패: {str(e)}")
                print(f"  수동으로 다음 경로를 브라우저에서 열어주세요: {view_html_path}")
                
        except Exception as e:
            print(f"⚠️ 썸네일 뷰어 HTML 생성 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return len(generated_files) > 0

def generate_product_subset_html(products, title="관련 상품"):
    """상품 서브셋에 대한 HTML을 생성합니다."""
    try:
        if not products:
            return ""
            
        html_content = f"""
        <div class="product-section">
            <h3>{title}</h3>
            <div class="products-grid">
        """
        
        for product in products:
            try:
                # Google 이미지 프록시를 사용하여 이미지 URL 변환
                product_name = product.get('name', '상품')
                product_image_url = product.get('image_url', '')
                product_image = proxy_image_url(product_image_url, product_name)
                
                price_text = f"{product.get('price', 0):,}원"
                product_url = product.get('url', '#')
                
                # 상품 카드 HTML 생성
                product_card = f"""
                <div class="product-card">
                    <div class="product-image">
                        <a href="{product_url}" target="_blank">
                            <img src="{product_image}" alt="{product_name}" loading="lazy">
                        </a>
                    </div>
                    <div class="product-info">
                        <h3 class="product-title">{product_name}</h3>
                        <p class="product-price">{price_text}</p>
                        <a href="{product_url}" class="product-link" target="_blank">상품 보기</a>
                    </div>
                </div>
                """
                html_content += product_card
                
            except Exception as e:
                print(f"   ⚠️ 상품 카드 생성 중 오류: {str(e)}")
                continue
        
        html_content += """
            </div>
        </div>
        """
        
        return html_content
        
    except Exception as e:
        print(f"❌ 상품 서브셋 HTML 생성 중 오류 발생: {str(e)}")
        return ""

def proxy_image_url(url, default_text="상품 이미지"):
    """이미지 URL을 Google 이미지 프록시를 통해 제공
    유효하지 않은 URL인 경우 기본 이미지 생성"""
    try:
        if not url or url.strip() == "":
            # URL이 없으면 로컬에서 기본 이미지 생성
            return create_base64_placeholder_image(default_text)
        
        # Google 이미지 프록시 사용
        return f"https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url={urllib.parse.quote(url)}"
        
    except Exception as e:
        print(f"   ⚠️ 이미지 URL 처리 중 오류: {str(e)}")
        # 오류 발생 시 기본 이미지 반환
        return create_base64_placeholder_image("이미지 없음")

if __name__ == "__main__":
    # 기존 테스트 함수 실행 대신 썸네일 테스트 추가
    if len(sys.argv) > 1 and sys.argv[1] == "thumbnail":
        test_thumbnail_generation()
    else:
        run_test_suite() 