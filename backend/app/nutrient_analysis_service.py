"""
nutrient_analysis_service.py
Provides bounded, academically grounded agronomic nutrient depletion intelligence.
Estimates depletion tendencies across 11 essential plant nutrients based on:
- Previous crop uptake curves & residues
- Current crop sequence
- Repeated monoculture/cultivation count
- Soil physical & chemical characteristics (leaching vs fixation)
- Optional soil pH
- Optional laboratory soil test values (which override estimates with High confidence)

Distinguishes explicitly between:
- Automatically estimated information (Agronomic Inference)
- Farmer-provided crop & soil observations
- Actual laboratory soil-test measurements
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# 11 Essential Target Nutrients
ALL_NUTRIENTS = [
    {"name": "Nitrogen", "symbol": "N", "category": "Macronutrient"},
    {"name": "Phosphorus", "symbol": "P", "category": "Macronutrient"},
    {"name": "Potassium", "symbol": "K", "category": "Macronutrient"},
    {"name": "Sulfur", "symbol": "S", "category": "Secondary Nutrient"},
    {"name": "Calcium", "symbol": "Ca", "category": "Secondary Nutrient"},
    {"name": "Magnesium", "symbol": "Mg", "category": "Secondary Nutrient"},
    {"name": "Zinc", "symbol": "Zn", "category": "Micronutrient"},
    {"name": "Iron", "symbol": "Fe", "category": "Micronutrient"},
    {"name": "Boron", "symbol": "B", "category": "Micronutrient"},
    {"name": "Manganese", "symbol": "Mn", "category": "Micronutrient"},
    {"name": "Copper", "symbol": "Cu", "category": "Micronutrient"},
]

# Heavy Feeders & Nutrient Affinity by Crop
CROP_PROFILES: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "family": "cereal",
        "heavy_uptake": ["N", "P"],
        "moderate_uptake": ["K", "Zn", "Mn"],
        "restorative": False,
        "notes": "Intensive cereal crop that exhausts 100–120 kg N/ha and draws down available zinc in alkaline soils."
    },
    "rice": {
        "family": "cereal",
        "heavy_uptake": ["N", "P", "K"],
        "moderate_uptake": ["Zn", "Fe"],
        "restorative": False,
        "notes": "Anaerobic submerged paddies cause substantial nitrogen volatilization/denitrification and immobilize zinc."
    },
    "mustard": {
        "family": "oilseed",
        "heavy_uptake": ["S", "N", "P"],
        "moderate_uptake": ["K", "B", "Zn"],
        "restorative": False,
        "notes": "High glucosinolate and oil synthesis requires large sulfur uptake (20–40 kg S/ha); causes rapid sulfur drawdown."
    },
    "maize": {
        "family": "cereal",
        "heavy_uptake": ["N", "K", "P"],
        "moderate_uptake": ["Zn", "Mg"],
        "restorative": False,
        "notes": "Extremely vigorous vegetative feeder requiring substantial N and K; highly sensitive to zinc deficiency."
    },
    "potato": {
        "family": "tuber",
        "heavy_uptake": ["K", "N", "P"],
        "moderate_uptake": ["Mg", "B"],
        "restorative": False,
        "notes": "Tuber bulking exhausts soil potassium reserves (150–200 kg K2O/ha); leaves limited residual potassium."
    },
    "tomato": {
        "family": "vegetable",
        "heavy_uptake": ["K", "Ca", "N"],
        "moderate_uptake": ["B", "P", "Mg"],
        "restorative": False,
        "notes": "Prolific fruiting demands abundant potassium and calcium; susceptible to blossom end rot under calcium deficiency."
    },
    "gram": {
        "family": "legume",
        "heavy_uptake": ["P", "S"],
        "moderate_uptake": ["Zn", "Mo"],
        "restorative": True,
        "notes": "Symbiotic Rhizobium fixation adds 20–40 kg N/ha into soil, but crop draws moderately on phosphorus and sulfur."
    },
    "chickpea": {
        "family": "legume",
        "heavy_uptake": ["P", "S"],
        "moderate_uptake": ["Zn", "Mo"],
        "restorative": True,
        "notes": "Leguminous pulse that enriches soil nitrogen while demanding adequate available phosphorus."
    },
    "cotton": {
        "family": "fiber",
        "heavy_uptake": ["K", "N", "P"],
        "moderate_uptake": ["B", "Mg", "Zn"],
        "restorative": False,
        "notes": "Deep rooted taproot system with prolonged boll development exhausting potassium and boron."
    },
    "sugarcane": {
        "family": "grass",
        "heavy_uptake": ["N", "K", "P", "S"],
        "moderate_uptake": ["Fe", "Mn", "Zn"],
        "restorative": False,
        "notes": "Long-duration heavy biomass crop causing severe multi-nutrient depletion."
    }
}

# Soil Type Vulnerabilities
SOIL_VULNERABILITIES: Dict[str, Dict[str, Any]] = {
    "Sandy soil": {
        "leaching_prone": ["N", "K", "S", "B", "Mg"],
        "fixation_prone": [],
        "retentive": [],
        "summary": "Low cation exchange capacity and high porosity promote rapid leaching of soluble anions (N, S, B) and potassium."
    },
    "Sandy loam": {
        "leaching_prone": ["N", "K", "S", "B"],
        "fixation_prone": [],
        "retentive": ["Mg"],
        "summary": "Moderate drainage with moderate leaching potential for nitrogen and sulfur under high rainfall or heavy irrigation."
    },
    "Loamy soil": {
        "leaching_prone": ["N"],
        "fixation_prone": [],
        "retentive": ["K", "Ca", "Mg"],
        "summary": "Balanced texture with good nutrient retention capacity and steady organic turnover."
    },
    "Clay soil": {
        "leaching_prone": [],
        "fixation_prone": ["P", "Zn"],
        "retentive": ["K", "Ca", "Mg", "Fe"],
        "summary": "High nutrient buffering capacity; low leaching, but strong tendency to fix phosphate and reduce zinc mobility."
    },
    "Clay loam": {
        "leaching_prone": [],
        "fixation_prone": ["P"],
        "retentive": ["K", "Ca", "Mg"],
        "summary": "Strong moisture and cation retention with moderate phosphorus fixation."
    },
    "Black soil": {
        "leaching_prone": [],
        "fixation_prone": ["P", "Zn"],
        "retentive": ["K", "Ca", "Mg", "Fe"],
        "summary": "Montmorillonite-rich Vertisol with high calcium and potassium reserves, but commonly prone to zinc and phosphorus fixation."
    },
    "Red soil": {
        "leaching_prone": ["N", "K", "S"],
        "fixation_prone": ["P"],
        "retentive": ["Fe", "Mn"],
        "summary": "Rich in kaolinite and iron/aluminum oxides which actively fix soluble phosphorus; prone to potassium and boron deficiency."
    },
    "Laterite soil": {
        "leaching_prone": ["N", "K", "Ca", "Mg", "B"],
        "fixation_prone": ["P"],
        "retentive": ["Fe", "Mn"],
        "summary": "Intensely weathered, acidic soil where bases (Ca, Mg, K) have leached; severe phosphorus fixation by iron oxides."
    },
    "Desert/Arid Soil": {
        "leaching_prone": [],
        "fixation_prone": ["P", "Zn", "Fe"],
        "retentive": ["Ca", "Mg", "K"],
        "summary": "Low organic carbon with high alkaline salts and calcareous nodules; phosphorus and micronutrients (Zn, Fe) are immobilized."
    },
    "Alluvial Soil": {
        "leaching_prone": ["N"],
        "fixation_prone": ["Zn"],
        "retentive": ["K"],
        "summary": "Naturally fertile riverine sediment; under intensive double-cropping, available nitrogen and zinc deplete first."
    },
    "Mountain/Forest Soil": {
        "leaching_prone": ["Ca", "Mg"],
        "fixation_prone": ["P"],
        "retentive": ["N", "Fe"],
        "summary": "High organic humus layer with rich nitrogen, but acidic subsoils can restrict phosphorus and calcium availability."
    },
    "Saline/Alkaline Soil": {
        "leaching_prone": [],
        "fixation_prone": ["Zn", "Fe", "Mn", "P"],
        "retentive": ["Ca", "Mg", "K"],
        "summary": "Excess sodium/calcium carbonates drastically suppress availability of zinc, iron, manganese, and phosphorus."
    }
}


BILINGUAL_CROP_NORM = {
    "wheat": "wheat", "गेहूं": "wheat", "gehun": "wheat", "gehu": "wheat",
    "mustard": "mustard", "सरसों": "mustard", "sarson": "mustard", "rai": "mustard",
    "rice": "rice", "चावल": "rice", "धान": "rice", "paddy": "rice", "chawal": "rice", "dhan": "rice",
    "maize": "maize", "मक्का": "maize", "makka": "maize", "corn": "maize",
    "potato": "potato", "आलू": "potato", "aalu": "potato", "alu": "potato",
    "tomato": "tomato", "टमाटर": "tomato", "tamatar": "tomato",
    "gram": "gram", "चना": "gram", "chana": "gram", "chickpea": "chickpea", "gram/chickpea": "gram",
    "cotton": "cotton", "कपास": "cotton", "kapas": "cotton",
    "sugarcane": "sugarcane", "गन्ना": "sugarcane", "ganna": "sugarcane"
}

BILINGUAL_SOIL_NORM = {
    "alluvial soil": "Alluvial soil", "जलोढ़ मिट्टी": "Alluvial soil", "alluvial": "Alluvial soil",
    "black soil": "Black soil", "काली मिट्टी": "Black soil", "regur": "Black soil",
    "red soil": "Red soil", "लाल मिट्टी": "Red soil",
    "laterite soil": "Laterite soil", "लैटेराइट मिट्टी": "Laterite soil",
    "desert/arid soil": "Desert / Arid soil", "desert soil": "Desert / Arid soil", "मरुस्थलीय / रेतीली मिट्टी": "Desert / Arid soil",
    "mountain/forest soil": "Mountain / Forest soil", "पर्वतीय / वन मिट्टी": "Mountain / Forest soil",
    "saline/alkaline soil": "Saline / Alkaline soil", "लवणीय / क्षारीय मिट्टी": "Saline / Alkaline soil",
    "loamy soil": "Loamy soil", "दोमट मिट्टी": "Loamy soil",
    "sandy soil": "Sandy soil", "बलुई मिट्टी": "Sandy soil",
    "clayey soil": "Clayey soil", "चिकनी मिट्टी": "Clayey soil",
    "sandy loam": "Sandy loam", "बलुई दोमट": "Sandy loam",
    "clay loam": "Clay loam", "चिकनी दोमट": "Clay loam",
    "silty soil": "Silty soil", "गाद युक्त मिट्टी": "Silty soil"
}

def resolve_crop_key(name: Optional[str]) -> str:
    if not name:
        return ""
    clean = name.strip().lower()
    if "(" in clean:
        parts = clean.replace(")", "").split("(")
        for p in parts:
            if p.strip() in BILINGUAL_CROP_NORM:
                return BILINGUAL_CROP_NORM[p.strip()]
    if clean in BILINGUAL_CROP_NORM:
        return BILINGUAL_CROP_NORM[clean]
    for k, v in BILINGUAL_CROP_NORM.items():
        if k in clean:
            return v
    return clean

def resolve_soil_key(name: Optional[str]) -> str:
    if not name:
        return "Loamy soil"
    clean = name.strip().lower()
    if clean in BILINGUAL_SOIL_NORM:
        return BILINGUAL_SOIL_NORM[clean]
    for k, v in BILINGUAL_SOIL_NORM.items():
        if k in clean:
            return v
    # Check case-insensitive against SOIL_VULNERABILITIES keys
    for k in SOIL_VULNERABILITIES:
        if k.lower() == clean:
            return k
    return "Loamy soil"


def analyze_nutrient_depletion(
    soil_type: str,
    previous_crop: Optional[str] = None,
    previous_crop_period: Optional[str] = None,
    current_crop: Optional[str] = None,
    cultivation_count: int = 1,
    soil_ph: Optional[float] = None,
    soil_n: Optional[float] = None,
    soil_p: Optional[float] = None,
    soil_k: Optional[float] = None,
    organic_carbon: Optional[float] = None,
    soil_type_source: str = "auto_detected"
) -> Dict[str, Any]:
    """
    Computes nutrient depletion status across 11 nutrients.
    Returns structured results, plain-language 'Why' explanations, confidence, and verification steps.
    """
    prev_clean = resolve_crop_key(previous_crop)
    curr_clean = resolve_crop_key(current_crop)
    soil_clean = resolve_soil_key(soil_type)

    prev_prof = CROP_PROFILES.get(prev_clean)
    curr_prof = CROP_PROFILES.get(curr_clean)
    soil_vuln = SOIL_VULNERABILITIES.get(soil_clean, SOIL_VULNERABILITIES["Loamy soil"])

    has_lab_test = any(v is not None for v in [soil_n, soil_p, soil_k, organic_carbon])
    assessments: List[Dict[str, Any]] = []

    # Track summary categorizations
    potentially_depleted: List[str] = []
    possibly_depleted: List[str] = []
    likely_adequate: List[str] = []
    requires_testing: List[str] = []

    for item in ALL_NUTRIENTS:
        sym = item["symbol"]
        name = item["name"]
        cat = item["category"]

        # --- 1. Laboratory Test Check (Highest Priority) ---
        if sym == "N" and soil_n is not None:
            if soil_n < 40:
                status = "Likely depleted"
                reason = f"Laboratory soil test shows low available Nitrogen ({soil_n:.1f} kg/ha, below optimum 40–80 kg/ha)."
            elif soil_n > 80:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows high available Nitrogen ({soil_n:.1f} kg/ha)."
            else:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows adequate available Nitrogen ({soil_n:.1f} kg/ha)."
            assessments.append({
                "nutrient": name,
                "symbol": sym,
                "category": cat,
                "status": status,
                "confidence": "High",
                "source": "Laboratory Soil Test",
                "reason": reason,
                "verification": "Confirmed by entered laboratory measurement. Periodic re-testing every 2 years is recommended."
            })
            if status == "Likely depleted":
                potentially_depleted.append(sym)
            else:
                likely_adequate.append(sym)
            continue

        if sym == "P" and soil_p is not None:
            if soil_p < 20:
                status = "Likely depleted"
                reason = f"Laboratory soil test shows low available Phosphorus ({soil_p:.1f} kg/ha, below optimum 20–45 kg/ha)."
            elif soil_p > 45:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows abundant available Phosphorus ({soil_p:.1f} kg/ha)."
            else:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows adequate available Phosphorus ({soil_p:.1f} kg/ha)."
            assessments.append({
                "nutrient": name,
                "symbol": sym,
                "category": cat,
                "status": status,
                "confidence": "High",
                "source": "Laboratory Soil Test",
                "reason": reason,
                "verification": "Confirmed by entered laboratory measurement."
            })
            if status == "Likely depleted":
                potentially_depleted.append(sym)
            else:
                likely_adequate.append(sym)
            continue

        if sym == "K" and soil_k is not None:
            if soil_k < 25:
                status = "Likely depleted"
                reason = f"Laboratory soil test shows low available Potassium ({soil_k:.1f} kg/ha, below optimum 25–50 kg/ha)."
            elif soil_k > 55:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows high available Potassium ({soil_k:.1f} kg/ha)."
            else:
                status = "Likely adequate"
                reason = f"Laboratory soil test shows adequate available Potassium ({soil_k:.1f} kg/ha)."
            assessments.append({
                "nutrient": name,
                "symbol": sym,
                "category": cat,
                "status": status,
                "confidence": "High",
                "source": "Laboratory Soil Test",
                "reason": reason,
                "verification": "Confirmed by entered laboratory measurement."
            })
            if status == "Likely depleted":
                potentially_depleted.append(sym)
            else:
                likely_adequate.append(sym)
            continue

        # --- 2. Agronomic Estimate Model (No direct lab measurement) ---
        status = "Likely adequate"
        confidence = "Medium"
        reasons_list: List[str] = []

        # Previous crop uptake impact
        if prev_prof and sym in prev_prof["heavy_uptake"]:
            status = "Likely depleted"
            confidence = "High" if prev_clean == curr_clean else "Medium"
            reasons_list.append(f"Previous crop ({previous_crop}) has heavy {name} demand. {prev_prof['notes']}")
        elif prev_prof and sym in prev_prof["moderate_uptake"]:
            status = "Possibly depleted"
            reasons_list.append(f"Previous crop ({previous_crop}) exerts moderate demand on available {name}.")

        # Legume restorative effect on Nitrogen
        if prev_prof and prev_prof.get("restorative") and sym == "N":
            if status == "Likely depleted":
                status = "Possibly depleted"
            else:
                status = "Likely adequate"
            reasons_list.append(f"Legume cropping ({previous_crop}) helps biological nitrogen fixation, mitigating severe N depletion.")

        # Consecutive monoculture / repeated cultivation penalty
        if cultivation_count >= 2 and prev_prof and sym in prev_prof["heavy_uptake"]:
            status = "Likely depleted"
            confidence = "High"
            reasons_list.append(f"Repeated cultivation ({cultivation_count} consecutive cycles) without crop rotation accelerates {name} mining.")

        # Soil Texture & Type Impact
        if sym in soil_vuln.get("leaching_prone", []):
            if status == "Likely adequate":
                status = "Possibly depleted"
            elif status == "Possibly depleted":
                status = "Likely depleted"
            reasons_list.append(f"{soil_clean} is prone to leaching of {name} under irrigation or rain.")

        if sym in soil_vuln.get("fixation_prone", []):
            if status == "Likely adequate":
                status = "Possibly depleted"
            reasons_list.append(f"{soil_clean} chemical properties can fix {name} into insoluble forms, lowering plant availability.")

        # Soil pH impact (if provided)
        if soil_ph is not None:
            if soil_ph < 6.0:  # Acidic
                if sym in ["P", "Ca", "Mg"]:
                    if status == "Likely adequate":
                        status = "Possibly depleted"
                    reasons_list.append(f"Acidic soil pH ({soil_ph:.1f}) reduces availability of {name} due to aluminum/iron binding.")
                elif sym in ["Fe", "Mn"]:
                    reasons_list.append(f"Acidic pH ({soil_ph:.1f}) increases {name} solubility, making deficiency rare.")
            elif soil_ph > 7.8:  # Alkaline / Calcareous
                if sym in ["Zn", "Fe", "Mn", "B"]:
                    status = "Likely depleted" if sym == "Zn" else "Possibly depleted"
                    reasons_list.append(f"Alkaline soil pH ({soil_ph:.1f}) precipitates {name}, causing low plant-available uptake.")
                elif sym == "P":
                    if status == "Likely adequate":
                        status = "Possibly depleted"
                    reasons_list.append(f"Alkaline pH ({soil_ph:.1f}) leads to calcium-phosphate precipitation, fixing available phosphorus.")

        # Micronutrients without strong signals fall into "Requires Testing"
        if cat == "Micronutrient" and not reasons_list:
            status = "Unknown / requires soil test"
            confidence = "Low"
            reasons_list.append(f"Background availability of {name} varies widely by micro-topography and parent material; cannot be determined reliably without lab testing.")

        if not reasons_list:
            reasons_list.append(f"Standard cropping sequence on {soil_clean} typically maintains acceptable baseline {name} under normal management.")

        # Recommended verification
        if status in ["Likely depleted", "Possibly depleted"]:
            verification = f"A standard laboratory soil test (0–15 cm core) is advised before applying {name}-based fertilizers to avoid over- or under-fertilization."
        elif status == "Unknown / requires soil test":
            verification = f"Send a soil sample to a certified Krishi Vigyan Kendra (KVK) or government soil testing laboratory to assess {name} micronutrient levels."
        else:
            verification = f"Maintain standard organic manure or basal dose. Routine soil testing every 2–3 seasons is sufficient."

        # Assign to summary buckets
        if status == "Likely depleted":
            potentially_depleted.append(sym)
        elif status == "Possibly depleted":
            possibly_depleted.append(sym)
        elif status == "Likely adequate":
            likely_adequate.append(sym)
        else:
            requires_testing.append(sym)

        assessments.append({
            "nutrient": name,
            "symbol": sym,
            "category": cat,
            "status": status,
            "confidence": confidence,
            "source": "Agronomic Cropping History & Soil Model",
            "reason": " ".join(reasons_list),
            "verification": verification
        })

    return {
        "farm_context": {
            "soil_type": soil_clean,
            "soil_type_source": soil_type_source,
            "previous_crop": previous_crop or "Not specified",
            "previous_crop_period": previous_crop_period or "Not specified",
            "current_crop": current_crop or "None / Fallow",
            "cultivation_count": cultivation_count,
            "soil_ph": soil_ph,
            "soil_ph_status": f"pH {soil_ph:.1f}" if soil_ph is not None else "Not provided (Optional)",
            "is_lab_verified": has_lab_test
        },
        "summary": {
            "potentially_depleted": potentially_depleted,
            "possibly_depleted": possibly_depleted,
            "likely_adequate": likely_adequate,
            "requires_testing": requires_testing
        },
        "nutrients": assessments,
        "soil_vulnerability_notes": soil_vuln.get("summary", ""),
        "disclaimer": (
            "IMPORTANT: This nutrient depletion analysis is an AI-based agronomic estimate derived from cropping history, "
            "soil characteristics, and established regional nutrient uptake patterns. It does NOT measure exact soil concentrations. "
            "For precise fertilizer application doses, farmers are strongly encouraged to obtain a formal laboratory Soil Health Card test."
        ),
        "analyzed_at": datetime.now(timezone.utc).isoformat()
    }
