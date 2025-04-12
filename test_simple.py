print("간단한 테스트 시작")

try:
    print("패키지 가져오기 시도")
    import sys
    print(f"Python 버전: {sys.version}")
    print(f"Python 경로: {sys.executable}")
    
    # 시스템 패키지 정보
    print("\n설치된 패키지 확인:")
    import pkg_resources
    installed_packages = pkg_resources.working_set
    for package in installed_packages:
        print(f"{package.key} == {package.version}")
        
    print("\n테스트 완료")
except Exception as e:
    print(f"오류 발생: {str(e)}")
    import traceback
    traceback.print_exc() 