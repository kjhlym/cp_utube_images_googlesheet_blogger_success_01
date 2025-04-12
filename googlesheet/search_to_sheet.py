#!/usr/bin/env python3
"""
YouTube 검색 결과를 Google Sheets에 저장하는 CLI 프로그램
"""

import os
import sys
import argparse
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from typing import List, Dict, Any
import json

# OAuth 2.0 인증 범위 설정
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_credentials() -> Credentials:
    """Google API 인증 정보를 가져옵니다."""
    creds = None
    
    # 토큰 파일이 있으면 로드
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # 유효한 인증 정보가 없으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # 인증 정보 저장
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def search_youtube(youtube, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """YouTube API를 사용하여 동영상을 검색합니다."""
    try:
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=max_results,
            type='video'
        ).execute()

        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            
            # 동영상 상세 정보 가져오기
            video_response = youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            ).execute()
            
            if video_response['items']:
                video_data = video_response['items'][0]
                snippet = video_data['snippet']
                statistics = video_data['statistics']
                
                videos.append({
                    'title': snippet['title'],
                    'video_id': video_id,
                    'channel_title': snippet['channelTitle'],
                    'published_at': snippet['publishedAt'],
                    'view_count': statistics.get('viewCount', '0'),
                    'like_count': statistics.get('likeCount', '0'),
                    'comment_count': statistics.get('commentCount', '0'),
                    'url': f'https://www.youtube.com/watch?v={video_id}'
                })
                
        return videos
    except Exception as e:
        print(f"YouTube 검색 중 오류 발생: {str(e)}")
        return []

def create_or_get_spreadsheet(sheets, title: str) -> str:
    """스프레드시트를 생성하거나 가져옵니다."""
    try:
        # 기존 스프레드시트 검색
        result = sheets.spreadsheets().list().execute()
        for sheet in result.get('files', []):
            if sheet['name'] == title:
                return sheet['id']
        
        # 새 스프레드시트 생성
        spreadsheet = {
            'properties': {
                'title': title
            }
        }
        result = sheets.spreadsheets().create(body=spreadsheet).execute()
        return result['spreadsheetId']
    except Exception as e:
        print(f"스프레드시트 생성 중 오류 발생: {str(e)}")
        return None

def update_sheet(sheets, spreadsheet_id: str, sheet_name: str, data: List[Dict[str, Any]]):
    """스프레드시트를 업데이트합니다."""
    try:
        # 헤더 생성
        headers = ['제목', '채널명', '게시일', '조회수', '좋아요', '댓글수', 'URL']
        
        # 데이터 포맷팅
        rows = [headers]
        for video in data:
            rows.append([
                video['title'],
                video['channel_title'],
                video['published_at'],
                video['view_count'],
                video['like_count'],
                video['comment_count'],
                video['url']
            ])
            
        # 새 시트 생성
        try:
            sheets.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }
            ).execute()
        except Exception:
            # 시트가 이미 존재하는 경우 무시
            pass
            
        # 데이터 업데이트
        range_name = f'{sheet_name}!A1:G{len(rows)}'
        sheets.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': rows}
        ).execute()
        
        print(f"✅ '{sheet_name}' 시트에 {len(data)} 개의 동영상 정보를 저장했습니다.")
        
    except Exception as e:
        print(f"시트 업데이트 중 오류 발생: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='YouTube 검색 결과를 Google Sheets에 저장')
    parser.add_argument('query', help='검색할 키워드')
    parser.add_argument('--max-results', type=int, default=50, help='검색할 최대 동영상 수 (기본값: 50)')
    args = parser.parse_args()

    try:
        # 인증
        creds = get_credentials()
        
        # YouTube API 클라이언트 생성
        youtube = build('youtube', 'v3', credentials=creds)
        
        # Google Sheets API 클라이언트 생성
        sheets = build('sheets', 'v4', credentials=creds)
        
        # YouTube 검색
        print(f"🔍 '{args.query}' 검색 중...")
        videos = search_youtube(youtube, args.query, args.max_results)
        
        if not videos:
            print("⚠️ 검색 결과가 없습니다.")
            return
            
        # 스프레드시트 생성 또는 가져오기
        spreadsheet_id = create_or_get_spreadsheet(sheets, 'YouTube 검색 결과')
        if not spreadsheet_id:
            print("⚠️ 스프레드시트 생성에 실패했습니다.")
            return
            
        # 시트 이름 생성 (검색어_날짜)
        sheet_name = f"{args.query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 데이터 저장
        update_sheet(sheets, spreadsheet_id, sheet_name, videos)
        
        print(f"✨ 작업이 완료되었습니다!")
        print(f"📊 스프레드시트 ID: {spreadsheet_id}")
        
    except Exception as e:
        print(f"⚠️ 오류 발생: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 