import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv
import yt_dlp
from datetime import datetime
import time

# .env 파일 로드
load_dotenv()

# API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("오류: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다")
    exit(1)

# Gemini 모델 설정
model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-pro-exp-02-05")

def get_video_id(url):
    """유튜브 URL에서 비디오 ID를 추출합니다."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
        return None
    except Exception as e:
        print(f"URL 파싱 중 오류가 발생했습니다: {str(e)}")
        return None

def get_video_info(url):
    """비디오의 제목, 썸네일 URL, 스크린샷을 가져옵니다."""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ko', 'en'],
            'skip_download': True,
            'format': 'best[height<=720]'  # 720p 이하의 포맷만 선택
        }
        
        max_retries = 3
        retry_delay = 2  # 초
        
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # 썸네일 URL 가져오기
                    thumbnail_url = info.get('thumbnail', '')
                    
                    # 스크린샷 URL 가져오기 (최대 3개)
                    screenshots = []
                    if 'thumbnails' in info:
                        for thumb in info['thumbnails']:
                            if thumb.get('width', 0) >= 640:  # 고해상도 썸네일만 선택
                                screenshots.append(thumb['url'])
                                if len(screenshots) >= 3:  # 최대 3개만 저장
                                    break
                    
                    return {
                        'title': info.get('title', '제목 없음'),
                        'description': info.get('description', '설명 없음'),
                        'thumbnail_url': thumbnail_url,
                        'screenshots': screenshots,
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'uploader': info.get('uploader', '작성자 정보 없음')
                    }
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"비디오 정보 가져오기 시도 {attempt + 1}/{max_retries} 실패. {retry_delay}초 후 재시도합니다...")
                    time.sleep(retry_delay)
                else:
                    print(f"비디오 정보를 가져오는 중 오류가 발생했습니다: {str(e)}")
                    # 기본 정보만 반환
                    return {
                        'title': '제목을 가져올 수 없음',
                        'description': '설명을 가져올 수 없음',
                        'thumbnail_url': '',
                        'screenshots': [],
                        'duration': 0,
                        'view_count': 0,
                        'uploader': '작성자 정보를 가져올 수 없음'
                    }
    except Exception as e:
        print(f"비디오 정보를 가져오는 중 치명적인 오류가 발생했습니다: {str(e)}")
        return None

def get_transcript(video_id):
    """비디오 ID로 자막을 가져옵니다."""
    max_retries = 3
    retry_delay = 2  # 초
    
    for attempt in range(max_retries):
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
            return ' '.join([t['text'] for t in transcript_list])
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"자막 가져오기 시도 {attempt + 1}/{max_retries} 실패. {retry_delay}초 후 재시도합니다...")
                time.sleep(retry_delay)
            else:
                print(f"자막을 가져오는 중 오류가 발생했습니다: {str(e)}")
                return None

def summarize_text(text):
    """Gemini API를 사용하여 텍스트를 HTML 형식으로 정리합니다."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    다음 텍스트를 간결하게 요약하고 추가 인사이트를 제공해주세요.
    
    요구사항:
    1. 대본을 그대로 옮기지 말고 핵심 내용만 간단히 요약
    2. 중요한 포인트나 키워드는 강조
    3. 관련된 추가 정보나 인사이트 제공
    4. 전문 용어가 있다면 간단한 설명 추가
    5. 실용적인 팁이나 조언이 있다면 추가
    
    응답 형식:
    - <h2> 태그: 섹션 제목
    - <p> 태그: 문단
    - <strong> 태그: 중요 내용 강조
    - <ul>과 <li> 태그: 목록
    - <blockquote> 태그: 인용구나 핵심 메시지
    - <div class="section"> 태그: 섹션 구분
    
    텍스트:
    {text}
    """
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            content = response.text
            
            # 코드 블록 마커 제거
            content = content.replace('```html', '').replace('```', '').strip()
            
            return content
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"텍스트 정리 시도 {attempt + 1}/{max_retries} 실패. {retry_delay}초 후 재시도합니다...")
                time.sleep(retry_delay)
            else:
                print(f"텍스트 정리 중 오류가 발생했습니다: {str(e)}")
                return None

def generate_thumbnail_with_gemini(summary):
    """Gemini API를 사용하여 요약 내용에 맞는 텍스트 기반 썸네일을 생성합니다."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # 전체 내용을 사용하여 키워드와 이모지 추출
        prompt = f"""
        다음 내용을 바탕으로 블로그 스타일의 강력한 키워드를 추출해주세요.
        키워드는 '디지털 디톡스'와 같이 두 단어를 조합하여 만들어주세요.
        각 단어는 2-3글자의 한글로 구성하며, 내용의 핵심을 전달해야 합니다.
        
        응답 형식:
        첫번째단어
        두번째단어

        예시:
        디지털
        디톡스

        내용:
        {summary}
        """
        
        response = model.generate_content(prompt)
        if response and response.text:
            # 키워드 추출
            lines = response.text.strip().split('\n')
            keywords = lines[:2]  # 첫 두 줄은 키워드
            
            # 카테고리/주제 생성
            category_prompt = f"""
            위의 키워드들을 보고 1-2단어의 짧은 카테고리나 주제를 생성해주세요.
            예시: 리빙, 운동, 취미, 교육, 문화 등
            
            키워드:
            {' '.join(keywords)}
            """
            
            category_response = model.generate_content(category_prompt)
            category = category_response.text.strip() if category_response else "리빙"
            
            # HTML 템플릿 생성
            html_content = f"""
            <div style="
                position: relative;
                width: 100%;
                max-width: 800px;
                aspect-ratio: 16/9;
                background-color: #4285f4;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                font-family: 'Noto Sans KR', sans-serif;
                overflow: hidden;
            ">
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: white;
                    margin: 20px;
                    border-radius: 15px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                ">
                    <div style="
                        position: absolute;
                        top: 40px;
                        left: 50%;
                        transform: translateX(-50%);
                        background-color: #e5ff54;
                        padding: 5px 40px;
                        border-radius: 20px;
                        font-size: 16px;
                        font-weight: 500;
                        color: #333;
                    ">
                        {category}
                    </div>
                    <div style="
                        text-align: center;
                        font-size: 72px;
                        font-weight: 700;
                        line-height: 1.3;
                        letter-spacing: -0.02em;
                        margin-top: 20px;
                    ">
                        <div style="color: #4285f4;">{keywords[0]}</div>
                        <div style="color: #333;">{keywords[1] if len(keywords) > 1 else ''}</div>
                    </div>
                </div>
            </div>
            """
            return html_content
        return None
    except Exception as e:
        print(f"썸네일 생성 중 오류 발생: {str(e)}")
        return None

