import cv2
import numpy as np
from paddleocr import PaddleOCR

# Initialize OCR once
ocr = PaddleOCR(use_angle_cls=True, lang='en')

def preprocess_image(image_bytes):
    image_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image is None: 
        raise ValueError("Could not read image.")

    # Resize small images to help OCR read small text
    height, width = image.shape[:2]
    if width < 1200:
        scale = 1200 / width
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    # Removed CLAHE filter: Raw color is often better for gradient packaging
    return image

def extract_text(image_bytes):
    processed = preprocess_image(image_bytes)
    height, width = processed.shape[:2]
    
    extracted_data = []
    seen_texts = set()

    def parse_result(result, is_rotated=False):
        if result and result[0]:
            for detection in result[0]:
                box = detection[0]
                text = detection[1][0]
                confidence = detection[1][1]

                # LOWERED THRESHOLD TO 0.40 TO CATCH SMALL SIDEWAYS TEXT
                if confidence >= 0.40 and text.lower() not in seen_texts:
                    seen_texts.add(text.lower())
                    
                    if is_rotated:
                        # Map rotated coordinates back to original image
                        box = [[pt[1], height - pt[0]] for pt in box]
                        
                    extracted_data.append({
                        "text": text,
                        "box": box,
                        "confidence": float(confidence)
                    })

    # PASS 1: Horizontal Text
    parse_result(ocr.ocr(processed), is_rotated=False)
    
    # PASS 2: Vertical Text (Clockwise rotation)
    rotated = cv2.rotate(processed, cv2.ROTATE_90_CLOCKWISE)
    parse_result(ocr.ocr(rotated), is_rotated=True)

    return extracted_data, processed