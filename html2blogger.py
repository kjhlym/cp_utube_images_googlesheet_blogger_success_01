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
import googleapiclient.errors

# Load environment variables
load_dotenv()

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/blogger',
    'https://www.googleapis.com/auth/blogger.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly'
]

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

def get_credentials(force_new_token=False):
    """OAuth 2.0 인증 정보를 가져옵니다."""
    creds = None
    
    # token.pickle 파일은 사용자의 액세스 및 새로 고침 토큰을 저장
    token_path = 'token.pickle'
    
    # 강제로 새 토큰 생성이 요청된 경우 기존 토큰 파일 삭제
    if force_new_token and os.path.exists(token_path):
        try:
            os.remove(token_path)
            print("🔄 기존 토큰 파일을 삭제하고 새로 인증합니다...")
        except Exception as e:
            print(f"⚠️ 토큰 파일 삭제 실패: {str(e)}")
    
    # 토큰 파일이 있으면 로드
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            print("✅ 기존 토큰 로드 성공")
        except Exception as e:
            print(f"⚠️ 토큰 파일 로드 실패: {str(e)}")
            creds = None
    
    # 유효한 인증 정보가 없으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ 만료된 토큰 갱신 성공")
            except Exception as e:
                print(f"⚠️ 토큰 갱신 실패: {str(e)}")
                print("💡 새로운 인증을 시도합니다.")
                creds = None
        
        if not creds:
            # client_secret.json 파일 확인
            if not os.path.exists('client_secret.json'):
                print("❌ client_secret.json 파일이 없습니다.")
                print("💡 다음 단계를 따라 client_secret.json 파일을 생성하세요:")
                print("1. https://console.cloud.google.com/apis/credentials 페이지로 이동")
                print("2. '사용자 인증 정보 만들기' > 'OAuth 클라이언트 ID'를 선택")
                print("3. 애플리케이션 유형으로 '데스크톱 앱'을 선택")
                print("4. 이름을 입력하고 '만들기'를 클릭")
                print("5. 'JSON 다운로드' 버튼을 클릭하여 파일을 다운로드")
                print("6. 다운로드한 파일을 이 프로그램의 실행 디렉토리에 'client_secret.json' 이름으로 저장")
                return None
                
            try:
                print("\n🔐 브라우저가 열리면 Google 계정으로 로그인하고 요청된 모든 권한을 허용해주세요.")
                print("💡 권한 허용 후 '승인되었습니다' 또는 'localhost로 연결할 수 없음' 메시지가 표시되면 정상입니다.")
                flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
                
                # 토큰 저장
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
                print("✅ 새 인증 토큰 생성 및 저장 성공")
            except Exception as e:
                print(f"❌ 인증 프로세스 실패: {str(e)}")
                print("\n💡 다음 사항을 확인하세요:")
                print("1. 인터넷 연결이 정상인지 확인")
                print("2. Google Cloud Console에서 OAuth 동의 화면이 구성되어 있는지 확인")
                print("3. API 및 서비스 > 사용자 인증 정보에서 OAuth 클라이언트 ID가 생성되어 있는지 확인")
                print("4. client_secret.json 파일이 올바른지 확인")
                return None
    
    try:
        # 서비스 생성
        service = build('blogger', 'v3', credentials=creds)
        print("✅ Blogger API 서비스 생성 성공")
        return service
    except Exception as e:
        print(f"❌ Blogger API 서비스 생성 실패: {str(e)}")
        print("\n💡 다음 사항을 확인하세요:")
        print("1. Google Cloud Console에서 Blogger API가 활성화되어 있는지 확인")
        print("2. 인증된 계정이 블로그에 접근할 권한이 있는지 확인")
        print("3. 인터넷 연결이 정상인지 확인")
        print("4. token.pickle 파일을 삭제하고 다시 시도")
        return None

