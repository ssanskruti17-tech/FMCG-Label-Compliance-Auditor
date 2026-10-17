from ocr_engine import extract_text

image_path = "test_images/Back_Test_01.png"

with open(image_path, "rb") as image_file:
    image_bytes = image_file.read()

extracted_data, processed_image = extract_text(image_bytes)

print("\n--- OCR RESULT ---")
for detection in extracted_data:
    print(detection)
