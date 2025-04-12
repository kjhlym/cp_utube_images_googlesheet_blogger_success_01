from PIL import Image, ImageDraw, ImageFont
import os

def create_dummy_image(filename, text, size=(300, 300), bg_color='white', text_color='black'):
    try:
        # 이미지 생성
        image = Image.new('RGB', size, bg_color)
        draw = ImageDraw.Draw(image)
        
        # 텍스트 크기 계산
        font_size = 40
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        # 텍스트 위치 계산 (중앙 정렬)
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        
        # 텍스트 그리기
        draw.text((x, y), text, font=font, fill=text_color)
        
        # 이미지 저장
        image.save(filename, 'JPEG')
        print(f"이미지 생성 성공: {filename}")
        return True
    except Exception as e:
        print(f"이미지 생성 중 오류 발생: {filename} - {str(e)}")
        return False

def main():
    # 이미지 저장 디렉토리 생성
    if not os.path.exists('images'):
        os.makedirs('images')
    
    # 더미 이미지 생성
    products = [
        "헤트라스 디퓨저",
        "양배추즙",
        "매직랩",
        "후드 커버",
        "이불 세트",
        "올인원",
        "압력솥",
        "된장찌개",
        "카시트",
        "크로스백"
    ]
    
    for i, product in enumerate(products, 1):
        print(f"\n이미지 생성 중 ({i}/{len(products)}): {product}")
        filename = f"images/product{i}.jpg"
        create_dummy_image(filename, f"Product {i}\n{product}")
    
    print("\n모든 이미지 생성 완료")

if __name__ == "__main__":
    main() 