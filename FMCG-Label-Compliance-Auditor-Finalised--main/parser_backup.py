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
    "no added salt"
]


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(text):
    """
    Normalize OCR text while preserving enough structure
    for claim and nutrition detection.
    """

    if not text:
        return ""

    text = text.lower()

    # Normalize common OCR punctuation/noise
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace(":", " ")

    # Collapse repeated whitespace/newlines
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# CLAIM EXTRACTION
# ============================================================

def extract_claims(text):
    """
    Detect product claims from OCR text.

    Handles OCR fragmentation such as:

        "Sugar free"
        "Sugar\nfree"
        "free ... Sugar"
        "Sugar - Free"
        "Low GI"
        "Low Maida GI"

    Fragmented claim matchers are deliberately bounded so
    unrelated packaging text does not easily become a claim.
    """

    if not text:
        return []

    normalized = normalize_text(text)

    detected_claims = []

    # --------------------------------------------------------
    # 1. Exact / normal claim matching
    # --------------------------------------------------------

    for claim in CLAIMS:

        claim_normalized = normalize_text(claim)

        pattern = (
            r"\b"
            + re.escape(
                claim_normalized.replace(" ", r"\s+")
            )
            + r"\b"
        )

        if re.search(
            pattern,
            normalized,
            re.IGNORECASE
        ):

            detected_claims.append(claim)

    # --------------------------------------------------------
    # 2. OCR-fragmented "Sugar Free"
    # --------------------------------------------------------

    sugar_free_patterns = [
        r"\bsugar\b.{0,35}\bfree\b",
        r"\bfree\b.{0,35}\bsugar\b"
    ]

    if any(
        re.search(
            pattern,
            normalized,
            re.IGNORECASE
        )
        for pattern in sugar_free_patterns
    ):

        if "sugar free" not in detected_claims:
            detected_claims.append("sugar free")

    # --------------------------------------------------------
    # 3. OCR-fragmented "Low GI"
    #
    # Example actual OCR:
    #
    #   Low
    #   Maida
    #   GI*
    #
    # After normalization:
    #
    #   low maida gi*
    #
    # We allow up to two intervening words so we can handle
    # OCR fragmentation while keeping the match bounded.
    # --------------------------------------------------------

    low_gi_pattern = (
        r"\blow\b"
        r"(?:\s+\w+){0,2}"
        r"\s+\bgi\b"
    )

    if re.search(
        low_gi_pattern,
        normalized,
        re.IGNORECASE
    ):

        if "low gi" not in detected_claims:
            detected_claims.append("low gi")

    # --------------------------------------------------------
    # Remove duplicates while preserving order
    # --------------------------------------------------------

    return list(dict.fromkeys(detected_claims))


# ============================================================
# INGREDIENT EXTRACTION
# ============================================================

