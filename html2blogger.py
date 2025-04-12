import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from bs4 import BeautifulSoup
import glob
from dotenv import load_dotenv
import sys
import traceback
import time
import re
import argparse
from google.oauth2.credentials import Credentials
from config import BLOGGER_BLOGS, DEFAULT_BLOG_NUMBER, get_blog_list_text, set_blog_id, BLOGGER_BLOG_ID

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/blogger']

def select_blog():
    """사용자에게 블로그를 선택하도록 합니다."""
    print("\n=== 블로그 선택 ===")
    print(get_blog_list_text())
    print(f"\n기본값: {DEFAULT_BLOG_NUMBER}. {BLOGGER_BLOGS[DEFAULT_BLOG_NUMBER]['name']}")
    
    try:
        choice = input("\n블로그 번호를 선택하세요 (Enter 키를 누르면 기본값 선택): ").strip()
        if not choice:  # 기본값 사용
            return DEFAULT_BLOG_NUMBER
        
        choice = int(choice)
        if choice in BLOGGER_BLOGS:
            return choice
        else:
            print(f"잘못된 선택입니다. 기본값({DEFAULT_BLOG_NUMBER})을 사용합니다.")
            return DEFAULT_BLOG_NUMBER
    except ValueError:
        print(f"잘못된 입력입니다. 기본값({DEFAULT_BLOG_NUMBER})을 사용합니다.")
        return DEFAULT_BLOG_NUMBER

