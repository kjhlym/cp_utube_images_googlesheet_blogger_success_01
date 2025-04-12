import requests
import os

def download_image(url, file_path):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.coupang.com/'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"이미지가 성공적으로 다운로드되었습니다: {file_path}")
    except Exception as e:
        print(f"이미지 다운로드 중 오류 발생: {e}")

# 이미지 URL과 저장할 경로 설정
image_url = "https://ads-partners.coupang.com/image1/65NziKqHMuVvoBDP69Jl1oIrYXOzRZNXE4ZrLcqwiUWFaCLCkF8zFyOSlDX5-CJgFEEtn7HMT8TN1OWkcU8zEPnYO28dAYVyFNIevUufGJvM4jDiwDSFSDVk08gf-fHIg6QPnQfVHFYfDLsuWK2royoz0zu_OH1cyTp-TYeAnga41pDvowb2UIBRX-blO-W_qiKoeWSZhhEPq_teYFKTcCARJla_mzBuhB1-zYVgwMrQXnVgGzvYF2s0PdjspfOhEoHnB0M6pBvySS6mPiE5UpYsa_Q="
save_path = "images/iriver_earphone.jpg"

# 이미지 다운로드 실행
download_image(image_url, save_path) 