import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

# .env 파일 로드
load_dotenv()

# API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("오류: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다")
    exit(1)

def extract_keywords_from_html(html_path):
    """HTML 파일에서 텍스트를 추출하고 키워드를 분석합니다."""
    try:
        # 파일 존재 여부 확인
        if not os.path.exists(html_path):
            print(f"오류: HTML 파일을 찾을 수 없습니다: {html_path}")
            return None
            
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # BeautifulSoup을 사용하여 HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 섹션 내용 추출
        sections = soup.find_all('div', class_='section')
        if not sections:
            print("경고: HTML에서 섹션을 찾을 수 없습니다.")
            # 섹션이 없는 경우 전체 텍스트 사용
            text_content = soup.get_text()
        else:
            text_content = '\n'.join([section.get_text() for section in sections])
        
        if not text_content.strip():
            print("오류: 추출된 텍스트가 없습니다.")
            return None
            
        return text_content
        
    except Exception as e:
        print(f"HTML 파일 처리 중 오류 발생: {str(e)}")
        return None

def analyze_content(text):
    """Gemini API를 사용하여 컨텐츠를 분석하고 검색 키워드를 추출합니다."""
    if not text:
        print("오류: 분석할 텍스트가 없습니다.")
        return None
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')
    
    prompt = f"""당신은 테니스 라켓 전문가입니다. 주어진 텍스트를 분석하여 정확히 2개의 테니스 라켓 검색 키워드를 생성해야 합니다.

입력 텍스트 예시 1:
"초보자를 위한 테니스 라켓을 찾고 있습니다. 가벼운 라켓이 좋을 것 같아요."

올바른 응답 1:
{{
    "product_searches": [
        {{
            "query": "윌슨 블레이드 98"
        }},
        {{
            "query": "바볼랏 퓨어 드라이브 라이트"
        }}
    ]
}}

입력 텍스트 예시 2:
"프로 선수들이 사용하는 고급 라켓을 찾고 있습니다."

올바른 응답 2:
{{
    "product_searches": [
        {{
            "query": "윌슨 프로스태프 97"
        }},
        {{
            "query": "요넥스 브이코어 프로"
        }}
    ]
}}

입력 텍스트 예시 3:
"중급자용 라켓 추천해주세요."

올바른 응답 3:
{{
    "product_searches": [
        {{
            "query": "헤드 래디컬 프로"
        }},
        {{
            "query": "던롭 CX 200"
        }}
    ]
}}

잘못된 응답의 예 (절대 사용하지 말 것):
1. 잘못된 검색어 형식:
{{
    "product_searches": [
        {{
            "query": "좋은 라켓"  # 브랜드와 모델명 없음 - 잘못됨
        }}
    ]
}}

엄격한 규칙:
1. 검색어 규칙
   - 반드시 "브랜드명 + 구체적인 모델명" 형식을 사용할 것
   - 허용되는 브랜드와 대표 모델:
     * 윌슨: 프로스태프, 블레이드, 클래시, 울트라
     * 바볼랏: 퓨어 드라이브, 퓨어 스트라이크, 퓨어 에어로
     * 헤드: 프레스티지, 래디컬, 익스트림
     * 요넥스: 브이코어, 이존, 아스트렐
     * 던롭: CX, FX, SX
   - 예시:
     * 올바른 예: "윌슨 프로스태프 97", "바볼랏 퓨어 드라이브"
     * 잘못된 예: "좋은 라켓", "초보자용 라켓", "윌슨 라켓"

2. 응답 규칙
   - 정확히 2개의 검색어를 생성할 것
   - 위의 예시와 정확히 동일한 JSON 형식을 사용할 것
   - 추가 설명이나 주석 없이 JSON만 반환할 것

분석할 텍스트:
{text}

응답은 반드시 위의 예시와 동일한 JSON 형식이어야 하며, 모든 규칙을 준수해야 합니다.
규칙을 위반하는 응답은 절대 허용되지 않습니다."""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            result = response.text.strip()
            
            # JSON 문자열 추출 (중괄호로 둘러싸인 부분)
            json_match = re.search(r'\{[\s\S]*\}', result)
            if not json_match:
                print(f"시도 {attempt + 1}/{max_retries}: JSON 형식의 응답을 찾을 수 없습니다.")
                continue
                
            try:
                parsed_result = json.loads(json_match.group())
                
                # 기본 구조 검증
                if not isinstance(parsed_result, dict) or "product_searches" not in parsed_result:
                    print(f"시도 {attempt + 1}/{max_retries}: 잘못된 JSON 구조입니다.")
                    continue
                    
                searches = parsed_result["product_searches"]
                if not isinstance(searches, list) or len(searches) != 2:
                    print(f"시도 {attempt + 1}/{max_retries}: 검색어 수가 잘못되었습니다. (현재: {len(searches)}개, 요구: 2개)")
                    continue
                
                # 허용되는 브랜드와 모델
                brand_models = {
                    '윌슨': ['프로스태프', '블레이드', '클래시', '울트라'],
                    '바볼랏': ['퓨어 드라이브', '퓨어 스트라이크', '퓨어 에어로'],
                    '헤드': ['프레스티지', '래디컬', '익스트림'],
                    '요넥스': ['브이코어', '이존', '아스트렐'],
                    '던롭': ['CX', 'FX', 'SX']
                }
                
                # 각 검색어 검증
                valid_searches = []
                print("\n검색어 검증:")
                for i, search in enumerate(searches, 1):
                    # 필수 필드 확인
                    if not isinstance(search, dict):
                        print(f"- 검색어 {i}가 올바른 형식이 아닙니다.")
                        continue
                        
                    if "query" not in search:
                        print(f"- 검색어 {i}에 'query' 필드가 없습니다.")
                        continue
                        
                    # 브랜드와 모델 검증
                    query = search["query"]
                    valid_brand_model = False
                    matching_brand = None
                    matching_model = None
                    
                    for brand, models in brand_models.items():
                        if brand in query:
                            for model in models:
                                if model.lower() in query.lower():
                                    valid_brand_model = True
                                    matching_brand = brand
                                    matching_model = model
                                    break
                        if valid_brand_model:
                            break
                    
                    if not valid_brand_model:
                        print(f"- 검색어 {i} '{query}'에 유효한 브랜드와 모델명이 없습니다.")
                        continue
                        
                    print(f"- 검색어 {i} 검증 성공:")
                    print(f"  * 브랜드: {matching_brand}")
                    print(f"  * 모델: {matching_model}")
                    valid_searches.append(search)
                
                # 모든 검색어가 유효한 경우에만 결과 반환
                if len(valid_searches) == 2:
                    parsed_result["product_searches"] = valid_searches
                    return parsed_result
                else:
                    print(f"\n시도 {attempt + 1}/{max_retries}: 유효한 검색어가 부족합니다. (현재: {len(valid_searches)}개, 요구: 2개)")
                    
            except json.JSONDecodeError as e:
                print(f"시도 {attempt + 1}/{max_retries}: JSON 파싱 오류: {str(e)}")
                continue
                
        except Exception as e:
            print(f"시도 {attempt + 1}/{max_retries}: 컨텐츠 분석 중 오류 발생: {str(e)}")
            continue
            
    print("\n최대 시도 횟수를 초과했습니다. 유효한 결과를 얻지 못했습니다.")
    return None

def process_html_file(file_path):
    """HTML 파일을 처리하고 검색 키워드를 추출합니다."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 텍스트 추출
        text = soup.get_text()
        
        print(f"처리할 파일: {file_path}")
        
        # 컨텐츠 분석
        result = analyze_content(text)
        
        if result and "product_searches" in result:
            print("\n최종 검색 결과:")
            for i, search in enumerate(result["product_searches"], 1):
                query = search["query"]
                print(f"{i}. {query}")
            return result
            
        return None
        
    except Exception as e:
        print(f"파일 처리 중 오류 발생: {str(e)}")
        return None

def main():
    """메인 함수"""
    # HTML 파일 찾기
    html_dir = "html"
    if not os.path.exists(html_dir):
        print(f"오류: '{html_dir}' 디렉토리를 찾을 수 없습니다.")
        return
        
    html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
    if not html_files:
        print(f"오류: '{html_dir}' 디렉토리에 HTML 파일이 없습니다.")
        return
        
    # 가장 최근 파일 선택
    latest_file = max(html_files, key=lambda x: os.path.getmtime(os.path.join(html_dir, x)))
    file_path = os.path.join(html_dir, latest_file)
    
    # 파일 처리
    process_html_file(file_path)

if __name__ == "__main__":
    main() 