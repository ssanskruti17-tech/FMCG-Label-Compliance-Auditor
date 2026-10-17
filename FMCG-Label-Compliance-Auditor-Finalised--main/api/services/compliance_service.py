from compliance import run_compliance_checks

def evaluate_compliance(product_data: dict) -> dict:
    cleaned_nutrition = {}
    for k, v in product_data.get("nutrition", {}).items():
        try:
            if v is not None:
                cleaned_nutrition[k] = float(v)
        except (ValueError, TypeError):
            pass
    product_data["nutrition"] = cleaned_nutrition

    results = run_compliance_checks(product_data)
    
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    flagged_count = sum(1 for r in results if r["status"] == "FLAGGED")
    review_count = sum(1 for r in results if r["status"] == "REVIEW")

    overall_status = "PASSED CURRENT AUDITS"
    if flagged_count > 0:
        overall_status = "VIOLATION"
    elif review_count > 0:
        overall_status = "REQUIRES REVIEW"

    return {
        "overall_status": overall_status,
        "passed_count": passed_count,
        "flagged_count": flagged_count,
        "review_count": review_count,
        "results": results
    }
