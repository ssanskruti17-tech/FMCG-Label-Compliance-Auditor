import json
import os


# ============================================================
# LOAD RULES
# ============================================================

def load_rules(rules_path="rules.json"):
    """
    Load the deterministic regulatory rule repository.
    """

    if not os.path.exists(rules_path):
        raise FileNotFoundError(
            f"Rule repository '{rules_path}' not found."
        )

    with open(
        rules_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# NUTRITION BASIS NORMALIZATION
# ============================================================

NON_SCALED_NUTRIENTS = {
    "gi"
}


def _parse_serving_size_g(value):
    if value is None or value == "":
        return None

    try:
        size = float(value)
    except (
        TypeError,
        ValueError
    ):
        return None

    if size <= 0:
        return None

    return size


def _numeric_nutrition_values(nutrition):
    values = {}

    for key, raw_value in (nutrition or {}).items():

        if raw_value is None:
            continue

        try:
            values[key] = float(raw_value)
        except (
            TypeError,
            ValueError
        ):
            continue

    return values


def _scale_nutrition(values, factor):
    scaled = {}

    for key, value in values.items():

        if key in NON_SCALED_NUTRIENTS:
            scaled[key] = value
        else:
            scaled[key] = value * factor

    return scaled


def _condition_basis_key(basis):
    text = str(basis or "").strip().lower()

    if "serving" in text:
        return "serving"

    return "100g"


def build_normalized_nutrition(
    nutrition,
    declared_basis,
    serving_size_g
):
    """
    Project extracted nutrition onto per-100g and per-serving
    views using the declared label basis.
    """

    normalized_nutrition = {
        "100g": {},
        "serving": {}
    }

    raw_values = _numeric_nutrition_values(
        nutrition
    )

    if not raw_values:
        return normalized_nutrition

    basis_text = str(
        declared_basis or ""
    ).lower()

    compact_basis = basis_text.replace(" ", "")
    is_per_100 = "100" in compact_basis
    is_serving = (
        (not is_per_100)
        and (
            "serving" in basis_text
            or any(ch.isdigit() for ch in basis_text)
        )
    )

    if is_per_100 or not is_serving:

        normalized_nutrition["100g"] = dict(
            raw_values
        )

        if serving_size_g is not None:
            normalized_nutrition["serving"] = _scale_nutrition(
                raw_values,
                serving_size_g / 100.0
            )

    else:

        normalized_nutrition["serving"] = dict(
            raw_values
        )

        if serving_size_g is not None:
            normalized_nutrition["100g"] = _scale_nutrition(
                raw_values,
                100.0 / serving_size_g
            )

    return normalized_nutrition


def nutrient_condition_fails(
    actual_value,
    operator,
    threshold
):
    if operator == "<=":
        return actual_value > threshold

    if operator == "<":
        return actual_value >= threshold

    if operator == ">=":
        return actual_value < threshold

    if operator == ">":
        return actual_value <= threshold

    return False


# ============================================================
# MAIN COMPLIANCE ENGINE
# ============================================================

def run_compliance_checks(
    product_data,
    rules_path="rules.json"
):
    """
    Run deterministic compliance checks.

    Status meanings:

        PASS
            The applicable rule was successfully evaluated
            and the product satisfied the configured condition.

        FLAGGED
            The applicable deterministic rule was evaluated
            and the product failed it.

        REVIEW
            The system does not have enough reliable information
            to make the determination.
    """

    rules_db = load_rules(
        rules_path
    )

    claims_detected = (
        product_data.get("claims", [])
        or []
    )

    ingredients = (
        product_data.get("ingredients", [])
        or []
    )

    nutrition = (
        product_data.get("nutrition", {})
        or {}
    )

    declared_basis = product_data.get(
        "declared_basis"
    )

    serving_size_g = _parse_serving_size_g(
        product_data.get("serving_size_g")
    )

    normalized_nutrition = build_normalized_nutrition(
        nutrition,
        declared_basis,
        serving_size_g
    )

    audit_results = []


    # ========================================================
    # 0. COMPLETE EXTRACTION FAILURE
    # ========================================================

    if (
        not claims_detected
        and not ingredients
        and not nutrition
    ):

        return [{
            "rule_id": "EXTRACTION_INCOMPLETE",

            "status": "REVIEW",

            "severity": "HIGH",

            "claim": "N/A",

            "evidence": (
                "No claims, ingredients, or nutritional "
                "values could be extracted from the "
                "supplied image(s)."
            ),

            "message": (
                "Unable to perform an automated compliance "
                "decision because insufficient label data "
                "was extracted. Please provide a clearer "
                "image."
            ),

            "regulation": (
                "Automated screening requires sufficient "
                "label data."
            )
        }]


    # ========================================================
    # 1. PROCESS EACH CLAIM
    # ========================================================

    for raw_claim in claims_detected:

        if not raw_claim:
            continue

        claim_clean = (
            raw_claim
            .strip()
            .lower()
        )

        matched_rule = None


        # ----------------------------------------------------
        # Find matching rule
        # ----------------------------------------------------

        for rule_id, rule_def in rules_db.get(
            "claims",
            {}
        ).items():

            aliases = rule_def.get(
                "aliases",
                []
            )

            normalized_aliases = [
                alias.strip().lower()
                for alias in aliases
            ]

            if claim_clean in normalized_aliases:

                matched_rule = rule_def

                break


        # ----------------------------------------------------
        # No rule mapped to claim
        # ----------------------------------------------------

        if not matched_rule:

            audit_results.append({

                "rule_id": "UNMAPPED_CLAIM",

                "status": "REVIEW",

                "severity": "MEDIUM",

                "claim": raw_claim,

                "evidence": (
                    "A claim was detected, but no "
                    "deterministic rule currently maps "
                    "to this claim."
                ),

                "message": (
                    "Manual regulatory review is recommended "
                    "because this claim is not covered by "
                    "the current rule repository."
                ),

                "regulation": (
                    "FSSAI General Principles for "
                    "Advertising & Claims"
                )
            })

            continue


        # ====================================================
        # 2. NUTRIENT CONTENT CLAIM
        # ====================================================

        if matched_rule.get(
            "type"
        ) == "NUTRIENT_CONTENT":

            target = matched_rule.get(
                "target_nutrient"
            )

            conditions = list(
                matched_rule.get("conditions") or []
            )

            evaluation_mode = (
                matched_rule.get("evaluation_mode")
                or "ALL"
            ).upper()

            # Legacy single-threshold rules
            if not conditions:

                conditions = [{
                    "basis": "100g",
                    "operator": matched_rule.get(
                        "operator",
                        "<="
                    ),
                    "threshold": matched_rule.get(
                        "threshold"
                    ),
                    "unit": matched_rule.get(
                        "unit",
                        ""
                    )
                }]

            if (
                target not in nutrition
                or nutrition.get(target) is None
            ):

                audit_results.append({

                    "rule_id": matched_rule[
                        "claim_id"
                    ],

                    "status": "REVIEW",

                    "severity": "HIGH",

                    "claim": raw_claim,

                    "evidence": (
                        f"Required nutrition value "
                        f"'{target}' could not be extracted."
                    ),

                    "message": (
                        f"Unable to automatically verify "
                        f"'{raw_claim}' because the required "
                        f"nutrition value was not detected."
                    ),

                    "regulation": matched_rule[
                        "regulation_ref"
                    ]
                })

                continue

            passed_evidence = []
            failed_evidence = []
            review_evidence = []

            for condition in conditions:

                condition_basis = condition.get(
                    "basis"
                )

                operator = condition.get(
                    "operator",
                    "<="
                )

                threshold = condition.get(
                    "threshold"
                )

                unit = condition.get(
                    "unit",
                    ""
                )

                if condition_basis == "metric":

                    if threshold is None:

                        review_evidence.append(
                            f"Could not evaluate {target} "
                            "because the metric threshold is missing."
                        )
                        continue

                    # STRUCTURAL FIX: Safely cast the metric to float to prevent string crash
                    try:
                        actual_value = float(nutrition[target])
                    except (ValueError, TypeError):
                        review_evidence.append(
                            f"Could not evaluate {target} because the declared value '{nutrition[target]}' is not a valid number."
                        )
                        continue

                    condition_evidence = (
                        f"Declared {target} is "
                        f"{actual_value} ({unit}) on a 'metric' basis. "
                        f"Permitted limit: "
                        f"{operator} {threshold} {unit}."
                    )

                    if nutrient_condition_fails(
                        actual_value,
                        operator,
                        threshold
                    ):
                        failed_evidence.append(
                            condition_evidence
                        )
                    else:
                        passed_evidence.append(
                            condition_evidence
                        )

                    continue

                if condition_basis == "energy_ratio":

                    calories = nutrition.get(
                        "calories"
                    )

                    if not calories:

                        review_evidence.append(
                            "Cannot calculate energy ratio without "
                            "total calories."
                        )
                        continue

                    multiplier = condition.get(
                        "nutrient_kcal_multiplier"
                    )

                    if multiplier is None or threshold is None:

                        review_evidence.append(
                            f"Could not evaluate {target} "
                            "energy ratio because its configuration "
                            "is incomplete."
                        )
                        continue

                    energy_percentage = (
                        actual_value * multiplier / calories
                    ) * 100

                    condition_evidence = (
                        f"Energy ratio for {target} is "
                        f"{energy_percentage}% using "
                        f"{multiplier} kcal/g. Permitted limit: "
                        f"{operator} {threshold}%."
                    )

                    if nutrient_condition_fails(
                        energy_percentage,
                        operator,
                        threshold
                    ):
                        failed_evidence.append(
                            condition_evidence
                        )
                    else:
                        passed_evidence.append(
                            condition_evidence
                        )

                    continue

                basis_key = _condition_basis_key(
                    condition_basis
                )

                basis_values = (
                    normalized_nutrition.get(basis_key)
                    or {}
                )

                if (
                    target not in basis_values
                    or basis_values.get(target) is None
                    or threshold is None
                ):

                    review_evidence.append(
                        f"Could not evaluate {target} "
                        f"on a '{basis_key}' basis."
                    )
                    continue

                actual_value = basis_values[target]

                condition_evidence = (
                    f"Declared {target} is "
                    f"{actual_value} "
                    f"({unit}) on a '{basis_key}' basis. "
                    f"Permitted limit: "
                    f"{operator} {threshold} {unit}."
                )

                if nutrient_condition_fails(
                    actual_value,
                    operator,
                    threshold
                ):
                    failed_evidence.append(
                        condition_evidence
                    )
                else:
                    passed_evidence.append(
                        condition_evidence
                    )

            if evaluation_mode == "ANY":

                if passed_evidence:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "PASS",

                        "severity": "LOW",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            passed_evidence
                        ),

                        "message": (
                            "The claim satisfies the configured "
                            "deterministic nutritional condition."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

                elif failed_evidence and not review_evidence:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "FLAGGED",

                        "severity": "HIGH",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            failed_evidence
                        ),

                        "message": (
                            f"Non-compliant under the configured "
                            f"deterministic rule for "
                            f"'{raw_claim}'."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

                else:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "REVIEW",

                        "severity": "HIGH",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            review_evidence
                            or failed_evidence
                        ),

                        "message": (
                            f"Unable to automatically verify "
                            f"'{raw_claim}' because a required "
                            "nutrition basis could not be evaluated."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

            else:

                if failed_evidence:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "FLAGGED",

                        "severity": "HIGH",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            failed_evidence
                        ),

                        "message": (
                            f"Non-compliant under the configured "
                            f"deterministic rule for "
                            f"'{raw_claim}'."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

                elif review_evidence:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "REVIEW",

                        "severity": "HIGH",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            review_evidence
                        ),

                        "message": (
                            f"Unable to automatically verify "
                            f"'{raw_claim}' because a required "
                            "nutrition basis could not be evaluated."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

                else:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "PASS",

                        "severity": "LOW",

                        "claim": raw_claim,

                        "evidence": " ".join(
                            passed_evidence
                        ),

                        "message": (
                            "The claim satisfies the configured "
                            "deterministic nutritional condition."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })


        # ====================================================
        # 3. NON-ADDITION CLAIM
        # ====================================================

        elif matched_rule.get(
            "type"
        ) == "NON_ADDITION":

            required_warning = matched_rule.get(
                "required_warning"
            )

            if (
                required_warning
                and nutrition.get("total_sugars_g", 0) > 0
            ):

                warning_normalized = required_warning.lower()
                warning_present = any(
                    warning_normalized in str(claim).lower()
                    for claim in claims_detected
                )

                if not warning_present:

                    audit_results.append({

                        "rule_id": matched_rule[
                            "claim_id"
                        ],

                        "status": "FLAGGED",

                        "severity": "HIGH",

                        "claim": raw_claim,

                        "evidence": (
                            "Product contains naturally occurring sugars, "
                            "but the required warning label was not detected."
                        ),

                        "message": (
                            "Mandatory FSSAI warning label is missing for "
                            "a product containing naturally occurring sugars."
                        ),

                        "regulation": matched_rule[
                            "regulation_ref"
                        ]
                    })

            # ------------------------------------------------
            # Ingredient list missing
            # ------------------------------------------------

            if not ingredients:

                audit_results.append({

                    "rule_id": matched_rule[
                        "claim_id"
                    ],

                    "status": "REVIEW",

                    "severity": "HIGH",

                    "claim": raw_claim,

                    "evidence": (
                        "Ingredient list was not extracted "
                        "from the supplied image(s)."
                    ),

                    "message": (
                        f"Unable to verify '{raw_claim}' "
                        "because ingredient information "
                        "is missing."
                    ),

                    "regulation": matched_rule[
                        "regulation_ref"
                    ]
                })

                continue


            forbidden_list = matched_rule.get(
                "forbidden_ingredients",
                []
            )

            detected_forbidden = []


            # ------------------------------------------------
            # Ingredient screening
            # ------------------------------------------------

            for ingredient in ingredients:

                if not ingredient:
                    continue

                ingredient_clean = (
                    ingredient
                    .strip()
                    .lower()
                )

                for forbidden in forbidden_list:

                    forbidden_clean = (
                        forbidden
                        .strip()
                        .lower()
                    )

                    if (
                        forbidden_clean
                        in ingredient_clean
                    ):

                        if ingredient not in (
                            detected_forbidden
                        ):

                            detected_forbidden.append(
                                ingredient
                            )

                        break


            # ------------------------------------------------
            # Restricted ingredient found
            # ------------------------------------------------

            if detected_forbidden:

                audit_results.append({

                    "rule_id": matched_rule[
                        "claim_id"
                    ],

                    "status": "FLAGGED",

                    "severity": "HIGH",

                    "claim": raw_claim,

                    "evidence": (
                        "Configured restricted "
                        "ingredient(s) detected: "
                        + ", ".join(
                            detected_forbidden
                        )
                    ),

                    "message": (
                        f"Potential non-compliance "
                        f"detected for '{raw_claim}' "
                        "under the configured ingredient rule."
                    ),

                    "regulation": matched_rule[
                        "regulation_ref"
                    ]
                })


            # ------------------------------------------------
            # No restricted ingredient found
            # ------------------------------------------------

            else:

                audit_results.append({

                    "rule_id": matched_rule[
                        "claim_id"
                    ],

                    "status": "PASS",

                    "severity": "LOW",

                    "claim": raw_claim,

                    "evidence": (
                        "No configured restricted "
                        "ingredient synonyms were "
                        "detected."
                    ),

                    "message": (
                        "The claim passed the configured "
                        "deterministic ingredient screening rule."
                    ),

                    "regulation": matched_rule[
                        "regulation_ref"
                    ]
                })


        # ====================================================
        # 4. UNKNOWN RULE TYPE
        # ====================================================

        else:

            audit_results.append({

                "rule_id": matched_rule.get(
                    "claim_id",
                    "UNKNOWN_RULE"
                ),

                "status": "REVIEW",

                "severity": "MEDIUM",

                "claim": raw_claim,

                "evidence": (
                    "The claim matched a rule, but "
                    "the current engine does not "
                    "support this rule type."
                ),

                "message": (
                    "Manual review is required because "
                    "this rule type has not yet been implemented."
                ),

                "regulation": matched_rule.get(
                    "regulation_ref",
                    "Unknown"
                )
            })


    # ========================================================
    # 5. NO CLAIM DETECTED
    # ========================================================
    #
    # This is NOT the same as "product compliant".
    #
    # Example:
    #
    # Front not provided
    # Back provided
    # Ingredients extracted
    # Nutrition extracted
    # No claims detected
    #
    # The system can analyze the available data, but cannot
    # claim complete legal compliance.
    # ========================================================

    if not audit_results:

        front_uploaded = product_data.get(
            "front_uploaded",
            False
        )

        if not front_uploaded:

            evidence = (
                "No auditable marketing claim was detected "
                "in the supplied image(s). The front package "
                "image was not supplied, so front-of-pack "
                "claims could not be assessed."
            )

        else:

            evidence = (
                "No auditable marketing claim was detected "
                "in the supplied image(s)."
            )


        audit_results.append({

            "rule_id": "NO_AUDITABLE_CLAIMS",

            "status": "REVIEW",

            "severity": "LOW",

            "claim": "N/A",

            "evidence": evidence,

            "message": (
                "No claim covered by the current rule "
                "repository was detected. This does not "
                "constitute a complete legal compliance "
                "determination."
            ),

            "regulation": (
                "FSSAI Labelling & Display / "
                "Advertising & Claims framework"
            )
        })


    return audit_results