from generate_product_page import generate_product_html, generate_video_html
import json
import os

def test_html_generation():
    # Test data
    test_products = [
        {
            'name': '테스트 상품',
            'price': 10000,
            'url': 'https://www.example.com',
            'image_url': 'https://thumbnail10.coupangcdn.com/thumbnails/remote/212x212ex/image/vendor_inventory/54a9/d463f8b61edeb1bb160153097f913cea11116830cd217d15fd0007144d0a.jpg'
        },
        {
            'name': '테스트 상품 2',
            'price': 20000,
            'url': 'https://www.example.com',
            'image_url': ''  # Empty URL to test placeholder
        }
    ]
    
    # Test generate_product_html
    print("Testing generate_product_html...")
    product_html = generate_product_html(test_products)
    if product_html:
        print("✅ generate_product_html passed")
        
        # Write to file for inspection
        os.makedirs('test_output', exist_ok=True)
        with open('test_output/product_html.html', 'w', encoding='utf-8') as f:
            f.write('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>' + product_html + '</body></html>')
        print("✅ HTML written to test_output/product_html.html")
    else:
        print("❌ generate_product_html failed")
    
    # Test generate_video_html
    print("\nTesting generate_video_html...")
    video_info = {
        'title': '테스트 비디오',
        'thumbnail_url': 'https://i.ytimg.com/vi/zI06jY9r3OE/hqdefault.jpg',
        'description': '테스트 설명'
    }
    summary = '<p>테스트 요약</p>'
    
    try:
        video_html = generate_video_html(video_info, summary, test_products)
        if video_html:
            print("✅ generate_video_html passed")
            
            # Write to file for inspection
            with open('test_output/video_html.html', 'w', encoding='utf-8') as f:
                f.write(video_html)
            print("✅ HTML written to test_output/video_html.html")
        else:
            print("❌ generate_video_html failed")
    except Exception as e:
        print(f"❌ generate_video_html error: {str(e)}")

if __name__ == "__main__":
    test_html_generation() 