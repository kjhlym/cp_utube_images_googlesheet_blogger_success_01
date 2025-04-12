#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pickle
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import sys

# .env 파일 로드
load_dotenv()

# 작업 디렉토리 설정
WORK_DIR = os.getenv('WORK_DIR', os.getcwd())

# OAuth 설정
CLIENT_SECRETS_FILE = os.path.join(WORK_DIR, "client_secret.json")
TOKEN_FILE_PATH = os.path.join(WORK_DIR, 'token.pickle')
SCOPES = ['https://www.googleapis.com/auth/blogger']

def get_credentials():
    """Google API 인증 정보를 가져옵니다."""
    creds = None
    
    # 토큰 파일이 있으면 로드
    if os.path.exists(TOKEN_FILE_PATH):
        print(f"기존 토큰 파일을 로드합니다: {TOKEN_FILE_PATH}")
        with open(TOKEN_FILE_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # 유효한 인증 정보가 없거나 만료된 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("토큰이 만료되어 갱신합니다.")
            creds.refresh(Request())
        else:
            print("새로운 인증 과정을 시작합니다.")
            print(f"클라이언트 시크릿 파일: {CLIENT_SECRETS_FILE}")
            
            # 클라이언트 시크릿 파일 존재 확인
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"오류: {CLIENT_SECRETS_FILE} 파일을 찾을 수 없습니다.")
                print(f"현재 작업 디렉토리: {os.getcwd()}")
                sys.exit(1)
                
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            
            # 브라우저를 자동으로 열어 인증 진행
            creds = flow.run_local_server(port=0)
        
        # 토큰 저장
        with open(TOKEN_FILE_PATH, 'wb') as token:
            pickle.dump(creds, token)
        print(f"인증 토큰이 저장되었습니다: {TOKEN_FILE_PATH}")
    
    return creds

if __name__ == '__main__':
    print("Google OAuth 인증을 시작합니다...")
    print(f"작업 디렉토리: {WORK_DIR}")
    
    try:
        credentials = get_credentials()
        print("인증이 성공적으로 완료되었습니다!")
        print(f"토큰이 {TOKEN_FILE_PATH}에 저장되었습니다.")
    except Exception as e:
        print(f"인증 과정에서 오류가 발생했습니다: {e}")
        sys.exit(1) 