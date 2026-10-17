from ocr_engine import extract_text
from parser import parse_product

def optimize_for_llm(spatial_map, y_tolerance=12):
    if not spatial_map: 
        return []
    sorted_boxes = sorted(spatial_map, key=lambda x: x['box'][0][1])
    lines = []
    current_line = []
    current_y = sorted_boxes[0]['box'][0][1]
    
    for item in sorted_boxes:
        y = item['box'][0][1]
        if abs(y - current_y) <= y_tolerance:
            current_line.append(item)
        else:
            current_line = sorted(current_line, key=lambda x: x['box'][0][0])
            lines.append(" | ".join([x['text'] for x in current_line]))
            current_line = [item]
            current_y = y
            
    if current_line:
        current_line = sorted(current_line, key=lambda x: x['box'][0][0])
        lines.append(" | ".join([x['text'] for x in current_line]))
        
    optimized_map = []
    for line in lines:
        optimized_map.append({
            "text": line,
            "box": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "confidence": 0.99
        })
    return optimized_map

def process_images(front_bytes: bytes = None, back_bytes: bytes = None) -> dict:
    front_data = {}
    if front_bytes:
        raw_front_spatial, _ = extract_text(front_bytes)
        front_spatial = optimize_for_llm(raw_front_spatial)
        if front_spatial:
            front_data = parse_product(front_spatial) or {}

    back_data = {}
    if back_bytes:
        raw_back_spatial, _ = extract_text(back_bytes)
        back_spatial = optimize_for_llm(raw_back_spatial)
        if back_spatial:
            back_data = parse_product(back_spatial) or {}

    front_claims = front_data.get("claims", []) or []
    back_claims = back_data.get("claims", []) or []
    combined_claims = list(dict.fromkeys(front_claims + back_claims))

    front_ingredients = front_data.get("ingredients", []) or []
    back_ingredients = back_data.get("ingredients", []) or []
    combined_ingredients = list(dict.fromkeys(front_ingredients + back_ingredients))

    front_nutrition = front_data.get("nutrition", {}) or {}
    back_nutrition = back_data.get("nutrition", {}) or {}
    combined_nutrition = {}
    for key in set(front_nutrition.keys()).union(set(back_nutrition.keys())):
        val = back_nutrition.get(key)
        if val is None:
            val = front_nutrition.get(key)
        if val is not None:
            combined_nutrition[key] = val

    declared_basis = back_data.get("declared_basis") or front_data.get("declared_basis")
    serving_size_g = back_data.get("serving_size_g") or front_data.get("serving_size_g")

    return {
        "product_name": "Live Scanned Upload",
        "category": "Uncategorized",
        "claims": combined_claims,
        "ingredients": combined_ingredients,
        "nutrition": combined_nutrition,
        "declared_basis": declared_basis,
        "serving_size_g": serving_size_g,
        "front_uploaded": front_bytes is not None,
        "back_uploaded": back_bytes is not None,
    }
