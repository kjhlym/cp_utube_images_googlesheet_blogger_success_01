import google.generativeai as genai
from PIL import Image
from io import BytesIO
import base64

genai.configure(api_key='AIzaSyDPcZydw8oEwda1QzLRRFEvaWpnQTc6VUU')

contents = ('Create a 3D rendered image of a cartoon character cup '
            )

# 기본 설정만 사용 (없는 파라미터 제거)
model = genai.GenerativeModel('gemini-2.0-flash-exp-image-generation')
response = model.generate_content(
    contents,
    generation_config={
        "temperature": 0.9,
        "top_p": 1.0,
        "top_k": 32,
    }
)

# 응답 처리
for candidate in response.candidates:
    for part in candidate.content.parts:
        if hasattr(part, 'text') and part.text:
            print(f"텍스트 응답: {part.text}")
        
        if hasattr(part, 'inline_data') and part.inline_data:
            try:
                print(f"이미지 데이터 형식: {part.inline_data.mime_type}")
                image_data = base64.b64decode(part.inline_data.data)
                image = Image.open(BytesIO(image_data))
                image.save('gemini-native-image.png')
                print("이미지 저장 완료: gemini-native-image.png")
                image.show()
            except Exception as e:
                print(f"이미지 처리 오류: {e}")