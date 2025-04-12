import os
from main import merge_html_contents, summarize_text, search_products_with_keywords, process_youtube_video
import time
from datetime import datetime
from bs4 import BeautifulSoup
import re

def create_test_summary_html():
    """테스트용 요약 HTML 파일 생성"""
    test_summary = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>테니스 라켓 구매 가이드: 초보자를 위한 완벽 정리</title>
</head>
<body>
    <h2>테니스 라켓 구매 가이드: 초보자를 위한 완벽 정리</h2>
    
    ```html
    <div class="section">
        <h3>나에게 맞는 테니스 라켓, 어떻게 골라야 할까요?</h3>
        <p>테니스를 시작할 때 가장 고민되는 것 중 하나가 바로 라켓 선택입니다. 이 가이드에서는 초보자분들이 라켓을 고를 때 반드시 고려해야 할 사항들을 쉽고 명확하게 정리했습니다.</p>
    </div>
    ```

    <div class="section">
        <h3>가장 중요한 것은 '무게'입니다!</h3>
        <p>초보자용, 상급자용 라켓이 따로 구분되어 있는 것은 아닙니다. 가장 먼저 고려해야 할 것은 <strong>무게</strong>입니다.</p>
        <ul>
            <li><strong>여성</strong>: 250g ~ 270g</li>
            <li><strong>남성</strong>: 300g ~ 305g (힘이 없는 남성은 290g ~ 295g)</li>
        </ul>
    </div>

    ```html
    <div class="section">
        <h3>라켓 헤드 사이즈(빵)와 스트링 패턴</h3>
        <p>라켓 헤드 사이즈는 공을 치는 면적을 의미하며, 보통 98~100빵 사이가 일반적입니다.</p>
        <ul>
            <li><strong>16x19 (오픈 패턴)</strong>: 줄 간격이 넓어 스핀이 잘 걸리고 공이 잘 나갑니다. 초보자에게 추천.</li>
            <li><strong>18x20 (댄스 패턴)</strong>: 줄 간격이 촘촘하여 컨트롤이 용이하지만, 공이 덜 나갈 수 있습니다.</li>
        </ul>
    </div>
    ```
