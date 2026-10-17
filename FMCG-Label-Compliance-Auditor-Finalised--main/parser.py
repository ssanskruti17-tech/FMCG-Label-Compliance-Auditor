import json
import re
import requests

# ============================================================
# CLAIM DEFINITIONS
# ============================================================

CLAIMS = [
    "zero sugar",
    "no added sugar",
    "sugar free",
    "sugar-free",
    "100% natural",
    "organic",
    "high protein",
    "high fibre",
    "high fiber",
    "low fat",
    "low sodium",
    "low gi",
    "no added salt",
    "no added preservatives",  # <-- ADDED FOR REAL JUICE
    "rich in vitamin c"        # <-- ADDED FOR REAL JUICE
]

# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    if not text: return ""
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-").replace(":", " ")
    return re.sub(r"\s+", " ", text).strip()

# ============================================================
# CLAIM EXTRACTION (DETERMINISTIC)
# ============================================================

def extract_claims(text):
    if not text: return []
    
    # 1. Standard normalization (preserves spaces, allows proximity matching)
    normalized = normalize_text(text)
    
    # 2. Space-agnostic haystack (strips everything for fused OCR words)
    haystack = re.sub(r"[\s\-\.\,\:\;\'\"•\*]", "", text.lower())
    
    detected_claims = []

    for claim in CLAIMS:
        # Check exact pattern match
        claim_norm = normalize_text(claim)
        pattern = r"\b" + re.escape(claim_norm).replace(r"\ ", r"\s+") + r"\b"
        
        # Check fused match (Real Juice fix)
        claim_fused = re.sub(r"[\s\-]", "", claim.lower())
        
        if re.search(pattern, normalized, re.IGNORECASE) or claim_fused in haystack:
            detected_claims.append(claim)

    # Proximity matches for Sugar Free (Allows up to 35 chars of noise between words)
    sugar_free_patterns = [r"\bsugar\b.{0,35}\bfree\b", r"\bfree\b.{0,35}\bsugar\b"]
    if any(re.search(p, normalized, re.IGNORECASE) for p in sugar_free_patterns):
        if "sugar free" not in detected_claims: detected_claims.append("sugar free")
        
    # Fused fallback
    if "sugarfree" in haystack or "zerosugar" in haystack or "0%sugar" in haystack:
        if "sugar free" not in detected_claims: detected_claims.append("sugar free")

    # Proximity and Fused match for Low GI
    if re.search(r"\blow\b(?:\s+\w+){0,3}\s+\bgi\b", normalized, re.IGNORECASE) or "lowgi" in haystack:
        if "low gi" not in detected_claims: detected_claims.append("low gi")

    return list(dict.fromkeys(detected_claims))

def extract_ingredients(text):
    if not text:
        return []
    text_lower = text.lower()

    start_match = re.search(r"\bingredients?\b\s*:?", text_lower)
    if not start_match:
        return []

    ingredient_start = start_match.end()
    ingredient_text = text[ingredient_start:]

    stop_patterns = [
        r"\bnutrition(?:al)?\s+\w+\b", r"\bnutritional\s+information\b",
        r"\bnutritional\s+infonation\b", r"\bnutrition\s+information\b",
        r"\bserving\s+size\b", r"\bquantity\s+per\s+100\b",
        r"\bcalories\b", r"\benergy\b",
        r"\bcontains\s+naturally\b", r"\bwhy\s+\w+\b", r"\ballergen\s+information\b"
    ]

    end_position = len(ingredient_text)
    for pattern in stop_patterns:
        match = re.search(pattern, ingredient_text, re.IGNORECASE)
        if match:
            end_position = min(end_position, match.start())

    ingredient_text = ingredient_text[:end_position]

    filtered_lines = []
    metadata_line_patterns = [
        r"^\s*allergen\s+advice\b", r"^\s*lic(?:ence|ense)?\.?\s*no\b",
        r"^\s*lic\s*no\b", r"^\s*store\s+in\b",
        r"^\s*for\s+any\s+feedback\b", r"^\s*for\s+name,?\s+address\b",
        r"^\s*marketed\s+by\b"
    ]

    for raw_line in ingredient_text.splitlines():
        line = raw_line.strip()
        if not line: continue
        if any(re.search(p, line, re.IGNORECASE) for p in metadata_line_patterns): continue
        filtered_lines.append(line)

    ingredient_text = "\n".join(filtered_lines).lstrip(" :.-").strip()
    
    # STRUCTURAL FIX: Split by pipe '|' to sever multi-column pricing boxes
    raw_ingredients = re.split(r"[,;\n|]+", ingredient_text)
    
    raw_ingredients = [
        re.sub(r"\s+", " ", item).strip(" .:-") 
        for item in raw_ingredients if item.strip()
    ]

    cleaned = []
    
    # RUTHLESS DENYLIST
    discard_patterns = [
        r"^\*?\d{3,}[\w-]*$", r"^\d{5,}$", r"^\(?ins\s*\d+",
        r"mrp", r"₹", r"mfg", r"exp\.", r"lot\s*no", r"^\d+\s*(g|kg|ml|l|mg)$", 
        r"taxes", r"weight", r"laxative", r"units\s*x", r"incl\.?\s*of", r"use\s*by",
        r"rda", r"serve\s*size", r"servings?\s*per\s*pack",
        r"average\s*requirements", r"contribution\s*calculated", r"adult\s*per\s*day",
        r"^\d{1,3}\.?\d*\s*%\*?$", r"sugar\s*free", r"no\s*added", r"low\s*fat",
        r"trans\s*fat", r"high\s*protein", r"high\s*fiber", r"low\s*sodium", r"low\s*gi",
        r"occurring\s*sugars", r"clean\s*and\s*natural", r"net\s*weight",
        r"[o0]g\s*sugar", r"low\s*saturated\s*fat", r"almonds?\s*&?\s*seeds", r"healthy\s*protein\s*bar",
        r"^[oO0]\s*g\b", r"\b(free|low\s+in|high\s+in|no\s+added|rich\s+in)\b", r"net\s*(?:weight|wt|qty|quantity)"
    ]
    
    for item in raw_ingredients:
        if any(re.search(p, item, re.IGNORECASE) for p in discard_patterns): 
            continue
        
        # UNIVERSAL BRACKET SCRUBBER (handles (), {}, and [])
        item_clean = item.replace(')', '').replace('(', '').replace('}', '').replace('{', '').replace(']', '').replace('[', '').strip()
        
        if len(item_clean) > 2:
            cleaned.append(item_clean)

    return cleaned

