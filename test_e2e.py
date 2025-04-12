import unittest
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from main import ContentProcessor
from keyword_extractor import process_youtube_summary
from coupang_search import search_coupang, CoupangPartnersSearch
from generate_product_page import generate_html

class TestTennisRacketRecommendationSystem(unittest.TestCase):
    def setUp(self):
        """테스트 환경 설정"""
        # .env 파일 로드
        load_dotenv()
        
        # API 키 확인
        self.access_key = os.getenv('COUPANG_PARTNERS_ACCESS_KEY')
        self.secret_key = os.getenv('COUPANG_PARTNERS_SECRET_KEY')
        
        if not self.access_key or not self.secret_key:
            raise ValueError("Coupang Partners API 키가 설정되지 않았습니다.")
        
        self.processor = ContentProcessor()
        self.test_dirs = [
            'html',
            'coupang_html',
            'merged_html',
            'images'
        ]
        
        # 테스트 디렉토리 생성
        for dir_name in self.test_dirs:
            os.makedirs(dir_name, exist_ok=True)
            
        # 테스트용 YouTube 요약 HTML 생성
        self.create_test_youtube_html()

    def create_test_youtube_html(self):
        """테스트용 YouTube 요약 HTML 파일 생성"""
        test_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <div class="section">
                <h2>테니스 라켓 선택 가이드</h2>
                <p>초보자를 위한 테니스 라켓 추천:
                   - 바볼랏 퓨어 드라이브
                   - 윌슨 클래시
                   - 요넥스 이존
                   가격대는 20-30만원 정도가 적당합니다.</p>
            </div>
        </body>
        </html>
        """
        
        with open('html/test_summary.html', 'w', encoding='utf-8') as f:
            f.write(test_html)

    def test_01_directory_setup(self):
        """디렉토리 설정 테스트"""
        print("\n1. 디렉토리 설정 테스트 시작...")
        
        # 모든 필요한 디렉토리가 생성되었는지 확인
        for dir_name in self.test_dirs:
            self.assertTrue(os.path.exists(dir_name))
            print(f"✓ {dir_name} 디렉토리 확인 완료")

    def test_02_keyword_extraction(self):
        """키워드 추출 테스트"""
        print("\n2. 키워드 추출 테스트 시작...")
        
        # YouTube 요약 HTML에서 키워드 추출
        youtube_html = 'html/test_summary.html'
        search_results = process_youtube_summary(youtube_html)
        
        # 검색 결과 검증
        self.assertIsNotNone(search_results)
        self.assertIn('product_searches', search_results)
        self.assertTrue(len(search_results['product_searches']) > 0)
        
        # 특정 키워드가 추출되었는지 확인
        keywords = [search['query'] for search in search_results['product_searches']]
        expected_brands = ['바볼랏', '윌슨', '요넥스']
        
        for brand in expected_brands:
            self.assertTrue(any(brand in keyword for keyword in keywords))
            print(f"✓ '{brand}' 키워드 추출 확인")

    def test_03_coupang_search(self):
        """쿠팡 상품 검색 테스트"""
        print("\n3. 쿠팡 상품 검색 테스트 시작...")
        
        test_query = "테니스 라켓"
        price_range = {"min": 20000, "max": 150000}  # 가격 범위 조정
        
        # 실제 API를 사용한 상품 검색
        products = search_coupang(test_query, max_products=3, price_range=price_range)
        
        # 검색 결과 검증
        self.assertIsNotNone(products)
        self.assertTrue(len(products) > 0)
        print(f"✓ {len(products)}개의 상품 검색 완료")
        
        # 상품 정보 구조 확인
        required_fields = ['name', 'price', 'product_url', 'image_url']
        for product in products:
            for field in required_fields:
                self.assertIn(field, product)
            print(f"✓ 상품 '{product['name'][:30]}...' 정보 구조 확인")
            
            # 가격 범위 확인
            if price_range:
                self.assertTrue(price_range['min'] <= product['price'] <= price_range['max'])
                print(f"✓ 가격 범위 확인 ({price_range['min']:,}원 ~ {price_range['max']:,}원)")

    def test_04_html_generation(self):
        """HTML 생성 테스트"""
        print("\n4. HTML 생성 테스트 시작...")
        
        # 실제 검색 결과로 HTML 생성
        test_query = "테니스 라켓"
        products = search_coupang(test_query, max_products=3)
        
        # HTML 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = generate_html(products, timestamp)
        
        # 생성된 파일 확인
        self.assertTrue(os.path.exists(html_file))
        print(f"✓ HTML 파일 생성 확인: {html_file}")
        
        # HTML 내용 확인
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 필수 요소 확인
        required_elements = [
            'product-card',
            'product-title',
            'product-price',
            'product-meta'
        ]
        
        for element in required_elements:
            self.assertIn(element, content)
            print(f"✓ HTML에서 '{element}' 요소 확인")

    def test_05_full_process(self):
        """전체 프로세스 테스트"""
        print("\n5. 전체 프로세스 통합 테스트 시작...")
        
        # 전체 처리 과정 실행
        result = self.processor.process_content()
        
        # 처리 결과 확인
        self.assertTrue(result)
        print("✓ 전체 프로세스 완료")
        
        # 생성된 파일들 확인
        coupang_html_files = [f for f in os.listdir('coupang_html') if f.endswith('.html')]
        self.assertTrue(len(coupang_html_files) > 0)
        print(f"✓ 생성된 HTML 파일 확인: {len(coupang_html_files)}개")
        
        # 최신 생성된 HTML 파일 내용 확인
        latest_file = max(coupang_html_files, key=lambda x: os.path.getctime(os.path.join('coupang_html', x)))
        with open(os.path.join('coupang_html', latest_file), 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn('product-card', content)
            self.assertIn('product-price', content)
            print(f"✓ 최신 HTML 파일 내용 확인 완료: {latest_file}")

    def tearDown(self):
        """테스트 환경 정리"""
        # 테스트 파일 삭제 (선택적)
        pass

if __name__ == '__main__':
    unittest.main(verbosity=2) 