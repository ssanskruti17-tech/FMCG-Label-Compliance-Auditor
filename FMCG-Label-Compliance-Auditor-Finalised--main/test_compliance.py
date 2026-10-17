from parser import parse_product
from compliance import run_compliance_checks


sample_text = """
ZERO SUGAR

INGREDIENTS:
Carbonated Water
High Fructose Corn Syrup
Caramel Color
Phosphoric Acid
Natural Flavors

Calories 140
Sodium 45mg
Total Sugars 39g
Incl. 39g Added Sugars 39%
Protein 0g
"""


product = parse_product(sample_text)

print("\n--- PRODUCT DATA ---")

print("Claims:")
print(product["claims"])

print("\nIngredients:")
for ingredient in product["ingredients"]:
    print("-", ingredient)

print("\nNutrition:")
for key, value in product["nutrition"].items():
    print(f"{key}: {value}")


print("\n--- COMPLIANCE RESULT ---")

results = run_compliance_checks(product)

for result in results:

    print("\nStatus:", result["status"])
    print("Message:", result["message"])

    if "evidence" in result:
        print("Evidence:", result["evidence"])

    if "regulation" in result:
        print("Regulation:", result["regulation"])