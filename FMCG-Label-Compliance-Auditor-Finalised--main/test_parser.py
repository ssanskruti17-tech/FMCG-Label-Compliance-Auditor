import json
from parser import parse_product
from compliance import run_compliance_checks

def _mock_spatial_map(text: str) -> list:
    spatial_map = []

    for line in text.split("\n"):
        stripped = line.strip()

        if stripped:
            spatial_map.append(
                {
                    "text": stripped,
                    "box": [[0, 0], [1, 0], [1, 1], [0, 1]],
                    "confidence": 0.99
                }
            )

    return spatial_map


# ============================================================
# TEST 1: Existing sample
# ============================================================

sample_text = """
INGREDIENTS:
Carbonated Water
High Fructose Corn Syrup
Caramel Color
Phosphoric Acid
Natural Flavors

Calories 140
Sodium 45mg
Total Sugars 39g
Incl. 39g Added Sugars 78%
Protein 0g
"""


result = parse_product(_mock_spatial_map(sample_text))

print("\n--- TEST 1: EXISTING SAMPLE ---")
print("Claims:", result["claims"])
print("Ingredients:", result["ingredients"])
print("Nutrition:", result["nutrition"])

assert result["nutrition"]["calories"] == 140.0
assert result["nutrition"]["sodium_mg"] == 45.0
assert result["nutrition"]["total_sugars_g"] == 39.0
assert result["nutrition"]["protein_g"] == 0.0
assert result["nutrition"]["added_sugars_g"] == 39.0


# ============================================================
# TEST 2: Actual Unibic OCR regression case
# ============================================================

unibic_ocr = """
Ingredients: Cerea Products (46%XWhoe Wheat Flur (Atta); Oats Rce Rag, Com);
Marketed by: Unlbic Foods India Rivate Limited; *1134, Shreeram Niwas 2nd
Stee ener(INS 955 -
Desicated Coccnut Powder, Dextm Wheat Bran Emusifer
322 tom Soyk
Leavenng Agents (INS 500 M, INS 503
Lic No: 11222999000012
Allergen Advice: Ccntains Wheat, Oats Mik Soy & Nut.
Store in & cool, dry place and away from direct sunlight Once opened, store in
or Email: consumercare@unibicfoods.com
an airtight container: Please dispose this package thoughttully:
Nutritional Infonation
[Number of Servings per Container - Aoprox 2, Serving Szze - 30g}
Quantity per 100 9: Energy 405 1 kcal Protein 6 0 g Tolal Fat 19.99 Saturaled Fat
11.6 g, Monounsaturated Fat 5.7 g Poyunsaturated Fat 1.7 g, Trans Fat 0 g
Cholesterdl 2.8 mg; Carbohydrate 65.9, Total Sugars (Nalurally Occurg Sugars) 0.5
9 Added Sugars 0g Sugar alcohol (Pojyots) 29g, Sodium 250mg:
4% RDA per Serving: Energy
Total Fai 8 8, Saturated Fat 15.9, Trans Fat 0,
Acded Sugars 0, Sodum 3,7
UNIBIC
90600 9
(INS
prnted
pack
"""

unibic_result = parse_product(_mock_spatial_map(unibic_ocr))
unibic_nutrition = unibic_result["nutrition"]

print("\n--- TEST 2: UNIBIC OCR REGRESSION ---")
print("Claims:", unibic_result["claims"])
print("Ingredients:", unibic_result["ingredients"])
print("Nutrition:", unibic_nutrition)

assert unibic_nutrition["total_sugars_g"] == 0.5, (
    "Total sugars must be extracted as 0.5, not 0 or 29."
)
assert unibic_nutrition["added_sugars_g"] == 0.0
assert unibic_nutrition["sodium_mg"] == 250.0
assert unibic_nutrition["calories"] == 405.0



# ============================================================
# TEST 3: Front-of-pack fragmented claim
# ============================================================

front_ocr = """
1
1
8
20
8
free
{
2
UNIBIC
YEARS
ALICIOUSI
BIC
Sugar
Cookies
Multigrain
"""

front_result = parse_product(_mock_spatial_map(front_ocr))

print("\n--- TEST 3: FRONT CLAIM REGRESSION ---")
print("Claims:", front_result["claims"])

assert "sugar free" in front_result["claims"]


# ============================================================
# TEST 4: Basis normalization
# ============================================================

mock_llm_product = {
    "declared_basis": "30g",
    "serving_size_g": 30.0,
    "claims": ["high protein"],
    "ingredients": [],
    "nutrition": {
        "protein_g": 4.0
    }
}

basis_result = run_compliance_checks(
    mock_llm_product
)

print("\n--- TEST 4: BASIS NORMALIZATION ---")
print("Audit evidence:", basis_result[0]["evidence"])

assert basis_result[0]["status"] == "PASS"


# ============================================================
# TEST 5: Advanced FSSAI Math & Warnings
# ============================================================

mock_complex_product = {
    "declared_basis": "100g",
    "serving_size_g": None,
    "claims": ["low saturated fat", "no added sugar"],
    "ingredients": [],
    "nutrition": {
        "calories": 100.0,
        "saturated_fat_g": 1.5,
        "total_sugars_g": 5.0
    }
}

advanced_result = run_compliance_checks(mock_complex_product)

print("\n--- TEST 5: ADVANCED MATH & WARNINGS ---")
print(json.dumps(advanced_result, indent=2))

# Find the specific claim results in the returned list
sat_fat_result = next((r for r in advanced_result if r["rule_id"] == "CLAIM_LOW_SATURATED_FAT"), None)
sugar_result = next((r for r in advanced_result if r["rule_id"] == "CLAIM_NO_ADDED_SUGAR"), None)

assert sat_fat_result is not None, "CLAIM_LOW_SATURATED_FAT not found in compliance output"
assert sugar_result is not None, "CLAIM_NO_ADDED_SUGAR not found in compliance output"

assert sat_fat_result["status"] == "FLAGGED", "Low Saturated Fat should flag due to >10% energy cap."
assert sugar_result["status"] == "FLAGGED", "No Added Sugar should flag due to missing warning label."

print("\n✅ ALL PARSER TESTS PASSED")