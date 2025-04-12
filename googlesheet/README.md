# YouTube 검색 결과를 Google Sheets에 저장하는 CLI 프로그램

이 프로그램은 YouTube API를 사용하여 동영상을 검색하고, 검색 결과를 Google Sheets에 자동으로 저장합니다.

## 기능

- YouTube 동영상 검색
- 검색 결과를 Google Sheets에 자동 저장
- 각 검색어별로 새로운 시트 생성
- 동영상 정보 (제목, 채널명, 조회수 등) 저장

## 설치 방법

1. 필요한 패키지 설치:

```bash
pip install -r requirements.txt
```

2. Google API 인증 설정:
   - [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
   - YouTube Data API v3 활성화
   - Google Sheets API 활성화
   - OAuth 2.0 클라이언트 ID 생성
   - 다운로드한 클라이언트 시크릿 JSON 파일을 `client_secret.json`으로 저장

## 사용 방법

1. 기본 검색:

```bash
python search_to_sheet.py "검색어"
```

2. 검색 결과 수 지정:

```bash
python search_to_sheet.py "검색어" --max-results 10
```

## 출력 결과

- 검색 결과는 "YouTube 검색 결과" 스프레드시트에 저장됩니다
- 각 검색마다 새로운 시트가 생성됩니다 (시트 이름: 검색어\_날짜시간)
- 저장되는 정보:
  - 동영상 제목
  - 채널명
  - 게시일
  - 조회수
  - 좋아요 수
  - 댓글 수
  - 동영상 URL

## 주의사항

- YouTube API는 일일 할당량이 있으므로 과도한 사용을 피해주세요
- Google API 인증 정보는 안전하게 보관해주세요
- 처음 실행 시 Google 계정 인증이 필요합니다
