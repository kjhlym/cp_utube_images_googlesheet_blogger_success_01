import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

def merge_html_files(youtube_html_path, coupang_html_paths):
    """YouTube HTML과 여러 개의 쿠팡 상품 HTML을 병합하는 함수"""
    try:
        # YouTube HTML 읽기 및 파싱
        with open(youtube_html_path, 'r', encoding='utf-8') as f:
            youtube_content = f.read()
        
        # BeautifulSoup으로 파싱
        soup = BeautifulSoup(youtube_content, 'html.parser')
        
        # 중첩 HTML 구조 확인 및 수정
        summary_div = soup.select_one('div.summary')
        if summary_div:
            nested_html = summary_div.find('html')
            if nested_html:
                print("⚠️ 중첩된 HTML 구조가 감지되었습니다. 수정합니다.")
                # 중첩된 body 내용만 추출
                nested_body = nested_html.find('body')
                if nested_body:
                    # body 내용만 추출해서 div.summary 내에 배치
                    new_content = BeautifulSoup(nested_body.decode_contents(), 'html.parser')
                    summary_div.clear()
                    for tag in new_content:
                        summary_div.append(tag)
                else:
                    # body가 없는 경우, html과 head 태그 제거
                    for tag in summary_div.find_all(['html', 'head', 'doctype']):
                        tag.unwrap()  # 태그 제거하고 내용만 유지
        
        # 타임스탬프 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        merged_images_dir = f'merged_html/images_{timestamp}'
        os.makedirs(merged_images_dir, exist_ok=True)
        
        # 이미지 디렉토리 복사
        source_images_dir = 'coupang_html/images'
        if os.path.exists(source_images_dir):
            for image in os.listdir(source_images_dir):
                source_path = os.path.join(source_images_dir, image)
                target_path = os.path.join(merged_images_dir, image)
                if os.path.isfile(source_path):
                    import shutil
                    shutil.copy2(source_path, target_path)
            print(f"✅ 이미지 파일 복사 완료: {merged_images_dir}")
        
        # 모든 쿠팡 상품 HTML의 상품 섹션 추출
        all_products = []
        for product_html_path in coupang_html_paths:
            try:
                with open(product_html_path, 'r', encoding='utf-8') as f:
                    product_content = f.read()
                
                # BeautifulSoup으로 파싱
                product_soup = BeautifulSoup(product_content, 'html.parser')
                
                # 상품 그리드 추출 (container > product-grid)
                product_grid = product_soup.select_one('.container .product-grid')
                if product_grid:
                    # 이미지 경로 업데이트
                    for img in product_grid.select('img'):
                        if img.get('src') and img['src'].startswith('images/'):
                            img['src'] = img['src'].replace('images/', f'images_{timestamp}/')
                    
                    all_products.append(str(product_grid))
                else:
                    print(f"⚠️ {os.path.basename(product_html_path)}에서 상품 그리드를 찾을 수 없습니다.")
            except Exception as e:
                print(f"⚠️ {os.path.basename(product_html_path)} 파일 처리 중 오류 발생: {str(e)}")
                continue
        
        if not all_products:
            print("❌ 처리할 수 있는 상품이 없습니다.")
            return None
            
        print(f"✅ {len(all_products)}개의 상품 그리드 추출 완료")
        
        if all_products:
            # 섹션들 찾기
            sections = soup.select('.section')
            
            # 상품 섹션들을 분배할 위치 계산
            num_sections = len(sections)
            num_products = len(all_products)
            
            if num_sections > 0:
                # 섹션이 있는 경우, 섹션들 사이에 상품을 분배
                for i, product_html in enumerate(all_products):
                    # 상품을 삽입할 위치 결정 (균등 분배)
                    section_idx = min(i * num_sections // num_products, num_sections - 1)
                    section = sections[section_idx]
                    
                    # 새로운 상품 섹션 생성
                    product_section = BeautifulSoup(f'''
                    <div class="section product-section">
                        <h2>추천 상품</h2>
                        <div class="product-container">{product_html}</div>
                    </div>
                    ''', 'html.parser')
                    
                    # 선택한 섹션 뒤에 상품 섹션 삽입
                    section.insert_after(product_section)
            else:
                # 섹션이 없는 경우, body 끝에 상품 추가
                body = soup.body or soup
                for product_html in all_products:
                    product_section = BeautifulSoup(f'''
                    <div class="section product-section">
                        <h2>추천 상품</h2>
                        <div class="product-container">{product_html}</div>
                    </div>
                    ''', 'html.parser')
                    body.append(product_section)
            
            # 스타일 추가
            style_addition = '''
                .product-section {
                    margin: 1.5em auto;
                    padding: 1.5em;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    max-width: 85%;
                }
                .product-section h2 {
                    color: #2c3e50;
                    margin-bottom: 1em;
                    text-align: center;
                    font-size: 1.3em;
                }
                .product-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
                    gap: 12px;
                    padding: 0.8em;
                }
                .product-card {
                    background: white;
                    border-radius: 6px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    transition: transform 0.2s ease;
                    width: 100%;
                    margin: 0;
                }
                .product-image-container {
                    position: relative;
                    padding-top: 100%;
                    overflow: hidden;
                    background: #f8f9fa;
                }
                .product-image {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                    padding: 4px;
                }
                .product-info {
                    padding: 6px;
                    flex-grow: 1;
                    display: flex;
                    flex-direction: column;
                }
                .product-title {
                    font-size: 0.6rem;
                    line-height: 1.1;
                    margin-bottom: 2px;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                    color: #333;
                }
                .product-price {
                    font-size: 0.65rem;
                    font-weight: bold;
                    color: #e74c3c;
                    margin-top: auto;
                }
                .product-meta {
                    display: none;
                }
                
                /* 반응형 디자인 */
                @media (max-width: 1024px) {
                    .product-section {
                        max-width: 90%;
                        padding: 1.2em;
                    }
                    
                    .product-grid {
                        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
                        gap: 10px;
                    }
                }
                
                @media (max-width: 768px) {
                    .product-section {
                        max-width: 95%;
                        padding: 1em;
                    }
                    
                    .product-grid {
                        grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
                        gap: 8px;
                    }
                    
                    .product-title {
                        font-size: 0.55rem;
                    }
                    
                    .product-price {
                        font-size: 0.6rem;
                    }
                }
            '''
            
            # 스타일 태그 찾거나 추가
            style_tag = soup.find('style')
            if style_tag:
                style_tag.string = style_tag.string + style_addition
            else:
                head = soup.head
                if head:
                    new_style = soup.new_tag('style')
                    new_style.string = style_addition
                    head.append(new_style)
            
            # 병합된 파일 저장
            youtube_filename = os.path.basename(youtube_html_path)
            keyword = youtube_filename.split('_')[0] if '_' in youtube_filename else youtube_filename.split('.')[0]
            
            # merged_html 폴더에 저장
            os.makedirs('merged_html', exist_ok=True)
            output_path = f'merged_html/merged_{keyword}_{timestamp}.html'
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            
            # 추가로 posting 폴더에 복사본 저장 (블로거에 바로 업로드하기 위함)
            os.makedirs('posting', exist_ok=True)
            posting_path = f'posting/merged_{keyword}_{timestamp}.html'
            
            import shutil
            shutil.copy2(output_path, posting_path)
            
            print(f"HTML 파일 병합 완료: {output_path}")
            print(f"복사본 저장 완료: {posting_path}")
            return output_path
            
    except Exception as e:
        print(f"HTML 병합 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """메인 함수"""
    print("=== HTML 파일 병합 도구 ===")
    
    # 각 디렉토리 확인 및 생성
    necessary_dirs = ['utube_html', 'utube_mtml', 'coupang_html', 'merged_html', 'posting']
    for directory in necessary_dirs:
        if not os.path.exists(directory):
            print(f"'{directory}' 디렉토리가 없습니다. 생성합니다...")
            os.makedirs(directory, exist_ok=True)
    
    # YouTube HTML 파일 목록 표시 (utube_mtml 폴더 사용)
    youtube_files = [f for f in os.listdir('utube_mtml') if f.endswith('.html')]
    if not youtube_files:
        youtube_files = [f for f in os.listdir('utube_html') if f.endswith('.html')]
        youtube_dir = 'utube_html'
        if not youtube_files:
            print("'utube_mtml' 또는 'utube_html' 디렉토리에 HTML 파일이 없습니다.")
            return
        print("'utube_mtml' 디렉토리에 HTML 파일이 없어 'utube_html' 디렉토리의 파일을 사용합니다.")
    else:
        youtube_dir = 'utube_mtml'
        print("'utube_mtml' 디렉토리에서 YouTube HTML 파일을 가져옵니다.")
    
    print("\nYouTube HTML 파일 목록:")
    for i, file in enumerate(youtube_files, 1):
        print(f"{i}. {file}")
    
    # 쿠팡 HTML 파일 목록 표시
    coupang_files = [f for f in os.listdir('coupang_html') if f.endswith('.html')]
    if not coupang_files:
        print("\n'coupang_html' 디렉토리에 HTML 파일이 없습니다.")
        return
    
    print("\n쿠팡 상품 HTML 파일 목록:")
    for i, file in enumerate(coupang_files, 1):
        print(f"{i}. {file}")
    
    # YouTube 파일 선택
    while True:
        try:
            youtube_idx = int(input("\nYouTube HTML 파일 번호를 선택하세요: ")) - 1
            if 0 <= youtube_idx < len(youtube_files):
                break
            print("올바른 번호를 입력하세요.")
        except ValueError:
            print("숫자를 입력하세요.")
    
    # 여러 쿠팡 파일 선택 (쉼표로 구분)
    while True:
        try:
            numbers = input("\n쿠팡 HTML 파일 번호들을 쉼표로 구분하여 입력하세요 (예: 1,2,5): ").strip()
            selected_indices = [int(num.strip()) - 1 for num in numbers.split(',')]
            
            # 유효성 검사
            invalid_indices = [idx + 1 for idx in selected_indices if idx < 0 or idx >= len(coupang_files)]
            if invalid_indices:
                print(f"잘못된 번호가 있습니다: {invalid_indices}")
                continue
            
            selected_coupang_files = [os.path.join('coupang_html', coupang_files[idx]) for idx in selected_indices]
            
            if not selected_coupang_files:
                print("최소 하나의 파일을 선택해야 합니다.")
                continue
                
            print("\n선택된 쿠팡 파일:")
            for file in selected_coupang_files:
                print(f"- {os.path.basename(file)}")
                
            confirm = input("\n이대로 진행하시겠습니까? (y/n): ").lower()
            if confirm == 'y':
                break
                
        except ValueError:
            print("올바른 형식으로 입력하세요 (예: 1,2,5)")
        except Exception as e:
            print(f"오류가 발생했습니다: {str(e)}")
    
    # 파일 병합
    youtube_path = os.path.join(youtube_dir, youtube_files[youtube_idx])
    merged_path = merge_html_files(youtube_path, selected_coupang_files)
    
    if merged_path:
        print("\n병합이 완료되었습니다!")
        print(f"생성된 파일: {merged_path}")
        print(f"\n이 파일은 merged_html 디렉토리에 저장되었습니다.")
        print(f"동일한 파일이 posting 디렉토리에도 복사되었습니다.")
        print(f"html2blogger.py를 실행하여 이 파일을 블로거에 포스팅할 수 있습니다.")
        
        # 블로거에 자동으로 포스팅할지 물어보기
        post_now = input("\n지금 바로 블로거에 포스팅하시겠습니까? (y/n): ").lower()
        if post_now == 'y':
            import subprocess
            print("\n블로거 포스팅 도구를 실행합니다...")
            # posting 폴더의 복사본 사용
            posting_path = merged_path.replace('merged_html', 'posting')
            subprocess.run(['python', 'html2blogger.py', '--posting', posting_path])
    else:
        print("\n병합 중 오류가 발생했습니다.")

if __name__ == '__main__':
    main() 