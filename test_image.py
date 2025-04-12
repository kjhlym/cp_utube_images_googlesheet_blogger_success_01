print("Gemini API 테스트 시작")

try:
    import google.generativeai as genai
    print("패키지 가져오기 성공")
    
    # API 키 설정
    genai.configure(api_key="AIzaSyDPcZydw8oEwda1QzLRRFEvaWpnQTc6VUU")
    print("API 키 설정 완료")
    
    # 버전 확인
    if hasattr(genai, "__version__"):
        print(f"google.generativeai 버전: {genai.__version__}")
    
    print("테스트 완료")
except Exception as e:
    print(f"오류 발생: {str(e)}")
    import traceback
    traceback.print_exc() 