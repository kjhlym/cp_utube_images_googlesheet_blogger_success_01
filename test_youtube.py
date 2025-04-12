from main import (
    extract_video_id,
    get_video_info,
    get_video_transcript,
    summarize_text,
    extract_product_keywords,
    search_products_with_keywords,
    generate_html
)
import json
import os
from datetime import datetime
from youtube_summery import get_video_id, get_video_info, get_transcript, summarize_text
from generate_product_page import process_search_results, generate_video_html

def test_youtube():
    """YouTube 영상 처리 테스트"""
    # 테스트할 YouTube URL
    video_url = "https://www.youtube.com/watch?v=Sn0ffsEZ41w&ab_channel=%EC%8A%A4%EB%A7%A4%EC%8B%9C%EC%96%B4%EC%9B%A8%EC%9D%B4SMASHAWAY"
    
    try:
        # 1. 비디오 ID 추출
        print("\n1. 비디오 ID 추출 중...")
        video_id = extract_video_id(video_url)
        if not video_id:
            print("❌ 비디오 ID 추출 실패")
            return
        print(f"✅ 비디오 ID: {video_id}")
        
        # 2. 비디오 정보 가져오기
        print("\n2. 비디오 정보 가져오는 중...")
        video_info = get_video_info(video_id)
        if not video_info:
            print("❌ 비디오 정보 가져오기 실패")
            return
        print("✅ 비디오 정보 추출 완료")
        
        # 3. 자막 가져오기
        print("\n3. 자막 가져오는 중...")
        transcript = get_video_transcript(video_id)
        if not transcript:
            print("❌ 자막 가져오기 실패")
            return
        print(f"✅ 자막 추출 완료")
        print(f"자막 길이: {len(transcript)} 글자")
        
        # 4. 내용 요약
        print("\n4. 내용 요약 중...")
        summary = summarize_text(transcript)
        if not summary:
            print("❌ 내용 요약 실패")
            return
        print("✅ 요약 완료")
        print(f"요약 길이: {len(summary)} 글자")
        
        print("\n=== 요약 내용 ===")
        print(summary)
        
        # 5. 키워드 추출
        print("\n5. 영상 내용에서 상품 키워드 추출 중...")
        keywords = extract_product_keywords(summary)
        if not keywords:
            print("❌ 키워드 추출 실패")
            return
            
        print("\n=== Gemini API 응답 ===")
        print("```json")
        print(json.dumps({"keywords": keywords}, indent=2, ensure_ascii=False))
        print("```")
        
        print("\n추출된 키워드:")
        for i, keyword in enumerate(keywords, 1):
            print(f"{i}. {keyword}")
        print(f"✅ {len(keywords)}개의 키워드 추출 완료")
        
        # 6. 상품 검색
        print("\n6. 추출된 키워드로 상품 검색 중...")
        all_products = []
        for keyword in keywords:
            print(f"\n키워드 '{keyword}'로 상품 검색 중...")
            products = search_products_with_keywords(keyword)
            if products:
                all_products.extend(products)
                
        if not all_products:
            print("❌ 상품 검색 실패")
            return
            
        print(f"✅ 총 {len(all_products)}개의 상품 검색 완료")
        
        # 7. HTML 생성
        print("\n7. HTML 생성 중...")
        html_content = generate_video_html(video_info, summary, all_products)
        if not html_content:
            print("❌ HTML 생성 실패")
            return
        print("✅ HTML 생성 완료")
        
        # 8. HTML 파일 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_file = f'coupang_html/merged_{timestamp}.html'
        
        os.makedirs('coupang_html', exist_ok=True)
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"\n✅ HTML 파일 생성 완료: {html_file}")
        print("처리 결과:", html_file)
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {str(e)}")
        return None

if __name__ == "__main__":
    test_youtube() 