import os
import requests
from datetime import datetime
import hmac
import hashlib
from urllib.parse import quote, quote_plus
from dotenv import load_dotenv
from time import gmtime, strftime
import json
import time
import re

class CoupangPartnersSearch:
    def __init__(self):
        load_dotenv()
        self.access_key = os.getenv('COUPANG_PARTNERS_ACCESS_KEY')
        self.secret_key = os.getenv('COUPANG_PARTNERS_SECRET_KEY')
        self.base_url = "https://api-gateway.coupang.com"
        
    def _generate_signature(self, method, url_path):
        # GMT 시간으로 타임스탬프 생성 (YYMMDDTHHMMSSZ 형식)
        datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
        
        # URL에서 path와 query 분리
        path, *query = url_path.split("?")
        query_string = query[0] if query else ""
        
        # 서명 생성에 사용할 메시지 구성
        message = datetime_gmt + method + path + query_string
        
        # HMAC 서명 생성
        signature = hmac.new(
            bytes(self.secret_key, "utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        
        return datetime_gmt, signature

    def search_products(self, keyword, limit=10, subId=None):
        """
        쿠팡파트너스 상품 검색 API 호출
        :param keyword: 검색어
        :param limit: 검색 결과 개수 (기본값: 10)
        :param subId: 서브 ID (선택사항)
        :return: 검색 결과
        """
        endpoint = "/v2/providers/affiliate_open_api/apis/openapi/products/search"
        
        # URL 파라미터 설정
        params = {
            'keyword': keyword,
            'limit': limit,
            'sortType': 'BEST_SELLING',  # 인기도순 정렬
            'productType': 'BEST'  # 베스트 상품
        }
        if subId:
            params['subId'] = subId
            
        # URL 인코딩
        query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in sorted(params.items())])
        url_path = f"{endpoint}?{query_string}"
        
        # 서명 생성
        datetime_gmt, signature = self._generate_signature('GET', url_path)
        
        # Authorization 헤더 생성
        authorization = f"CEA algorithm=HmacSHA256, access-key={self.access_key}, signed-date={datetime_gmt}, signature={signature}"
        
        # 헤더 설정
        headers = {
            'Authorization': authorization,
            'Content-Type': 'application/json'
        }
        
        # API 요청
        try:
            url = f"{self.base_url}{url_path}"
            response = requests.get(url, headers=headers)
            response_json = response.json()
            
            if response.status_code == 200 and response_json.get('rCode') == '0':
                return response_json
            else:
                error_msg = f"API 요청 실패 (상태 코드: {response.status_code})"
                if response_json:
                    error_msg += f"\n응답: {response_json}"
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"API 요청 중 오류 발생: {str(e)}")

class CoupangAPI:
    def __init__(self):
        load_dotenv()
        self.access_key = os.getenv('COUPANG_PARTNERS_ACCESS_KEY')
        self.secret_key = os.getenv('COUPANG_PARTNERS_SECRET_KEY')
        
        if not self.access_key or not self.secret_key:
            raise ValueError("쿠팡 파트너스 API 키가 설정되지 않았습니다.")
        
        self.client = CoupangPartnersSearch()
    
    def search_products(self, keyword, limit=3):
        """쿠팡 상품 검색 API 호출"""
        try:
            response = self.client.search_products(keyword, limit)
            
            if response and 'data' in response:
                products = response['data']
                return {
                    "data": [
                        {
                            "name": item.get('productName', ''),
                            "price": str(item.get('productPrice', '0')),
                            "productUrl": item.get('productUrl', ''),
                            "imageUrl": item.get('productImage', ''),
                            "rating": str(item.get('rating', '0')),
                            "reviewCount": str(item.get('reviewCount', '0'))
                        }
                        for item in products.get('productData', [])
                    ]
                }
            else:
                print(f"⚠️ API 응답 형식 오류: {response}")
                return None
                
        except Exception as e:
            print(f"⚠️ API 호출 오류: {str(e)}")
            return None

# 전역 API 인스턴스 생성
coupang_api = CoupangAPI()

def search_coupang(keyword, max_products=3, price_range=None):
    """쿠팡 상품 검색 및 필터링"""
    try:
        print(f"\n검색: {keyword}")
        print(f"설정: 최대 {max_products}개 상품, 가격 범위: {price_range}")
        
        # API 응답 받기
        response = coupang_api.search_products(keyword, max_products)
        
        if not response or "data" not in response:
            print(f"⚠️ API 응답 오류: {response}")
            return []
            
        products = []
        for item in response["data"]:
            # 가격 추출 및 변환
            price = int(re.sub(r'[^0-9]', '', item.get("price", "0")))
            
            # 가격 범위 필터링
            if price_range:
                if price < price_range["min"] or price > price_range["max"]:
                    print(f"   가격 범위 제외 ({price:,}원): {item.get('name', '')}")
                    continue
            
            products.append({
                "name": item.get("name", ""),
                "price": price,
                "product_url": item.get("productUrl", ""),
                "image_url": item.get("imageUrl", ""),
                "rating": float(item.get("rating", "0")),
                "review_count": int(item.get("reviewCount", "0"))
            })
            print(f"   ✅ 상품 추가: {item.get('name', '')} ({price:,}원)")
        
        # 리뷰 수와 평점으로 정렬
        products.sort(key=lambda x: (x["review_count"], x["rating"]), reverse=True)
        
        print(f"   총 {len(products)}개 상품 처리 완료")
        return products[:max_products]
        
    except Exception as e:
        print(f"⚠️ 상품 검색 중 오류 발생: {str(e)}")
        return []

if __name__ == "__main__":
    # 환경 변수 확인
    if not os.getenv('COUPANG_PARTNERS_ACCESS_KEY') or not os.getenv('COUPANG_PARTNERS_SECRET_KEY'):
        print("Error: COUPANG_PARTNERS_ACCESS_KEY와 COUPANG_PARTNERS_SECRET_KEY를 .env 파일에 설정해주세요.")
    else:
        keyword = input("검색어를 입력하세요: ")
        results = search_coupang(keyword)
        if results:
            print(f"\n검색 결과: {len(results)}개의 상품을 찾았습니다.") 