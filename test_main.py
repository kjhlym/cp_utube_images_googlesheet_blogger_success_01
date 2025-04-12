from main import process_youtube_and_products

def main():
    # 테스트할 YouTube URL - 테니스 라켓 관련 영상
    youtube_url = "https://www.youtube.com/watch?v=zI06jY9r3OE"
    
    print("===== main.py 기능 테스트 시작 =====")
    print(f"테스트 URL: {youtube_url}")
    
    # 전체 프로세스 실행
    result = process_youtube_and_products(youtube_url)
    
    if result:
        print("\n✅ 테스트 성공!")
        print(f"생성된 HTML 파일: {result}")
    else:
        print("\n❌ 테스트 실패!")
    
    print("===== 테스트 종료 =====")

if __name__ == "__main__":
    main() 