</body>
</html>
    """
    
    # 파일 저장
    os.makedirs('coupang_html', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = f'coupang_html/test_summary_{timestamp}.html'
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(test_summary)
        
    print(f"✅ 테스트 요약 HTML 파일 생성 완료: {summary_file}")
    return summary_file

def create_test_products_html():
    """테스트용 상품 HTML 파일 생성"""
    test_products = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>테니스 라켓 상품 목록</title>
    <style>
        .product-card {
            border: 1px solid #ddd;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .product-image {
            max-width: 100%;
            height: auto;
        }
        .product-title {
            font-size: 16px;
            margin: 10px 0;
        }
        .product-price {
            font-weight: bold;
            color: #e53935;
        }
        .product-link {
            display: inline-block;
            margin-top: 10px;
            background-color: #4CAF50;
            color: white;
            padding: 5px 10px;
            text-decoration: none;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <h1>테니스 라켓 추천 상품</h1>
    
    <div class="product-card">
        <img src="https://thumbnail8.coupangcdn.com/thumbnails/remote/230x230ex/image/vendor_inventory/809a/2d3f414108065d586d909f9f24a14af3f825ab37f44e4e38865a8cceeb5c.jpg" alt="테니스 라켓 1" class="product-image">
        <h2 class="product-title">알루미늄 합금 테니스 라켓 PRO-560 685mm</h2>
        <div class="product-price">39,800원</div>
        <a href="https://www.coupang.com/vp/products/7212691247" class="product-link" target="_blank">상품 보기</a>
    </div>
    
    <div class="product-card">
        <img src="https://thumbnail9.coupangcdn.com/thumbnails/remote/230x230ex/image/vendor_inventory/dcc0/ed1ea3e8386b5c0d31fba02e692ca4f7578446f05b4e99ec6c3364c4eae2.jpg" alt="테니스 라켓 2" class="product-image">
        <h2 class="product-title">요넥스 2023 퍼셉트 게임 100 270g 테니스라켓</h2>
        <div class="product-price">222,000원</div>
        <a href="https://www.coupang.com/vp/products/7156268010" class="product-link" target="_blank">상품 보기</a>
    </div>
    
    <div class="product-card">
        <img src="https://thumbnail6.coupangcdn.com/thumbnails/remote/230x230ex/image/vendor_inventory/6a95/8a8d7b7e99a4bba72dcf3a4b0a0d76fe50d2bb182e6ec9bbf9cb3dfaaea2.jpg" alt="테니스 라켓 3" class="product-image">
        <h2 class="product-title">바볼랏 2023 퓨어 에어로 100 라켓</h2>
        <div class="product-price">288,800원</div>
        <a href="https://www.coupang.com/vp/products/7103369198" class="product-link" target="_blank">상품 보기</a>
    </div>
</body>
</html>
    """
    
    # 파일 저장
    os.makedirs('coupang_html', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    products_file = f'coupang_html/test_products_{timestamp}.html'
    
    with open(products_file, 'w', encoding='utf-8') as f:
        f.write(test_products)
        
    print(f"✅ 테스트 상품 HTML 파일 생성 완료: {products_file}")
    return products_file

def create_test_with_thumbnail():
    """YouTube 썸네일이 포함된 테스트 HTML 생성"""
    test_html = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>테니스 라켓 영상 요약</title>
</head>
<body>
    <h1>테니스 라켓 구매 가이드</h1>
    
    <div class="video-info">
        <img src="https://i.ytimg.com/vi/zI06jY9r3OE/hqdefault.jpg" alt="YouTube 영상 썸네일" class="thumbnail">
        <p>출처: YouTube 채널 '테니스 꿀팁'</p>
    </div>
    
    <div class="section">
        <h3>나에게 맞는 테니스 라켓 고르기</h3>
        <p>테니스 라켓을 고를 때는 무게와 헤드 사이즈를 우선적으로 고려해야 합니다.</p>
    </div>
</body>
</html>
    """
    
    # 파일 저장
    os.makedirs('coupang_html', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    thumbnail_file = f'coupang_html/test_thumbnail_{timestamp}.html'
    
    with open(thumbnail_file, 'w', encoding='utf-8') as f:
        f.write(test_html)
        
    print(f"✅ 썸네일 포함 테스트 HTML 파일 생성 완료: {thumbnail_file}")
    return thumbnail_file

def search_real_products():
    """실제 상품 검색 테스트"""
    print("\n실제 상품 검색 테스트...")
    keywords = ["테니스 라켓 270g", "테니스 라켓 300g", "윌슨 테니스 라켓"]
    
    all_products = []
    for keyword in keywords:
        print(f"\n키워드 '{keyword}'로 상품 검색 중...")
        products = search_products_with_keywords(keyword)
        if products:
            all_products.extend(products)
            print(f"✅ {len(products)}개 상품 찾음")
        else:
            print(f"⚠️ '{keyword}'로 상품을 찾을 수 없음")
    
    print(f"\n총 {len(all_products)}개 상품 검색됨")
    return all_products

def remove_markdown_code_blocks(html_content):
    """HTML 내용에서 마크다운 코드 블록 표시(```html ```)를 제거"""
    # ```html로 시작하고 ```로 끝나는 블록에서 마크다운 표시만 제거
    pattern = r'```html\s*(.*?)\s*```'
    
    def replace_markdown(match):
        # 코드 블록 내용만 반환 (마크다운 표시 제거)
        return match.group(1)
    
    # 정규식을 사용하여 마크다운 표시 제거
    cleaned_html = re.sub(pattern, replace_markdown, html_content, flags=re.DOTALL)
    
    # 추가: 남아있을 수 있는 독립적인 ```html 또는 ``` 표시 제거
    cleaned_html = cleaned_html.replace('```html', '')
    cleaned_html = cleaned_html.replace('```', '')
    
    return cleaned_html

def center_youtube_thumbnail(html_content):
    """YouTube 썸네일을 중앙에 배치하도록 CSS 스타일 추가"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 스타일 태그 찾기 또는 생성
    style_tag = soup.find('style')
    if not style_tag:
        style_tag = soup.new_tag('style')
        soup.head.append(style_tag)
    
    # 썸네일 중앙 정렬 CSS 추가
    thumbnail_css = """
    .video-info {
        text-align: center;
        margin: 30px 0;
    }
    .thumbnail {
        display: block;
        max-width: 100%;
        height: auto;
        margin: 0 auto 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        border-radius: 8px;
    }
    """
    
    # 기존 스타일에 추가
    style_tag.string = style_tag.string + thumbnail_css if style_tag.string else thumbnail_css
    
    # 썸네일 이미지 찾기
    thumbnail_img = soup.find('img', class_='thumbnail')
    if thumbnail_img:
        # 이미 클래스가 있으면 'thumbnail' 클래스 추가, 없으면 클래스 설정
        if thumbnail_img.has_attr('class'):
            if 'thumbnail' not in thumbnail_img['class']:
                thumbnail_img['class'].append('thumbnail')
        else:
            thumbnail_img['class'] = ['thumbnail']
        
        # 썸네일 이미지의 부모가 video-info 클래스를 가지고 있는지 확인
        parent = thumbnail_img.parent
        if parent and not parent.has_attr('class') or 'video-info' not in parent['class']:
            # 부모가 div가 아니거나 video-info 클래스가 없으면, 이미지를 div로 감싸기
            wrapper = soup.new_tag('div', attrs={'class': 'video-info'})
            thumbnail_img.wrap(wrapper)
    
    return str(soup)

def custom_merge_html_contents(summary_html, products_html):
    """요약 HTML과 상품 HTML을 병합하는 사용자 정의 함수"""
    try:
        # 1. 요약 HTML에서 마크다운 코드 블록 제거
        with open(summary_html, 'r', encoding='utf-8') as f:
            summary_content = f.read()
        
        # 마크다운 코드 블록 제거
        cleaned_summary = remove_markdown_code_blocks(summary_content)
        
        # 임시 파일에 저장
        cleaned_summary_file = summary_html.replace('.html', '_cleaned.html')
        with open(cleaned_summary_file, 'w', encoding='utf-8') as f:
            f.write(cleaned_summary)
        
        # 2. main.py의 merge_html_contents 함수 호출
        merged_html = merge_html_contents(cleaned_summary_file, products_html)
        
        if not merged_html:
            print("❌ 기본 HTML 병합 실패")
            return None
        
        # 3. 병합된 HTML에서 YouTube 썸네일 중앙 배치
        with open(merged_html, 'r', encoding='utf-8') as f:
            merged_content = f.read()
        
        centered_content = center_youtube_thumbnail(merged_content)
        
        # 4. 최종 HTML 저장 - 고정된 파일명 사용
        output_file = 'coupang_html/merged_html.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(centered_content)
        
        print(f"✅ 개선된 HTML 병합 완료: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ 사용자 정의 HTML 병합 실패: {str(e)}")
        return None

def test_merge_html():
    """HTML 병합 테스트"""
    print("\n===== HTML 병합 테스트 시작 =====")
    
    # 1. 테스트용 HTML 파일 생성
    summary_html = create_test_summary_html()
    products_html = create_test_products_html()
    
    # 2. HTML 병합 실행 (사용자 정의 함수 사용)
    print("\nHTML 병합 중...")
    merged_html = custom_merge_html_contents(summary_html, products_html)
    
    if merged_html:
        print("\n✅ HTML 병합 테스트 성공!")
        print(f"병합된 HTML 파일: {merged_html}")
        
        # 3. 병합된 파일 내용 확인
        try:
            with open(merged_html, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                
            # 요약 섹션 확인
            sections = soup.find_all('div', class_='section')
            print(f"\n요약 섹션 수: {len(sections)}")
            
            # 상품 섹션 확인
            product_section = soup.find('h2', string='추천 상품')
            if product_section:
                print("✅ 상품 섹션 확인 완료")
                
                # 상품 카드 확인
                product_cards = soup.find_all('div', class_='product-card')
                print(f"상품 카드 수: {len(product_cards)}")
            else:
                print("❌ 상품 섹션이 없습니다.")
                
            # 마크다운 코드 블록 확인
            markdown_blocks = re.findall(r'```html|```', str(soup))
            if markdown_blocks:
                print(f"❌ 마크다운 코드 블록이 {len(markdown_blocks)}개 남아있습니다.")
            else:
                print("✅ 마크다운 코드 블록이 모두 제거되었습니다.")
                
        except Exception as e:
            print(f"❌ 병합된 HTML 파일 확인 중 오류 발생: {str(e)}")
    else:
        print("\n❌ HTML 병합 테스트 실패!")
    
    # 4. 썸네일 중앙 배치 테스트
    print("\n===== YouTube 썸네일 중앙 배치 테스트 =====")
    thumbnail_html = create_test_with_thumbnail()
    
    try:
        with open(thumbnail_html, 'r', encoding='utf-8') as f:
            content = f.read()
        
        centered_content = center_youtube_thumbnail(content)
        
        centered_file = thumbnail_html.replace('.html', '_centered.html')
        with open(centered_file, 'w', encoding='utf-8') as f:
            f.write(centered_content)
            
        print(f"✅ 썸네일 중앙 배치 테스트 완료: {centered_file}")
    except Exception as e:
        print(f"❌ 썸네일 중앙 배치 테스트 실패: {str(e)}")
    
    print("\n===== HTML 병합 테스트 종료 =====")

def main():
    """메인 함수"""
    print("\n===== test__merge.py 실행 =====")
    print("HTML 병합 기능 테스트를 시작합니다.")
    
    # HTML 병합 테스트
    test_merge_html()

if __name__ == "__main__":
    main() 