def extract_ingredients(text):
    """
    Extract the ingredient section from OCR text.

    The parser keeps the existing simple OCR-first strategy but
    stops at clear section boundaries. It also removes obvious
    packaging metadata lines that are not ingredients.
    """

    if not text:
        return []

    text_lower = text.lower()

    # --------------------------------------------------------
    # Find ingredient heading
    # --------------------------------------------------------

    start_match = re.search(
        r"\bingredients?\b\s*:?",
        text_lower
    )

    if not start_match:
        return []

    ingredient_start = start_match.end()

    ingredient_text = text[
        ingredient_start:
    ]

    # --------------------------------------------------------
    # Stop when nutrition / major section information begins
    # --------------------------------------------------------

    stop_patterns = [
        r"\bnutrition(?:al)?\s+\w+\b",
        r"\bnutritional\s+information\b",
        r"\bnutritional\s+infonation\b",
        r"\bnutrition\s+information\b",
        r"\bserving\s+size\b",
        r"\bquantity\s+per\s+100\b",
        r"\bcalories\b",
        r"\benergy\b"
    ]

    end_position = len(ingredient_text)

    for pattern in stop_patterns:

        match = re.search(
            pattern,
            ingredient_text,
            re.IGNORECASE
        )

        if match:
            end_position = min(
                end_position,
                match.start()
            )

    ingredient_text = ingredient_text[:end_position]

    # --------------------------------------------------------
    # Remove obvious package metadata while preserving actual
    # ingredient text. These filters are intentionally narrow.
    # --------------------------------------------------------

    filtered_lines = []

    metadata_line_patterns = [
        r"^\s*allergen\s+advice\b",
        r"^\s*lic(?:ence|ense)?\.?\s*no\b",
        r"^\s*lic\s*no\b",
        r"^\s*store\s+in\b",
        r"^\s*for\s+any\s+feedback\b",
        r"^\s*for\s+name,?\s+address\b",
        r"^\s*marketed\s+by\b"
    ]

    for raw_line in ingredient_text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        if any(
            re.search(pattern, line, re.IGNORECASE)
            for pattern in metadata_line_patterns
        ):
            continue

        filtered_lines.append(line)

    ingredient_text = "\n".join(filtered_lines)

    ingredient_text = (
        ingredient_text
        .lstrip(" :.-")
        .strip()
    )

    # --------------------------------------------------------
    # Split on commas, semicolons and newlines
    # --------------------------------------------------------

    ingredients = re.split(
        r"[,;\n]+",
        ingredient_text
    )

    ingredients = [
        re.sub(
            r"\s+",
            " ",
            item
        ).strip(" .:-")
        for item in ingredients
        if item.strip()
    ]

    # --------------------------------------------------------
    # Remove clearly non-ingredient fragments introduced by
    # OCR, without attempting semantic ingredient classification.
    # --------------------------------------------------------

    cleaned = []

    discard_patterns = [
        r"^\*?\d{3,}[\w-]*$",             # e.g. *1134 / licence-like codes
        r"^\d{5,}$",                       # long numeric OCR fragments
        r"^\(?ins\s*\d+",                  # stray INS-only fragments
    ]

    for item in ingredients:

        if any(
            re.search(pattern, item, re.IGNORECASE)
            for pattern in discard_patterns
        ):
            continue

        cleaned.append(item)

    return cleaned


# ============================================================
# NUTRITION HELPERS
# ============================================================

def _extract_first_number(text):
    """
    Return the first decimal/integer number from a short field.
    """

    match = re.search(
        r"(?<!\d)(\d+(?:\.\d+)?)",
        text
    )

    if not match:
        return None

    return float(match.group(1))