def get_credentials():
    """Google API 인증 정보를 가져옵니다."""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    # Blogger API 서비스 객체 생성 및 반환
    try:
        service = build('blogger', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Blogger service: {str(e)}")
        return None

def post_html_to_blogger(service, blog_id, html_content, title):
    """HTML 컨텐츠를 블로거에 포스팅합니다."""
    try:
        # HTML 파일인 경우 파일 내용을 읽어옴
        if isinstance(html_content, str) and html_content.endswith('.html'):
            with open(html_content, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = html_content
        
        # HTML 내용 정리
        # 문자열이 아닌 경우 문자열로 변환
        if not isinstance(content, str):
            content = str(content)
            
        # 파일 경로로 오인될 수 있는 패턴인지 확인
        if content.strip().endswith('.html') and os.path.exists(content.strip()):
            with open(content.strip(), 'r', encoding='utf-8') as f:
                content = f.read()
        
        # DOCTYPE 태그 제거 (BeautifulSoup으로 파싱하기 전에 문자열에서 직접 제거)
        content = re.sub(r'<!DOCTYPE[^>]*>', '', content)
        
        # 마크다운 코드 블록 표시 제거 (```html과 ```)
        content = content.replace('```html', '')
        content = content.replace('```', '')
                
        soup = BeautifulSoup(content, 'html.parser')
        
        # script 태그만 제거하고 style 태그는 유지
        for tag in soup.find_all('script'):
            tag.decompose()
            
        print("script 태그를 제거했습니다. style 태그는 유지합니다.")
        
        # 중첩된 HTML 구조 검사 및 수정
        summary_div = soup.select_one('div.summary')
        if summary_div and summary_div.find('html'):
            # 중첩된 HTML 구조 발견, 내용만 추출
            print("⚠️ 중첩된 HTML 구조가 발견되었습니다. 내용만 추출합니다.")
            nested_body = summary_div.find('body')
            if nested_body:
                # 중첩된 body의 내용으로 대체
                summary_div.replace_with(BeautifulSoup(nested_body.decode_contents(), 'html.parser'))
            else:
                # body가 없는 경우, div.summary 내부의 doctype과 html 태그 제거
                for tag in summary_div.find_all(['html', 'head']):
                    tag.unwrap()  # 태그 제거하고 내용만 유지

        # 이미지 URL 상대 경로 처리 및 확인
        print("이미지 경로 처리 중...")
        images = soup.find_all('img')
        if images:
            print(f"총 {len(images)}개의 이미지 발견")
            for i, img in enumerate(images):
                if 'src' in img.attrs:
                    img_src = img['src']
                    # base64 데이터 URL 확인
                    if img_src.startswith('data:image'):
                        print(f"이미지 {i+1}: Base64 데이터 URL (이미 포함됨)")
                    # 절대 URL 확인
                    elif img_src.startswith(('http://', 'https://')):
                        print(f"이미지 {i+1}: 절대 URL - {img_src[:50]}...")
                    # 상대 경로 처리
                    elif img_src.startswith(('images/', './images/', '../images/')):
                        print(f"⚠️ 이미지 {i+1}: 상대 경로 URL - {img_src}")
                        # 여기서는 경고만 출력하고, 실제 이미지 경로는 유지
                        # Blogger API는 HTML 내용의 상대 경로 이미지를 처리하지 못할 수 있음
                    else:
                        print(f"이미지 {i+1}: 기타 경로 - {img_src[:50]}...")
        else:
            print("이미지가 발견되지 않았습니다.")
        
        # 썸네일 이미지 URL 추출 (첫 번째 이미지)
        thumbnail_url = ""
        first_img = soup.find('img')
        if first_img and first_img.get('src'):
            thumbnail_url = first_img['src']
            # 상대 경로인 경우 처리 (경고만 표시)
            if thumbnail_url.startswith(('images/', './images/', '../images/')):
                print(f"⚠️ 썸네일 상대 경로 감지: {thumbnail_url}")
                print("블로거에서는 외부 URL만 썸네일로 사용할 수 있습니다.")
        
        # HTML 구조 태그 제거
        body = soup.find('body')
        if body:
            # body 태그 내부의 실제 콘텐츠만 추출
            # 이미지 태그는 보존되도록 함
            content = body.decode_contents().strip()
            print("body 태그에서 내용만 추출했습니다. (이미지 태그 보존)")
        else:
            # body 태그가 없는 경우, html과 head 태그를 제외한 내용 추출
            for tag in soup.find_all(['html', 'head']):
                tag.unwrap()  # 태그 제거하고 내용만 유지
            
            content = str(soup).strip()
            print("HTML 구조 태그를 제거했습니다. (이미지 태그 보존)")
        
        print(f"HTML 구조 태그가 제거된 내용으로 포스팅합니다. 이미지는 유지됩니다.")
        
        # 포스트 생성 및 업로드
        post = {
            'title': title,
            'content': content,  # 이미지 태그가 포함된 콘텐츠
            'status': 'DRAFT'  # DRAFT로 저장 (나중에 검토 후 발행)
        }
        
        # 이미지 URL이 있는 경우 포스트 데이터에 이미지 설정 추가
        if thumbnail_url:
            # 이미지가 base64 데이터 URL인지 확인
            if thumbnail_url.startswith('data:image'):
                print("Base64 이미지는 Blogger API에서 직접 썸네일로 사용할 수 없습니다.")
                # 이 경우 HTML 내 이미지가 포스트에 포함되므로 별도 처리 불필요
            elif not thumbnail_url.startswith(('images/', './images/', '../images/')):
                print(f"썸네일 이미지 URL: {thumbnail_url}")
                # Blogger API에서 지원하는 경우 images 필드 추가
                post['images'] = [{'url': thumbnail_url}]
        
        response = service.posts().insert(blogId=blog_id, body=post).execute()
        post_id = response.get('id')
        print(f"Successfully posted: {title}")
        print(f"Post ID: {post_id}")
        print(f"블로그 URL: https://www.blogger.com/blog/post/edit/{blog_id}/{post_id}")
        return True
    except Exception as e:
        print(f"Error posting to Blogger: {str(e)}")
        traceback.print_exc()
        return False

def process_html_file(file_path):
    """HTML 파일을 처리하여 제목과 내용을 추출합니다."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # DOCTYPE 태그 제거 (BeautifulSoup으로 파싱하기 전에 문자열에서 직접 제거)
    content = re.sub(r'<!DOCTYPE[^>]*>', '', content)
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # 제목 추출
    title = ""
    if soup.title:
        title = soup.title.string
    else:
        # h1 또는 h2 태그에서 제목 추출 시도
        h1 = soup.find('h1')
        if h1:
            title = h1.text.strip()
        else:
            h2 = soup.find('h2')
            if h2:
                title = h2.text.strip()
            else:
                # 제목이 없는 경우 파일명 사용
                title = os.path.basename(file_path).split('.')[0]
    
    # 이미지 확인 (디버깅 정보)
    images = soup.find_all('img')
    print(f"HTML 파일에서 {len(images)}개의 이미지 발견")
    
    # HTML 구조 태그 제거
    body = soup.find('body')
    if body:
        # body 태그 내부의 실제 콘텐츠만 추출 (이미지 태그 유지)
        content = body.decode_contents().strip()
    else:
        # body 태그가 없는 경우, html과 head 태그를 제외한 내용 추출
        for tag in soup.find_all(['html', 'head']):
            tag.unwrap()  # 태그 제거하고 내용만 유지
        
        content = str(soup).strip()
    
    print(f"추출된 제목: {title}")
    print(f"HTML 구조 태그가 제거된 내용으로 포스팅합니다 (이미지 태그 유지)")
    
    return title, content

def find_json_file(html_filename):
    """HTML 파일에 해당하는 JSON 파일을 찾습니다."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_dir = os.path.join(script_dir, "newsJson")
    
    # HTML 파일명에서 시간 정보 추출 (YYYYMMDD)
    date_match = re.search(r'_(\d{8})_', html_filename)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    # 해당 날짜의 JSON 파일 찾기
    json_files = glob.glob(os.path.join(json_dir, f"*_{date_str}_*.json"))
    return json_files[0] if json_files else None

def post_specific_file(service, blog_id, file_path):
    """특정 HTML 파일을 블로거에 포스팅합니다."""
    print(f"\n지정된 파일 처리 중: {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return False
    
    title, content = process_html_file(file_path)
    
    if post_html_to_blogger(service, blog_id, content, title):
        print(f"✅ 성공적으로 포스팅 완료: {title}")
        return True
    else:
        print(f"❌ 포스팅 실패: {title}")
        return False

def main():
    try:
        print("=== HTML to Blogger 업로더 ===")
        print("-" * 40)
        
        # 인자 파싱
        parser = argparse.ArgumentParser(description='HTML 파일을 Blogger에 포스팅합니다.')
        parser.add_argument('--auto', action='store_true', help='모든 HTML 파일을 자동으로 포스팅합니다.')
        parser.add_argument('--posting', type=str, help='특정 HTML 파일을 직접 포스팅합니다.')
        args = parser.parse_args()
        
        # Blogger 서비스 객체 생성
        blog_number = select_blog()
        set_blog_id(blog_number)
        service = get_credentials()
        
        # 블로그 ID 가져오기
        blog_id = BLOGGER_BLOG_ID
        if not blog_id:
            print("Error: BLOGGER_BLOG_ID not found in .env file")
            return
        
        # 직접 파일 포스팅 모드인 경우
        if args.posting:
            file_path = args.posting
            print(f"\n파일 처리 중: {os.path.basename(file_path)}")
            print("첨부 내용(HTML 구조 태그)을 제거하고 실제 콘텐츠만 포스팅합니다.")
            post_specific_file(service, blog_id, file_path)
            return
        
        # 콘텐츠 타입 선택
        print("\n포스팅할 콘텐츠 타입을 선택하세요:")
        print("1. 유튜브 요약 (utube_html)")
        print("2. 쿠팡 상품 (coupang_html)")
        print("3. 병합된 콘텐츠 (merged_html)")
        print("4. 포스팅 파일 (posting)")
        print("5. 기타 HTML (html)")
        
        while True:
            try:
                type_choice = input("\n콘텐츠 타입 번호 선택 (1-5): ")
                type_idx = int(type_choice)
                if 1 <= type_idx <= 5:
                    break
                print("유효하지 않은 번호입니다. 다시 시도하세요.")
            except ValueError:
                print("숫자를 입력해주세요.")
        
        # 선택한 타입에 따라 디렉토리 설정
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if type_idx == 1:
            html_dir = os.path.join(script_dir, "utube_html")
            content_type = "유튜브 요약"
        elif type_idx == 2:
            html_dir = os.path.join(script_dir, "coupang_html")
            content_type = "쿠팡 상품"
        elif type_idx == 3:
            html_dir = os.path.join(script_dir, "merged_html")
            content_type = "병합된 콘텐츠"
        elif type_idx == 4:
            html_dir = os.path.join(script_dir, "posting")
            content_type = "포스팅 파일"
        else:
            html_dir = os.path.join(script_dir, "html")
            content_type = "기타 HTML"
        
        if not os.path.exists(html_dir):
            print(f"{content_type} 디렉토리를 찾을 수 없습니다: {html_dir}")
            print("디렉토리를 생성합니다...")
            os.makedirs(html_dir, exist_ok=True)
            print(f"{content_type} 디렉토리가 생성되었습니다.")
            print("해당 디렉토리에 HTML 파일을 추가한 후 다시 실행해주세요.")
            return
        
        # HTML 파일 목록 가져오기
        html_files = glob.glob(os.path.join(html_dir, "*.html"))
        
        if not html_files:
            print(f"{content_type} 디렉토리에 HTML 파일이 없습니다.")
            return
        
        # 자동 모드 확인
        if args.auto:
            print(f"\n자동 모드: 모든 {content_type} HTML 파일 처리 중")
            success_count = 0
            failed_files = []
            processed_jsons = set()  # 처리된 JSON 파일 추적
            
            for file in sorted(html_files):
                try:
                    print(f"\n처리 중: {os.path.basename(file)}")
                    print("첨부 내용(HTML 구조 태그)을 제거하고 실제 콘텐츠만 포스팅합니다.")
                    title, content = process_html_file(file)
                    
                    # 블로거에 포스팅
                    if post_html_to_blogger(service, blog_id, content, title):
                        print(f"성공적으로 포스팅 완료: {title}")
                        
                        # 관련된 JSON 파일 찾기 및 삭제
                        json_file = find_json_file(os.path.basename(file))
                        if json_file and os.path.exists(json_file):
                            processed_jsons.add(json_file)
                        
                        os.remove(file)
                        success_count += 1
                        # 각 포스팅 사이에 30초 대기
                        if success_count < len(html_files):  # 마지막 파일이 아닌 경우에만 대기
                            print("다음 포스팅 전 60초 대기 중...")
                            time.sleep(30)
                    else:
                        print(f"포스팅 실패: {title}")
                        failed_files.append(file)
                except Exception as e:
                    print(f"{os.path.basename(file)} 처리 중 오류 발생: {str(e)}")
                    failed_files.append(file)
                    continue
            
            # 모든 HTML 파일 처리가 완료된 후 JSON 파일 삭제
            if processed_jsons:
                print("\n처리된 JSON 파일 삭제 중:")
                for json_file in processed_jsons:
                    try:
                        os.remove(json_file)
                        print(f"JSON 파일 삭제됨: {os.path.basename(json_file)}")
                    except Exception as e:
                        print(f"JSON 파일 {os.path.basename(json_file)} 삭제 중 오류 발생: {str(e)}")
            
            if failed_files:
                print("\n실패한 파일 (다음 실행을 위해 보존됨):")
                for f in failed_files:
                    print(f"- {os.path.basename(f)}")
            
            print(f"\n처리 완료: {success_count}/{len(html_files)} 파일이 성공적으로 업로드됨")
            
        else:
            # 대화형 모드
            print(f"\n{content_type} 디렉토리에서 찾은 HTML 파일:")
            for i, file in enumerate(html_files, 1):
                print(f"{i}. {os.path.basename(file)}")
            
            while True:
                try:
                    choice = input(f"\n포스팅할 파일 번호 선택 (1-{len(html_files)}): ")
                    idx = int(choice) - 1
                    if 0 <= idx < len(html_files):
                        selected_file = html_files[idx]
                        break
                    print("유효하지 않은 번호입니다. 다시 시도하세요.")
                except ValueError:
                    print("유효한 숫자를 입력해주세요.")
            
            print(f"\n처리 중: {os.path.basename(selected_file)}")
            print("첨부 내용(HTML 구조 태그)을 제거하고 실제 콘텐츠만 포스팅합니다.")
            title, content = process_html_file(selected_file)
            
            if post_html_to_blogger(service, blog_id, content, title):
                print("\n블로거에 성공적으로 포스팅되었습니다!")
                delete_file = input("포스팅된 파일을 삭제할까요? (y/n): ").lower()
                if delete_file == 'y':
                    os.remove(selected_file)
                    print(f"파일 삭제됨: {os.path.basename(selected_file)}")
            else:
                print("\n블로거 포스팅에 실패했습니다.")
            
    except Exception as e:
        print(f"오류: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    main() 