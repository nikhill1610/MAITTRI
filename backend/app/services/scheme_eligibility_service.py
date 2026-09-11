"""
Scheme Eligibility Service for MAITTRI Platform
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Evaluates farmer eligibility against official government schemes.
Outputs:
- Eligible
- Potentially Eligible
- Not Eligible
- Insufficient Information
- Unknown
Never outputs 'Eligible' when critical information is missing.
"""

from typing import Dict, Any, List, Optional
from .government_scheme_service import get_scheme_by_id, get_government_schemes

OFFICIAL_DISCLAIMER = (
    "MAITTRI provides informational decision-support based on official government guidelines. "
    "Final eligibility, subsidy allocation, and benefit release are subject to physical document verification "
    "and sanction by the competent government authority or nodal agency."
)

def evaluate_scheme_eligibility(
    scheme: Dict[str, Any],
    state: Optional[str] = None,
    district: Optional[str] = None,
    crop: Optional[str] = None,
    season: Optional[str] = None,
    farm_size_acres: Optional[float] = None,
    farmer_category: Optional[str] = "General",
    land_ownership: Optional[str] = "Owner",
    irrigation_type: Optional[str] = "available",
    solar_pump_needed: Optional[bool] = False,
    equipment_needed: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates farmer inputs against a specific scheme's verified rules.
    """
    reasons: List[str] = []
    missing_info: List[str] = []
    action_steps: List[str] = []
    match_score = 100
    is_ineligible = False
    ineligible_reason = ""

    norm_state = state.strip().title() if state else None
    norm_crop = crop.strip().title() if crop else None
    norm_season = season.strip().title() if season else None
    norm_ownership = land_ownership.strip().title() if land_ownership else "Owner"
    norm_category = farmer_category.strip().title() if farmer_category else "General"

    # 1. State Compatibility Check
    if scheme["level"] == "state":
        if not norm_state:
            missing_info.append("State location is required to evaluate state-specific schemes.")
            match_score -= 40
        elif norm_state.lower() != scheme["state"].lower():
            is_ineligible = True
            ineligible_reason = f"This scheme is strictly applicable to farmers of {scheme['state']} (your selected state: {norm_state})."
            match_score = 0
        else:
            reasons.append(f"State residency matches {scheme['state']}.")
    else:
        reasons.append("Central Government scheme applicable across all Indian States & UTs.")

    # 2. Land Ownership Check
    scheme_name_lower = scheme["scheme_name"].lower()
    if "pm-kisan" in scheme_name_lower or "kisan kalyan" in scheme_name_lower:
        if norm_ownership in ["Tenant", "Sharecropper", "Oral Lessee"]:
            is_ineligible = True
            ineligible_reason = "Official guidelines require cultivable land to be registered in the farmer's name. Tenant farmers are not eligible for direct landholder income transfers."
            match_score = 0
        else:
            reasons.append("Land ownership requirement met (Registered landholder).")

    # 3. Farm Size & Category Check (1 ha = 2.47 acres)
    if farm_size_acres is not None:
        farm_size_ha = farm_size_acres / 2.471
        farm_size_rule = scheme.get("farm_size_rule", "All").lower()

        if "marginal (<1 ha) & small (1-2 ha)" in farm_size_rule:
            if farm_size_ha > 2.05:
                if "sc" in norm_category.lower() or "st" in norm_category.lower():
                    reasons.append(f"Farm size ({farm_size_acres:.1f} acres / {farm_size_ha:.1f} ha) exceeds standard small farmer limits, but priority applies for SC/ST category.")
                    match_score -= 15
                else:
                    is_ineligible = True
                    ineligible_reason = f"Scheme is restricted to Small & Marginal farmers owning up to 2 hectares (5 acres). Your farm area is {farm_size_acres:.1f} acres ({farm_size_ha:.1f} ha)."
                    match_score = 0
            else:
                reasons.append(f"Farm size ({farm_size_acres:.1f} acres / {farm_size_ha:.1f} ha) qualifies as Small/Marginal farmer.")
        elif "minimum 0.60 hectare" in farm_size_rule:
            if farm_size_ha < 0.60:
                is_ineligible = True
                ineligible_reason = f"Scheme requires at least 0.60 hectare (1.5 acres) land. Your farm area is {farm_size_acres:.1f} acres ({farm_size_ha:.1f} ha)."
                match_score = 0
            else:
                reasons.append(f"Meets minimum area threshold ({farm_size_acres:.1f} acres >= 1.5 acres).")
        elif "minimum 1.5 ha" in farm_size_rule:
            if farm_size_ha < 1.5:
                reasons.append("Individual landholding is under 1.5 ha; you can still apply as a joint farmer group (minimum combined 5 ha).")
                match_score -= 10
            else:
                reasons.append("Meets individual area threshold for fencing subsidy.")
        else:
            reasons.append("Open to all landholding sizes (Marginal, Small, Medium, Large).")
    else:
        missing_info.append("Farm size (acres/hectares) not specified.")
        match_score -= 20

    # 4. Crop Applicability Check
    crop_rule = scheme.get("crop_applicability", "All Crops").lower()
    if "all" not in crop_rule:
        if norm_crop:
            if norm_crop.lower() in crop_rule:
                reasons.append(f"Current crop '{norm_crop}' is explicitly covered under this scheme.")
            else:
                if "paddy" in crop_rule and norm_crop.lower() in ["rice", "paddy"]:
                    reasons.append(f"Crop '{norm_crop}' matches Paddy criteria.")
                elif "wheat" in crop_rule and norm_crop.lower() == "wheat":
                    reasons.append("Crop matches Wheat criteria.")
                else:
                    match_score -= 25
                    reasons.append(f"Scheme focuses on {scheme['crop_applicability']}, but your current crop is {norm_crop}. Verify if crop change or multi-crop applies.")
        else:
            missing_info.append("Crop not specified. Some benefits depend on specific notified crops.")
            match_score -= 15

    # 5. Determine Overall Verdict
    if is_ineligible:
        status = "Not Eligible"
        match_score = 0
        reasons.insert(0, f"Ineligibility factor: {ineligible_reason}")
    elif len(missing_info) >= 2 or not norm_state:
        status = "Insufficient Information"
        match_score = max(match_score, 30)
    elif match_score >= 80 and len(missing_info) == 0:
        status = "Potentially Eligible"
        # Note: We reserve 'Eligible' strictly for cases where official document records are pre-verified
        # per Prompt Section 18 & 19 safety rules.
    elif match_score >= 60:
        status = "Potentially Eligible"
    else:
        status = "Unknown"

    # Action steps based on status
    if status in ["Eligible", "Potentially Eligible"]:
        action_steps = [
            f"Review official guidelines on {scheme['official_source']}.",
            "Gather required documents: " + ", ".join(scheme.get("documents", [])[:3]) + ".",
            f"Visit official portal: {scheme['official_url']} or contact your block agricultural officer.",
            "Complete registration before application deadline."
        ]
    elif status == "Insufficient Information":
        action_steps = [
            "Update your farm profile with State, District, Crop, and Farm Area.",
            "Re-run scheme eligibility check for precise matching."
        ]
    else:
        action_steps = [
            "Explore other Central and State schemes matching your profile.",
            "Consult local Krishi Vigyan Kendra (KVK) for alternative assistance programs."
        ]

    return {
        "scheme_id": scheme["id"],
        "scheme_name": scheme["scheme_name"],
        "level": scheme["level"],
        "state": scheme["state"],
        "category": scheme["category"],
        "eligibility_status": status,
        "match_percentage": max(0, min(100, match_score)),
        "reasons": reasons,
        "missing_information": missing_info,
        "action_steps": action_steps,
        "official_disclaimer": OFFICIAL_DISCLAIMER
    }

def check_bulk_eligibility(
    state: Optional[str] = None,
    district: Optional[str] = None,
    crop: Optional[str] = None,
    season: Optional[str] = None,
    farm_size_acres: Optional[float] = None,
    farmer_category: Optional[str] = "General",
    land_ownership: Optional[str] = "Owner",
    irrigation_type: Optional[str] = "available",
    solar_pump_needed: Optional[bool] = False,
    equipment_needed: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates all schemes applicable to the farmer's state + Central schemes.
    Sorts by match percentage and status.
    """
    schemes = get_government_schemes(state=state)
    results = []

    for s in schemes:
        eval_res = evaluate_scheme_eligibility(
            scheme=s,
            state=state,
            district=district,
            crop=crop,
            season=season,
            farm_size_acres=farm_size_acres,
            farmer_category=farmer_category,
            land_ownership=land_ownership,
            irrigation_type=irrigation_type,
            solar_pump_needed=solar_pump_needed,
            equipment_needed=equipment_needed
        )
        # Attach full scheme card metadata for easy UI consumption
        eval_res["scheme_details"] = s
        results.append(eval_res)

    # Sort: Potentially Eligible / Eligible first, highest match percentage first
    status_order = {
        "Eligible": 1,
        "Potentially Eligible": 2,
        "Insufficient Information": 3,
        "Unknown": 4,
        "Not Eligible": 5
    }
    results.sort(key=lambda x: (status_order.get(x["eligibility_status"], 9), -x["match_percentage"]))
    return results
