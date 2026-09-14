from ..data import CROPS

CROP_ALIASES = {
    "wheat": "Wheat", "गेहूं": "Wheat", "gehun": "Wheat", "gehu": "Wheat",
    "mustard": "Mustard", "सरसों": "Mustard", "sarson": "Mustard", "rai": "Mustard",
    "rice": "Rice", "चावल": "Rice", "धान": "Rice", "chawal": "Rice", "dhan": "Rice", "paddy": "Rice",
    "maize": "Maize", "मक्का": "Maize", "makka": "Maize", "corn": "Maize",
    "potato": "Potato", "आलू": "Potato", "aalu": "Potato", "alu": "Potato",
    "tomato": "Tomato", "टमाटर": "Tomato", "tamatar": "Tomato",
    "gram": "Gram", "चना": "Gram", "chana": "Gram", "chickpea": "Gram", "gram/chickpea": "Gram",
    "cotton": "Cotton", "कपास": "Cotton", "kapas": "Cotton",
    "sugarcane": "Sugarcane", "गन्ना": "Sugarcane", "ganna": "Sugarcane"
}

SEASON_ALIASES = {
    "rabi": "rabi", "रबी": "rabi", "रबी (rabi)": "rabi", "winter": "rabi",
    "kharif": "kharif", "खरीफ": "kharif", "खरीफ (kharif)": "kharif", "monsoon": "kharif",
    "zaid": "zaid", "जायद": "zaid", "summer": "zaid"
}

SOIL_ALIASES = {
    "alluvial soil": "alluvial soil", "alluvial": "alluvial soil", "जलोढ़ मिट्टी": "alluvial soil",
    "black soil": "black soil", "काली मिट्टी": "black soil", "regur": "black soil",
    "red soil": "red soil", "लाल मिट्टी": "red soil",
    "laterite soil": "laterite soil", "laterite": "laterite soil", "लैटेराइट मिट्टी": "laterite soil",
    "desert/arid soil": "desert/arid soil", "desert soil": "desert/arid soil", "मरुस्थलीय / रेतीली मिट्टी": "desert/arid soil",
    "mountain/forest soil": "mountain/forest soil", "mountain soil": "mountain/forest soil", "पर्वतीय / वन मिट्टी": "mountain/forest soil",
    "saline/alkaline soil": "saline/alkaline soil", "लवणीय / क्षारीय मिट्टी": "saline/alkaline soil",
    "loamy soil": "loamy soil", "दोमट मिट्टी": "loamy soil", "दोमट": "loamy soil",
    "sandy soil": "sandy soil", "बलुई मिट्टी": "sandy soil",
    "clayey soil": "clay soil", "clay soil": "clay soil", "चिकनी मिट्टी": "clay soil",
    "sandy loam": "sandy loam", "बलुई दोमट": "sandy loam",
    "clay loam": "clay loam", "चिकनी दोमट": "clay loam",
    "silty soil": "silty soil", "गाद युक्त मिट्टी": "silty soil"
}

def normalize_crop_name(name: str) -> str:
    if not name:
        return ""
    clean = name.strip().lower()
    # If string contains parenthesis like 'गेहूं (Wheat)', extract sub-parts
    if "(" in clean:
        parts = clean.replace(")", "").split("(")
        for p in parts:
            p_strip = p.strip()
            if p_strip in CROP_ALIASES:
                return CROP_ALIASES[p_strip]
    if clean in CROP_ALIASES:
        return CROP_ALIASES[clean]
    for k, v in CROP_ALIASES.items():
        if k in clean:
            return v
    return name.strip().capitalize()

def normalize_season(season: str) -> str:
    if not season:
        return "rabi"
    clean = season.strip().lower()
    return SEASON_ALIASES.get(clean, clean)

def normalize_soil(soil: str) -> str:
    if not soil:
        return "loamy soil"
    clean = soil.strip().lower()
    return SOIL_ALIASES.get(clean, clean)

def nutrient_status(value, low_threshold, high_threshold):
    if value is None:
        return "unknown"
    if value < low_threshold:
        return "low"
    if value > high_threshold:
        return "high"
    return "adequate"

