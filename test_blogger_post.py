import os
from html2blogger import get_blogger_service
from bs4 import BeautifulSoup
import base64
import time

def list_merged_html_files():
    """merged_html 폴더의 HTML 파일 목록을 표시합니다."""
    merged_dir = 'merged_html'
    if not os.path.exists(merged_dir):
        print("❌ merged_html 디렉토리가 존재하지 않습니다.")
        return None
        
    html_files = [f for f in os.listdir(merged_dir) if f.endswith('.html')]
    if not html_files:
        print("❌ HTML 파일을 찾을 수 없습니다.")
        return None
        
    print("\n=== 병합된 HTML 파일 목록 ===")
    for i, file in enumerate(html_files, 1):
        print(f"{i}. {file}")
    
    return html_files

def fix_image_paths(html_content, base_dir):
    """HTML 내용의 이미지를 base64로 인코딩하여 직접 포함시킵니다."""
    soup = BeautifulSoup(html_content, 'html.parser')
    total_images = len(soup.find_all('img'))
    processed_images = 0
    
    print(f"\n총 {total_images}개의 이미지를 처리합니다...\n")
    
    # 모든 이미지 태그 찾기
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src:
            # 상대 경로인 경우
            if src.startswith(('images/', 'images_', 'merged_html/images_')):
                try:
                    # 이미지 파일 경로 구성
                    if src.startswith('merged_html/'):
                        full_path = os.path.join(base_dir, src)
                    else:
                        img_dir = os.path.dirname(src)
                        img_name = os.path.basename(src)
                        if img_dir.startswith('images_'):
                            full_path = os.path.join(base_dir, 'merged_html', src)
                        else:
                            full_path = os.path.join(base_dir, 'coupang_html', src)
                    
                    print(f"\n[이미지 {processed_images + 1}/{total_images}]")
                    print(f"처리 중인 이미지: {os.path.basename(full_path)}")
                    print(f"전체 경로: {full_path}")
                    
                    # 파일이 존재하는지 확인
                    if os.path.exists(full_path):
                        # 이미지를 base64로 인코딩
                        with open(full_path, 'rb') as f:
                            img_data = f.read()
                            
                        # 파일 확장자 확인 및 MIME 타입 설정
                        file_ext = os.path.splitext(full_path)[1].lower()
                        if file_ext in ['.jpg', '.jpeg']:
                            mime_type = 'image/jpeg'
                        elif file_ext == '.png':
                            mime_type = 'image/png'
                        elif file_ext == '.gif':
                            mime_type = 'image/gif'
                        elif file_ext == '.webp':
                            mime_type = 'image/webp'
                        else:
                            mime_type = 'image/jpeg'  # 기본값
                            
                        # base64 인코딩
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        img['src'] = f'data:{mime_type};base64,{img_base64}'
                        
                        # 인코딩된 데이터 미리보기 출력
                        print(f"MIME 타입: {mime_type}")
                        print(f"원본 파일 크기: {len(img_data):,} bytes")
                        print(f"Base64 길이: {len(img_base64):,} characters")
                        print(f"Base64 미리보기: {img_base64[:50]}...")
                        print(f"✅ 이미지 변환 성공")
                        processed_images += 1
                    else:
                        print(f"⚠️ 이미지 파일을 찾을 수 없음: {full_path}")
                except Exception as e:
                    print(f"⚠️ 이미지 처리 중 오류 발생: {str(e)}")
                    continue
                
                print("-" * 50)
    
    print(f"\n✅ 총 {processed_images}/{total_images} 개의 이미지 처리 완료")
    return str(soup)

def post_to_blogger(service, blog_id, html_content, title):
    """HTML 내용을 블로그에 포스팅합니다."""
    try:
        print("\n1. HTML 내용 정리 중...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 불필요한 태그 제거
        for tag in soup.find_all(['script', 'style', 'meta']):
            tag.decompose()
            
        # body 태그 내용만 추출
        body = soup.find('body')
        if body:
            content = str(body)
        else:
            content = str(soup)
        
        # HTML 태그 정리
        content = content.replace('<body>', '').replace('</body>', '')
        
        print("2. 블로그 포스트 생성 중...")
        post = {
            'kind': 'blogger#post',
            'title': title,
            'content': content,
            'blog': {
                'id': blog_id
            },
            'status': 'DRAFT'  # 임시로 초안으로 저장
        }
        
        print("3. 블로그에 포스트 업로드 중...")
        request = service.posts().insert(
            blogId=blog_id,
            body=post,
            isDraft=True
        )
        response = request.execute()
        
        print("\n✅ 블로그 포스팅 완료!")
        print(f"포스트 ID: {response.get('id')}")
        return True
        
    except Exception as e:
        print(f"\n❌ 블로그 포스팅 중 오류 발생: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("\n=== 블로그 포스팅 테스트 ===")
    
    # 1. HTML 파일 목록 표시
    html_files = list_merged_html_files()
    if not html_files:
        return
    
    # 2. 파일 선택
    while True:
        try:
            choice = int(input("\n포스팅할 파일 번호를 선택하세요: ")) - 1
            if 0 <= choice < len(html_files):
                selected_file = html_files[choice]
                break
            print("❌ 올바른 번호를 입력하세요.")
        except ValueError:
            print("❌ 숫자를 입력하세요.")
    
    # 3. 선택된 파일 처리
    file_path = os.path.join('merged_html', selected_file)
    print(f"\n선택된 파일: {selected_file}")
    
    try:
        # 4. HTML 파일 읽기
        print("\n1. HTML 파일 읽는 중...")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 5. 이미지 변환
        print("\n2. 이미지 변환 중...")
        content_with_images = fix_image_paths(content, os.getcwd())
        
        # 6. 제목 추출
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.title.string if soup.title else os.path.basename(file_path)
        
        # 7. 블로거 서비스 초기화
        print("\n3. 블로거 서비스 초기화 중...")
        service = get_blogger_service()
        
        # 8. 블로그 포스팅
        print("\n4. 블로그에 포스팅 중...")
        from config import BLOGGER_BLOG_ID
        blog_id = BLOGGER_BLOG_ID
        print(f"🌐 블로그 ID: {blog_id}")
            
        success = post_to_blogger(service, blog_id, content_with_images, title)
        
        if success:
            print("\n✨ 테스트가 성공적으로 완료되었습니다!")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")

if __name__ == "__main__":
    main() 