def generate_html(video_info, summary):
    """HTML 파일을 생성합니다."""
    try:
        # utube_mtml 폴더 확인 및 생성
        if not os.path.exists('utube_mtml'):
            os.makedirs('utube_mtml')
        
        # 기존 html 폴더도 확인 및 생성 (호환성 유지)
        if not os.path.exists('html'):
            os.makedirs('html')
        
        # 제목 생성
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        title_prompt = f"""
        다음 내용을 바탕으로 블로그 제목을 생성해주세요.
        제목은 호기심을 자극하고 클릭을 유도하는 형태로 만들어주세요.
        단, 다음 규칙을 반드시 지켜주세요:
        1. '유튜브' 단어를 사용하지 마세요
        2. 저작권이나 상표권이 있는 용어는 피해주세요
        3. 10-20자 내외로 작성해주세요
        4. 감정을 자극하는 단어나 궁금증을 유발하는 표현을 사용하세요
        5. 내용의 핵심 가치나 이점을 강조해주세요

        원본 제목: {video_info['title']}
        내용 요약: {summary}

        응답 형식:
        제목만 작성해주세요 (다른 설명이나 부가 내용 없이)
        """
        
        title_response = model.generate_content(title_prompt)
        engaging_title = title_response.text.strip() if title_response else video_info['title']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 파일 경로를 html 대신 utube_mtml 폴더로 변경
        filename = f"utube_mtml/summary_{timestamp}.html"
        backup_filename = f"html/summary_{timestamp}.html"
        
        # 유튜브 썸네일 URL 가져오기
        thumbnail_url = video_info.get('thumbnail_url', '') or video_info.get('thumbnail', '')
        if not thumbnail_url:
            print("⚠️ 유튜브 썸네일 URL을 찾을 수 없습니다.")
            thumbnail_img = '<div class="no-thumbnail">썸네일 이미지를 찾을 수 없습니다</div>'
        else:
            print(f"✅ 유튜브 썸네일 URL: {thumbnail_url}")
            thumbnail_img = f'<img src="{thumbnail_url}" alt="비디오 썸네일" class="video-thumbnail">'
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{engaging_title}</title>
            <style>
                body {{
                    font-family: 'Noto Sans KR', sans-serif;
                    line-height: 1.8;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .thumbnail-container {{
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .video-thumbnail {{
                    width: 100%;
                    max-width: 640px;
                    height: auto;
                    border-radius: 8px;
                }}
                .no-thumbnail {{
                    padding: 100px 20px;
                    background-color: #f0f0f0;
                    border-radius: 8px;
                    color: #666;
                    text-align: center;
                    font-style: italic;
                }}
                h1 {{
                    color: #333;
                    margin-bottom: 20px;
                    font-size: 1.8em;
                    line-height: 1.4;
                    word-break: keep-all;
                }}
                h2 {{
                    color: #2c3e50;
                    margin-top: 1.5em;
                    margin-bottom: 0.8em;
                    font-size: 1.4em;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 0.3em;
                }}
                .content {{
                    background-color: #f8f9fa;
                    padding: 30px;
                    border-radius: 8px;
                    font-size: 1.1em;
                }}
                .section {{
                    margin-bottom: 2em;
                    padding: 1em;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                }}
                p {{
                    margin-bottom: 1em;
                    color: #444;
                }}
                strong {{
                    color: #2c3e50;
                    font-weight: 600;
                }}
                ul {{
                    margin: 1em 0;
                    padding-left: 1.5em;
                }}
                li {{
                    margin-bottom: 0.5em;
                    color: #444;
                }}
                blockquote {{
                    margin: 1em 0;
                    padding: 1em;
                    border-left: 4px solid #2c3e50;
                    background-color: #f1f3f5;
                    color: #444;
                }}
                .timestamp {{
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 20px;
                    text-align: right;
                }}
                .error {{
                    color: #dc3545;
                    background-color: #f8d7da;
                    padding: 10px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .affiliate-disclosure {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #888;
                    font-size: 0.9em;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>{engaging_title}</h1>
                <div class="thumbnail-container">
                    {thumbnail_img}
                </div>
                <div class="content">
                    {summary}
                </div>
                <div class="timestamp">
                    생성일시: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                </div>
                <div class="affiliate-disclosure">
                    <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # HTML 파일 생성
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 기존 html 폴더에도 백업 복사본 저장 (호환성 유지)
        with open(backup_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML 파일이 생성되었습니다: {filename}")
        print(f"백업 파일도 생성되었습니다: {backup_filename}")
        
        return filename
    except Exception as e:
        print(f"HTML 파일 생성 중 오류가 발생했습니다: {str(e)}")
        return None

def main():
    print("유튜브 동영상 요약 프로그램")
    print("동영상 URL을 입력해주세요:")
    url = input("> ").strip()
    
    if not url:
        print("URL이 입력되지 않았습니다.")
        return
    
    # 비디오 정보 가져오기
    print("\n비디오 정보를 가져오는 중...")
    video_info = get_video_info(url)
    if not video_info:
        print("비디오 정보를 가져올 수 없습니다.")
        return
    
    # 비디오 ID 추출
    video_id = get_video_id(url)
    if not video_id:
        print("올바른 유튜브 URL이 아닙니다.")
        return
    
    # 자막 가져오기
    print("\n자막을 가져오는 중...")
    transcript = get_transcript(video_id)
    if not transcript:
        print("자막을 가져올 수 없습니다.")
        return
    
    # 텍스트 요약
    print("\n동영상을 요약하는 중...")
    summary = summarize_text(transcript)
    if not summary:
        print("요약에 실패했습니다.")
        return
    
    # HTML 생성
    print("\nHTML 파일을 생성하는 중...")
    html_file = generate_html(video_info, summary)
    if html_file:
        print(f"\n요약이 완료되었습니다. HTML 파일이 생성되었습니다: {html_file}")
    else:
        print("HTML 파일 생성에 실패했습니다.")

if __name__ == "__main__":
    main()
