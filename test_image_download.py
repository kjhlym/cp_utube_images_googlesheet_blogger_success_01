from generate_product_page import download_image, create_dummy_image, download_image_to_base64
import os

def test_image_download():
    """이미지 다운로드 테스트"""
    print("\n=== 이미지 다운로드 테스트 시작 ===")
    
    # 테스트 상품 정보
    product_name = "삼성전자 갤럭시 A16 자급제 SM-A165N"
    
    # 테스트용 저장 경로
    test_dir = "test_images"
    os.makedirs(test_dir, exist_ok=True)
    test_path = os.path.join(test_dir, f"{product_name.replace(' ', '_')}.jpg")
    
    print(f"테스트 상품: {product_name}")
    print(f"저장 경로: {test_path}")
    
    # 더미 이미지 생성
    result = create_dummy_image(test_path, product_name)
    
    if result:
        print("\n✅ 테스트 성공")
        if os.path.exists(test_path):
            size = os.path.getsize(test_path)
            print(f"파일 크기: {size:,} bytes")
    else:
        print("\n❌ 테스트 실패")

def test_download():
    # Test with a valid image URL
    test_url = "https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg"
    print("Testing with valid URL...")
    result = download_image_to_base64(test_url)
    if result:
        print("✅ Valid URL test passed")
        print(f"Result starts with: {result[:50]}...")
    else:
        print("❌ Valid URL test failed")
    
    # Test with an empty URL (should generate a placeholder)
    print("\nTesting with empty URL...")
    result = download_image_to_base64("")
    if result:
        print("✅ Empty URL test passed (placeholder generated)")
        print(f"Result starts with: {result[:50]}...")
    else:
        print("❌ Empty URL test failed")

if __name__ == "__main__":
    test_image_download()
    test_download() 