def post_html_to_blogger(service, blog_id, html_file_path, title):
    """HTML 파일을 Blogger에 포스팅합니다."""
    try:
        print(f"📄 HTML 파일을 읽는 중: {html_file_path}")
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        print(f"🔍 HTML 파일 크기: {len(html_content)} 바이트")
        print(f"📝 포스팅 제목: {title}")
        print(f"🌐 블로그 ID: {blog_id}")
        
        post = {
            'kind': 'blogger#post',
            'blog': {
                'id': blog_id
            },
            'title': title,
            'content': html_content
        }
        
        print("🔄 Blogger API에 포스팅 중...")
        response = service.posts().insert(blogId=blog_id, body=post).execute()
        
        print(f"✅ 블로그 포스팅 성공: {response.get('url', '알 수 없는 URL')}")
        return response.get('url')
    except googleapiclient.errors.HttpError as e:
        print(f"Error posting to Blogger: {e}")
        
        # 인증 스코프 부족 오류 처리
        if "Request had insufficient authentication scopes" in str(e):
            print("\n⚠️ Blogger API 접근 권한 부족 오류")
            print("💡 문제 해결 방법:")
            print("1. token.pickle 파일을 삭제합니다.")
            print("2. 프로그램을 다시 실행하면 새로운 인증 프로세스가 시작됩니다.")
            print("3. 인증 시 모든 요청된 권한을 허용해주세요.")
            
            # 토큰 파일 삭제
            token_path = 'token.pickle'
            if os.path.exists(token_path):
                try:
                    os.remove(token_path)
                    print("✅ token.pickle 파일이 자동으로 삭제되었습니다. 다음 실행 시 새로 인증하세요.")
                except Exception as remove_err:
                    print(f"❌ token.pickle 파일 삭제 실패: {remove_err}")
                    print("💡 수동으로 token.pickle 파일을 삭제하세요.")
        
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ 블로거 포스팅 중 오류 발생: {str(e)}")
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
    
    if post_html_to_blogger(service, blog_id, file_path, title):
        print(f"✅ 성공적으로 포스팅 완료: {title}")
        return True
    else:
        print(f"❌ 포스팅 실패: {title}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Blogger 포스팅 도구')
    parser.add_argument('--posting', help='포스팅할 HTML 파일 경로')
    parser.add_argument('--folder', help='포스팅할 HTML 파일이 있는 폴더 경로')
    parser.add_argument('--blog', type=int, help='블로그 번호 (기본값: 1)')
    parser.add_argument('--delete', action='store_true', help='포스팅 후 원본 파일 삭제')
    parser.add_argument('--all', action='store_true', help='폴더 내 모든 HTML 파일 포스팅')
    parser.add_argument('--force-new-token', action='store_true', help='인증 토큰 강제 재생성')
    
    args = parser.parse_args()
    
    # 블로그 선택
    blog_id = BLOGGER_BLOG_ID
    if args.blog:
        blog_id = set_blog_id(args.blog)
    
    # 토큰 강제 재생성 옵션이 있는 경우
    force_new_token = args.force_new_token
    
    # Blogger API 서비스 생성
    service = get_credentials(force_new_token=force_new_token)
    
    # 인증에 실패한 경우 토큰을 강제로 재생성하고 다시 시도
    if service is None and not force_new_token:
        print("\n🔄 인증에 실패했습니다. 토큰을 재생성하여 다시 시도합니다...")
        service = get_credentials(force_new_token=True)
        
        if service is None:
            print("\n❌ 인증에 계속 실패하고 있습니다.")
            print("💡 다음 사항을 확인하세요:")
            print("1. client_secret.json 파일이 올바른지 확인하세요.")
            print("2. Google Cloud Console에서 Blogger API가 활성화되어 있는지 확인하세요.")
            print("3. 프로젝트의 OAuth 동의 화면과 범위가 올바르게 설정되어 있는지 확인하세요.")
            return 1
    
    try:
        print("=== HTML to Blogger 업로더 ===")
        print("-" * 40)
        
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
        if args.all:
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
                    if post_html_to_blogger(service, blog_id, file, title):
                        print(f"성공적으로 포스팅 완료: {title}")
                        
                        # 관련된 JSON 파일 찾기 및 삭제
                        json_file = find_json_file(os.path.basename(file))
                        if json_file and os.path.exists(json_file):
                            processed_jsons.add(json_file)
                        
                        if args.delete:
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
            
            if post_html_to_blogger(service, blog_id, selected_file, title):
                print("\n블로거에 성공적으로 포스팅되었습니다!")
                if args.delete:
                    os.remove(selected_file)
                    print(f"파일 삭제됨: {os.path.basename(selected_file)}")
            else:
                print("\n블로거 포스팅에 실패했습니다.")
            
    except Exception as e:
        print(f"오류: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    main() 