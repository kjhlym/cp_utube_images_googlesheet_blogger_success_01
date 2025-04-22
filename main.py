import os
import json
from datetime import datetime
import re
from youtube_summery import get_video_id, get_video_info, get_transcript, summarize_text, generate_html as generate_youtube_html
from generate_product_page import process_search_results, generate_html, generate_video_html
from html2blogger import post_html_to_blogger, get_credentials, select_blog
from coupang_search import search_coupang
from keyword_extractor import process_html_file
import requests
from urllib.parse import quote_plus
import time
from typing import List, Dict
from bs4 import BeautifulSoup
import base64
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
import yt_dlp
from PIL import Image, ImageDraw, ImageFont
import urllib.parse
import hmac
import hashlib
from time import strftime, gmtime
import webbrowser
import shutil
from googleapiclient.discovery import build
from config import set_blog_id, get_blog_list_text
import gspread
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

# .env 파일 로드
load_dotenv()

# API 키 설정
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("오류: .env 파일에서 GEMINI_API_KEY를 찾을 수 없습니다")
    exit(1)

# Gemini 모델 설정
model_name = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.0-pro-exp-02-05")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(model_name)

# utube_mtml 폴더 생성 추가
necessary_dirs = ['utube_html', 'utube_mtml', 'coupang_html', 'merged_html', 'posting']
for directory in necessary_dirs:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