def analyze_nutrients(farm):
    result = []
    for nutrient, value, low, high, source in [
        ("Nitrogen", farm.soil_n, 40, 80, "Nitrogen fertilizer or validated organic source"),
        ("Phosphorus", farm.soil_p, 20, 45, "Phosphorus fertilizer based on soil-test recommendation"),
        ("Potassium", farm.soil_k, 20, 50, "Potassium fertilizer based on soil-test recommendation"),
    ]:
        status = nutrient_status(value, low, high)
        result.append({
            "nutrient": nutrient,
            "value": value,
            "status": status,
            "suggestion": source if status == "low" else "No deficiency action suggested from this input"
        })
    return result

def score_crop(crop, farm, season):
    score = 50.0
    reasons = []

    norm_season = normalize_season(season)
    if norm_season in crop["seasons"]:
        score += 18
        reasons.append("Suitable for the selected season.")
    else:
        score -= 20
        reasons.append("Season suitability is weaker.")

    farm_soil_norm = normalize_soil(farm.soil_type)
    crop_ideal_norms = [normalize_soil(s) for s in crop["ideal_soils"]]
    if farm_soil_norm in crop_ideal_norms:
        score += 18
        reasons.append("Soil type is compatible.")
    else:
        score -= 5
        reasons.append("Soil compatibility is less favorable.")

    if farm.irrigation == "limited" and crop["water"] == "high":
        score -= 18
        reasons.append("High water requirement conflicts with limited irrigation.")
    elif farm.irrigation == "available":
        score += 4

    prev_crop_norm = normalize_crop_name(farm.previous_crop)
    if prev_crop_norm and prev_crop_norm.lower() == crop["name"].lower():
        score -= 8
        reasons.append("Growing the same crop repeatedly may be less desirable for rotation.")

    nutrients = analyze_nutrients(farm)
    low_count = sum(1 for n in nutrients if n["status"] == "low")
    if low_count:
        score -= min(8, low_count * 2)
        reasons.append("Nutrient correction may be needed before or during cultivation.")

    if crop["base_cost"] <= 30000:
        score += 4
        reasons.append("Lower estimated production cost in the demo model.")

    return max(0, min(100, round(score, 1))), reasons

def recommend(farm, season, budget):
    scored = []
    for crop in CROPS:
        score, reasons = score_crop(crop, farm, season)
        area_factor = farm.area if farm.area_unit == "acre" else farm.area * 2.471
        cost = crop["base_cost"] * area_factor
        revenue = crop["yield_q_acre"] * crop["price"] * area_factor
        profit = revenue - cost
        scored.append({
            "crop": crop["name"],
            "score": score,
            "duration_days": crop["duration"],
            "water_requirement": crop["water"],
            "estimated_cost": round(cost),
            "expected_yield_quintal": round(crop["yield_q_acre"] * area_factor, 1),
            "expected_revenue": round(revenue),
            "estimated_profit": round(profit),
            "reasons": reasons
        })
    scored.sort(key=lambda x: (x["score"], x["estimated_profit"]), reverse=True)
    return scored

def make_plan(farm, crop_name):
    if not crop_name or not isinstance(crop_name, str):
        raise ValueError("Valid crop name is required")
    norm_name = normalize_crop_name(crop_name)
    crop = next((c for c in CROPS if c["name"].lower() == norm_name.lower()), None)
    if not crop:
        # Fallback to direct substring match if needed
        clean = crop_name.strip().lower()
        crop = next((c for c in CROPS if c["name"].lower() in clean or clean in c["name"].lower()), None)
    if not crop:
        raise ValueError(f"Crop '{crop_name}' not found")
    nutrients = analyze_nutrients(farm)
    return {
        "crop": crop["name"],
        "duration_days": crop["duration"],
        "steps": [
            {"stage": "Before sowing", "actions": ["Prepare field according to soil condition", "Use quality seed/planting material", "Follow validated soil-test based nutrient plan"]},
            {"stage": "Sowing", "actions": ["Follow recommended sowing window", "Maintain crop-specific spacing and seed rate"]},
            {"stage": "Early growth", "actions": ["Monitor germination", "Control weeds at the appropriate stage", "Irrigate according to crop and soil moisture"]},
            {"stage": "Vegetative growth", "actions": ["Monitor nutrients", "Scout for pests and diseases", "Follow weather-based precautions"]},
            {"stage": "Reproductive stage", "actions": ["Maintain appropriate moisture", "Monitor crop health frequently"]},
            {"stage": "Harvest", "actions": ["Harvest at crop-appropriate maturity", "Plan storage/transport to reduce losses"]},
        ],
        "nutrient_analysis": nutrients,
        "note": "This prototype plan is a decision-support example and must be validated with local agricultural recommendations before real-world use."
    }

