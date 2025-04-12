# https: // www.youtube.com/watch?v = QLSr-Kf8wsU
"""
쿠팡 파트너스 상품 검색 및 블로그 포스팅 스크립트

사용법:
1. 명령줄 인수로 실행하는 방법:
   python cp-search_product.py "키워드" [검색할상품개수]
   예: python cp-search_product.py "테니스 라켓" 10

2. 대화형으로 실행하는 방법:
   python cp-search_product.py
   (실행 후 키워드와 상품 개수를 입력)

각 상품의 이미지, 가격, 배송 정보 등을 포함한 블로그 포스트가 생성됩니다.
"""

import hmac
import hashlib
import requests
import json
from time import gmtime, strftime
from datetime import date
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os
import pickle
import time
from dotenv import load_dotenv
import sys
import urllib.parse
import base64
from io import BytesIO
from PIL import Image
import webbrowser

# Load configuration
from config import (
    COUPANG_PARTNERS_ACCESS_KEY,
    COUPANG_PARTNERS_SECRET_KEY,
    COUPANG_PARTNERS_VENDOR_ID,
    IMAGE_SIZE,
    BLOGGER_BLOG_ID,
    WORK_DIR
)
from error_handlers import *

# Blogger API configuration
BLOG_ID = BLOGGER_BLOG_ID
CLIENT_SECRETS_FILE = 'client_secret.json'
SCOPES = ['https://www.googleapis.com/auth/blogger']
TOKEN_FILE_PATH = 'token.pickle'

# 블로그 게시 여부를 결정하는 플래그 (이미지 검증 실패 시 False로 설정)
SHOULD_POST = True

### 위의 라이브러리가 설치 안된 경우 아래의 'pip install ~*~' 명령어를 복사하여 파이참 터미널에서 실행/설치
# hmac, hashlib, time은 파이선 기본 라이브러리로 설치 불필요
# pip install requests google-auth-oauthlib google-api-python-client google-auth python-dotenv pillow

# 이미지 유효성 검증 함수
def validate_image(image_url):
    """
    이미지 URL이 유효한지 확인하는 함수 (간단 체크)
    :param image_url: 확인할 이미지 URL
    :return: 항상 True 반환 (API에서 제공하는 이미지 URL을 신뢰)
    """
    # cp_best_product.py와 동일하게 API 이미지 URL을 신뢰하고 직접 사용
    return True

