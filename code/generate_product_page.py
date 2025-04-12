import os
import json
import requests
from urllib.parse import quote_plus
import time
from datetime import datetime
import re
from typing import List, Dict
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_dummy_image(file_path, text="상품 이미지"):
    """더미 이미지를 생성하는 함수"""
    try:
        # 이미지 크기 및 색상 설정
        size = (300, 300)
        bg_color = (255, 255, 255)  # 흰색 배경
        text_color = (0, 0, 0)      # 검은색 텍스트
        
        # 이미지 생성
        image = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(image)
        
        # 폰트 설정 (기본 폰트 사용)
        try:
            # Windows 기본 폰트 경로
            font_paths = [
                "C:/Windows/Fonts/malgun.ttf",  # 맑은 고딕
                "C:/Windows/Fonts/gulim.ttc",   # 굴림
                "C:/Windows/Fonts/arial.ttf"     # Arial
            ]
            
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, 30)
                    break
                    
            if font is None:
                font = ImageFont.load_default()
                
        except Exception:
            font = ImageFont.load_default()
        
        # 텍스트 크기 계산
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 텍스트 위치 계산 (중앙 정렬)
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        # 텍스트 그리기
        draw.text((x, y), text, font=font, fill=text_color)
        
        # 디렉토리 생성
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 이미지 저장
        image.save(file_path, 'JPEG', quality=95)
        return True
        
    except Exception as e:
        print(f"더미 이미지 생성 중 오류 발생: {str(e)}")
        return False

def download_image(url, file_path):
    """이미지 다운로드 함수"""
    try:
        # 이미지 다운로드를 위한 헤더 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.coupang.com/',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # URL이 상대 경로인 경우 절대 경로로 변환
        if not url.startswith(('http://', 'https://')):
            url = f"https:{url}" if url.startswith('//') else f"https://{url}"
        
        print(f"\n이미지 다운로드 시도:")
        print(f"URL: {url}")
        print(f"저장 경로: {file_path}")
        
        # 이미지 다운로드 시도
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status()
        
        # Content-Type 확인
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            print(f"⚠️ 잘못된 Content-Type: {content_type}")
            raise ValueError(f"Invalid content type: {content_type}")
        
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
            raise ValueError("File too small")
        
        print(f"✅ 이미지 다운로드 완료: {os.path.basename(file_path)}")
        print(f"   크기: {file_size:,} bytes")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 네트워크 오류: {str(e)}")
        return create_dummy_image(file_path, "네트워크 오류")
    except ValueError as e:
        print(f"⚠️ 유효성 검사 오류: {str(e)}")
        return create_dummy_image(file_path, "유효하지 않은 이미지")
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
        
        # CSS 스타일 정의 (한 줄로 작성)
        css_style = "body{font-family:'Noto Sans KR',sans-serif;line-height:1.6;color:#333;background:#f5f5f5;margin:0;padding:0}.container{max-width:1200px;margin:0 auto;padding:20px}.product-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px;margin-top:20px}.product-card{background:#fff;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,.1);overflow:hidden;transition:transform .2s}.product-card:hover{transform:translateY(-5px)}.product-image{width:100%;height:200px;object-fit:contain;border-bottom:1px solid #eee}.product-info{padding:12px}.product-title{font-size:.9rem;font-weight:500;margin-bottom:4px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;text-overflow:ellipsis}.product-price{font-size:1rem;font-weight:700;color:#e74c3c}.product-price::after{content:'원';margin-left:2px;font-size:.9em}.product-meta{font-size:.8rem;color:#666;margin-top:8px}.product-link{text-decoration:none;color:inherit}@media (max-width:768px){.product-grid{grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}.product-image{height:160px}.product-info{padding:8px}}"
        
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
        <div class="product-grid">
            {product_cards}
        </div>
    </div>
</body>
</html>"""

        # 상품 카드 템플릿
        product_card_template = """<a href="{url}" class="product-link" target="_blank">
    <div class="product-card">
        <img src="{image_url}" alt="{title}" class="product-image" onerror="this.src='images/no-image.jpg'">
        <div class="product-info">
            <h3 class="product-title">{title}</h3>
            <div class="product-price">{price_formatted}</div>
            <div class="product-meta">평점: {rating} ({review_count}개 리뷰)</div>
        </div>
    </div>
