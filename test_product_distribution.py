from generate_product_page import generate_video_html
import os
import webbrowser

def test_product_distribution():
    """상품이 글 사이에 분산되고 이미지가 표시되는지 테스트"""
    print("상품 분산 배치 및 이미지 표시 테스트 시작...")
    
    # 테스트 비디오 정보
    video_info = {
        'title': '비디오 테스트: 상품 분산 배치 및 이미지 표시',
        'description': '이 테스트는 상품이 콘텐츠 내용에 맞게 분산되어 배치되고 이미지가 제대로 표시되는지 확인합니다.',
        'thumbnail_url': 'https://via.placeholder.com/1280x720?text=Test+Thumbnail'
    }
    
    # 테스트 요약 내용 (여러 섹션으로 구성)
    summary = """
    <h2>스마트폰 구매 가이드</h2>
    <p>최신 스마트폰을 구매할 때는 여러 요소를 고려해야 합니다. 디스플레이 크기, 배터리 수명, 카메라 성능, 그리고 가격 등 자신에게 중요한 요소가 무엇인지 파악하는 것이 중요합니다.</p>
    
    <h2>최신 안드로이드 기기 비교</h2>
    <p>삼성 갤럭시 시리즈와 구글 픽셀은 각각 독특한 장점을 제공합니다. 특히 카메라 성능에서 구글 픽셀은 소프트웨어 처리에 강점을 보이고, 갤럭시는 다양한 렌즈 옵션을 제공합니다.</p>
    
    <h2>아이폰 선택 가이드</h2>
    <p>아이폰은 안정적인 성능과 오랜 업데이트 지원으로 많은 사용자들에게 사랑받고 있습니다. 최신 모델과 이전 모델 간의 차이점을 고려하여 최적의 가성비를 찾는 것이 중요합니다.</p>
    
    <h2>노트북 구매 팁</h2>
    <p>노트북을 구매할 때는 CPU, RAM, 저장 공간과 같은 하드웨어 사양뿐만 아니라 키보드 감촉, 화면 품질, 그리고 무게와 같은 실용적인 측면도 고려해야 합니다.</p>
    
    <h2>무선 이어폰 추천</h2>
    <p>무선 이어폰은 이제 많은 사람들의 필수품이 되었습니다. 음질, 배터리 수명, 노이즈 캔슬링 기능을 비교하여 자신에게 맞는 제품을 선택하세요.</p>
    """
    
    # 테스트 상품 목록 (각 섹션과 연관된 상품들)
    products = [
        {
            'name': '삼성 갤럭시 S23 울트라',
            'price': 1350000,
            'url': 'https://www.example.com/galaxy-s23',
            'image_url': 'https://via.placeholder.com/150?text=Galaxy+S23'
        },
        {
            'name': '애플 아이폰 14 프로',
            'price': 1250000,
            'url': 'https://www.example.com/iphone-14',
            'image_url': 'https://via.placeholder.com/150?text=iPhone+14'
        },
        {
            'name': '구글 픽셀 7 프로',
            'price': 1100000,
            'url': 'https://www.example.com/pixel-7',
            'image_url': 'https://via.placeholder.com/150?text=Pixel+7'
        },
        {
            'name': 'LG 그램 17인치 노트북',
            'price': 1800000,
            'url': 'https://www.example.com/lg-gram',
            'image_url': 'https://via.placeholder.com/150?text=LG+Gram'
        },
        {
            'name': '애플 맥북 에어 M2',
            'price': 1550000,
            'url': 'https://www.example.com/macbook-air',
            'image_url': 'https://via.placeholder.com/150?text=MacBook+Air'
        },
        {
            'name': '소니 WF-1000XM4 무선 이어폰',
            'price': 280000,
            'url': 'https://www.example.com/sony-earbuds',
            'image_url': 'https://via.placeholder.com/150?text=Sony+WF1000XM4'
        },
        {
            'name': '애플 에어팟 프로 2',
            'price': 320000,
            'url': 'https://www.example.com/airpods-pro',
            'image_url': 'https://via.placeholder.com/150?text=AirPods+Pro'
        },
    ]
    
    # HTML 생성
    result_html = generate_video_html(video_info, summary, products)
    
    if result_html:
        # 결과 HTML 파일 저장
        output_dir = "test_output"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, "product_distribution_test.html")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result_html)
        
        print(f"✅ HTML 생성 완료: {output_file}")
        
        # 브라우저에서 열기
        try:
            file_url = f"file://{os.path.abspath(output_file)}"
            webbrowser.open(file_url)
            print(f"✅ 브라우저에서 파일을 열었습니다: {file_url}")
        except Exception as e:
            print(f"❌ 브라우저에서 파일 열기 실패: {str(e)}")
    else:
        print("❌ HTML 생성 실패")

if __name__ == "__main__":
    test_product_distribution() 