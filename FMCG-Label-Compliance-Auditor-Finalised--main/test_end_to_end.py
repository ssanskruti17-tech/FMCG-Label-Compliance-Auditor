import json
import os

from ocr_engine import extract_text
from parser import parse_product
from compliance import run_compliance_checks


IMAGE_FOLDER = "test_images"
TEST_CASE_FILE = "test_cases.json"


def get_overall_status(results):
    """
    Convert individual rule results into one overall result.
    """

    if any(r["status"] == "FLAGGED" for r in results):
        return "FLAGGED"

    if any(r["status"] == "REVIEW" for r in results):
        return "REVIEW"

    return "PASS"


def run_test(test_case):

    image_path = os.path.join(
        IMAGE_FOLDER,
        test_case["image"]
    )

    print("\n" + "=" * 60)
    print(f"TEST: {test_case['image']}")
    print(f"DESCRIPTION: {test_case['description']}")
    print("=" * 60)

    # --------------------------------
    # 1. READ IMAGE
    # --------------------------------

    if not os.path.exists(image_path):
        print("ERROR: Image not found")
        return False

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    # --------------------------------
    # 2. OCR
    # --------------------------------

    print("\n[1] Running OCR...")

    raw_text, processed_image = extract_text(
        image_bytes
    )

    print("OCR TEXT:")
    print(raw_text)

    # --------------------------------
    # 3. PARSER
    # --------------------------------

    print("\n[2] Parsing product...")

    product = parse_product(raw_text)

    print("\nCLAIMS:")
    print(product["claims"])

    print("\nINGREDIENTS:")
    for ingredient in product["ingredients"]:
        print("-", ingredient)

    print("\nNUTRITION:")
    for key, value in product["nutrition"].items():
        print(f"{key}: {value}")

    # --------------------------------
    # 4. COMPLIANCE ENGINE
    # --------------------------------

    print("\n[3] Running compliance engine...")

    results = run_compliance_checks(product)

    # --------------------------------
    # 5. OVERALL RESULT
    # --------------------------------

    actual_status = get_overall_status(results)

    expected_status = test_case["expected_status"]

    print("\nEXPECTED:")
    print(expected_status)

    print("\nACTUAL:")
    print(actual_status)

    # --------------------------------
    # 6. INDIVIDUAL RULE RESULTS
    # --------------------------------

    print("\nRULE RESULTS:")

    for result in results:

        print(
            f"\n{result['status']} | "
            f"{result['claim']} | "
            f"{result['rule_id']}"
        )

        print(
            f"Evidence: "
            f"{result.get('evidence', 'N/A')}"
        )

    # --------------------------------
    # 7. TEST RESULT
    # --------------------------------

    if actual_status == expected_status:

        print("\n✅ TEST PASSED")
        return True

    else:

        print("\n❌ TEST FAILED")
        return False


def main():

    with open(TEST_CASE_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    passed = 0
    failed = 0

    for test_case in test_cases:

        success = run_test(test_case)

        if success:
            passed += 1
        else:
            failed += 1

    print("\n\n")
    print("=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)

    print(f"Total tests : {len(test_cases)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED")
    else:
        print("\n⚠️ SOME TESTS FAILED")


if __name__ == "__main__":
    main()