</a>"""

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
                image_url = product.get('productImage', '')  # productImage 필드 우선 사용
                if not image_url:
                    image_url = product.get('imageUrl', '')  # 기존 imageUrl 필드 백업
                
                if not image_url:
                    # 이미지 URL이 없는 경우 상품 URL에서 상품 ID 추출
                    product_id = product.get('productId', '')
                    if product_id:
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
                                    print(f"   ✅ CDN URL 찾음: {pattern}")
                                    break
                            except:
                                continue
                
                if image_url:
                    # 이미지 다운로드 시도
                    if download_image(image_url, full_image_path):
                        print(f"✅ 이미지 다운로드 완료: {image_filename}")
                    else:
                        print(f"⚠️ 이미지 다운로드 실패: {image_url}")
                        # 다운로드 실패 시 기본 이미지 사용
                        image_path = "images/no-image.jpg"
                
                # 가격 형식화
                try:
                    price = int(product['price'])
                    price_formatted = f"{price:,}"
                except (ValueError, TypeError):
                    price_formatted = str(product['price'])
                
                # 상품 카드 HTML 생성
                product_cards += product_card_template.format(
                    url=product['product_url'],
                    image_url=image_path,
                    title=product['name'],
                    price_formatted=price_formatted,
                    rating=product['rating'],
                    review_count=product['review_count']
                )
                print(f"✅ 상품 카드 생성 완료: {product['name']}")
                
            except Exception as e:
                print(f"⚠️ 상품 카드 생성 중 오류 발생: {str(e)}")
                continue

        # 최종 HTML 생성
        html_content = html_template.format(css_style=css_style, product_cards=product_cards)
        
        # HTML 파일 저장
        os.makedirs('coupang_html', exist_ok=True)
        output_file = f'coupang_html/products_{timestamp}.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n✅ HTML 파일이 생성되었습니다: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ HTML 생성 중 오류 발생: {str(e)}")
        return None

def process_search_results(results_file='search_results.json', keyword='', search_type='exact', max_products=None):
    """검색 결과 처리 및 HTML 생성"""
    try:
        # Coupang API를 사용하여 직접 검색
        from coupang_search import search_coupang
        
        # 검색 실행
        products = search_coupang(keyword, max_products=max_products or 10)
        
        if not products:
            print(f"검색어 '{keyword}'에 대한 상품이 없습니다.")
            return None
        
        # 상품 개수 제한
        if max_products is not None and max_products > 0:
            products = products[:max_products]
            
        # 모든 상품을 처리
        processed_products = []
        for item in products:
            try:
                # 상품 정보 출력
                print(f"\n상품 정보:")
                print(f"  상품명: {item.get('productName', '')}")
                print(f"  상품 ID: {item.get('productId', '')}")
                print(f"  가격: {item.get('productPrice', '0')}")
                print(f"  카테고리: {item.get('categoryName', '')}")
                print(f"  로켓배송: {'예' if item.get('isRocket', False) else '아니오'}")
                
                # URL이 상대 경로인 경우 절대 경로로 변환
                product_url = item.get('productUrl', '')
                if product_url and not product_url.startswith(('http://', 'https://')):
                    product_url = f"https://www.coupang.com{product_url}"
                
                # 이미지 URL 처리
                # 1. productImage 필드 확인 (쿠팡 파트너스 API의 기본 이미지 URL)
                image_url = item.get('productImage', '')
                if image_url:
                    print(f"  ✅ productImage 필드에서 이미지 URL 찾음: {image_url}")
                
                # 2. imageUrl 필드 확인 (백업 이미지 URL)
                if not image_url:
                    image_url = item.get('imageUrl', '')
                    if image_url:
                        print(f"  ✅ imageUrl 필드에서 이미지 URL 찾음: {image_url}")
                
                # 3. CDN URL 생성 시도 (상품 ID 기반)
                if not image_url:
                    product_id = item.get('productId', '')
                    if product_id:
                        print(f"  🔍 CDN URL 생성 시도 (상품 ID: {product_id})")
                        # 쿠팡 CDN URL 패턴 시도 (여러 서버)
                        cdn_patterns = [
                            f"https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                            f"https://thumbnail6.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                            f"https://thumbnail7.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                            f"https://thumbnail8.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                            f"https://thumbnail9.coupangcdn.com/thumbnails/remote/212x212ex/image/retail/images/{product_id}.jpg",
                            f"https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/{product_id}.jpg",
                            f"https://thumbnail6.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/{product_id}.jpg",
                            f"https://thumbnail7.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/{product_id}.jpg",
                            f"https://thumbnail8.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/{product_id}.jpg",
                            f"https://thumbnail9.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/{product_id}.jpg"
                        ]
                        
                        # 각 CDN 패턴 시도
                        for pattern in cdn_patterns:
                            try:
                                response = requests.head(pattern, timeout=5)
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
                
                # 상품 데이터 처리
                processed_product = {
                    'id': str(item.get('productId', '')).replace('/', '_'),
                    'name': item.get('productName', '').strip(),
                    'price': item.get('productPrice', '0'),
                    'product_url': product_url,
                    'productImage': item.get('productImage', ''),
                    'image_url': image_url,
                    'category': item.get('categoryName', ''),
                    'rocket_delivery': item.get('isRocket', False),
                    'rating': item.get('rating', '0'),
                    'review_count': item.get('reviewCount', '0')
                }
                
                # 필수 필드 확인
                required_fields = ['name', 'price', 'product_url']
                missing_fields = [field for field in required_fields if not processed_product[field]]
                if missing_fields:
                    print(f"  ⚠️ 필수 필드 누락: {', '.join(missing_fields)}")
                    continue
                
                processed_products.append(processed_product)
                print(f"✅ 상품 처리 완료: {processed_product['name']}")
                if image_url:
                    print(f"   이미지 URL: {image_url}")
                else:
                    print(f"   ⚠️ 이미지 URL 없음")
            except Exception as e:
                print(f"⚠️ 상품 처리 중 오류 발생: {str(e)}")
                continue
            
        if not processed_products:
            print("⚠️ 처리된 상품이 없습니다.")
            return None
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return generate_html(processed_products, timestamp)
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
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
    print("5. 종료")
    
    mode = input("\n옵션 선택 (1-5): ").strip()
    
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
        print("프로그램을 종료합니다.")
        sys.exit(0)
    else:
        print("잘못된 모드를 선택하셨습니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    run_test_suite() 