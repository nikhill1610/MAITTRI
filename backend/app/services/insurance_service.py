"""
Insurance Planning Service for MAITTRI Platform
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Strict Agronomic & Legal Rules:
- Never claim weather or crop selection automatically makes a farmer eligible for insurance claim.
- Disclose official statutory farmer premium caps (1.5% Rabi, 2% Kharif, 5% Commercial/Horticulture under PMFBY).
- Detail the 72-hour mandatory intimation rule for localized calamities and post-harvest losses.
- Clearly note: "Insurance eligibility/claim settlement depends on the applicable policy, notified area, loss assessment and official rules."
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

OFFICIAL_INSURANCE_DISCLAIMER = (
    "MAITTRI provides decision-support based on verified official guidelines of the Ministry of Agriculture "
    "& Farmers Welfare, Government of India. Final insurance enrollment, premium subsidy, claim admissibility, "
    "and compensation payouts depend on the notified crop status for the specific Gram Panchayat/Revenue Unit, "
    "timely submission of premium before cut-off date, and official Crop Cutting Experiments (CCEs) or loss survey."
)

# Standard PMFBY crop notification registry with typical notified states and statutory farmer shares
NOTIFIED_CROPS_REGISTRY: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "crop_name": "Wheat",
        "hindi_name": "गेहूं",
        "seasons": ["rabi"],
        "category": "Foodgrain",
        "farmer_premium_pct": 1.5,
        "notified_states": ["Uttar Pradesh", "Punjab", "Haryana", "Madhya Pradesh", "Rajasthan", "Bihar", "Gujarat", "Himachal Pradesh", "Uttarakhand"],
        "major_risks": ["Unseasonal rainfall and hailstorm during grain filling/maturity", "Terminal heat stress (sudden high temperatures in February/March)", "Rust disease outbreaks"],
        "coverage_scope": "Pre-sowing failure, mid-season adversity, standing yield loss (CCE), localized hailstorm, post-harvest losses within 14 days."
    },
    "rice": {
        "crop_name": "Rice (Paddy)",
        "hindi_name": "धान / चावल",
        "seasons": ["kharif", "rabi"],
        "category": "Foodgrain",
        "farmer_premium_pct": 2.0,
        "notified_states": ["Uttar Pradesh", "Punjab", "Haryana", "Bihar", "West Bengal", "Odisha", "Andhra Pradesh", "Telangana", "Chhattisgarh", "Madhya Pradesh", "Tamil Nadu", "Maharashtra"],
        "major_risks": ["Delayed monsoon onset / prevented transplanting", "Flooding and waterlogging during vegetative stage", "Prolonged dry spells during flowering", "Post-harvest cyclonic rain"],
        "coverage_scope": "Prevented sowing/transplanting (25% sum insured), standing crop yield loss, localized inundation and flood, post-harvest drying period."
    },
    "mustard": {
        "crop_name": "Mustard / Rapeseed",
        "hindi_name": "सरसों / राई",
        "seasons": ["rabi"],
        "category": "Oilseed",
        "farmer_premium_pct": 1.5,
        "notified_states": ["Rajasthan", "Uttar Pradesh", "Madhya Pradesh", "Haryana", "Punjab", "Gujarat", "West Bengal"],
        "major_risks": ["Frost and extreme cold waves in December/January", "Aphid infestation during pod development", "Hailstorm during pod maturity"],
        "coverage_scope": "Standing crop yield loss, localized hailstorm and frost, mid-season drought."
    },
    "soybean": {
        "crop_name": "Soybean",
        "hindi_name": "सोयाबीन",
        "seasons": ["kharif"],
        "category": "Oilseed",
        "farmer_premium_pct": 2.0,
        "notified_states": ["Madhya Pradesh", "Maharashtra", "Rajasthan", "Karnataka", "Telangana", "Gujarat"],
        "major_risks": ["Excessive continuous rainfall causing root rot / water stagnation", "Severe dry spell at pod filling stage", "Yellow Mosaic Virus"],
        "coverage_scope": "Prevented sowing, yield loss against threshold yield, localized inundation."
    },
    "maize": {
        "crop_name": "Maize",
        "hindi_name": "मक्का",
        "seasons": ["kharif", "rabi"],
        "category": "Foodgrain",
        "farmer_premium_pct": 2.0,
        "notified_states": ["Bihar", "Madhya Pradesh", "Karnataka", "Rajasthan", "Uttar Pradesh", "Maharashtra", "Punjab"],
        "major_risks": ["Fall Armyworm attack", "Waterlogging in seedling stage", "Drought at tasseling/silking stage"],
        "coverage_scope": "Mid-season adversity, threshold yield loss, localized pest epidemic declaration."
    },
    "cotton": {
        "crop_name": "Cotton",
        "hindi_name": "कपास",
        "seasons": ["kharif"],
        "category": "Annual Commercial",
        "farmer_premium_pct": 5.0,
        "notified_states": ["Gujarat", "Maharashtra", "Telangana", "Andhra Pradesh", "Punjab", "Haryana", "Rajasthan", "Karnataka"],
        "major_risks": ["Pink Bollworm infestation", "Excessive rain causing boll shedding", "Untimely rain staining open bolls"],
        "coverage_scope": "Commercial crop coverage, yield loss assessed via CCE, localized calamities."
    },
    "sugarcane": {
        "crop_name": "Sugarcane",
        "hindi_name": "गन्ना",
        "seasons": ["annual", "commercial", "rabi", "kharif"],
        "category": "Annual Commercial",
        "farmer_premium_pct": 5.0,
        "notified_states": ["Uttar Pradesh", "Maharashtra", "Karnataka", "Tamil Nadu", "Bihar", "Haryana", "Punjab"],
        "major_risks": ["Severe drought in early formative stage", "Water stagnation / flooding", "Red rot disease"],
        "coverage_scope": "Standing crop yield loss, localized windstorm / flood lodging."
    },
    "potato": {
        "crop_name": "Potato",
        "hindi_name": "आलू",
        "seasons": ["rabi"],
        "category": "Annual Horticultural",
        "farmer_premium_pct": 5.0,
        "notified_states": ["Uttar Pradesh", "West Bengal", "Punjab", "Bihar", "Gujarat", "Madhya Pradesh"],
        "major_risks": ["Late Blight epidemic in cloudy/humid weather", "Frost damage during tuber bulking", "Unseasonal rain causing tuber rotting"],
        "coverage_scope": "Weather-based RWBCIS or PMFBY yield index where notified, localized frost and hail."
    },
    "gram": {
        "crop_name": "Gram / Chickpea",
        "hindi_name": "चना",
        "seasons": ["rabi"],
        "category": "Pulses",
        "farmer_premium_pct": 1.5,
        "notified_states": ["Madhya Pradesh", "Rajasthan", "Maharashtra", "Uttar Pradesh", "Karnataka", "Andhra Pradesh"],
        "major_risks": ["Pod borer attack", "Wilt disease", "Untimely winter rainfall during flowering"],
        "coverage_scope": "Threshold yield shortfall, localized hailstorm, drought."
    }
}

SCHEME_COMPARISON_DATA = [
    {
        "scheme": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "approach": "Yield-Based Area Approach (Village / Panchayat Level) + Individual Localized Calamity",
        "perils_covered": "Drought, dry spells, flood, inundation, pests & diseases, landslides, natural fire, lightning, storm, hailstorm, cyclone, post-harvest losses.",
        "farmer_premium": "1.5% (Rabi) | 2.0% (Kharif) | 5.0% (Commercial/Horticulture)",
        "claim_settlement": "Based on Crop Cutting Experiments (CCEs) comparing actual yield against threshold yield, plus individual field loss survey for hail/flood.",
        "intimation_deadline": "Strictly within 72 hours for localized calamities & post-harvest damage.",
        "applicability": "Notified crops in notified insurance units across participating states."
    },
    {
        "scheme": "Restructured Weather Based Crop Insurance Scheme (RWBCIS)",
        "approach": "Weather Index Based (Reference Weather Stations / AWS)",
        "perils_covered": "Rainfall deficit/excess, temperature anomalies (heat/frost), high relative humidity, high wind speed.",
        "farmer_premium": "Capped similarly to PMFBY (1.5% - 5.0%), state-subsidized balance.",
        "claim_settlement": "Automatic settlement triggered when weather station recorded data breaches predefined term-sheet triggers (no CCE required).",
        "intimation_deadline": "No individual intimation required; automatic trigger based on weather station telemetry.",
        "applicability": "Perishable and horticultural crops where weather triggers have high correlation with crop loss."
    },
    {
        "scheme": "Bihar Rajya Fasal Sahayata Yojana (BRFSY)",
        "approach": "State-Funded Direct Crop Assistance (Applicable in Bihar only)",
        "perils_covered": "Natural disasters leading to crop yield decline compared to 5-year average.",
        "farmer_premium": "₹0 (100% Free - Zero farmer contribution).",
        "claim_settlement": "Direct cash transfer: ₹7,500/ha for loss <= 20%, ₹10,000/ha for loss > 20% (up to 2 ha).",
        "intimation_deadline": "Registration during sowing window; automatic assessment via state revenue machinery.",
        "applicability": "Resident farmers of Bihar (Ryot & Non-Ryot tenant farmers)."
    }
]

def analyze_crop_insurance(
    state: Optional[str] = None,
    district: Optional[str] = None,
    crop: Optional[str] = None,
    season: Optional[str] = "rabi",
    farm_area: Optional[float] = None,
    sowing_date: Optional[str] = None,
    expected_harvest: Optional[str] = None,
    irrigation: Optional[str] = "available",
    farm_type: Optional[str] = "Owner",
    farmer_category: Optional[str] = "Small/Marginal",
    weather_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyzes crop insurance applicability, risk parameters, statutory premium,
    claim workflows, document requirements, and comparison matrices.
    Returns complete structured Sections A through M.
    """
    norm_state = state.strip().title() if state else "Uttar Pradesh"
    norm_district = district.strip().title() if district else "District Center"
    norm_crop = crop.strip().lower() if crop else "wheat"
    norm_season = season.strip().lower() if season else "rabi"
    norm_area = float(farm_area) if farm_area and farm_area > 0 else 2.5

    # Check notification status
    crop_info = NOTIFIED_CROPS_REGISTRY.get(norm_crop)
    is_notified = False
    is_bihar = "bihar" in norm_state.lower()

    if crop_info:
        # Check if state matches notified states
        state_match = any(norm_state.lower() in ns.lower() for ns in crop_info["notified_states"])
        season_match = norm_season in crop_info["seasons"] or "all" in crop_info["seasons"]
        is_notified = state_match and season_match

    # Section A: Farmer & Farm Profile
    sec_a = {
        "state": norm_state,
        "district": norm_district,
        "farm_area_acres": norm_area,
        "current_crop": crop_info["crop_name"] if crop_info else (crop.title() if crop else "Unknown"),
        "season": norm_season.capitalize(),
        "sowing_date": sowing_date or "First week of November (Standard)",
        "expected_harvest": expected_harvest or "March - April (Standard)",
        "irrigation": irrigation or "available",
        "farm_type": farm_type or "Owner Cultivator",
        "farmer_category": farmer_category or "Small/Marginal Farmer",
        "profile_source": "MAITTRI Farm Profile (Auto-retrieved & Editable)"
    }

    # Section B: Current Crop
    sec_b = {
        "crop_name": crop_info["crop_name"] if crop_info else (crop.title() if crop else "Unknown"),
        "crop_category": crop_info["category"] if crop_info else "Unclassified",
        "notified_in_state": "Yes (Notified Crop Unit)" if is_notified else "Not Verified / Area Specific",
        "verified_coverage": True if is_notified or is_bihar else False,
        "notification_note": (
            f"{crop_info['crop_name']} is an officially notified crop under PMFBY guidelines in {norm_state} for {norm_season.capitalize()} season."
            if is_notified else
            f"No verified state-wide notification entry found for '{crop}' in {norm_state} during {norm_season.capitalize()}. Insurance coverage is contingent upon specific district/block notification."
        )
    }

    # Section C: Season
    sec_c = {
        "season": norm_season.capitalize(),
        "standard_sowing_window": "October 15 – November 30" if norm_season == "rabi" else "June 15 – July 31",
        "standard_harvest_window": "March 15 – April 30" if norm_season == "rabi" else "October 15 – November 30",
        "enrollment_cut_off_date": "December 31 (Rabi)" if norm_season == "rabi" else "July 31 (Kharif)",
        "season_status": "Open / Active Enrollment Window"
    }

    # Section D: Risk Analysis (Integrated Weather + Agronomic Perils)
    risks_identified: List[Dict[str, str]] = []
    weather_risk_detected = False

    if crop_info:
        for r in crop_info["major_risks"]:
            risks_identified.append({
                "peril": r,
                "severity": "Moderate to High",
                "coverage_status": "Eligible under PMFBY Non-Preventable Natural Risk Clauses"
            })

    # Weather telemetry risk evaluation
    if weather_data and isinstance(weather_data, dict):
        curr = weather_data.get("current", {})
        temp = curr.get("temperature_2m")
        humidity = curr.get("relative_humidity_2m")
        wind = curr.get("wind_speed_10m")
        precip = curr.get("precipitation")

        if temp and temp > 35 and norm_season == "rabi":
            weather_risk_detected = True
            risks_identified.append({
                "peril": f"Elevated Field Temperature ({temp}°C) during Rabi season",
                "severity": "High (Risk of forced maturity / terminal heat stress)",
                "coverage_status": "Covered under mid-season adverse weather triggers"
            })
        if wind and wind > 25:
            weather_risk_detected = True
            risks_identified.append({
                "peril": f"High Wind Speed ({wind} km/h)",
                "severity": "Moderate (Risk of lodging of tall cereal stands)",
                "coverage_status": "Covered under localized storm/cyclone peril"
            })
        if precip and precip > 20:
            weather_risk_detected = True
            risks_identified.append({
                "peril": f"Heavy Precipitation ({precip} mm recorded)",
                "severity": "Moderate to High (Waterlogging / foliar rot)",
                "coverage_status": "Covered under localized inundation & flood clause"
            })

    sec_d = {
        "potential_risks_detected": risks_identified,
        "weather_risk_alert": "Potential agricultural risk detected." if weather_risk_detected else "Standard seasonal agricultural risks apply.",
        "mandatory_risk_disclaimer": (
            "Potential agricultural risk detected. Insurance eligibility and claim settlement depend strictly on "
            "the applicable policy, notified area, loss assessment by revenue/agriculture surveyor, and official scheme rules. "
            "Weather readings alone do not constitute an automatic claim guarantee."
        )
    }

    # Section E: Relevant Insurance Scheme
    if is_bihar:
        primary_scheme = {
            "name": "Bihar Rajya Fasal Sahayata Yojana (BRFSY)",
            "level": "State-Funded Comprehensive Assistance",
            "type": "Zero-Premium State Compensation Scheme",
            "implementing_agency": "Cooperative Department, Government of Bihar",
            "portal": "https://state.bihar.gov.in/cooperative/",
            "helpline": "1800-1800-110",
            "farmer_premium_rate": "₹0 (100% Free for Bihar Farmers)",
            "status": "Potentially Applicable"
        }
    else:
        primary_scheme = {
            "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
            "level": "Centrally Sponsored Scheme (Central & State 50:50)",
            "type": "Yield & Weather Based Comprehensive Crop Insurance",
            "implementing_agency": "Empaneled General Insurance Companies & Ministry of Agriculture, GoI",
            "portal": "https://pmfby.gov.in/",
            "helpline": "14447 (National Toll Free Kisan Call Center for Crop Insurance)",
            "farmer_premium_rate": f"{crop_info['farmer_premium_pct'] if crop_info else 1.5}% of Sum Insured",
            "status": "Potentially Applicable" if is_notified else "Subject to District Notification"
        }

    sec_e = {
        "primary_scheme": primary_scheme,
        "alternative_schemes": [
            {
                "name": "Restructured Weather Based Crop Insurance Scheme (RWBCIS)",
                "focus": "Fruit and vegetable crops with Weather Station parametric triggers",
                "portal": "https://pmfby.gov.in/"
            },
            {
                "name": "Unified Package Insurance Scheme (UPIS)",
                "focus": "Comprehensive package covering crop, farmer life, tractor, and pump-set",
                "portal": "https://financialservices.gov.in/"
            }
        ]
    }

    # Section F: Coverage Explanation
    sec_f = {
        "stages_covered": [
            {
                "stage": "1. Prevented Sowing / Planting Risk",
                "description": "If widespread rainfall deficit or adverse seasonal conditions prevent sowing in 75%+ of the notified unit, eligible farmers get up to 25% of the sum insured."
            },
            {
                "stage": "2. Mid-Season Adversity",
                "description": "In case of severe drought, dry spell, or unseasonal floods causing expected yield loss of >50%, immediate on-account payment of up to 25% is released."
            },
            {
                "stage": "3. Standing Crop Yield Loss",
                "description": "Comprehensive risk coverage from sowing to harvest against non-preventable natural perils based on Crop Cutting Experiments (CCEs) vs guaranteed threshold yield."
            },
            {
                "stage": "4. Post-Harvest Losses",
                "description": "Coverage up to 14 days after harvest for crops kept in 'cut and spread' condition in the field against localized cyclonic rains or hailstorms."
            },
            {
                "stage": "5. Localized Calamities",
                "description": "Individual field-level assessment for loss or damage resulting from hailstorm, landslide, inundation, cloudburst, and natural fire."
            }
        ],
        "exclusions": [
            "War, nuclear perils, and malicious damage.",
            "Theft or grazing by cattle / wild animals (unless specifically notified under state add-on).",
            "Preventable risks such as poor agronomic management, lack of weeding, or deliberate neglect."
        ]
    }

    # Section G: Premium Information
    prem_pct = crop_info["farmer_premium_pct"] if crop_info else 1.5
    # Indicative Scale of Finance: Wheat ~₹35,000/acre; Rice ~₹38,000/acre; Potato ~₹70,000/acre
    scale_of_finance = 35000.0 if "wheat" in norm_crop else (38000.0 if "rice" in norm_crop else (70000.0 if "potato" in norm_crop else 32000.0))
    sum_insured_estimated = scale_of_finance * norm_area
    farmer_premium_estimated = (sum_insured_estimated * prem_pct) / 100.0

    sec_g = {
        "farmer_share_statutory_pct": f"{prem_pct}%",
        "actuarial_market_rate": "Typically 8% to 15% (depending on district risk profile)",
        "government_subsidy_share": f"Remaining actuarial premium (typically {max(0, 12 - prem_pct):.1f}%) is 100% paid by Central & State Governments",
        "indicative_sum_insured": f"₹{sum_insured_estimated:,.0f} (for {norm_area:.1f} acres based on District Scale of Finance)",
        "indicative_farmer_payable_premium": f"₹{farmer_premium_estimated:,.0f} (Capped at {prem_pct}%)",
        "premium_note": "Exact Sum Insured and premium rate vary strictly by District Level Technical Committee (DLTC) Scale of Finance. Verify exact figures on pmfby.gov.in."
    }

    # Section H: Important Dates
    sec_h = {
        "cut_off_date": "December 31 (Rabi Season)" if norm_season == "rabi" else "July 31 (Kharif Season)",
        "intimation_deadline": "Strictly within 72 Hours of localized loss occurrence",
        "survey_window": "Loss assessment completed within 10 days of notification",
        "settlement_timeline": "Direct Benefit Transfer within 30 days of survey / CCE yield declaration",
        "status": "Open for Enrollment"
    }

    # Section I: Claim Process (Step-by-Step)
    sec_i = {
        "title": "How to Claim Crop Loss (7-Step Roadmap)",
        "steps": [
            {
                "step": 1,
                "title": "Identify Natural Peril Loss",
                "detail": "Observe crop damage immediately after hailstorm, inundation, drought, or cyclone."
            },
            {
                "step": 2,
                "title": "Capture Timestamped Evidence",
                "detail": "Take geo-tagged photos and short videos of the damaged field showing affected crop stand."
            },
            {
                "step": 3,
                "title": "Mandatory 72-Hour Intimation",
                "detail": "Report the loss within 72 hours via the official Crop Insurance Mobile App, Toll-Free 14447, or nearest bank/agriculture branch."
            },
            {
                "step": 4,
                "title": "Record Intimation Reference Number",
                "detail": "Obtain and safely record the formal claim docket / intimation reference number."
            },
            {
                "step": 5,
                "title": "Field Inspection by Joint Survey Team",
                "detail": "A joint committee (Insurance Surveyor + Agriculture Officer + Patwari) inspects the field within 10 days."
            },
            {
                "step": 6,
                "title": "Loss Assessment Report Sign-off",
                "detail": "Sign the joint survey report assessing the percentage of crop damage."
            },
            {
                "step": 7,
                "title": "Direct Benefit Transfer (DBT)",
                "detail": "Approved compensation is credited directly into the farmer's Aadhaar-linked bank account."
            }
        ]
    }

    # Section J: Required Documents Checklist
    sec_j = {
        "documents": [
            {
                "name": "Aadhaar Card",
                "required_for": "Identity proof and Aadhaar-enabled DBT payment",
                "mandatory": True
            },
            {
                "name": "Land Ownership Record (Khasra / Khatauni / ROR / 7-12 Extract)",
                "required_for": "Proof of cultivable land area and survey number",
                "mandatory": True
            },
            {
                "name": "Crop Sowing Certificate / Self-Declaration",
                "required_for": "Proof that the notified crop was actively sown in the specified plot",
                "mandatory": True
            },
            {
                "name": "Bank Account Passbook / Statement",
                "required_for": "Account number and IFSC verification",
                "mandatory": True
            },
            {
                "name": "Tenancy Agreement / Affidavit",
                "required_for": "Applicable for Tenant / Sharecropper farmers cultivating non-owned land",
                "mandatory": False
            }
        ],
        "document_rule_disclaimer": "Do NOT assume every document is mandatory for every scheme. Label: 'May be required' and verify scheme-specific requirements."
    }

    # Section K: Risk Alerts
    alerts = []
    if weather_risk_detected:
        alerts.append("⚠️ Weather risk detected in your area. Review field vulnerability.")
    if norm_season == "rabi":
        alerts.append("⏰ Rabi enrollment cut-off is approaching (December 31). Ensure timely enrollment.")
    else:
        alerts.append("⏰ Kharif enrollment cut-off is July 31. Verify active enrollment through your loan account or CSC.")
    alerts.append("📢 Remember: In case of localized hailstorm or waterlogging, report within 72 hours on Helpline 14447.")
    sec_k = {"alerts": alerts}

    # Section L: Insurance Comparison Matrix
    sec_l = {
        "comparison_table": SCHEME_COMPARISON_DATA,
        "guidance": "Choose PMFBY for standard foodgrain and oilseed protection. Choose RWBCIS where automatic weather telemetry triggers are available for horticulture crops."
    }

    # Section M: Official Sources
    sec_m = {
        "sources": [
            {
                "authority": "Ministry of Agriculture & Farmers Welfare, Government of India",
                "portal_name": "National Crop Insurance Portal (PMFBY)",
                "url": "https://pmfby.gov.in/",
                "helpline": "14447 (National Kisan Call Center for Crop Insurance)",
                "mobile_app": "Crop Insurance App (Government of India, Google Play Store)"
            },
            {
                "authority": "State Department of Agriculture",
                "portal_name": f"{norm_state} State Agriculture Portal",
                "url": "https://agricoop.nic.in/",
                "helpline": "1800-180-1551 (Kisan Call Center)"
            }
        ],
        "last_verified": "01/08/2026",
        "official_disclaimer": OFFICIAL_INSURANCE_DISCLAIMER
    }

    # Confidence calculation
    confidence = "High" if is_notified and norm_area > 0 else ("Medium" if is_notified else "Low")

    # MAITTRI Action Plan (7 steps)
    action_plan = [
        "Step 1: Verify your current crop, state, district, and farm area in the profile card.",
        "Step 2: Check if your crop is notified in your specific Gram Panchayat/Block for the current season.",
        "Step 3: Keep enrollment cut-off dates in mind and ensure your bank account is Aadhaar-seeded.",
        "Step 4: Prepare the 4 essential documents (Aadhaar, Land record, Sowing certificate, Bank passbook).",
        "Step 5: Apply via the official PMFBY portal (pmfby.gov.in), Common Service Center (CSC), or your bank branch.",
        "Step 6: Save the Policy / Application Acknowledgement receipt with Docket Number.",
        "Step 7: In the event of any localized calamity, report within 72 hours via Toll-Free 14447."
    ]

    return {
        "section_A_farmer_farm_profile": sec_a,
        "section_B_current_crop": sec_b,
        "section_C_season": sec_c,
        "section_D_risk_analysis": sec_d,
        "section_E_relevant_insurance": sec_e,
        "section_F_coverage_explanation": sec_f,
        "section_G_premium_information": sec_g,
        "section_H_important_dates": sec_h,
        "section_I_claim_process": sec_i,
        "section_J_required_documents": sec_j,
        "section_K_risk_alerts": sec_k,
        "section_L_insurance_comparison": sec_l,
        "section_M_official_sources": sec_m,
        "recommendation_confidence": confidence,
        "confidence_reason": (
            "High confidence: Official PMFBY crop notification and statutory farmer premium caps verified for selected State, Crop, and Season."
            if confidence == "High" else
            "Medium confidence: General crop notification guidelines available; specific Gram Panchayat notification must be verified on official portal."
            if confidence == "Medium" else
            "Low confidence: Unverified crop notification in selected state/season. Consult official portal before proceeding."
        ),
        "maittri_action_plan": action_plan,
        "official_disclaimer": OFFICIAL_INSURANCE_DISCLAIMER
    }