# ============================================================
# NUTRITION & LLM ENGINE
# ============================================================

def _extract_first_number(text):
    match = re.search(r"(?<!\d)(\d+(?:\.\d+)?)", text)
    return float(match.group(1)) if match else None

def extract_nutrition(text):
    if not text: return {}
    t = normalize_text(text)
    t = re.sub(r"\b[oO]\s*g\b", "0g", t)
    nut = {}

    def get_val(pattern):
        m = re.search(pattern + r"[\s\:\-\|~]{0,30}(\d+(?:\.\d+)?)", t, re.IGNORECASE)
        return float(m.group(1)) if m else None

    cal = get_val(r"\b(?:energy|calories)\b")
    if cal is not None: nut["calories"] = cal

    ts = get_val(r"(?:total\s*sugars?|sugars?\s*total)[\^\*]?")
    if ts is not None: nut["total_sugars_g"] = ts

    added = get_val(r"(?:added\s*sugars?|sugars?\s*added)")
    if added is not None: nut["added_sugars_g"] = added

    protein = get_val(r"\bprotein\b")
    if protein is not None: nut["protein_g"] = protein

    fat = get_val(r"\btotal\s+fat\b")
    if fat is not None: nut["total_fat_g"] = fat

    sat = get_val(r"\bsaturated\s+fat\b")
    if sat is not None: nut["saturated_fat_g"] = sat

    trans = get_val(r"\btrans\s+fat\b")
    if trans is not None: nut["trans_fat_g"] = trans

    fiber = get_val(r"\b(?:dietary\s+)?(?:fiber|fibre)\b")
    if fiber is not None: nut["dietary_fiber_g"] = fiber

    sod = get_val(r"\bsodium\b")
    if sod is not None: nut["sodium_mg"] = sod

    gi_match = re.search(r"\b(?:gi|glycemic\s+index)\b([^\n]*)", text, re.IGNORECASE)
    if gi_match:
        gi_nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", gi_match.group(1))]
        if gi_nums:
            nut["gi"] = min(gi_nums)

    return {k: v for k, v in nut.items() if v is not None}

def call_ollama_parser(spatial_map: list) -> dict:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "qwen2.5:7b",
                "system": "Extract OCR map to JSON with keys: claims[], ingredients[], nutrition{}, declared_basis, serving_size_g. Numbers must be floats.",
                "prompt": json.dumps(spatial_map),
                "format": "json", "stream": False
            }, timeout=60
        )
        return json.loads(response.json().get("response", "{}"))
    except: return {}

def validate_extraction(llm_json: dict, raw_ocr_text: str) -> dict:
    haystack = re.sub(r"\s+", "", raw_ocr_text.lower())
    nut = llm_json.get("nutrition", {})
    claims = [c for c in llm_json.get("claims", []) if re.sub(r"\s+", "", str(c).lower()) in haystack]
    return {"nutrition": nut, "claims": claims, "ingredients": llm_json.get("ingredients", [])}

def parse_product(spatial_map):
    raw_text = "\n".join(str(i.get("text", "")) for i in (spatial_map or []) if isinstance(i, dict))
    det_claims = extract_claims(raw_text)
    det_ingredients = extract_ingredients(raw_text)
    det_nutrition = extract_nutrition(raw_text)
    
    llm_json = call_ollama_parser(spatial_map)
    validated = validate_extraction(llm_json, raw_text)
    
    # ==========================================
    # GENERALIZED CLAIM DEDUPLICATION
    # ==========================================
    raw_merged_claims = det_claims
    final_claims = []
    seen_fingerprints = set()
    
    for raw_claim in raw_merged_claims:
        # 1. Create a universal fingerprint: lowercase, stripping ALL punctuation and spaces
        fingerprint = re.sub(r"[^a-z0-9]", "", str(raw_claim).lower())
        
        if not fingerprint:
            continue
            
        # 2. Check if this fingerprint (or a substring of it) already exists
        is_duplicate = False
        for seen in seen_fingerprints:
            if fingerprint in seen or seen in fingerprint:
                is_duplicate = True
                break
                
        # 3. If it is unique, add it to the final UI list in standard lowercase
        if not is_duplicate:
            final_claims.append(str(raw_claim).lower().strip(" *.-"))
            seen_fingerprints.add(fingerprint)
    
    final_nut = validated.get("nutrition", {})
    final_nut.update(det_nutrition)

    return {
        "claims": final_claims,
        "ingredients": det_ingredients if det_ingredients else validated.get("ingredients", []),
        "nutrition": final_nut,
        "declared_basis": llm_json.get("declared_basis", "100ml"),
        "serving_size_g": llm_json.get("serving_size_g")
    }