from generate_product_page import generate_video_html

def test_function():
    try:
        # 간단한 테스트 데이터
        video_info = {
            'title': '테스트 제목',
            'description': '테스트 설명',
            'thumbnail_url': 'https://via.placeholder.com/1280x720'
        }
        
        summary = """
        <h2>첫 번째 섹션</h2>
        <p>이것은 첫 번째 섹션의 내용입니다.</p>
        <h2>두 번째 섹션</h2>
        <p>이것은 두 번째 섹션의 내용입니다.</p>
        """
        
        products = [
            {
                'name': '첫 번째 상품',
                'price': 10000,
                'url': '#',
                'image_url': 'https://via.placeholder.com/150'
            },
            {
                'name': '두 번째 상품',
                'price': 20000,
                'url': '#',
                'image_url': 'https://via.placeholder.com/150'
            }
        ]
        
        # 함수 실행
        result = generate_video_html(video_info, summary, products)
        
        # 결과 확인
        if result:
            print("✅ 함수 실행 성공")
            # 결과의 일부만 출력하여 확인
            print(result[:500] + "...")
        else:
            print("❌ 함수 실행 실패")
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_function() 