def clear_screen():
    """터미널 화면을 지웁니다."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """프로그램 헤더를 출력합니다."""
    print("=" * 50)
    print("     쿠팡 파트너스 상품 검색 프로그램")
    print("=" * 50)
    print()

def get_search_input():
    """사용자로부터 검색어와 검색 방식을 입력받습니다."""
    # 검색어 입력
    while True:
        keyword = input("\n검색어를 입력하세요: ").strip()
        if keyword:
            break
        print("! 검색어를 입력해주세요.")
    
    # 검색 방식 선택
    print("\n검색 방식을 선택하세요:")
    print("1. 완전일치 검색 (검색어와 정확히 일치하는 상품)")
    print("2. 유사검색 (검색어가 포함된 모든 상품)")
    print("3. 확장검색 (검색어와 연관된 모든 상품)")
    
    while True:
        choice = input("\n선택 (1, 2 또는 3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("! 1, 2 또는 3을 입력해주세요.")
    
    search_type = 'exact' if choice == '1' else 'similar' if choice == '2' else 'expanded'
    return keyword, search_type

def extract_product_keywords(summary):
    """YouTube 요약 내용에서 상품 관련 키워드를 추출하는 함수"""
    try:
        print("\n=== 요약 내용 ===")
        print(summary)
        
        # Gemini API를 사용하여 키워드 추출
        prompt = f"""
        다음 YouTube 영상 요약 내용에서 쿠팡에서 검색할 만한 상품 키워드를 3-5개 추출해주세요.
        각 키워드는 구체적이고 검색 가능한 형태여야 합니다.
        각 키워드는 반드시 50자 이내여야 합니다. 쿠팡 API는 50자 이상의 키워드를 허용하지 않습니다.
        간결하고 짧은 키워드가 더 좋은 검색 결과를 제공합니다.
        응답은 JSON 형식으로 다음과 같이 작성해주세요:
        {{"keywords": ["키워드1", "키워드2", "키워드3"]}}

        요약 내용:
        {summary}
        """
        
        print("\n=== Gemini API 응답 ===")
        response = model.generate_content(prompt)
        response_text = response.text.strip()
        print(response_text)
        
        if response_text:
            try:
                # JSON 문자열에서 실제 JSON 부분만 추출
                json_str = response_text
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                
                # JSON 파싱
                result = json.loads(json_str)
                keywords = result.get('keywords', [])
                
                # 키워드 길이 제한 (쿠팡 API 제한: 50자)
                MAX_KEYWORD_LENGTH = 50
                limited_keywords = []
                
                for idx, keyword in enumerate(keywords, 1):
                    # 키워드 길이 제한
                    if len(keyword) > MAX_KEYWORD_LENGTH:
                        shortened_keyword = keyword[:MAX_KEYWORD_LENGTH]
                        print(f"⚠️ 키워드 길이 초과 ({len(keyword)}자): '{keyword}'")
                        print(f"✂️ 키워드 축소: '{shortened_keyword}'")
                        limited_keywords.append(shortened_keyword)
                    else:
                        limited_keywords.append(keyword)
                        
                if limited_keywords:
                    print("\n추출된 키워드:")
                    for idx, keyword in enumerate(limited_keywords, 1):
                        print(f"{idx}. {keyword} ({len(keyword)}자)")
                    return limited_keywords
                else:
                    print("키워드가 추출되지 않았습니다.")
                    return []
            except json.JSONDecodeError as e:
                print(f"\nJSON 파싱 오류: {str(e)}")
                print("원본 응답:", response_text)
                return []
        return []
    except Exception as e:
        print(f"\n키워드 추출 중 오류 발생: {str(e)}")
        return []

def search_products_with_keywords(keyword):
    """키워드로 상품 검색"""
    try:
        # Coupang API를 사용하여 상품 검색
        products = search_coupang(keyword, max_products=3)
        
        if not products:
            print(f"검색어 '{keyword}'에 대한 상품이 없습니다.")
            return None
        
        # 검색 결과 처리
        processed_products = []
        for product in products:
            try:
                # 이미지 URL 추출
                image_url = product.get('productImage', '') or product.get('imageUrl', '')
                if not image_url:
                    image_url = 'https://via.placeholder.com/300x300?text=No+Image'
                
                # Google 이미지 프록시 사용
                if image_url and not image_url.startswith('data:'):
                    image_url = f"https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url={urllib.parse.quote(image_url)}"
                
                # URL 처리
                product_url = product.get('productUrl', '')
                if product_url and not product_url.startswith(('http://', 'https://')):
                    product_url = f"https://www.coupang.com{product_url}"
                
                # 가격 처리
                price = product.get('productPrice', '0')
                if isinstance(price, str):
                    try:
                        price = int(price.replace(',', '').replace('원', ''))
                    except:
                        price = 0
                
                # 상품 정보 구성
                processed_product = {
                    'name': product.get('productName', '제목 없음'),
                    'price': price,
                    'url': product_url,
                    'image_url': image_url
                }
                
                processed_products.append(processed_product)
            except Exception as e:
                print(f"⚠️ 상품 처리 중 오류: {str(e)}")
                continue
            
        return processed_products
    except Exception as e:
        print(f"❌ 상품 검색 중 오류 발생: {str(e)}")
        return None

# 1. YouTube 처리 함수
def process_youtube_video(youtube_url):
    """YouTube 영상을 처리하여 HTML 파일을 생성하는 함수"""
    try:
        print("\n1. 비디오 ID 추출 중...")
        video_id = get_video_id(youtube_url)
        if not video_id:
            print("❌ 잘못된 YouTube URL입니다.")
            return None
        print(f"✅ 비디오 ID: {video_id}")
        
        print("\n2. 비디오 정보 가져오는 중...")
        try:
            video_info = get_video_info(video_id)
            if not video_info:
                print("❌ 비디오 정보를 가져올 수 없습니다.")
                return None
            
            # thumbnail_url 키가 없으면 thumbnail 키로 대체
            if 'thumbnail' in video_info and 'thumbnail_url' not in video_info:
                video_info['thumbnail_url'] = video_info['thumbnail']
                
            print("✅ 비디오 정보 추출 완료")
            print(f"✅ 썸네일 URL: {video_info.get('thumbnail_url', '') or video_info.get('thumbnail', '없음')}")
        except Exception as e:
            print(f"❌ 비디오 정보 추출 중 오류 발생: {str(e)}")
            # 비디오 정보가 없어도 자막은 추출 시도
            video_info = {"title": "", "description": "", "thumbnail_url": ""}
        
        print("\n3. 자막 가져오는 중...")
        try:
            transcript = get_transcript(video_id)
            if not transcript:
                print("❌ 자막을 가져올 수 없습니다.")
                return None
            print("✅ 자막 추출 완료")
            print(f"자막 길이: {len(transcript)} 글자")
        except Exception as e:
            print(f"❌ 자막 추출 중 오류 발생: {str(e)}")
            return None
        
        print("\n4. 내용 요약 중...")
        try:
            summary = summarize_text(transcript)
            if not summary:
                print("❌ 내용을 요약할 수 없습니다.")
                return None
            print("✅ 요약 완료")
            print(f"요약 길이: {len(summary)} 글자")
        except Exception as e:
            print(f"❌ 내용 요약 중 오류 발생: {str(e)}")
            return None
        
        # 키워드 추출
        print("\n5. 영상 내용에서 상품 키워드 추출 중...")
        try:
            keywords = extract_product_keywords(summary)
            if not keywords:
                print("❌ 키워드 추출 실패")
                return None
            print(f"✅ {len(keywords)}개의 키워드 추출 완료")
        except Exception as e:
            print(f"❌ 키워드 추출 중 오류 발생: {str(e)}")
            return None
        
        # 상품 검색
        print("\n6. 추출된 키워드로 상품 검색 중...")
        try:
            products = []
            for keyword in keywords:
                print(f"\n키워드 '{keyword}'로 상품 검색 중...")
                keyword_products = search_products_with_keywords(keyword)
                if keyword_products:
                    products.extend(keyword_products)
                    print(f"✅ {len(keyword_products)}개 상품 찾음")
                else:
                    print(f"⚠️ '{keyword}'로 상품을 찾을 수 없음")
            
            if not products:
                print("❌ 모든 키워드에 대해 상품 검색 실패")
                return None
            print(f"✅ 총 {len(products)}개의 상품 검색 완료")
        except Exception as e:
            print(f"❌ 상품 검색 중 오류 발생: {str(e)}")
            return None
        
        # 전체 비디오 정보 반환
        result = {
            'title': video_info.get('title', ''),
            'description': video_info.get('description', ''),
            'thumbnail_url': video_info.get('thumbnail_url', '') or video_info.get('thumbnail', ''),
            'transcript': transcript
        }
        
        return result
        
    except Exception as e:
        print(f"❌ YouTube 영상 처리 중 오류 발생: {str(e)}")
        return None

# 2. 상품 검색 및 HTML 생성 함수
def search_and_generate_products(keyword, num_products):
    """상품을 검색하고 HTML을 생성하는 함수"""
    try:
        # 쿠팡 검색 실행
        search_coupang(keyword)
        
        # 검색 결과 처리 및 HTML 생성
        html_path = process_search_results(
            results_file='search_results.json',
            keyword=keyword,
            search_type='similar',
            max_products=num_products
        )
        return html_path
    except Exception as e:
        print(f"상품 검색 중 오류 발생: {str(e)}")
        return None

def match_products_to_sections(products, sections_or_headers):
    """상품과 섹션 간의 관련성을 계산하여 매칭"""
    try:
        import re
        from collections import defaultdict
        
        # 섹션/헤더 텍스트 추출
        section_texts = []
        for section in sections_or_headers:
            # 헤더인 경우
            if section.name in ['h1', 'h2', 'h3', 'h4']:
                section_texts.append({
                    'element': section,
                    'text': section.text.strip()
                })
            # 섹션 div인 경우
            else:
                # 섹션 내 텍스트 추출 (헤더 포함)
                header = section.find(['h1', 'h2', 'h3', 'h4'])
                section_text = header.text.strip() if header else ""
                
                # 섹션 내 모든 텍스트 추가
                all_text = section.get_text(" ", strip=True)
                
                section_texts.append({
                    'element': section,
                    'text': f"{section_text} {all_text}"
                })
        
        # 매칭 결과 저장
        section_products = defaultdict(list)
        
        # 각 상품에 대해 가장 관련성 높은 섹션 찾기
        for product in products:
            best_match_score = -1
            best_match_section = None
            
            product_title = product.get('title', '').lower()
            product_keywords = set(re.findall(r'\w+', product_title))
            
            for section in section_texts:
                section_text = section['text'].lower()
                section_keywords = set(re.findall(r'\w+', section_text))
                
                # 공통 키워드 수 계산
                common_keywords = product_keywords.intersection(section_keywords)
                match_score = len(common_keywords)
                
                # 전체 키워드 대비 공통 키워드 비율
                if len(product_keywords) > 0:
                    match_ratio = len(common_keywords) / len(product_keywords)
                    # 가중치 적용 (일치 비율에 가중치 부여)
                    match_score = match_score * (1 + match_ratio)
                
                if match_score > best_match_score:
                    best_match_score = match_score
                    best_match_section = section
            
            # 가장 관련성 높은 섹션에 상품 할당
            if best_match_section:
                section_products[best_match_section['element']].append({
                    'product': product,
                    'score': best_match_score
                })
        
        # 상품이 할당되지 않은 섹션이 있으면 상품 분배 재조정
        sections_without_products = [s['element'] for s in section_texts 
                                   if s['element'] not in section_products]
        
        remaining_products = []
        for section, products_in_section in list(section_products.items()):
            # 각 섹션에서 상위 2개만 유지하고 나머지는 재분배 대상으로
            if len(products_in_section) > 2:
                # 점수 기준 내림차순 정렬
                products_in_section.sort(key=lambda x: x['score'], reverse=True)
                remaining_products.extend([p['product'] for p in products_in_section[2:]])
                section_products[section] = products_in_section[:2]
        
        # 남은 상품을 상품이 없는 섹션에 분배
        if sections_without_products and remaining_products:
            products_per_section = max(1, len(remaining_products) // len(sections_without_products))
            
            for i, section in enumerate(sections_without_products):
                start_idx = i * products_per_section
                end_idx = start_idx + products_per_section
                
                if start_idx < len(remaining_products):
                    section_products[section] = [{'product': p, 'score': 0} 
                                              for p in remaining_products[start_idx:end_idx]]
        
        # 남은 상품들을 저장 (어떤 섹션에도 할당되지 않은 상품)
        all_assigned_products = []
        for products_in_section in section_products.values():
            all_assigned_products.extend([p['product'] for p in products_in_section])
        
        unassigned_products = [p for p in products if p not in all_assigned_products]
        
        return section_products, unassigned_products
        
    except Exception as e:
        print(f"⚠️ 상품-섹션 매칭 중 오류 발생: {str(e)}")
        # 오류 발생시 빈 결과 반환
        return defaultdict(list), products

# 3. HTML 병합 함수
def merge_html_contents(summary_html, products_html):
    """요약 HTML과 상품 HTML을 병합"""
    try:
        # 상품 HTML에서 상품 카드 추출
        with open(products_html, 'r', encoding='utf-8') as f:
            products_content = f.read()
        
        # 상품 카드 찾기
        product_cards = []
        soup = BeautifulSoup(products_content, 'html.parser')
        cards = soup.find_all('div', class_='product-card')
        
        if not cards:
            print("상품 카드를 찾을 수 없습니다.")
            return None
        
        # 상품 카드 정보 추출
        for card in cards:
            try:
                # 이미지 정보 추출
                img = card.find('img')
                if not img:
                    continue
                image_src = img.get('src', '')
                
                # Google 이미지 프록시 사용 (base64 데이터 URL이 아닌 경우에만)
                if image_src and not image_src.startswith('data:'):
                    image_src = f"https://images1-focus-opensocial.googleusercontent.com/gadgets/proxy?container=focus&refresh=2592000&url={urllib.parse.quote(image_src)}"
                 
                # 제목 추출
                title_elem = card.find('h2', class_='product-title') or card.find('h3', class_='product-title')
                if not title_elem:
                    continue
                title = title_elem.text.strip()
                
                # 가격 추출
                price_elem = card.find('div', class_='product-price') or card.find('p', class_='product-price')
                price = price_elem.text.strip() if price_elem else "가격 정보 없음"
                
                # URL 추출
                link = card.find('a')
                if not link:
                    continue
                url = link.get('href', '#')
                
                # 상품 카드 HTML 생성
                product_card = f"""
                <div class="product-card">
                    <div class="product-image">
                        <a href="{url}" target="_blank">
                            <img src="{image_src}" alt="{title}" loading="lazy">
                        </a>
                    </div>
                    <div class="product-info">
                        <h3 class="product-title">{title}</h3>
                        <div class="product-price">{price}</div>
                        <a href="{url}" class="product-link" target="_blank">상품 보기</a>
                    </div>
                </div>
                """
                product_cards.append({
                    'html': product_card,
                    'title': title,
                    'url': url,
                    'image_src': image_src,
                    'price': price
                })
                
            except Exception as e:
                print(f"⚠️ 상품 카드 처리 중 오류 발생: {str(e)}")
                continue
        
        if not product_cards:
            print("유효한 상품 카드를 찾을 수 없습니다.")
            return None
        
        # 요약 HTML에 상품 카드 삽입
        with open(summary_html, 'r', encoding='utf-8') as f:
            summary_content = f.read()
        
        # HTML 파싱
        soup = BeautifulSoup(summary_content, 'html.parser')
        
        # 제품 섹션용 CSS 스타일 추가
        head = soup.find('head')
        if head:
            style = soup.find('style')
            if style:
                new_css = """
                .product-section {
                    margin: 20px 0;
                    padding: 12px;
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    max-width: 100%;
                }
                .product-section h3 {
                    margin-top: 0;
                    color: #333;
                    font-size: 16px;
                }
                .product-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin: 15px auto;
                    max-width: 100%;
                }
                .product-card {
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                    width: 100%;
                    max-width: 300px;
                    margin: 0 auto;
                    display: flex;
                    flex-direction: column;
                }
                .product-card:hover {
                    transform: translateY(-3px);
                }
                .product-image {
                    width: 100%;
                    height: 120px;
                    text-align: center;
                    overflow: hidden;
                    border-bottom: 1px solid #eee;
                }
                .product-image img {
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }
                .product-info {
                    padding: 10px;
                }
                .product-title {
                    font-size: 13px;
                    margin: 0 0 8px 0;
                    color: #333;
                    line-height: 1.3;
                    max-height: 2.6em;
                    overflow: hidden;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                }
                .product-price {
                    font-size: 14px;
                    font-weight: bold;
                    color: #e44d26;
                    margin: 0 0 8px 0;
                }
                .product-link {
                    display: inline-block;
                    margin: 0;
                    padding: 6px 12px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: background-color 0.2s;
                    text-align: center;
                    font-size: 12px;
                }
                .product-link:hover {
                    background-color: #0056b3;
                }
                .affiliate-disclosure {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #888;
                    font-size: 0.9em;
                    text-align: center;
                }
                @media (max-width: 768px) {
                    .product-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                @media (max-width: 480px) {
                    .product-grid {
                        grid-template-columns: 1fr;
                    }
                }
                """
                style.string = style.string + new_css
            else:
                style_tag = soup.new_tag('style')
                style_tag.string = """
                .product-section {
                    margin: 20px 0;
                    padding: 12px;
                    background-color: #f9f9f9;
                    border-radius: 8px;
                    border-left: 4px solid #007bff;
                    max-width: 100%;
                }
                .product-section h3 {
                    margin-top: 0;
                    color: #333;
                    font-size: 16px;
                }
                .product-grid {
                    display: grid;
                    grid-template-columns: repeat(2, 1fr);
                    gap: 15px;
                    margin: 15px auto;
                    max-width: 100%;
                }
                .product-card {
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                    width: 100%;
                    max-width: 300px;
                    margin: 0 auto;
                    display: flex;
                    flex-direction: column;
                }
                .product-card:hover {
                    transform: translateY(-3px);
                }
                .product-image {
                    width: 100%;
                    height: 120px;
                    text-align: center;
                    overflow: hidden;
                    border-bottom: 1px solid #eee;
                }
                .product-image img {
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }
                .product-info {
                    padding: 10px;
                }
                .product-title {
                    font-size: 13px;
                    margin: 0 0 8px 0;
                    color: #333;
                    line-height: 1.3;
                    max-height: 2.6em;
                    overflow: hidden;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                }
                .product-price {
                    font-size: 14px;
                    font-weight: bold;
                    color: #e44d26;
                    margin: 0 0 8px 0;
                }
                .product-link {
                    display: inline-block;
                    margin: 0;
                    padding: 6px 12px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    transition: background-color 0.2s;
                    text-align: center;
                    font-size: 12px;
                }
                .product-link:hover {
                    background-color: #0056b3;
                }
                .affiliate-disclosure {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #888;
                    font-size: 0.9em;
                    text-align: center;
                }
                @media (max-width: 768px) {
                    .product-grid {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
                @media (max-width: 480px) {
                    .product-grid {
                        grid-template-columns: 1fr;
                    }
                }
                """
                head.append(style_tag)
        
        # 섹션 또는 헤더 태그 찾기
        sections = soup.find_all('div', class_='section')
        
        # 섹션이나 헤더를 기준으로 상품 카드 배치
        if not sections:
            headers = soup.find_all(['h2', 'h3'])
            if headers:
                print(f"✅ {len(headers)}개의 헤더를 찾았습니다.")
                
                # 상품과 헤더 매칭
                section_products, unassigned_products = match_products_to_sections(product_cards, headers)
                
                # 매칭된 헤더에 상품 삽입
                for header, products_in_section in section_products.items():
                    if products_in_section:
                        # 상품 섹션 HTML 생성
                        product_section = f"""
                        <div class="section product-section">
                            <h3>관련 추천 상품</h3>
                            <div class="product-grid">
                                {''.join([p['product']['html'] for p in products_in_section])}
                            </div>
                        </div>
                        """
                        
                        # 상품 섹션 삽입
                        header.insert_after(BeautifulSoup(product_section, 'html.parser'))
                        print(f"✅ {len(products_in_section)}개의 상품 카드를 헤더 다음에 삽입했습니다.")
                
                # 할당되지 않은 상품 처리
                if unassigned_products:
                    # 본문 끝에 남은 상품 추가
                    remaining_section = f"""
                    <div class="section product-section">
                        <h3>더 많은 추천 상품</h3>
                        <div class="product-grid">
                            {''.join([p['html'] for p in unassigned_products[:8]])}
                        </div>
                    </div>
                    """
                    
                    content_div = soup.find('div', class_='content')
                    if content_div:
                        content_div.append(BeautifulSoup(remaining_section, 'html.parser'))
                    else:
                        # content div가 없으면 마지막 헤더 다음에 추가
                        if headers[-1]:
                            headers[-1].insert_after(BeautifulSoup(remaining_section, 'html.parser'))
            else:
                # 헤더가 없으면 기존 방식대로 모든 상품을 한 곳에 모아서 표시
                products_section = f"""
                <div class="section">
                    <h2>추천 상품</h2>
                    <div class="product-grid">
                        {''.join([card['html'] for card in product_cards[:8]])}  <!-- 최대 8개 상품만 표시 -->
                    </div>
                </div>
                """
                
                # 상품 섹션을 요약 HTML에 추가
                body = soup.find('body')
                if body:
                    container = body.find('div', class_='container')
                    if container:
                        container.append(BeautifulSoup(products_section, 'html.parser'))
                    else:
                        body.append(BeautifulSoup(products_section, 'html.parser'))
        else:
            print(f"✅ {len(sections)}개의 섹션을 찾았습니다.")
            
            # 상품과 섹션 매칭
            section_products, unassigned_products = match_products_to_sections(product_cards, sections)
            
            # 매칭된 섹션에 상품 삽입
            for section, products_in_section in section_products.items():
                if products_in_section:
                    # 상품 섹션 HTML 생성
                    product_section = f"""
                    <div class="section product-section">
                        <h3>이 섹션 관련 추천 상품</h3>
                        <div class="product-grid">
                            {''.join([p['product']['html'] for p in products_in_section])}
                        </div>
                    </div>
                    """
                    
                    # 상품 섹션 삽입
                    section.insert_after(BeautifulSoup(product_section, 'html.parser'))
                    print(f"✅ {len(products_in_section)}개의 상품 카드를 섹션 다음에 삽입했습니다.")
            
            # 할당되지 않은 상품 처리
            if unassigned_products:
                # 마지막 섹션 다음에 남은 상품 추가
                remaining_section = f"""
                <div class="section product-section">
                    <h3>더 많은 추천 상품</h3>
                    <div class="product-grid">
                        {''.join([p['html'] for p in unassigned_products[:8]])}
                    </div>
                </div>
                """
                
                if sections[-1]:
                    sections[-1].insert_after(BeautifulSoup(remaining_section, 'html.parser'))
                    print(f"✅ {len(unassigned_products[:8])}개의 미할당 상품 카드를 마지막에 추가했습니다.")
        
        # 제휴 마케팅 문구 추가
        affiliate_disclosure = soup.find('div', class_='affiliate-disclosure')
        if not affiliate_disclosure:
            disclosure_html = """
            <div class="affiliate-disclosure">
                <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
            </div>
            """
            
            # 본문 끝에 추가
            container = soup.find('div', class_='container')
            if container:
                container.append(BeautifulSoup(disclosure_html, 'html.parser'))
            else:
                body = soup.find('body')
                if body:
                    body.append(BeautifulSoup(disclosure_html, 'html.parser'))
        
        # 병합된 HTML 저장 - merged_html 폴더에 저장
        os.makedirs('merged_html', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'merged_html/merged_content_{timestamp}.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        
        # 추가로 posting 폴더에 복사본 저장 (블로거에 바로 업로드하기 위함)
        os.makedirs('posting', exist_ok=True)
        posting_file = f'posting/merged_content_{timestamp}.html'
        
        import shutil
        shutil.copy2(output_file, posting_file)
        
        print(f"✅ HTML 병합 완료: {output_file}")
        print(f"✅ posting 폴더에 복사본 저장: {posting_file}")
        return output_file
        
    except Exception as e:
        print(f"❌ HTML 병합 실패: {str(e)}")
        return None

# 4. 전체 프로세스 처리 함수
def process_youtube_and_products(video_url):
    """YouTube 영상 처리 및 상품 검색"""
    try:
        # 1. YouTube 영상 처리
        video_info = process_youtube_video(video_url)
        if not video_info:
            print("❌ YouTube 영상 처리 실패")
            return None
            
        # 2. 자막 요약
        summary = summarize_text(video_info['transcript'])
        if not summary:
            print("❌ 영상 내용 요약 실패")
            return None
            
        # 유튜브 요약 HTML 파일 먼저 생성 (utube_mtml 폴더에 저장)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        title_slug = ''.join(c if c.isalnum() else '_' for c in video_info.get('title', 'video')[:30])
        youtube_html_file = f'utube_mtml/{title_slug}_{timestamp}.html'
        
        # YouTube 요약 HTML 생성
        youtube_html_content = generate_youtube_html(video_info, summary)
        with open(youtube_html_file, 'w', encoding='utf-8') as f:
            f.write(youtube_html_content)
        
        print(f"✅ YouTube 요약 HTML 파일 생성: {youtube_html_file}")
            
        # 3. 키워드 추출
        keywords = extract_product_keywords(summary)
        if not keywords:
            print("❌ 키워드 추출 실패")
            return None
            
        # 4. 상품 검색
        all_products = []
        for keyword in keywords:
            print(f"\n키워드 '{keyword}'로 상품 검색 중...")
            products = search_products_with_keywords(keyword)
            if products:
                all_products.extend(products)
                
        if not all_products:
            print("❌ 상품 검색 실패")
            return None
        
        # video_info 디버그 출력
        print("\n비디오 정보 확인:")
        for key, value in video_info.items():
            print(f"  - {key}: {value[:50]}..." if isinstance(value, str) and len(value) > 50 else f"  - {key}: {value}")
            
        # 5. HTML 생성
        try:
            # thumbnail_url 키가 없으면 thumbnail 키를 사용하도록 video_info 보정
            if 'thumbnail' in video_info and 'thumbnail_url' not in video_info:
                video_info['thumbnail_url'] = video_info['thumbnail']
            elif 'thumbnail_url' not in video_info and 'thumbnail' not in video_info:
                # 두 키 모두 없는 경우 기본 썸네일 생성
                video_id = extract_video_id(video_url)
                if video_id:
                    video_info['thumbnail_url'] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                else:
                    video_info['thumbnail_url'] = "https://via.placeholder.com/1280x720?text=No+Thumbnail"
                
            html_content = generate_video_html(video_info, summary, all_products)
            if not html_content:
                print("❌ HTML 생성 실패")
                return None
                
            # 6. HTML 파일 저장 - merged_html 폴더에 저장
            os.makedirs('merged_html', exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            title_slug = ''.join(c if c.isalnum() else '_' for c in video_info.get('title', 'video')[:30])
            html_file = f'merged_html/{title_slug}_{timestamp}.html'
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            # posting 폴더에도 복사본 저장
            os.makedirs('posting', exist_ok=True)
            posting_file = f'posting/{title_slug}_{timestamp}.html'
            
            import shutil
            shutil.copy2(html_file, posting_file)
                
        except Exception as e:
            print(f"❌ HTML 생성 중 상세 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
            
        print(f"✅ HTML 파일 경로: {html_file}")
        print(f"✅ posting 폴더에 복사본 저장: {posting_file}")
        
        # 7. 블로그 업로드
        try:
            # HTML 파일에서 제목 추출
            soup = BeautifulSoup(html_content, 'html.parser')
            h1_tag = soup.find('h1')
            h2_tag = soup.find('h2')
            title = h1_tag.text if h1_tag else (h2_tag.text if h2_tag else "YouTube 영상 요약")
            
            # 블로그 업로드 전 확인
            upload_to_blog = input(f"\nHTML 파일이 {html_file}에 저장되었습니다. 블로그에 포스팅하시겠습니까? (y/n): ").lower().strip()
            
            if upload_to_blog == 'y':
                # Blogger API 서비스 객체 얻기
                service = get_credentials()
                if not service:
                    print("❌ Blogger API 서비스 초기화 실패")
                    return html_file
                    
                # config.py에서 블로그 ID 가져오기
                from config import BLOGGER_BLOG_ID
                blog_id = BLOGGER_BLOG_ID
                print(f"🌐 블로그 ID: {blog_id}")
                    
                # 블로그 업로드 - posting 폴더의 파일 전달
                post_url = post_html_to_blogger(service, blog_id, posting_file, title)
                if post_url:
                    print(f"✅ 블로그 업로드 완료: {post_url}")
                else:
                    print("❌ 블로그 업로드 실패")
            else:
                print(f"✅ 블로그 업로드를 건너뛰었습니다. HTML 파일은 {html_file}에 저장되어 있습니다.")
                print(f"✅ 복사본은 {posting_file}에 저장되어 있습니다.")
                print("나중에 html2blogger.py를 사용하여 수동으로 업로드할 수 있습니다.")
        except Exception as e:
            print(f"❌ 블로그 업로드 중 오류 발생: {str(e)}")
            print(f"블로그 업로드는 실패했지만, HTML 파일은 {html_file}에 정상적으로 생성되었습니다.")
        
        return html_file
        
    except Exception as e:
        print(f"❌ 처리 중 오류 발생: {str(e)}")
        return None

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1]
        elif 'youtube.com' in url:
            return url.split('v=')[1].split('&')[0]
        return None
    except Exception as e:
        print(f"❌ 비디오 ID 추출 중 오류 발생: {str(e)}")
        return None

def get_video_info(video_id):
    """YouTube 비디오 정보 가져오기"""
    try:
        # YouTube Data API를 사용하여 비디오 정보 가져오기
        from googleapiclient.discovery import build
        youtube = build('youtube', 'v3', developerKey=os.getenv('YOUTUBE_API_KEY'))
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if not response['items']:
            print("❌ 비디오 정보를 찾을 수 없습니다.")
            return None
            
        video_info = response['items'][0]['snippet']
        
        # 최고 해상도의 썸네일 URL 가져오기
        thumbnails = video_info['thumbnails']
        thumbnail_url = None
        
        # 가능한 최고 해상도 순서대로 확인
        for quality in ['maxres', 'standard', 'high', 'medium', 'default']:
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality]['url']
                print(f"✅ {quality} 해상도 썸네일을 사용합니다.")
                break
        
        if not thumbnail_url and 'thumbnails' in video_info:
            # fallback: 첫 번째로 찾은 썸네일 사용
            thumbnail_url = next(iter(thumbnails.values()))['url']
        
        if not thumbnail_url:
            # 썸네일을 찾을 수 없는 경우
            print("⚠️ 썸네일을 찾을 수 없습니다.")
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        
        return {
            'title': video_info['title'],
            'thumbnail': thumbnail_url,
            'thumbnail_url': thumbnail_url,  # 중복으로 저장하여 안정성 높임
            'description': video_info['description']
        }
    except Exception as e:
        print(f"❌ 비디오 정보 가져오기 중 오류 발생: {str(e)}")
        # 기본 썸네일 URL로 폴백
        return {
            'title': '제목을 가져올 수 없음',
            'description': '설명을 가져올 수 없음',
            'thumbnail': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        }

def get_video_transcript(video_id):
    """YouTube 비디오 자막 가져오기"""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"❌ 자막 가져오기 중 오류 발생: {str(e)}")
        return None

def summarize_text(text):
    """텍스트 요약"""
    try:
        # Gemini API를 사용하여 텍스트 요약
        prompt = f"""
        다음 텍스트를 요약해주세요. 주요 내용과 핵심 포인트를 포함해주세요.
        요약은 마크다운 형식이 아닌 HTML 형식으로 작성해주세요.
        다음과 같은 HTML 태그를 사용하여 구조적으로 작성해주세요:
        - <h2>, <h3> : 제목과 소제목
        - <p> : 단락
        - <ul>, <li> : 목록
        - <strong>, <em> : 강조
        - <div class="section"> : 섹션 구분
        
        블로그 형식으로 깔끔하게 작성해주세요.
        마크다운 코드 블록(```html 또는 ```)을 절대 사용하지 마세요.
        
        텍스트:
        {text}
        """
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        # 마크다운 코드 블록 표시 제거 (```html과 ```)
        response_text = response_text.replace('```html', '')
        response_text = response_text.replace('```', '')
        
        return response_text
    except Exception as e:
        print(f"❌ 텍스트 요약 중 오류 발생: {str(e)}")
        return None

def search_coupang(keyword, max_products=5, price_range=None):
    """쿠팡 API를 통해 상품을 검색합니다."""
    try:
        # 키워드 길이 제한 (쿠팡 API 제한: 50자)
        MAX_KEYWORD_LENGTH = 50
        original_keyword = keyword
        
        if len(keyword) > MAX_KEYWORD_LENGTH:
            keyword = keyword[:MAX_KEYWORD_LENGTH]
            print(f"⚠️ 키워드 길이 초과 ({len(original_keyword)}자): '{original_keyword}'")
            print(f"✂️ 검색 키워드 축소: '{keyword}' ({len(keyword)}자)")
        
        print(f"\n검색: {keyword}")
        print(f"설정: 최대 {max_products}개 상품, 가격 범위: {price_range}")
        
        # 환경 변수에서 API 키 가져오기
        ACCESS_KEY = os.getenv('COUPANG_PARTNERS_ACCESS_KEY')
        SECRET_KEY = os.getenv('COUPANG_PARTNERS_SECRET_KEY')
        
        if not ACCESS_KEY or not SECRET_KEY:
            print("⚠️ 쿠팡 API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
            return []
        
        # API 요청 URL 생성
        DOMAIN = "https://api-gateway.coupang.com"
        REQUEST_METHOD = "GET"
        
        # 채널 ID 및 이미지 크기 설정
        CHANNEL_ID = os.getenv('COUPANG_PARTNERS_VENDOR_ID', '사용할채널ID')
        IMAGE_SIZE = os.getenv('IMAGE_SIZE', '200x200')
        
        # URL 인코딩 및 경로 설정
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            URL = f"/v2/providers/affiliate_open_api/apis/openapi/products/search?keyword={encoded_keyword}&limit={max_products}&subid={CHANNEL_ID}&imageSize={IMAGE_SIZE}"
        except Exception as e:
            print(f"⚠️ URL 인코딩 오류: {str(e)}. 검색어를 확인하세요.")
            return []
        
        if price_range:
            min_price, max_price = price_range
            URL += f"&minPrice={min_price}&maxPrice={max_price}"
        
        # API 서명 생성
        def generate_hmac(method, url, secret_key, access_key):
            path, *query = url.split("?")
            datetime_gmt = strftime('%y%m%d', gmtime()) + 'T' + strftime('%H%M%S', gmtime()) + 'Z'
            message = datetime_gmt + method + path + (query[0] if query else "")
            
            signature = hmac.new(bytes(secret_key, "utf-8"),
                             message.encode("utf-8"),
                             hashlib.sha256).hexdigest()
            
            return "CEA algorithm=HmacSHA256, access-key={}, signed-date={}, signature={}".format(access_key, datetime_gmt, signature)
        
        authorization = generate_hmac(REQUEST_METHOD, URL, SECRET_KEY, ACCESS_KEY)
        url = f"{DOMAIN}{URL}"
        
        # API 호출 시도 (재시도 로직 포함)
        max_retries = 3
        retry_delay = 1  # 초 단위
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=REQUEST_METHOD,
                    url=url,
                    headers={
                        "Authorization": authorization,
                        "Content-Type": "application/json;charset=UTF-8"
                    },
                    timeout=10  # 10초 타임아웃 설정
                )
                
                # 성공적인 응답
                if response.status_code == 200:
                    response_data = response.json()
                    # API 응답에서 상품 데이터 추출
                    if 'data' in response_data and 'productData' in response_data['data']:
                        products = response_data['data']['productData']
                        return products
                    else:
                        print(f"⚠️ API 응답 오류: {response_data}")
                        return []
                        
                # 오류 응답 처리
                else:
                    error_message = f"API 응답 오류: 상태 코드 {response.status_code}"
                    
                    if response.status_code == 401:
                        error_message = "API 인증 실패: API 키를 확인하세요"
                    elif response.status_code == 429:
                        error_message = "API 요청 한도 초과: 잠시 후 다시 시도하세요"
                    elif response.status_code >= 500:
                        error_message = "쿠팡 서버 오류: 잠시 후 다시 시도하세요"
                        
                    print(f"⚠️ {error_message}")
                    
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2 ** attempt)  # 지수 백오프
                        print(f"🔄 {wait_time}초 후 재시도합니다... ({attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                    else:
                        print("❌ 최대 재시도 횟수 초과")
                        return []
                        
            except requests.exceptions.ConnectionError:
                print(f"⚠️ API 연결 오류 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"🔄 {wait_time}초 후 재시도합니다...")
                    time.sleep(wait_time)
                else:
                    print("❌ 최대 재시도 횟수 초과")
                    return []
                    
            except requests.exceptions.Timeout:
                print(f"⚠️ API 요청 시간 초과 (시도 {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"🔄 {wait_time}초 후 재시도합니다...")
                    time.sleep(wait_time)
                else:
                    print("❌ 최대 재시도 횟수 초과")
                    return []
                    
            except Exception as e:
                print(f"⚠️ API 호출 오류: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"🔄 {wait_time}초 후 재시도합니다...")
                    time.sleep(wait_time)
                else:
                    print("❌ 최대 재시도 횟수 초과")
                    return []
        
        # 모든 시도 실패
        return []
                
    except Exception as e:
        print(f"⚠️ API 호출 오류: API 요청 중 오류 발생: {str(e)}")
        return []

def process_products(products, keyword, max_count=5):
    """쿠팡 API로부터 받은 상품 데이터를 가공합니다."""
    processed_products = []
    
    if not products:
        print(f"검색어 '{keyword}'에 대한 상품이 없습니다.")
        return processed_products
    
    # 중복 제거를 위한 ID 집합
    processed_ids = set()
    
    # 상품 정렬 (베스트 셀러, 랭킹 점수 등으로 정렬)
    try:
        # 랭킹 점수가 있으면 그것으로 정렬, 없으면 순서 유지
        sorted_products = sorted(
            products, 
            key=lambda p: (
                p.get('rank', 999999),  # 낮은 순위가 더 좋음
                -p.get('productScore', 0),  # 높은 점수가 더 좋음
                -p.get('productPrice', 0)  # 높은 가격이 더 좋음 (일반적으로 품질 좋은 상품)
            )
        )
    except Exception as e:
        print(f"⚠️ 상품 정렬 중 오류 발생: {str(e)}")
        sorted_products = products
    
    # 최대 개수는 원래 상품 개수와 max_count 중 작은 값
    products_to_process = min(len(sorted_products), max_count)
    print(f"🔍 {products_to_process}개 상품 처리 중...")
    
    # 상품 처리
    for product in sorted_products:
        # 최대 개수에 도달하면 중단
        if len(processed_products) >= max_count:
            break
            
        try:
            # 이미 처리된 상품인지 확인 (중복 제거)
            product_id = product.get('productId')
            if product_id in processed_ids:
                continue
                
            # 필수 필드 확인
            required_fields = ['productId', 'productName', 'productPrice', 'productImage', 'productUrl']
            missing_fields = [field for field in required_fields if field not in product]
            
            if missing_fields:
                print(f"⚠️ 상품에 필수 필드가 누락되었습니다: {missing_fields}")
                continue
            
            # 이미지 URL 처리
            original_image = product['productImage']
            
            # 이미지 URL이 없는 경우
            if not original_image:
                print(f"⚠️ 상품 '{product['productName'][:30]}...'에 이미지 URL이 없습니다. 기본 이미지로 대체합니다.")
                product['productImage'] = 'https://via.placeholder.com/200x200?text=No+Image'
            else:
                # 이미지 URL 정규화 (상대 경로를 절대 경로로 변환)
                if original_image.startswith('//'):
                    original_image = 'https:' + original_image
                elif not original_image.startswith(('http://', 'https://')):
                    original_image = 'https://' + original_image
                
                # 정규화된 URL 저장
                product['productImage'] = original_image
            
            # 가격 정보가 문자열인 경우 숫자로 변환
            if isinstance(product['productPrice'], str):
                try:
                    # 쉼표 제거 후 정수 변환
                    product['productPrice'] = int(product['productPrice'].replace(',', ''))
                except ValueError:
                    print(f"⚠️ 가격 변환 오류: {product['productPrice']}")
            
            # 추가 정보 설정 (없는 경우 기본값 사용)
            product['isRocket'] = product.get('isRocket', False)
            product['isFreeShipping'] = product.get('isFreeShipping', False)
            
            # 상품명에서 쉼표 제거 (CSV 저장 시 문제 방지)
            product['productName'] = product['productName'].replace(',', '')
            
            # 처리된 상품 추가
            processed_products.append(product)
            processed_ids.add(product_id)
            
        except Exception as e:
            print(f"⚠️ 상품 데이터 처리 중 오류 발생: {str(e)}")
            continue
    
    print(f"✅ {len(processed_products)}개의 상품을 성공적으로 처리했습니다.")
    return processed_products

def generate_product_html(products, keyword, extracted_keywords=None):
    """상품 정보를 HTML로 변환하여 반환합니다."""
    if not products:
        return f"<p>'{keyword}'에 대한 검색 결과가 없습니다.</p>"
    
    # 오늘 날짜
    today = datetime.now().strftime("%Y년 %m월 %d일")
    
    # CSS 스타일
    html = f"""
    <style>
    body {{
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}
    .header-section {{
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 25px;
        border-left: 4px solid #4285f4;
    }}
    .keyword-tag {{
        display: inline-block;
        background-color: #e6f2ff;
        color: #0066cc;
        padding: 5px 10px;
        border-radius: 20px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }}
    .cup-list {{
        border: 1px solid #e0e0e0;
        padding: 20px;
        margin-bottom: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }}
    .cup-list:hover {{
        transform: translateY(-3px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}
    .product-name {{
        font-size: 16px;
        margin-bottom: 15px;
        line-height: 1.3;
        height: 65px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }}
    .product-name a {{
        color: #0066cc;
        text-decoration: none;
    }}
    .product-name a:hover {{
        text-decoration: underline;
    }}
    .cup-img {{
        text-align: center;
        margin: 15px 0;
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background-color: #f9f9f9;
        border-radius: 4px;
    }}
    .cup-img img {{
        max-width: 100%;
        max-height: 180px;
        object-fit: contain;
        border-radius: 4px;
        transition: transform 0.3s ease;
    }}
    .cup-img img:hover {{
        transform: scale(1.05);
    }}
    .product-price {{
        font-size: 18px;
        color: #e94d4d;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
    }}
    .delivery-info {{
        color: #666;
        font-size: 14px;
        text-align: center;
    }}
    .product-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
    }}
    .ai-info {{
        background-color: #f5f5f5;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #4285f4;
    }}
    .ai-title {{
        color: #4285f4;
        margin-top: 0;
    }}
    </style>
    """
    
    # AI 정보 섹션 (키워드가 제공된 경우)
    if extracted_keywords:
        html += f"""
        <div class="ai-info">
            <h3 class="ai-title">🤖 Gemini AI 추천 상품</h3>
            <p>AI가 동영상 내용을 분석하여 추출한 키워드로 상품을 검색했습니다.</p>
            <p>추출된 키워드:</p>
            <div>
                {' '.join([f'<span class="keyword-tag">{k}</span>' for k in extracted_keywords])}
            </div>
        </div>
        """
    
    # 상품 리스트 헤더
    html += f"""
    <div class="header-section">
        <h2>쿠팡 검색결과: '{keyword}'</h2>
        <p>{today} 기준 검색 결과입니다.</p>
        <p>검색 결과에서 인기 상품 {len(products)}개를 소개합니다.</p>
        <p style="color: #666; font-size: 12px;">* 이 포스팅은 파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있습니다.</p>
    </div>
    
    <div class="product-grid">
    """
    
    # 상품 정보 추가
    for i, product in enumerate(products):
        try:
            product_name = product['productName']
            product_url = product['productUrl']
            product_price = format(product['productPrice'], ',')
            
            # 원본 이미지 URL
            original_image = product['productImage']
            
            # 다중 프록시 접근 방식: wsrv.nl 이미지 프록시와 플레이스홀더 이미지 폴백 적용
            img_tag = f"""<img src="{original_image}" 
                alt="{product_name}" 
                title="{product_name}"
                width="200"
                height="auto"
                loading="lazy"
                onerror="this.onerror=null; this.src='https://wsrv.nl/?url={urllib.parse.quote(original_image)}&n=0'; this.onerror=function(){{this.src='https://via.placeholder.com/200x200?text=No+Image';}}" />"""
            
            # 상품 정보 HTML 추가
            html += f"""
            <div class="cup-list">
                <div class="product-name">
                    <h3>🔍 상품 #{i + 1}</h3>
                    <a href="{product_url}" target="_blank" rel="nofollow">➡️ {product_name}</a>
                </div>
                <div class="cup-img">
                    <a href="{product_url}" target="_blank" rel="nofollow">
                        {img_tag}
                    </a>
                </div>
                <div class="product-price">
                    💰 판매가: {product_price}원
                </div>
                <div class="delivery-info">
                    🚚 배송: {'🚀 로켓배송' if product.get('isRocket', False) else '일반배송'} 
                    | {'✨ 무료배송' if product.get('isFreeShipping', False) else '유료배송'}
                </div>
            </div>
            """
        except Exception as e:
            print(f"⚠️ 상품 HTML 생성 중 오류 발생: {str(e)}")
            continue
    
    # 그리드 닫기
    html += "</div>"
    
    # 마무리 내용
    html += f"""
    <hr/>
    <h3>마무리</h3>
    <p>지금까지 {today} 기준 AI가 추천한 '{keyword}' 관련 상품 리스트 총 {len(products)}개를 공유하였습니다.</p>
    <p>구매하시기 전에 상품의 구체적인 정보와 최신 가격을 확인하시기 바랍니다.</p>
    <p>이 포스팅이 여러분의 현명한 쇼핑에 도움이 되었길 바랍니다! 😊</p>
    <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
    """
    
    return html

def generate_integrated_html(video_info, summary, products, keywords):
    """
    YouTube 영상 요약, 썸네일, 쿠팡 제품을 통합한 HTML을 생성합니다.
    """
    # 오늘 날짜
    today = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 썸네일 URL 확인
    thumbnail_url = video_info.get('thumbnail', '')
    if not thumbnail_url:
        # 썸네일이 없는 경우 기본 이미지 사용
        thumbnail_url = f"https://img.youtube.com/vi/{video_info.get('id', '')}/maxresdefault.jpg"
    
    # HTML 시작 부분
    html = f"""
    <style>
    body {{
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}
    .video-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 30px;
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .video-info {{
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}
    .video-thumbnail {{
        width: 100%;
        max-width: 640px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }}
    .video-title {{
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
        color: #212121;
    }}
    .video-meta {{
        display: flex;
        align-items: center;
        justify-content: center;
        color: #606060;
        margin-bottom: 15px;
    }}
    .channel-name {{
        margin-right: 10px;
    }}
    .view-count::before {{
        content: "•";
        margin: 0 5px;
    }}
    .summary-container {{
        width: 100%;
        margin-top: 20px;
    }}
    .summary-title {{
        font-size: 20px;
        margin-bottom: 15px;
        color: #212121;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 10px;
    }}
    .keyword-tag {{
        display: inline-block;
        background-color: #e6f2ff;
        color: #0066cc;
        padding: 5px 10px;
        border-radius: 20px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }}
    .products-container {{
        margin-top: 40px;
    }}
    .products-title {{
        font-size: 22px;
        margin-bottom: 20px;
        color: #212121;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 10px;
    }}
    .product-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-top: 20px;
    }}
    .cup-list {{
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        background-color: white;
        display: flex;
        flex-direction: column;
        height: 100%;
    }}
    .cup-list:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.15);
    }}
    .product-name {{
        font-size: 16px;
        margin-bottom: 15px;
        line-height: 1.3;
        height: 65px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }}
    .product-name a {{
        color: #0066cc;
        text-decoration: none;
    }}
    .product-name a:hover {{
        text-decoration: underline;
    }}
    .cup-img {{
        text-align: center;
        margin: 15px 0;
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background-color: #f9f9f9;
        border-radius: 4px;
    }}
    .cup-img img {{
        max-width: 100%;
        max-height: 180px;
        object-fit: contain;
        border-radius: 4px;
        transition: transform 0.3s ease;
    }}
    .cup-img img:hover {{
        transform: scale(1.05);
    }}
    .product-price {{
        font-size: 18px;
        color: #e94d4d;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
    }}
    .delivery-info {{
        color: #666;
        font-size: 14px;
    }}
    .ai-info {{
        background-color: #f0f7ff;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0;
        border-left: 4px solid #4285f4;
    }}
    .ai-title {{
        color: #4285f4;
        margin-top: 0;
    }}
    .footer {{
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        text-align: center;
        color: #666;
        font-size: 14px;
    }}
    .watch-btn {{
        display: inline-block;
        background-color: #FF0000;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 15px;
        transition: background-color 0.2s;
    }}
    .watch-btn:hover {{
        background-color: #D60000;
    }}
    .section {{
        margin-bottom: 30px;
    }}
    @media (max-width: 768px) {{
        .product-grid {{
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .cup-list {{
            padding: 15px;
        }}
    }}
    @media (max-width: 480px) {{
        .product-grid {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>

   

   

    <div class="summary-container">
       
        <div class="summary-content">
            {summary}
        </div>
    </div>
    """
    
    # 상품 섹션 추가
    if products:
        html += f"""
        <div class="products-container">
            <h2 class="products-title">🛒 관련 추천 상품</h2>
           
            <div class="product-grid">
        """
        
        # 상품 정보 추가
        for i, product in enumerate(products):
            try:
                product_name = product['productName']
                product_url = product['productUrl']
                product_price = format(product['productPrice'], ',')
                
                # 원본 이미지 URL
                original_image = product['productImage']
                
                # 이미지 처리 개선: Blogger용 직접 URL 사용 및 인라인 스타일 추가
                img_tag = f"""<img src="{original_image}" 
                    alt="{product_name}" 
                    title="{product_name}"
                    loading="lazy"
                    style="max-width: 100%; max-height: 180px; display: block; margin: 0 auto; border-radius: 4px; transition: transform 0.3s ease;"
                    onmouseover="this.style.transform='scale(1.05)'" 
                    onmouseout="this.style.transform='scale(1)'"
                    onerror="this.onerror=null; if (!this.src.includes('wsrv.nl')) {{this.src='https://wsrv.nl/?url={urllib.parse.quote(original_image)}&default=https://via.placeholder.com/200x200?text=No+Image&n=-1';}} else {{this.src='https://via.placeholder.com/200x200?text=No+Image';}}" />"""
                
                # 상품 정보 HTML 추가
                html += f"""
                <div class="cup-list" style="border: 1px solid #e0e0e0; padding: 20px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.08); transition: all 0.3s ease; background-color: white; display: flex; flex-direction: column; height: 100%;">
                    <div class="product-name" style="font-size: 16px; margin-bottom: 15px; line-height: 1.3; height: 65px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
                        <a href="{product_url}" target="_blank" rel="nofollow" style="color: #0066cc; text-decoration: none;">
                            {product_name}
                        </a>
                    </div>
                    <div class="cup-img" style="text-align: center; margin: 15px 0; height: 200px; display: flex; align-items: center; justify-content: center; overflow: hidden; background-color: #f9f9f9; border-radius: 4px;">
                        <a href="{product_url}" target="_blank" rel="nofollow">
                            {img_tag}
                        </a>
                    </div>
                    <div style="margin-top: auto;">
                        <div class="product-price" style="font-size: 18px; color: #e94d4d; font-weight: bold; margin: 10px 0; text-align: center;">
                            💰 {product_price}원
                        </div>
                        <div class="delivery-info" style="color: #666; font-size: 14px; text-align: center;">
                            {'🚀 로켓배송' if product.get('isRocket', False) else '일반배송'} 
                            | {'✨ 무료배송' if product.get('isFreeShipping', False) else '유료배송'}
                        </div>
                    </div>
                </div>
                """
            except Exception as e:
                print(f"⚠️ 상품 HTML 생성 중 오류 발생: {str(e)}")
                continue
        
        # 상품 그리드 닫기
        html += """
            </div>
        </div>
        """
    
    # 푸터 추가
    html += f"""
    <div class="footer">
       
        <p>"이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."</p>
    </div>
    """
    
    return html

def post_to_blogger(html_file_path, title):
    """HTML 파일을 블로거에 포스팅하는 함수"""
    try:
        print("\n=== 블로그 선택 ===")
        print(get_blog_list_text())
        blog_number = select_blog()
        set_blog_id(blog_number)
        
        service = get_credentials()
        if not service:
            print("❌ Blogger API 서비스 생성 실패")
            return False
            
        # BLOGGER_BLOG_ID 값 사용 (blog_number가 아님)
        from config import BLOGGER_BLOG_ID
        print(f"🌐 선택된 블로그 ID: {BLOGGER_BLOG_ID}")
            
        return post_html_to_blogger(service, BLOGGER_BLOG_ID, html_file_path, title)
    except Exception as e:
        print(f"❌ 블로거 포스팅 중 오류 발생: {str(e)}")
        return False

def get_unchecked_youtube_url_from_sheet(force_new_token=False):
    """구글 시트에서 체크되지 않은 YouTube URL을 하나 가져옵니다.
    모든 워크시트를 순차적으로 확인하여 체크되지 않은 URL을 찾습니다."""
    try:
        # 환경 변수에서 시트 ID와 시트 이름 가져오기
        spreadsheet_id = os.getenv('GOOGLE_SHEET_ID', '1eQl-BUMzAkP9gxX56eokwpz31_CstqTz_06rgByEw1A')
            
        if not spreadsheet_id:
            print("❌ 구글 시트 ID가 설정되지 않았습니다.")
            return None
            
        # 필요한 모듈 가져오기
        try:
            import gspread
            from google.oauth2.service_account import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import pickle
        except ImportError:
            print("❌ gspread 모듈이 설치되어 있지 않습니다. 다음 명령어로 설치하세요:")
            print("pip install gspread google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return None
            
        # Google API 스코프 설정 - 충분한 권한을 가진 스코프 설정
        SCOPES = [
            'https://www.googleapis.com/auth/blogger',
            'https://www.googleapis.com/auth/blogger.readonly',
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        
        # OAuth 인증 시도
        creds = None
        token_file = 'token.pickle'
        
        # 강제로 새 토큰 생성이 요청된 경우 기존 토큰 파일 삭제
        if force_new_token and os.path.exists(token_file):
            print("🔄 기존 토큰 파일을 삭제하고 새로 인증합니다...")
            os.remove(token_file)
        
        if os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"❌ 토큰 파일 읽기 실패: {str(e)}")
                import traceback
                traceback.print_exc()
                pass
        
        # 토큰이 없거나 만료된 경우 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✅ 기존 토큰 갱신 성공")
                except Exception as e:
                    print(f"❌ 토큰 갱신 실패: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    print("\n💡 토큰 갱신이 실패했습니다. 새로운 인증을 시도합니다.")
            else:
                if os.path.exists('client_secret.json'):
                    try:
                        print("\n🔐 브라우저가 열리면 Google 계정으로 로그인하고 요청된 권한을 허용해주세요.")
                        print("💡 권한 허용 후 'localhost로 연결할 수 없음' 메시지가 표시되어도 정상입니다.")
                        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
                        creds = flow.run_local_server(port=0)
                        # 토큰 저장
                        with open(token_file, 'wb') as token:
                            pickle.dump(creds, token)
                        print("✅ OAuth 인증 성공 및 토큰 저장 완료")
                    except Exception as e:
                        print(f"❌ OAuth 인증 실패: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        print("\n💡 OAuth 인증 실패 해결 방법:")
                        print("1. client_secret.json 파일이 올바른지 확인하세요.")
                        print("2. Google Cloud Console에서 해당 프로젝트에 OAuth 동의 화면이 구성되어 있는지 확인하세요.")
                        print("3. Google Cloud Console에서 해당 프로젝트에 OAuth 클라이언트 ID가 생성되어 있는지 확인하세요.")
                        return None
                else:
                    print("❌ client_secret.json 파일이 없어 OAuth 인증을 진행할 수 없습니다.")
                    print("\n💡 client_secret.json 파일 생성 방법:")
                    print("1. https://console.cloud.google.com/apis/credentials 페이지로 이동합니다.")
                    print("2. '사용자 인증 정보 만들기' > 'OAuth 클라이언트 ID'를 선택합니다.")
                    print("3. 애플리케이션 유형으로 '데스크톱 앱'을 선택합니다.")
                    print("4. 이름을 입력하고 '만들기'를 클릭합니다.")
                    print("5. 'JSON 다운로드' 버튼을 클릭하여 client_secret.json 파일을 다운로드합니다.")
                    print("6. 다운로드한 파일을 이 프로그램의 실행 디렉토리에 'client_secret.json' 이름으로 저장합니다.")
                    return None
        
        # gspread 클라이언트 생성
        try:
            client = gspread.authorize(creds)
            print("✅ OAuth로 인증 성공")
        except Exception as e:
            print(f"❌ gspread 인증 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        
        # 스프레드시트 접근 시도
        try:
            print(f"📄 스프레드시트 ID: {spreadsheet_id} 접근 시도...")
            spreadsheet = client.open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"❌ 스프레드시트를 찾을 수 없습니다. ID: {spreadsheet_id}")
            print("💡 스프레드시트가 존재하고 접근 권한이 있는지 확인하세요.")
            return None
        except Exception as e:
            print(f"❌ 스프레드시트 접근 오류: {str(e)}")
            print("\n--- 상세 오류 정보 ---")
            import traceback
            traceback.print_exc()
            print("\n--- 권한 확인 사항 ---")
            print("1. 스프레드시트가 '링크가 있는 모든 사용자'와 공유되어 있는지 확인하세요.")
            print("2. 또는 현재 로그인한 Google 계정을 스프레드시트에 공유하세요.")
            return None
            
        # 워크시트 목록 확인
        try:
            worksheets = spreadsheet.worksheets()
            worksheet_names = [ws.title for ws in worksheets]
            print(f"📋 스프레드시트의 시트 목록: {', '.join(worksheet_names)}")
            
            if not worksheets:
                print("❌ 스프레드시트에 워크시트가 없습니다.")
                return None
                
        except Exception as e:
            print(f"❌ 워크시트 목록 가져오기 실패: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        
        # 열 인덱스 설정
        check_col = 0  # A열 (체크박스)
        url_col = 2    # C열 (URL)
        
        print(f"✅ 체크 열: A열, URL 열: C열 사용")
        
        # 모든 워크시트를 순환하며 체크되지 않은 URL 찾기
        print("\n🔍 모든 워크시트에서 체크되지 않은 URL 검색 중...")
        
        for worksheet in worksheets:
            print(f"\n📊 '{worksheet.title}' 시트 확인 중...")
            
            # 시트 데이터 가져오기
            try:
                data = worksheet.get_all_values()
                print(f"✅ '{worksheet.title}' 시트 데이터 로드 성공 (행: {len(data)}개)")
                
                if not data or len(data) <= 1:  # 헤더만 있거나 비어있음
                    print(f"⚠️ '{worksheet.title}' 시트에 데이터가 없습니다. 다음 시트로 넘어갑니다.")
                    continue
                    
                # 체크되지 않은 URL 찾기
                for i in range(1, len(data)):
                    row = data[i]
                    if len(row) <= url_col:
                        # URL 열이 없는 경우 다음 행으로
                        continue
                        
                    url = row[url_col].strip() if url_col < len(row) else ""
                    check_value = row[check_col].strip() if check_col < len(row) and len(row) > 0 else ""
                    
                    # 체크박스 상태 디버깅 정보 출력
                    print(f"행 {i+1}: 체크박스 값 = '{check_value}', URL = '{url}'")
                    
                    # URL이 있고 체크박스가 체크되지 않은 경우 (FALSE 또는 빈 값)
                    if url and not url.startswith("#") and (check_value == "FALSE" or check_value == ""):
                        try:
                            # 체크 표시 업데이트 (TRUE로 설정)
                            cell = gspread.utils.rowcol_to_a1(i+1, check_col+1)
                            print(f"📝 '{worksheet.title}' 시트의 {i+1}행 ({cell} 셀) 체크 업데이트 시도 중...")
                            # update_cell 메서드는 행, 열, 값 형식으로 사용 (1-indexed)
                            worksheet.update_cell(i+1, check_col+1, "TRUE")
                            print(f"✅ '{worksheet.title}' 시트의 {i+1}행 체크 완료: {url}")
                            return url
                        except Exception as e:
                            print(f"⚠️ 체크 업데이트 실패: {str(e)}")
                            import traceback
                            traceback.print_exc()
                            print("💡 체크 업데이트 실패 이유:")
                            print("  1. 스프레드시트에 대한 '편집자' 권한이 없을 수 있습니다.")
                            print("  2. 네트워크 연결 문제가 있을 수 있습니다.")
                            print("  3. Google API 할당량 제한에 도달했을 수 있습니다.")
                            # 업데이트 실패해도 URL은 반환
                            return url
                
                print(f"📢 '{worksheet.title}' 시트에서 체크되지 않은 URL을 찾지 못했습니다. 다음 시트로 넘어갑니다.")
                
            except Exception as e:
                print(f"❌ '{worksheet.title}' 시트 데이터 로드 실패: {str(e)}")
                print("다음 시트로 넘어갑니다.")
                continue
        
        print("\n📢 모든 워크시트에서 체크되지 않은 URL을 찾지 못했습니다.")
        return None
        
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 시스템 정보 출력
        import sys
        import platform
        print("\n--- 시스템 정보 ---")
        print(f"Python 버전: {sys.version}")
        print(f"운영체제: {platform.system()} {platform.release()}")
        
        try:
            # 설치된 패키지 버전 확인
            import pkg_resources
            print("\n--- 관련 패키지 버전 ---")
            for pkg in ['gspread', 'google-auth', 'google-auth-oauthlib', 'google-api-python-client']:
                try:
                    version = pkg_resources.get_distribution(pkg).version
                    print(f"{pkg}: {version}")
                except:
                    print(f"{pkg}: 설치되지 않음")
        except:
            pass
            
        return None

def main():
    """메인 함수"""
    try:
        # 0. 환경 변수 로드
        load_dotenv()
        
        # 1. 유튜브 정보 가져오기 (1차 시도)
        video_url = get_unchecked_youtube_url_from_sheet()
        
        # 첫 시도 실패 시 토큰 재생성 후 재시도
        if not video_url:
            print("\n🔄 인증 토큰을 재생성하여 다시 시도합니다...\n")
            video_url = get_unchecked_youtube_url_from_sheet(force_new_token=True)
            
            # 그래도 실패하면 OAuth 스코프 문제를 안내하고 종료
            if not video_url:
                print("\n❌ 구글 시트 접근에 지속적으로 실패했습니다.")
                print("\n💡 가능한 해결 방법:")
                print("1. token.pickle 파일을 수동으로 삭제하고 다시 시도하세요.")
                print("2. 구글 클라우드 콘솔에서 해당 프로젝트의 OAuth 동의 화면에서 스코프를 확인하세요.")
                print("3. 스프레드시트가 현재 로그인한 계정과 공유되어 있는지 확인하세요.")
                print("4. 스프레드시트를 '링크가 있는 모든 사용자'와 공유해보세요.")
                print("5. 스프레드시트 ID가 올바른지 확인하세요: " + os.getenv('GOOGLE_SHEET_ID', '1eQl-BUMzAkP9gxX56eokwpz31_CstqTz_06rgByEw1A'))
                print("\n🔚 프로그램을 종료합니다.")
                return
        
        if video_url:
            print(f"✅ 구글 시트에서 가져온 URL: {video_url}")
        else:
            # 시트에서 URL을 가져오지 못한 경우 종료
            print("🔚 프로그램을 종료합니다.")
            return
        
        if not video_url:
            print("❌ YouTube URL이 필요합니다.")
            return
        
        try:
            # 비디오 정보 및 자막 가져오기
            print("\n===== YouTube 영상 처리 중 =====")
            video_id = get_video_id(video_url)
            if not video_id:
                print("❌ 잘못된 YouTube URL입니다.")
                return
                    
            video_info = get_video_info(video_id)
            if not video_info:
                print("❌ 비디오 정보를 가져올 수 없습니다.")
                return
                    
            print(f"✅ 영상 제목: {video_info['title']}")
            
            # 자막 가져오기 및 요약
            transcript = get_transcript(video_id)
            if not transcript:
                print("❌ 자막을 가져올 수 없습니다.")
                return
                    
            summary = summarize_text(transcript)
            if not summary:
                print("❌ 내용을 요약할 수 없습니다.")
                return
                    
            # Gemini AI로 키워드 추출
            print("\n===== Gemini AI로 키워드 추출 중 =====")
            keywords = extract_product_keywords(summary)
            
            if not keywords or len(keywords) == 0:
                print("❌ 키워드 추출 실패. 영상 제목을 키워드로 사용합니다.")
                # 영상 제목을 키워드로 사용할 때 길이 제한 적용
                MAX_KEYWORD_LENGTH = 50
                title_keyword = video_info['title']
                if len(title_keyword) > MAX_KEYWORD_LENGTH:
                    title_keyword = title_keyword[:MAX_KEYWORD_LENGTH]
                    print(f"⚠️ 제목 길이 초과 ({len(video_info['title'])}자): '{video_info['title']}'")
                    print(f"✂️ 키워드로 사용할 제목 축소: '{title_keyword}' ({len(title_keyword)}자)")
                keywords = [title_keyword]
            
            print(f"✅ 추출된 키워드: {', '.join(keywords)}")
            
        except Exception as e:
            print(f"⚠️ YouTube 영상 처리 오류: {str(e)}")
            return
            
        # 2. 상품 개수 설정 - 묻지 않고 기본값 10개로 설정
        max_products = 10
        print(f"\n검색할 상품 개수를 자동으로 {max_products}개로 설정했습니다.")
        
        # 3. 각 키워드로 상품 검색 및 결과 합치기
        all_products = []
        for keyword in keywords:
            print(f"\n===== 키워드 '{keyword}'로 상품 검색 중 =====")
            products = search_coupang(keyword, max_products)
            
            if products:
                # 중복 제거를 위해 이미 추가된 상품 ID 저장
                existing_ids = {p.get('productId') for p in all_products}
                
                # 신규 상품만 추가
                for product in products:
                    if product.get('productId') not in existing_ids:
                        all_products.append(product)
                        existing_ids.add(product.get('productId'))
                
                print(f"✅ '{keyword}' 키워드로 {len(products)}개 상품 찾음")
            else:
                print(f"⚠️ '{keyword}' 키워드로 상품을 찾을 수 없음")
        
        if not all_products:
            print("❌ 모든 키워드에 대해 상품 검색 실패")
            return
                
        print(f"\n✅ 총 {len(all_products)}개의 상품을 찾았습니다")
        
        # 4. 상품 데이터 가공 (중복 제거 및 정리)
        main_keyword = keywords[0]  # 첫 번째 키워드를 메인 키워드로 사용
        processed_products = process_products(all_products, main_keyword, max_products)
        
        if not processed_products:
            print("❌ 처리할 상품 데이터가 없습니다.")
            return
            
        # 5. 통합 HTML 생성 (요약, 썸네일, 제품 정보 포함)
        html_content = generate_integrated_html(
            video_info=video_info, 
            summary=summary, 
            products=processed_products, 
            keywords=keywords
        )
        
        # 6. HTML 파일로 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        html_dir = 'output'
        
        if not os.path.exists(html_dir):
            os.makedirs(html_dir)
            print(f"✅ '{html_dir}' 폴더를 생성했습니다.")
        
        # YouTube 제목과 키워드를 파일명에 포함
        safe_title = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in video_info['title'])[:30]
        filename = f"integrated_{safe_title}_{timestamp}.html"
        filepath = os.path.join(html_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # 전체 HTML 문서 구조 추가
            full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{video_info['title']} - 요약 및 추천 상품</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    body {{
        font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 1200px;
        margin: 0 auto;
        padding: 20px;
    }}
    .video-container {{
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-bottom: 30px;
        background-color: #f9f9f9;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .video-info {{
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
    }}
    .video-thumbnail {{
        width: 100%;
        max-width: 640px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.2);
    }}
    .video-title {{
        font-size: 24px;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
        color: #212121;
    }}
    .video-meta {{
        display: flex;
        align-items: center;
        justify-content: center;
        color: #606060;
        margin-bottom: 15px;
    }}
    .channel-name {{
        margin-right: 10px;
    }}
    .view-count::before {{
        content: "•";
        margin: 0 5px;
    }}
    .summary-container {{
        width: 100%;
        margin-top: 20px;
    }}
    .summary-title {{
        font-size: 20px;
        margin-bottom: 15px;
        color: #212121;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 10px;
    }}
    .keyword-tag {{
        display: inline-block;
        background-color: #e6f2ff;
        color: #0066cc;
        padding: 5px 10px;
        border-radius: 20px;
        margin-right: 8px;
        margin-bottom: 8px;
        font-size: 14px;
    }}
    .products-container {{
        margin-top: 40px;
    }}
    .products-title {{
        font-size: 22px;
        margin-bottom: 20px;
        color: #212121;
        border-bottom: 2px solid #e0e0e0;
        padding-bottom: 10px;
    }}
    .product-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-top: 20px;
    }}
    .cup-list {{
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        background-color: white;
        display: flex;
        flex-direction: column;
        height: 100%;
    }}
    .cup-list:hover {{
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.15);
    }}
    .product-name {{
        font-size: 16px;
        margin-bottom: 15px;
        line-height: 1.3;
        height: 65px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }}
    .product-name a {{
        color: #0066cc;
        text-decoration: none;
    }}
    .product-name a:hover {{
        text-decoration: underline;
    }}
    .cup-img {{
        text-align: center;
        margin: 15px 0;
        height: 200px;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        background-color: #f9f9f9;
        border-radius: 4px;
    }}
    .cup-img img {{
        max-width: 100%;
        max-height: 180px;
        object-fit: contain;
        border-radius: 4px;
        transition: transform 0.3s ease;
    }}
    .cup-img img:hover {{
        transform: scale(1.05);
    }}
    .product-price {{
        font-size: 18px;
        color: #e94d4d;
        font-weight: bold;
        margin: 10px 0;
        text-align: center;
    }}
    .delivery-info {{
        color: #666;
        font-size: 14px;
    }}
    .ai-info {{
        background-color: #f0f7ff;
        padding: 15px;
        border-radius: 8px;
        margin: 20px 0;
        border-left: 4px solid #4285f4;
    }}
    .ai-title {{
        color: #4285f4;
        margin-top: 0;
    }}
    .footer {{
        margin-top: 40px;
        padding-top: 20px;
        border-top: 1px solid #eee;
        text-align: center;
        color: #666;
        font-size: 14px;
    }}
    .watch-btn {{
        display: inline-block;
        background-color: #FF0000;
        color: white;
        padding: 10px 20px;
        border-radius: 4px;
        text-decoration: none;
        font-weight: bold;
        margin-top: 15px;
        transition: background-color 0.2s;
    }}
    .watch-btn:hover {{
        background-color: #D60000;
    }}
    .section {{
        margin-bottom: 30px;
    }}
    @media (max-width: 768px) {{
        .product-grid {{
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}
        .cup-list {{
            padding: 15px;
        }}
    }}
    @media (max-width: 480px) {{
        .product-grid {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
            f.write(full_html)
        
        print(f"\n✅ HTML 파일이 성공적으로 생성되었습니다: {os.path.abspath(filepath)}")
        
        # 7. 브라우저에서 HTML 파일 열기
        try:
            webbrowser.open('file://' + os.path.abspath(filepath))
            print("✅ 생성된 HTML 파일을 웹 브라우저에서 열었습니다.")
        except Exception as e:
            print(f"⚠️ 파일을 브라우저에서 열지 못했습니다: {str(e)}")
            print(f"💡 다음 경로에서 파일을 수동으로 열어주세요: {os.path.abspath(filepath)}")
        
        # 8. 블로그 업로드 (Blogger) - 자동 업로드로 설정
        try:
            from html2blogger import post_html_to_blogger, get_credentials
            
            # 블로그 업로드 자동 진행
            print("\n===== 블로그에 자동으로 포스팅 중 =====")
            
            # config.py에서 블로그 ID 가져오기
            from config import BLOGGER_BLOG_ID
            blog_id = BLOGGER_BLOG_ID
            print(f"🌐 블로그 ID: {blog_id}")
            
            # 블로거 서비스 얻기 (자동으로 토큰 재생성 시도)
            service = get_credentials()
            if not service:
                print("⚠️ Blogger API 인증에 실패했습니다. 토큰을 재생성하여 다시 시도합니다...")
                service = get_credentials(force_new_token=True)
            
            if not service:
                print("❌ Blogger API 인증에 계속 실패했습니다.")
                print("💡 아래 명령어로 수동으로 업로드를 시도하세요:")
                print(f"python html2blogger.py --posting {filepath} --force-new-token")
                
                # 포스팅 폴더에 실패한 파일 저장
                posting_dir = 'posting'
                if not os.path.exists(posting_dir):
                    os.makedirs(posting_dir)
                
                posting_file = os.path.join(posting_dir, f"failed_{safe_title}_{timestamp}.html")
                shutil.copy2(filepath, posting_file)
                print(f"⚠️ 실패한 HTML 파일을 {posting_dir} 폴더에 복사했습니다.")
            else:
                # 블로그에 포스팅할 제목 설정
                post_title = f"{video_info['title']} - 상품 추천"
                
                # 포스팅 시도
                if post_html_to_blogger(service, blog_id, filepath, post_title):
                    print("✅ 블로그에 성공적으로 포스팅되었습니다!")
                    
                    # 포스팅 폴더에 복사본 저장
                    posting_dir = 'posting'
                    if not os.path.exists(posting_dir):
                        os.makedirs(posting_dir)
                    
                    posting_file = os.path.join(posting_dir, f"posted_{safe_title}_{timestamp}.html")
                    shutil.copy2(filepath, posting_file)
                    print(f"✅ 포스팅된 HTML 파일을 {posting_dir} 폴더에 복사했습니다.")
                else:
                    print("❌ 블로그 포스팅에 실패했습니다.")
                    
                    # 포스팅 폴더에 실패한 파일 저장
                    posting_dir = 'posting'
                    if not os.path.exists(posting_dir):
                        os.makedirs(posting_dir)
                    
                    posting_file = os.path.join(posting_dir, f"failed_{safe_title}_{timestamp}.html")
                    shutil.copy2(filepath, posting_file)
                    print(f"⚠️ 실패한 HTML 파일을 {posting_dir} 폴더에 복사했습니다.")
                    print(f"💡 다음 명령으로 다시 시도할 수 있습니다: python html2blogger.py --posting {posting_file} --force-new-token")
                    
        except ImportError:
            print("⚠️ html2blogger 모듈을 불러올 수 없습니다.")
            print("💡 다음 명령으로 직접 업로드할 수 있습니다: python html2blogger.py --posting " + filepath)
        except Exception as e:
            print(f"⚠️ 블로그 업로드 과정에서 오류가 발생했습니다: {str(e)}")
            import traceback
            traceback.print_exc()
        
    except KeyboardInterrupt:
        print("\n\n프로그램이 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n⚠️ 예상치 못한 오류가 발생했습니다: {str(e)}")
        import traceback
        traceback.print_exc()

def generate_alternative_keywords(keyword):
    """원래 키워드에서 파생된 대체 키워드를 생성합니다."""
    words = keyword.split()
    
    alternatives = []
    
    # 원래 키워드에서 단어 하나씩 제거
    if len(words) > 1:
        for i in range(len(words)):
            alt = ' '.join(words[:i] + words[i+1:])
            alternatives.append(alt)
    
    # 일반적인 브랜드나 카테고리 추가
    if '라켓' in keyword or '테니스' in keyword:
        alternatives.extend(['테니스 라켓', '요넥스 라켓', '윌슨 라켓'])
    elif '노트북' in keyword:
        alternatives.extend(['노트북', '삼성 노트북', 'LG 노트북'])
    elif '카메라' in keyword:
        alternatives.extend(['카메라', '디지털카메라', '캐논 카메라'])
    
    # 중복 제거
    alternatives = list(dict.fromkeys(alternatives))
    
    # 원래 키워드와 동일한 항목 제거
    if keyword in alternatives:
        alternatives.remove(keyword)
    
    # 최대 3개의 대체 키워드만 반환
    return alternatives[:3]

def get_youtube_info(youtube_url):
    """YouTube URL에서 비디오 정보를 추출합니다."""
    try:
        print(f"\n✅ YouTube URL 처리 중: {youtube_url}")
        
        # 비디오 ID 추출
        video_id = None
        if 'youtube.com' in youtube_url or 'youtu.be' in youtube_url:
            # youtu.be 형식의 URL
            if 'youtu.be' in youtube_url:
                video_id = youtube_url.split('/')[-1].split('?')[0]
            # youtube.com 형식의 URL
            else:
                parsed_url = urlparse(youtube_url)
                query_params = parse_qs(parsed_url.query)
                video_id = query_params.get('v', [None])[0]
        
        if not video_id:
            print("⚠️ YouTube URL에서 비디오 ID를 추출할 수 없습니다.")
            return None
            
        print(f"✅ 비디오 ID: {video_id}")
            
        # yt-dlp로 비디오 정보 가져오기
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                
                if not info:
                    print("⚠️ 비디오 정보를 가져올 수 없습니다.")
                    return None
                
                # 필요한 정보 추출
                video_info = {
                    'id': video_id,
                    'title': info.get('title', '제목 없음'),
                    'channel': info.get('uploader', '채널명 없음'),
                    'description': info.get('description', '설명 없음'),
                    'thumbnail': info.get('thumbnail', None),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', '알 수 없음')
                }
                
                # 썸네일 URL 처리
                if 'thumbnails' in info and info['thumbnails']:
                    # 가장 고해상도 썸네일 선택
                    thumbnails = sorted(info['thumbnails'], 
                                       key=lambda x: x.get('height', 0) * x.get('width', 0) 
                                       if x.get('height') and x.get('width') else 0, 
                                       reverse=True)
                    video_info['thumbnail'] = thumbnails[0]['url']
                
                print(f"✅ 비디오 정보 추출 완료: {video_info['title']}")
                return video_info
                
            except Exception as e:
                print(f"⚠️ 비디오 정보 추출 중 오류 발생: {str(e)}")
                return None
                
    except Exception as e:
        print(f"⚠️ YouTube 정보 처리 중 오류 발생: {str(e)}")
        return None

def post_to_blogger(html_file_path, title):
    """HTML 파일을 블로거에 포스팅하는 함수"""
    try:
        print("\n=== 블로그 선택 ===")
        print(get_blog_list_text())
        blog_number = select_blog()
        set_blog_id(blog_number)
        
        service = get_credentials()
        if not service:
            print("❌ Blogger API 서비스 생성 실패")
            return False
            
        # BLOGGER_BLOG_ID 값 사용 (blog_number가 아님)
        from config import BLOGGER_BLOG_ID
        print(f"🌐 선택된 블로그 ID: {BLOGGER_BLOG_ID}")
            
        return post_html_to_blogger(service, BLOGGER_BLOG_ID, html_file_path, title)
    except Exception as e:
        print(f"❌ 블로거 포스팅 중 오류 발생: {str(e)}")
        return False

if __name__ == "__main__":
    main()
# https://www.youtube.com/watch?v=w6has5JyZoA&ab_channel=%ED%85%8C%EB%8B%88%EC%8A%A4%EB%B0%A9%EB%9E%91%EA%B8%B0