# 이미지를 Base64로 인코딩하는 함수
def encode_image_to_base64(image_url):
    """
    이미지 URL에서 이미지를 다운로드하여 Base64 문자열로 인코딩
    :param image_url: 이미지 URL
    :return: Base64로 인코딩된 이미지 문자열 또는 None (실패 시)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(image_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            # 이미지 형식 확인
            content_type = response.headers.get('Content-Type', 'image/jpeg')
            if not content_type.startswith('image/'):
                content_type = 'image/jpeg'  # 기본값 설정
                
            # Base64 인코딩
            encoded = base64.b64encode(response.content).decode('utf-8')
            return f"data:{content_type};base64,{encoded}"
        return None
    except Exception as e:
        print(f"Base64 인코딩 중 오류: {str(e)}")
        return None

# 쿠팡 이미지 URL을 CDN URL로 변환하는 함수
def convert_to_cdn_url(image_url, width=200, height=200):
    """
    쿠팡 이미지 URL을 안정적인 CDN URL로 변환
    :param image_url: 원본 쿠팡 이미지 URL
    :param width: 이미지 너비
    :param height: 이미지 높이
    :return: 변환된 CDN URL 또는 원본 URL (변환 실패 시)
    """
    try:
        # 이미 CDN URL인 경우 그대로 반환
        if 'coupangcdn.com' in image_url:
            return image_url
            
        # 파트너스 이미지 URL 패턴 확인
        if 'ads-partners.coupang.com/image1/' in image_url:
            # 제품 ID 또는 이미지 ID 추출 시도
            try:
                # 파트너스 이미지에서 CDN으로 변환할 수 있는 패턴 확인
                # (실제 구현에서는 쿠팡 API 문서 참조 필요)
                return f"https://t1a.coupangcdn.com/thumbnails/remote/{width}x{height}ex/image/retail/images/placeholder-{int(time.time())}.jpg"
            except:
                pass
                
        # 기본 CDN URL 형식으로 변환
        # 이 부분은 쿠팡의 실제 이미지 URL 구조에 맞게 조정 필요
        cdn_base = "https://thumbnail6.coupangcdn.com/thumbnails/remote"
        cdn_url = f"{cdn_base}/{width}x{height}ex/image/product/{int(time.time())}.jpg"
            
        # 최종적으로 안정적인 CDN URL과 기타 방법을 조합한 배열 반환
        return cdn_url
    except Exception as e:
        print(f"CDN URL 변환 오류: {str(e)}")
        return image_url

############################## 파트너스 API 인증 후 자료 입수를 위한 코드 ################################

REQUEST_METHOD = "GET"
DOMAIN = "https://api-gateway.coupang.com"

# 키워드를 명령줄 인수나 사용자 입력으로 받기
if len(sys.argv) > 1:
    # 명령줄 인수로 키워드를 받은 경우
    KEYWORD = sys.argv[1]
    print(f"명령줄 인수로 입력받은 키워드: '{KEYWORD}'")
    
    # 명령줄에서 상품 개수도 지정할 수 있음 (예: python cp-search_product.py "테니스 라켓" 10)
    PRODUCT_LIMIT = 5  # 기본값
    if len(sys.argv) > 2:
        try:
            PRODUCT_LIMIT = int(sys.argv[2])
            if PRODUCT_LIMIT < 1:
                PRODUCT_LIMIT = 5
                print(f"상품 개수는 1 이상이어야 합니다. 기본값 {PRODUCT_LIMIT}개로 설정합니다.")
            elif PRODUCT_LIMIT > 20:
                PRODUCT_LIMIT = 20
                print(f"상품 개수는 최대 20개까지 지정할 수 있습니다. {PRODUCT_LIMIT}개로 제한합니다.")
            else:
                print(f"검색할 상품 개수: {PRODUCT_LIMIT}개")
        except ValueError:
            print(f"상품 개수는 숫자여야 합니다. 기본값 {PRODUCT_LIMIT}개로 설정합니다.")
else:
    # 사용자 입력으로 키워드 받기
    KEYWORD = input("검색할 키워드를 입력하세요: ").strip()
    if not KEYWORD:
        KEYWORD = "테니스 라켓"  # 기본값 설정
        print(f"키워드가 입력되지 않아 기본값 '{KEYWORD}'를 사용합니다.")
    else:
        print(f"입력받은 키워드: '{KEYWORD}'")
        
    # 상품 개수 입력 받기
    PRODUCT_LIMIT = 5  # 기본값
    try:
        limit_input = input("검색할 상품 개수를 입력하세요 (기본값: 5, 최대: 20): ").strip()
        if limit_input:
            PRODUCT_LIMIT = int(limit_input)
            if PRODUCT_LIMIT < 1:
                PRODUCT_LIMIT = 5
                print(f"상품 개수는 1 이상이어야 합니다. 기본값 {PRODUCT_LIMIT}개로 설정합니다.")
            elif PRODUCT_LIMIT > 20:
                PRODUCT_LIMIT = 20
                print(f"상품 개수는 최대 20개까지 지정할 수 있습니다. {PRODUCT_LIMIT}개로 제한합니다.")
            else:
                print(f"검색할 상품 개수: {PRODUCT_LIMIT}개")
    except ValueError:
        print(f"상품 개수는 숫자여야 합니다. 기본값 {PRODUCT_LIMIT}개로 설정합니다.")

### 골드박스 상품 리스트
### 채널 아이디(subid)와 imageSize(200x200)는 원하는 값으로 수정 필요
### 매일 오전 7:30에 업데이트
URL = f"/v2/providers/affiliate_open_api/apis/openapi/v1/products/search?keyword={urllib.parse.quote(KEYWORD)}&limit={PRODUCT_LIMIT}&subid={COUPANG_PARTNERS_VENDOR_ID}&imageSize={IMAGE_SIZE}"

### 파트너스에서 발급 받은 API 키 : 환경 변수에서 로드
ACCESS_KEY = os.getenv('COUPANG_PARTNERS_ACCESS_KEY', COUPANG_PARTNERS_ACCESS_KEY)
SECRET_KEY = os.getenv('OUPANG_PARTNERS_SECRET_KEY', COUPANG_PARTNERS_SECRET_KEY)

### API 서버 인증 후 서명을 반환하는 함수 : 수정할 사항 없음
def generateHmac(method, url, secretKey, accessKey):
    try:
        path, *query = url.split("?")
        datetimeGMT = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
        message = datetimeGMT + method + path + (query[0] if query else "")

        signature = hmac.new(bytes(secretKey, "utf-8"),
                           message.encode("utf-8"),
                           hashlib.sha256).hexdigest()

        return "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(accessKey, datetimeGMT, signature)
    except Exception as e:
        raise AuthenticationError(f"API 인증 중 오류 발생: {str(e)}")

### 위에 정의된 generateHmac 함수로 API를 호출하여 JSON 형식의 자료 입수
try:
    print(f"\n===== API 요청 시작: 키워드 '{KEYWORD}', 상품 개수 {PRODUCT_LIMIT}개 =====")
    
    authorization = generateHmac(REQUEST_METHOD, URL, SECRET_KEY, ACCESS_KEY)
    url = "{}{}".format(DOMAIN, URL)
    
    try:
        response = requests.request(method=REQUEST_METHOD,
                                url=url,
                                headers={
                                    "Authorization": authorization,
                                    "Content-Type": "application/json;charset=UTF-8"
                                }, 
                                timeout=10)  # 타임아웃 10초 설정
    except requests.exceptions.Timeout:
        print("⚠️ API 요청 시간이 초과되었습니다. 네트워크 상태를 확인하세요.")
        raise NetworkError("API 요청 타임아웃")
    except requests.exceptions.ConnectionError:
        print("⚠️ 네트워크 연결 오류가 발생했습니다. 인터넷 연결을 확인하세요.")
        raise NetworkError("네트워크 연결 오류")
    
    if response.status_code != 200:
        error_msg = f"API 요청 실패: 상태 코드 {response.status_code}"
        
        if response.status_code == 401:
            error_msg = "⚠️ 인증 실패: API 키와 시크릿 키를 확인하세요."
        elif response.status_code == 429:
            error_msg = "⚠️ 요청 횟수 제한 초과: 잠시 후 다시 시도하세요."
        elif response.status_code >= 500:
            error_msg = "⚠️ 쿠팡 서버 오류: 잠시 후 다시 시도하세요."
        
        print(error_msg)
        raise NetworkError(error_msg, response.status_code)
        
    print("✅ API 요청 성공!")
    print(f"상태 코드: {response.status_code}")
    
    try:
        response_data = response.json()
        if 'rCode' in response_data and response_data['rCode'] != '0':
            print(f"⚠️ API 응답 코드 오류: {response_data['rCode']} - {response_data.get('rMessage', '알 수 없는 오류')}")
        else:
            print("✅ API 응답 데이터 수신 성공")
    except json.JSONDecodeError:
        print("⚠️ API 응답을 JSON으로 파싱할 수 없습니다.")
        raise DataProcessingError("JSON 데이터 처리 중 오류 발생: 올바른 JSON 형식이 아닙니다.")
    
except requests.exceptions.RequestException as e:
    print(f"⚠️ 네트워크 요청 중 오류 발생: {str(e)}")
    handle_api_error(NetworkError(f"네트워크 요청 중 오류 발생: {str(e)}"))
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"⚠️ JSON 데이터 파싱 오류: {str(e)}")
    handle_api_error(DataProcessingError(f"JSON 데이터 처리 중 오류 발생: {str(e)}"))
    sys.exit(1)
except AuthenticationError as e:
    print(f"⚠️ 인증 오류: {str(e)}")
    handle_api_error(e)
    sys.exit(1)
except NetworkError as e:
    print(f"⚠️ 네트워크 오류: {str(e)}")
    handle_api_error(e)
    sys.exit(1)
except Exception as e:
    print(f"⚠️ 예상치 못한 오류 발생: {str(e)}")
    handle_api_error(e)
    sys.exit(1)
    
print(f"===== API 요청 완료 =====\n")

############################## 입수한 자료를 정리하고 수정하여 html 본문 내용으로 변환하는 코드 ################################

### 입수한 JSON 데이터를 정리하고 data_list에 저장하여 전달하는 함수
def process_data():
    try:
        print(f"\n===== 데이터 처리 시작 =====")
        data_list = []
        
        # 검색 API 응답 구조 확인
        if 'data' in response_data and 'productData' in response_data['data']:
            products = response_data['data']['productData']
            product_count = len(products)
            if product_count == 0:
                print(f"⚠️ 키워드 '{KEYWORD}'에 대한 검색 결과가 없습니다.")
                global SHOULD_POST
                SHOULD_POST = False
                raise DataProcessingError(f"'{KEYWORD}' 키워드에 대한 검색 결과가 없습니다.")
            
            print(f"✅ 총 {product_count}개의 상품 정보를 찾았습니다.")
        else:
            print(f"⚠️ API 응답 구조가 예상과 다릅니다: {list(response_data.keys())}")
            SHOULD_POST = False
            raise DataProcessingError(f"예상과 다른 API 응답 구조: {list(response_data.keys())}")
        
        # 상품 정보 처리 - API에서 받은 이미지 URL을 그대로 사용
        image_errors = 0
        for item in products:
            try:
                # 필수 필드 확인
                required_fields = ['productId', 'productName', 'productPrice', 'productImage', 'productUrl']
                missing_fields = [field for field in required_fields if field not in item]
                
                if missing_fields:
                    print(f"⚠️ 상품에 필수 필드가 누락되었습니다: {missing_fields}")
                    continue
                    
                # 이미지 URL 정규화 - 단순히 상대 경로만 절대 경로로 변환
                if 'productImage' in item:
                    original_image = item.get('productImage', '')
                    
                    if not original_image:
                        print(f"⚠️ 상품 '{item['productName'][:30]}...'에 이미지 URL이 없습니다. 기본 이미지로 대체합니다.")
                        # 이미지 URL이 없는 경우 기본 이미지 URL 설정
                        item['productImage'] = 'https://via.placeholder.com/200x200?text=No+Image'
                        image_errors += 1
                    else:
                        # 이미지 URL 정규화
                        if original_image.startswith('//'):
                            original_image = 'https:' + original_image
                        elif not original_image.startswith(('http://', 'https://')):
                            original_image = 'https://' + original_image
                        
                        # API에서 제공한 URL 그대로 사용 (cp_best_product.py와 동일)
                        item['productImage'] = original_image
                
                data_list.append(item)
                
            except Exception as e:
                print(f"⚠️ 상품 데이터 처리 중 오류 발생: {str(e)}")
                continue
            
        # 모든 상품이 이미지 에러가 있는 경우
        if image_errors == len(products):
            print("⚠️ 모든 상품에 이미지 URL 오류가 있습니다. 포스팅이 불완전할 수 있습니다.")
        
        # 데이터 유효성 검증
        if not data_list:
            print("⚠️ 처리 가능한 상품 데이터가 없습니다.")
            SHOULD_POST = False
            raise DataProcessingError("처리 가능한 상품 데이터가 없습니다.")
            
        print(f"✅ {len(data_list)}개의 상품 정보 처리 완료")
        print(f"===== 데이터 처리 완료 =====\n")
            
        return generate_html(data_list)
    
    except KeyError as e:
        print(f"⚠️ 데이터 처리 중 필수 키를 찾을 수 없습니다: {str(e)}")
        SHOULD_POST = False
        raise DataProcessingError(f"데이터 처리 중 필수 키를 찾을 수 없습니다: {str(e)}")
    except Exception as e:
        print(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {str(e)}")
        SHOULD_POST = False
        raise DataProcessingError(f"데이터 처리 중 오류가 발생했습니다: {str(e)}")

### 오늘 날짜를 가져옵니다.
today = date.today()
### 날짜를 문자열로 변환합니다.
date_string = today.strftime("%Y년 %m월 %d일")


### data_list 자료를 참조하여 html 본문 내용 작성하는 함수
def generate_html(data_list):
    try:
        print(f"\n===== HTML 생성 시작 =====")
        
        for i in range(len(data_list)):   # data_list 자료의 각 항목을 순서 대로 작업
            data_list[i]['productName'] = data_list[i]['productName'].replace(",", "")   ### 각 항목의 ,기호를 제거합니다.

        ### html 문서 내용을 f"""  """ 안에 작성하는 코드입니다.

        ### html 도입부 내용
        html_content = f"""
        <style>
        .cup-list {{
            border: 1px solid #e0e0e0;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .product-name {{
            font-size: 18px;
            margin-bottom: 15px;
        }}
        .product-name a {{
            color: #0066cc;
            text-decoration: none;
        }}
        .cup-img {{
            text-align: center;
            margin: 15px 0;
        }}
        .cup-img img {{
            max-width: 200px;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            object-fit: contain;
        }}
        .product-price {{
            font-size: 16px;
            color: #e94d4d;
            font-weight: bold;
            margin: 10px 0;
        }}
        .delivery-info {{
            color: #666;
            font-size: 14px;
        }}
        </style>

        <h3>쿠팡 검색결과: '{KEYWORD}'</h3>
        <p>쿠팡에서 '{KEYWORD}' 키워드로 검색한 상품 결과입니다.</p>
        <h3>{date_string} 기준 '{KEYWORD}' 검색 상품 리스트</h3>
        <p>검색 결과에서 인기 상품 {len(data_list)}개를 소개합니다.</p>
        <p style="color: #666; font-size: 12px;">* 이 포스팅은 파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있습니다.</p>
        <hr/>
        """

        ### 검색된 상품 리스트를 데이터 목록의 개수만큼 처리
        for i in range(len(data_list)):
            try:
                product_name = data_list[i]['productName']
                product_url = data_list[i]['productUrl']
                
                # API에서 제공한 이미지 URL을 그대로 가져옴
                original_image = data_list[i]['productImage']
                
                # 이미지 URL 유효성 검사
                if not original_image or original_image == 'https://via.placeholder.com/200x200?text=No+Image':
                    print(f"⚠️ 상품 {i+1}: 이미지 URL이 누락되었거나 무효합니다. 기본 이미지를 사용합니다.")
                
                # Base64 인코딩 시도 (Blogger가 허용하는 경우만)
                base64_image = None
                # base64_image = encode_image_to_base64(original_image)
                
                print(f"✅ 상품 {i+1} 정보 준비 완료:")
                print(f"  - 이름: {product_name[:50]}..." if len(product_name) > 50 else f"  - 이름: {product_name}")
                print(f"  - 이미지 URL: {original_image[:50]}..." if len(original_image) > 50 else f"  - 이미지 URL: {original_image}")
                print("-" * 50)
                
                # 이미지를 표시하기 위한 다양한 접근 방식
                if base64_image:
                    # Base64로 인코딩된 이미지 사용
                    img_tag = f"""<img src="{base64_image}" 
                        alt="{product_name}" 
                        title="{product_name}"
                        width="200"
                        height="auto"
                        loading="lazy" />"""
                else:
                    # 다중 프록시 접근 방식: noop 속성을 사용하여 Blogger가 자체 프록시 서비스를 사용하도록 유도
                    img_tag = f"""<img src="{original_image}" 
                        alt="{product_name}" 
                        title="{product_name}"
                        width="200"
                        height="auto"
                        noop="true"
                        loading="lazy"
                        onerror="this.onerror=null; this.src='https://wsrv.nl/?url={urllib.parse.quote(original_image)}&n=0'; this.onerror=function(){{this.src='https://via.placeholder.com/200x200?text=No+Image';}}" />"""
                
                ### 상품 리스트 추가 - Blogger의 이미지 처리 방식에 최적화
                html_content += f"""
                <div class="cup-list">
                    <div class="product-name">
                        <h3>🔍 검색결과 [{i + 1}]</h3>
                        <a href="{product_url}" target="_blank" rel="nofollow">➡️ {product_name}</a>
                    </div>
                    <div class="cup-img">
                        <a href="{product_url}" target="_blank" rel="nofollow">
                            {img_tag}
                        </a>
                    </div>
                    <div class="product-price">
                        💰 판매가: {format(data_list[i]['productPrice'], ',')}원
                    </div>
                    <div class="delivery-info">
                        🚚 배송: {'🚀 로켓배송' if data_list[i]['isRocket'] else '일반배송'} 
                        | {'✨ 무료배송' if data_list[i]['isFreeShipping'] else '유료배송'}
                    </div>
                </div>
                """
            except Exception as e:
                print(f"⚠️ 상품 {i+1} HTML 생성 중 오류: {str(e)}")
                continue

        ### 마무리 내용을 += 기호 사용하여 추가합니다.
        html_content += f"""
        <hr/>
        <h3>마무리</h3>
        <p>지금까지 {date_string} 기준 '{KEYWORD}' 검색 결과 상품 리스트 총 {len(data_list)}개를 공유하였습니다.</p>
        <p>구매하시기 전에 상품의 구체적인 정보와 최신 가격을 확인하시기 바랍니다.</p>
        <p>이 포스팅이 여러분의 현명한 쇼핑에 도움이 되었길 바랍니다! 😊</p>
        <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
        """

        print(f"✅ HTML 생성 완료")
        print(f"===== HTML 생성 완료 =====\n")

        return html_content, f"검색결과_{KEYWORD}"   # 정리된 전체 html 본문 내용과 카테고리명을 반환합니다.
    except Exception as e:
        print(f"⚠️ HTML 생성 중 오류: {str(e)}")
        return f"<p>HTML 생성 중 오류가 발생했습니다: {str(e)}</p>", f"검색결과_{KEYWORD}"



### 위에 정의된 process_data() 함수를 사용한 후 바로 이어서
### generate_html() 함수를 사용하여 html 본문 내용을 goldbox_data에 저장하는 코드

goldbox_data, categoryName = process_data()
print(goldbox_data)   # 저장된 본문 내용 html 내용을 확인하기 위해 출력하는 코드

content = goldbox_data  # 구글 블로거 발행 글의 본문 변수 content에 모두 저장



############################## html 본문 내용을 블로거 API를 이용하여 포스트를 게시하는 코드입니다. ################################

blogger_id = BLOG_ID  # 본인의 구글 블로그 ID, 숫자
work_dir = WORK_DIR  # 작업 디렉토리 경로

### 구글 OAuth 클라이언트 시크릿 파일: JSON
client_secrets_file = CLIENT_SECRETS_FILE

scopes = SCOPES

### 매번 인증하지 않고 일정 기간 동안 토큰 파일 auto_token.pickle을 생성하여 자동 검증
token_file_path = TOKEN_FILE_PATH

### 토큰 파일로 인증하는 코드
creds = None
if os.path.exists(token_file_path):
    with open(token_file_path, 'rb') as token:
        creds = pickle.load(token)
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        # run_local_server will automatically prompt for authorization in the browser
        # and store the resulting credentials.
        creds = flow.run_local_server(port=0)

    with open(token_file_path, 'wb') as token:
         pickle.dump(creds, token)  # Save the credentials object to a file.

### 인증 결과 출력
print("Credentials:", creds)

### 토큰으로 구글 블로거 서비스에 연결
blogger_service = build("blogger", "v3", credentials=creds)


### html 본문 내용에 글 제목(title)과 라벨(labels)을 포함하여 구글 블로그 글 발행하는 코드

# 이 부분을 HTML 파일 저장 코드로 변경
# 로컬 merge/coupang_html 디렉토리 및 프로젝트 루트 merge/coupang_html 디렉토리 확인 및 생성
if not os.path.exists('merge'):
    os.makedirs('merge')
    print(f"✅ 'merge' 폴더를 생성했습니다.")

if not os.path.exists('merge/coupang_html'):
    os.makedirs('merge/coupang_html')
    print(f"✅ 'merge/coupang_html' 폴더를 생성했습니다.")

# 프로젝트 루트의 merge/coupang_html 경로 지정 (상대경로로 상위 디렉토리 접근)
root_merge_dir = os.path.join('..', 'merge')
root_coupang_html_dir = os.path.join(root_merge_dir, 'coupang_html')

# 프로젝트 루트에 디렉토리가 없으면 생성
if not os.path.exists(root_merge_dir):
    try:
        os.makedirs(root_merge_dir)
        print(f"✅ 프로젝트 루트에 'merge' 폴더를 생성했습니다.")
    except Exception as e:
        print(f"⚠️ 프로젝트 루트에 'merge' 폴더 생성 실패: {str(e)}")

if not os.path.exists(root_coupang_html_dir):
    try:
        os.makedirs(root_coupang_html_dir)
        print(f"✅ 프로젝트 루트에 'merge/coupang_html' 폴더를 생성했습니다.")
    except Exception as e:
        print(f"⚠️ 프로젝트 루트에 'merge/coupang_html' 폴더 생성 실패: {str(e)}")

# HTML 파일명 생성
timestamp = time.strftime('%Y%m%d_%H%M%S')
file_name = f"coupang_search_{KEYWORD.replace(' ', '_')}_{timestamp}.html"
html_filename = os.path.join('merge', 'coupang_html', file_name)
root_html_filename = os.path.join(root_coupang_html_dir, file_name)

# HTML 파일 작성
try:
    print(f"\n===== HTML 파일 저장 시작 =====")
    
    # 이미지 검증 결과에 따라 저장 여부 결정
    if not SHOULD_POST:
        print("⚠️ 경고: 데이터 처리 중 오류가 발생하여 HTML 파일 저장을 중단합니다.")
        print("🔍 가능한 원인:")
        print("  - 이미지 URL이 유효하지 않음")
        print("  - 검색 결과가 없음")
        print("  - API 응답 구조가 변경됨")
        print("\n💡 해결 방법:")
        print("  - 다른 검색어로 시도해보세요.")
        print("  - API 키와 시크릿 키가 올바른지 확인하세요.")
        print("  - 네트워크 연결을 확인하세요.")
        sys.exit(0)
    
    # HTML 전체 문서 구조 생성
    full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{KEYWORD} 검색결과 {date_string}</title>
</head>
<body>
{content}
</body>
</html>
"""
    
    # 로컬 디렉토리에 HTML 파일 저장
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ HTML 파일 저장 성공!")
    print(f"📝 로컬 파일명: {html_filename}")
    print(f"📂 로컬 저장 위치: {os.path.abspath(html_filename)}")
    
    # 프로젝트 루트 디렉토리에도 파일 복사 시도
    try:
        with open(root_html_filename, 'w', encoding='utf-8') as f:
            f.write(full_html)
        print(f"✅ HTML 파일을 프로젝트 루트에도 복사했습니다.")
        print(f"📝 루트 파일명: {root_html_filename}")
        print(f"📂 루트 저장 위치: {os.path.abspath(root_html_filename)}")
    except Exception as e:
        print(f"⚠️ 프로젝트 루트에 파일 복사 실패: {str(e)}")
        print(f"💡 로컬에 생성된 파일을 사용해주세요: {os.path.abspath(html_filename)}")
    
    print(f"\n===== HTML 파일 저장 완료 =====")
    
    # 최종 실행 요약 출력
    print(f"\n===== 실행 요약 =====")
    print(f"✅ 검색 키워드: '{KEYWORD}'")
    print(f"✅ 검색된 상품 수: {PRODUCT_LIMIT}개")
    print(f"✅ HTML 파일: {os.path.basename(html_filename)}")
    print(f"✅ 작업 완료 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"===== 성공적으로 완료되었습니다 =====\n")
    
    # 생성된 HTML 파일 웹 브라우저에서 열기 (선택 사항)
    try:
        webbrowser.open('file://' + os.path.abspath(html_filename))
        print(f"✅ 생성된 HTML 파일을 웹 브라우저에서 열었습니다.")
    except Exception as e:
        print(f"⚠️ 파일을 브라우저에서 열지 못했습니다: {str(e)}")
        print(f"💡 다음 경로에서 파일을 수동으로 열어주세요: {os.path.abspath(html_filename)}")
    
except Exception as e:
    print(f"⚠️ HTML 파일 저장 중 오류 발생: {str(e)}")
    sys.exit(1)