def _extract_field_number(
    text,
    label_pattern,
    next_label_pattern,
    max_chars=80
):
    """
    Extract the first numeric value after a nutrition label,
    stopping before the next nutrition label.

    This prevents a field from borrowing a number belonging to
    a later field such as Added Sugars or Sugar Alcohol.
    """

    match = re.search(
        label_pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    remainder = text[match.end():]

    boundary = re.search(
        next_label_pattern,
        remainder,
        re.IGNORECASE
    )

    if boundary:
        field_text = remainder[:boundary.start()]
    else:
        field_text = remainder[:max_chars]

    return _extract_first_number(field_text)


def _extract_energy(text):
    """
    Extract energy while tolerating common OCR forms such as:

        Energy 405.1 kcal
        Energy 405 1 kcal
        Calories 140

    A separated single digit is joined as a decimal only when it
    is immediately before the kcal unit.
    """

    energy_match = re.search(
        r"\benergy\b\s*[:\-]?\s*"
        r"(\d+)\s*(?:[.,](\d+)|\s+(\d))?"
        r"\s*kcal\b",
        text,
        re.IGNORECASE
    )

    if energy_match:

        whole = energy_match.group(1)
        decimal = energy_match.group(2)
        separated_decimal = energy_match.group(3)

        if decimal is not None:
            return float(f"{whole}.{decimal}")

        if separated_decimal is not None:
            return float(f"{whole}.{separated_decimal}")

        return float(whole)

    # Preserve support for simplified test/label text such as
    # "Calories 140" when kcal is absent.
    calories_match = re.search(
        r"\bcalories\b\s*[:\-]?\s*"
        r"(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if calories_match:
        return float(calories_match.group(1))

    return None


def _extract_gi(text):
    """
    Extract an explicitly declared Glycemic Index value.

    Supported examples:

        GI 52
        GI: 52
        GI - 52
        Glycemic Index 52
        Glycemic Index: 52

    The parser does NOT infer GI from carbohydrates, sugars,
    ingredients, or any other nutrition value.
    """

    gi_match = re.search(
        r"\b(?:gi|glycemic\s+index)\b"
        r"\s*[:\-]?\s*"
        r"(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )

    if gi_match:
        return float(
            gi_match.group(1)
        )

    return None


# ============================================================
# NUTRITION EXTRACTION
# ============================================================

def extract_nutrition(text):
    """
    Extract common nutrition values from OCR text.

    The extraction is field-bounded rather than using a large
    arbitrary character window. This is important for OCR such as:

        Total Sugars ... 0.5 9 Added Sugars 0g

    where the unit after 0.5 may be lost or misread as 9.
    """

    if not text:
        return {}

    text_lower = normalize_text(text)

    nutrition = {}

    # ========================================================
    # FIELD BOUNDARIES
    # ========================================================

    next_nutrition_field = (
        r"\b(?:"
        r"added\s+sugars?|"
        r"sugar\s+alcohol|"
        r"sodium|"
        r"carbohydrate(?:s)?|"
        r"protein|"
        r"total\s+fat|"
        r"saturated\s+fat|"
        r"monounsaturated\s+fat|"
        r"polyunsaturated\s+fat|"
        r"trans\s+fat|"
        r"cholesterol|"
        r"energy|"
        r"calories"
        r")\b"
    )

    # ========================================================
    # ENERGY
    # ========================================================

    energy = _extract_energy(text_lower)

    if energy is not None:
        nutrition["calories"] = energy

    # ========================================================
    # TOTAL SUGARS
    # ========================================================

    total_sugars = _extract_field_number(
        text_lower,
        r"\btotal\s+sugars?\b",
        next_nutrition_field,
        max_chars=80
    )

    if total_sugars is not None:
        nutrition["total_sugars_g"] = total_sugars

    # ========================================================
    # ADDED SUGARS
    # ========================================================

    # Most labels place the numeric value after the label:
    #   Added Sugars 0g
    # Some OCR samples instead place the gram value immediately
    # before the label:
    #   Incl. 39g Added Sugars 78%
    # Prefer the explicit post-label gram value, then fall back to
    # the pre-label form. Never treat a trailing percentage as grams.
    added_sugars_match = re.search(
        r"\badded\s+sugars?\b\s*"
        r"(?:[:\-]?\s*)"
        r"(\d+(?:\.\d+)?)\s*(?:g|9)\b",
        text_lower,
        re.IGNORECASE
    )

    if added_sugars_match:
        nutrition["added_sugars_g"] = float(
            added_sugars_match.group(1)
        )
    else:
        added_sugars_before_label = re.search(
            r"(\d+(?:\.\d+)?)\s*g\s+"
            r"(?:added\s+sugars?)\b",
            text_lower,
            re.IGNORECASE
        )

        if added_sugars_before_label:
            nutrition["added_sugars_g"] = float(
                added_sugars_before_label.group(1)
            )

    # ========================================================
    # PROTEIN
    # ========================================================

    protein = _extract_field_number(
        text_lower,
        r"\bprotein\b",
        r"\b(?:total\s+fat|saturated\s+fat|monounsaturated\s+fat|polyunsaturated\s+fat|trans\s+fat|cholesterol|carbohydrate(?:s)?|total\s+sugars?|added\s+sugars?|sodium|energy|calories)\b",
        max_chars=40
    )

    if protein is not None:
        nutrition["protein_g"] = protein

    # ========================================================
    # TOTAL FAT
    # ========================================================

    total_fat = _extract_field_number(
        text_lower,
        r"\btotal\s+fat\b",
        r"\b(?:saturated\s+fat|monounsaturated\s+fat|polyunsaturated\s+fat|trans\s+fat|cholesterol|carbohydrate(?:s)?|protein|total\s+sugars?|added\s+sugars?|sodium|energy|calories)\b",
        max_chars=40
    )

    if total_fat is not None:
        nutrition["total_fat_g"] = total_fat

    # ========================================================
    # SODIUM
    # ========================================================

    sodium_match = re.search(
        r"\bsodium\b\s*[:\-]?\s*"
        r"(\d+(?:\.\d+)?)\s*mg\b",
        text_lower
    )

    if sodium_match:
        nutrition["sodium_mg"] = float(
            sodium_match.group(1)
        )

    # ========================================================
    # GLYCEMIC INDEX
    # ========================================================

    gi = _extract_gi(text_lower)

    if gi is not None:
        nutrition["gi"] = gi

    return nutrition


# ============================================================
# LOCAL LLM PARSER (OLLAMA)
# ============================================================

OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_SYSTEM_PROMPT = (
  """You are an expert FMCG regulatory data extractor. You will receive an OCR spatial map of a food label.
Extract the data into a JSON object with these exact keys:
- 'claims': list of strings. Actively reconstruct fragmented marketing claims. Target FSSAI claims to look for include: 'sugar free', 'zero sugar', 'no added sugar', 'low sodium', 'low gi', 'low fat', 'trans fat free', 'low saturated fat', 'high protein', 'high fiber', 'no added salt'. ALSO explicitly extract warning statements like 'contains naturally occurring sugars'.
- 'ingredients': list of strings
- 'nutrition': object mapping only from these exact normalized keys (values must be numeric floats):
    'calories' (float)
    'total_sugars_g' (float)
    'added_sugars_g' (float)
    'sodium_mg' (float)
    'protein_g' (float)
    'total_fat_g' (float)
    'trans_fat_g' (float)
    'saturated_fat_g' (float)
    'dietary_fiber_g' (float)
    'gi' (float)
- 'declared_basis': string (e.g., "100g", "100ml", "serving", "30g"). This is the exact column header or baseline the nutrition values represent.
- 'serving_size_g': float (extract the numeric serving size in grams if declared anywhere on the package, otherwise null).
Return ONLY valid JSON."""
)

NUTRITION_KEY_ALIASES = {
    "calories": "calories",
    "energy": "calories",
    "energy_kcal": "calories",
    "total_sugars_g": "total_sugars_g",
    "total_sugars": "total_sugars_g",
    "total_sugar": "total_sugars_g",
    "totalsugars": "total_sugars_g",
    "sugars": "total_sugars_g",
    "sugar": "total_sugars_g",
    "added_sugars_g": "added_sugars_g",
    "added_sugars": "added_sugars_g",
    "added_sugar": "added_sugars_g",
    "addedsugars": "added_sugars_g",
    "sodium_mg": "sodium_mg",
    "sodium": "sodium_mg",
    "salt": "sodium_mg",
    "protein_g": "protein_g",
    "protein": "protein_g",
    "proteins": "protein_g",
    "total_fat_g": "total_fat_g",
    "total_fat": "total_fat_g",
    "fat": "total_fat_g",
    "totalfat": "total_fat_g",
    "trans_fat_g": "trans_fat_g",
    "trans_fat": "trans_fat_g",
    "transfat": "trans_fat_g",
    "trans_fats": "trans_fat_g",
    "transfats": "trans_fat_g",
    "saturated_fat_g": "saturated_fat_g",
    "saturated_fat": "saturated_fat_g",
    "sat_fat": "saturated_fat_g",
    "satfat": "saturated_fat_g",
    "saturated_fatty_acids": "saturated_fat_g",
    "saturatedfattyacids": "saturated_fat_g",
    "dietary_fiber_g": "dietary_fiber_g",
    "dietary_fiber": "dietary_fiber_g",
    "fiber": "dietary_fiber_g",
    "fibre": "dietary_fiber_g",
    "dietary_fibre": "dietary_fiber_g",
    "dietaryfibre": "dietary_fiber_g",
    "gi": "gi",
    "glycemic_index": "gi"
}


def normalize_nutrition_keys(raw_nutrition: dict) -> dict:
    """
    Map common nutrition label variations to canonical keys.
    Unknown keys are dropped.
    """

    if not raw_nutrition:
        return {}

    normalized = {}

    for raw_key, value in raw_nutrition.items():

        lookup = str(raw_key).strip().lower()
        lookup = lookup.replace(" ", "_").replace("-", "_")

        canonical = NUTRITION_KEY_ALIASES.get(lookup)

        if canonical is None:
            canonical = NUTRITION_KEY_ALIASES.get(
                lookup.replace("_", "")
            )

        if canonical is None:
            continue

        normalized[canonical] = value

    return normalized

EMPTY_PRODUCT_DATA = {
    "claims": [],
    "ingredients": [],
    "nutrition": {},
    "declared_basis": None,
    "serving_size_g": None
}


def call_ollama_parser(spatial_map: list) -> dict:
    """
    Send an OCR spatial map to a local Ollama model and
    return structured product data.
    """

    print("\n[DEBUG] Sending payload to Ollama...")

    try:
        response = requests.post(
            OLLAMA_GENERATE_URL,
            json={
                "model": OLLAMA_MODEL,
                "system": OLLAMA_SYSTEM_PROMPT,
                "prompt": json.dumps(spatial_map),
                "format": "json",
                "stream": False
            },
            timeout=60
        )

        print(f"[DEBUG] Ollama HTTP Status: {response.status_code}")
        print(f"[DEBUG] Raw Ollama Response: {response.text}")

        payload = response.json()
        parsed = json.loads(
            payload.get("response", "")
        )
        parsed["nutrition"] = normalize_nutrition_keys(
            parsed.get("nutrition", {})
        )
        return parsed

    except Exception as e:
        print(f"\n[FATAL] Ollama connection or parsing failed: {e}")
        return EMPTY_PRODUCT_DATA


# ============================================================
# DETERMINISTIC EXTRACTION VALIDATION
# ============================================================

def _ocr_match_haystack(raw_ocr_text: str) -> str:
    """Lowercase OCR text with whitespace removed."""

    if not raw_ocr_text:
        return ""

    return re.sub(r"\s+", "", raw_ocr_text.lower())


def _numeric_search_tokens(value) -> list:
    """
    String forms of a nutrition value that may appear in OCR.
    Whole numbers are checked as both '405.0' and '405'.
    """

    tokens = [str(value)]

    try:
        number = float(value)
    except (TypeError, ValueError):
        return tokens

    tokens.append(str(number))

    if number.is_integer():
        tokens.append(str(int(number)))

    # Preserve order, drop duplicates
    return list(dict.fromkeys(tokens))


def validate_extraction(llm_json: dict, raw_ocr_text: str) -> dict:
    """
    Drop LLM nutrition values and claims that cannot be
    grounded in the raw OCR text.
    """

    haystack = _ocr_match_haystack(raw_ocr_text)

    nutrition = dict(
        (llm_json or {}).get("nutrition", {}) or {}
    )
    claims = list(
        (llm_json or {}).get("claims", []) or []
    )
    ingredients = list(
        (llm_json or {}).get("ingredients", []) or []
    )

    for key, value in list(nutrition.items()):

        found = False

        for token in _numeric_search_tokens(value):

            compact_token = re.sub(r"\s+", "", str(token).lower())

            if compact_token and compact_token in haystack:
                found = True
                break

        if not found:
            print(
                f"WARNING: Dropped nutrition key '{key}' "
                f"with value {value!r} — not found in OCR text."
            )
            del nutrition[key]

    grounded_claims = []

    for claim in claims:

        words = re.findall(
            r"[a-z0-9%]+",
            str(claim).lower()
        )

        if words and all(word in haystack for word in words):
            grounded_claims.append(claim)

    sanitized = dict(llm_json or {})
    sanitized["nutrition"] = nutrition
    sanitized["claims"] = grounded_claims
    sanitized["ingredients"] = ingredients

    return sanitized


# ============================================================
# COMPLETE PRODUCT PARSER
# ============================================================

def parse_product(spatial_map):
    """
    Convert an OCR spatial map into structured product data
    using the local LLM parser and a deterministic validator.
    """

    spatial_map = spatial_map or []

    raw_text = "\n".join(
        str(item.get("text", ""))
        for item in spatial_map
        if isinstance(item, dict)
    )

    llm_json = call_ollama_parser(
        spatial_map
    )

    validated = validate_extraction(
        llm_json,
        raw_text
    )

    return {
        "claims": validated.get("claims", []) or [],
        "ingredients": validated.get("ingredients", []) or [],
        "nutrition": validated.get("nutrition", {}) or {},
        "declared_basis": validated.get("declared_basis"),
        "serving_size_g": validated.get("serving_size_g")
    }