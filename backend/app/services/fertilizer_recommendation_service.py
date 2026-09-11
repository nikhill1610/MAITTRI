"""
fertilizer_recommendation_service.py
MAITTRI Agricultural Decision Support System
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Intelligent, evidence-based fertilizer and pest-management decision engine.
Grounded in ICAR, CIBRC, Soil Health Card, and State Agricultural University standards.

SAFETY DIRECTIVES:
1. NEVER recommend chemical fertilizer or pesticide blindly based only on crop selection.
2. If data is insufficient, state: "Insufficient information for a reliable recommendation."
3. Do NOT fabricate soil nutrient readings, pest infestation, or pesticide efficacy.
4. Do NOT invent dosage or claim guaranteed results.
5. Clearly distinguish: Laboratory Test vs Sensor-based Reading vs Farmer Entered vs Agronomic Estimate.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

# =====================================================================
# 1. AUTHORITATIVE AGRONOMIC KNOWLEDGE BASE (ICAR, KVK, CIBRC)
# =====================================================================

CROP_DATABASE: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "name": "Wheat",
        "hindi_name": "गेहूं",
        "family": "Poaceae (Cereal)",
        "season": "rabi",
        "water_demand": "moderate",
        "root_depth": "medium (100–120 cm)",
        "stages": ["Basal / Sowing", "Crown Root Initiation (CRI)", "Tillering", "Jointing", "Flowering / Heading", "Grain Filling", "Maturity"],
        "heavy_uptake": ["N", "P"],
        "moderate_uptake": ["K", "Zn", "Mn", "S"],
        "ideal_soils": ["alluvial soil", "loamy soil", "clay loam", "sandy loam"],
        "ideal_ph": (6.0, 7.8),
        "notes": "Intensive cereal requiring 100–120 kg N/ha, 40–60 kg P2O5/ha, and 40 kg K2O/ha. Highly susceptible to Zinc deficiency in alkaline soils."
    },
    "rice": {
        "name": "Rice / Paddy",
        "hindi_name": "धान / चावल",
        "family": "Poaceae (Cereal)",
        "season": "kharif",
        "water_demand": "high",
        "root_depth": "shallow (40–60 cm)",
        "stages": ["Nursery / Basal", "Tillering", "Panicle Initiation", "Flowering", "Milking", "Dough", "Maturity"],
        "heavy_uptake": ["N", "P", "K"],
        "moderate_uptake": ["Zn", "Fe", "Si"],
        "ideal_soils": ["clay soil", "clay loam", "alluvial soil"],
        "ideal_ph": (5.5, 7.2),
        "notes": "Puddled anaerobic soil leads to N denitrification/volatilization and zinc fixation (Khaira disease). Requires split N and basal P/K."
    },
    "mustard": {
        "name": "Mustard",
        "hindi_name": "सरसों / राई",
        "family": "Brassicaceae (Oilseed)",
        "season": "rabi",
        "water_demand": "low-to-moderate",
        "root_depth": "medium (90–100 cm)",
        "stages": ["Basal / Sowing", "Rosette / Vegetative", "Branching", "Flowering", "Siliqua / Pod Formation", "Maturity"],
        "heavy_uptake": ["S", "N", "P"],
        "moderate_uptake": ["K", "B", "Zn"],
        "ideal_soils": ["sandy loam", "loamy soil", "alluvial soil"],
        "ideal_ph": (6.0, 7.5),
        "notes": "Oil and glucosinolate synthesis demands significant sulphur (20–40 kg S/ha). Very responsive to Single Super Phosphate (SSP)."
    },
    "maize": {
        "name": "Maize",
        "hindi_name": "मक्का",
        "family": "Poaceae (Cereal)",
        "season": "kharif",
        "water_demand": "moderate",
        "root_depth": "medium (80–100 cm)",
        "stages": ["Basal / Sowing", "Early Vegetative (V4-V6)", "Knee High (V8)", "Tasseling / Silking", "Grain Fill", "Maturity"],
        "heavy_uptake": ["N", "K", "P"],
        "moderate_uptake": ["Zn", "Mg", "Fe"],
        "ideal_soils": ["loamy soil", "alluvial soil", "sandy loam", "clay loam"],
        "ideal_ph": (5.8, 7.5),
        "notes": "Exhaustive C4 cereal. Zinc deficiency causes white bud syndrome. Demands split nitrogen top-dressing at knee-high and tasseling stages."
    },
    "potato": {
        "name": "Potato",
        "hindi_name": "आलू",
        "family": "Solanaceae (Tuber)",
        "season": "rabi",
        "water_demand": "moderate-to-high",
        "root_depth": "shallow (40–50 cm)",
        "stages": ["Basal / Planting", "Sprouting / Emergence", "Stolonization", "Tuber Initiation", "Tuber Bulking", "Maturity"],
        "heavy_uptake": ["K", "N", "P"],
        "moderate_uptake": ["Mg", "B", "Zn"],
        "ideal_soils": ["sandy loam", "loamy soil", "alluvial soil"],
        "ideal_ph": (5.2, 6.8),
        "notes": "Tuber development draws 150–200 kg K2O/ha. Chloride-sensitive; Sulphate of Potash (SOP) is agronomically preferred over MOP for tuber quality."
    },
    "tomato": {
        "name": "Tomato",
        "hindi_name": "टमाटर",
        "family": "Solanaceae (Vegetable)",
        "season": "rabi",
        "water_demand": "moderate",
        "root_depth": "medium (60–90 cm)",
        "stages": ["Basal / Transplanting", "Early Vegetative", "Flowering", "Fruit Setting", "Fruit Bulking", "Harvesting"],
        "heavy_uptake": ["K", "Ca", "N"],
        "moderate_uptake": ["B", "P", "Mg"],
        "ideal_soils": ["sandy loam", "loamy soil", "alluvial soil", "red soil"],
        "ideal_ph": (6.0, 7.0),
        "notes": "Calcium deficiency under water stress causes Blossom End Rot (BER). Balanced K and foliar micronutrients (B, Zn) improve fruit firmness."
    },
    "gram": {
        "name": "Gram / Chickpea",
        "hindi_name": "चना",
        "family": "Fabaceae (Legume / Pulse)",
        "season": "rabi",
        "water_demand": "low",
        "root_depth": "deep taproot (100–120 cm)",
        "stages": ["Basal / Sowing", "Vegetative / Branching", "Flowering", "Pod Formation", "Grain Filling", "Maturity"],
        "heavy_uptake": ["P", "S"],
        "moderate_uptake": ["Zn", "Mo", "K"],
        "ideal_soils": ["sandy loam", "clay loam", "black soil", "alluvial soil"],
        "ideal_ph": (6.0, 8.0),
        "notes": "Symbiotic Rhizobium fixation adds 20–40 kg N/ha. Avoid high chemical N application which inhibits nodulation. Demands starter P & S."
    },
    "cotton": {
        "name": "Cotton",
        "hindi_name": "कपास",
        "family": "Malvaceae (Fiber)",
        "season": "kharif",
        "water_demand": "moderate-to-high",
        "root_depth": "deep (120–180 cm)",
        "stages": ["Basal / Sowing", "Seedling", "Square Formation", "Flowering", "Boll Development", "Boll Bursting"],
        "heavy_uptake": ["K", "N", "P"],
        "moderate_uptake": ["B", "Mg", "Zn"],
        "ideal_soils": ["black soil", "alluvial soil", "clay loam"],
        "ideal_ph": (6.0, 8.2),
        "notes": "Deep rooted; prolonged boll development exhausts potassium reserves causing leaf reddening. Boron essential for square and boll retention."
    },
    "sugarcane": {
        "name": "Sugarcane",
        "hindi_name": "गन्ना",
        "family": "Poaceae (Sugar)",
        "season": "kharif",
        "water_demand": "high",
        "root_depth": "deep (120–150 cm)",
        "stages": ["Basal / Planting", "Germination / Emergence", "Tillering / Formative", "Grand Growth / Cane Elongation", "Ripening / Maturity"],
        "heavy_uptake": ["N", "K", "P"],
        "moderate_uptake": ["S", "Fe", "Zn", "Mn"],
        "ideal_soils": ["alluvial soil", "loamy soil", "clay loam", "black soil"],
        "ideal_ph": (6.0, 7.8),
        "notes": "Heavy multi-month feeder (150–250 kg N/ha, 60–80 kg P2O5, 60–120 kg K2O). High sulfur requirement; ratoon crops demand extra N and P."
    }
}

SOIL_CHARACTERISTICS: Dict[str, Dict[str, Any]] = {
    "alluvial soil": {
        "name": "Alluvial Soil (जलोढ़ मिट्टी)",
        "drainage": "Good to moderate",
        "retention": "Moderate",
        "fertility": "High natural fertility",
        "inherent_nutrients": "Adequate in Potash and Lime; deficient in Nitrogen and Organic Carbon",
        "p_fixation": "Low to moderate",
        "leaching_risk": "Moderate",
        "notes": "Responds well to balanced NPK. Intensive cropping often leads to Zinc drawdown."
    },
    "black soil": {
        "name": "Black / Regur Soil (काली मिट्टी)",
        "drainage": "Slow / poor",
        "retention": "Very high water retention (montmorillonite clay)",
        "fertility": "Medium to high",
        "inherent_nutrients": "Rich in Calcium, Potassium, Magnesium; deficient in Nitrogen and Phosphorus",
        "p_fixation": "Moderate to high",
        "leaching_risk": "Low",
        "notes": "Swells when wet, deep cracks when dry. Prone to waterlogging; apply fertilizers with care to avoid root suffocation."
    },
    "red soil": {
        "name": "Red Soil (लाल मिट्टी)",
        "drainage": "High / rapid",
        "retention": "Low moisture holding capacity",
        "fertility": "Low to medium",
        "inherent_nutrients": "Deficient in Nitrogen, Phosphorus, Potassium, and Organic Matter; rich in Iron oxides",
        "p_fixation": "High (P gets fixed by Iron/Aluminium oxides)",
        "leaching_risk": "High for Nitrogen and Potassium",
        "notes": "Split fertilizer application and heavy organic matter addition (FYM, compost) are essential to prevent leaching."
    },
    "laterite soil": {
        "name": "Laterite Soil (लैटेराइट मिट्टी)",
        "drainage": "Excessive / rapid",
        "retention": "Very low",
        "fertility": "Low (heavily leached)",
        "inherent_nutrients": "Severely deficient in N, P, K, Ca, Mg; high acidity",
        "p_fixation": "Very high",
        "leaching_risk": "Severe",
        "notes": "Requires liming or agricultural lime for acidic pH correction, along with rock phosphate / SSP and frequent split doses."
    },
    "desert/arid soil": {
        "name": "Desert / Arid Soil (मरुस्थलीय मिट्टी)",
        "drainage": "Excessive",
        "retention": "Very poor",
        "fertility": "Low, high salt accumulation risk",
        "inherent_nutrients": "Deficient in Nitrogen and Organic Matter; variable in Phosphates",
        "p_fixation": "Low",
        "leaching_risk": "Very high",
        "notes": "Prone to salinization; micro-irrigation (drip fertigation) and compost are crucial."
    },
    "mountain/forest soil": {
        "name": "Mountain / Forest Soil (पर्वतीय मिट्टी)",
        "drainage": "Moderate to good",
        "retention": "Moderate",
        "fertility": "High organic matter in surface horizon",
        "inherent_nutrients": "Rich in Humus; deficient in Potash, Phosphorus, and Lime",
        "p_fixation": "Moderate",
        "leaching_risk": "Moderate (prone to erosion on slopes)",
        "notes": "Acidic to slightly acidic; requires balanced phosphatic supplementation."
    },
    "loamy soil": {
        "name": "Loamy Soil (दोमट मिट्टी)",
        "drainage": "Optimum",
        "retention": "Optimum",
        "fertility": "High (ideal agricultural texture)",
        "inherent_nutrients": "Balanced texture supporting high cation exchange capacity (CEC)",
        "p_fixation": "Low to moderate",
        "leaching_risk": "Low to moderate",
        "notes": "Ideal structure for nutrient availability and root respiration."
    },
    "sandy soil": {
        "name": "Sandy Soil (बलुई मिट्टी)",
        "drainage": "Very fast",
        "retention": "Very low",
        "fertility": "Low",
        "inherent_nutrients": "Poor cation exchange capacity; poor nutrient holding",
        "p_fixation": "Low",
        "leaching_risk": "Severe for Nitrate (NO3-) and Potash (K+)",
        "notes": "Never apply large single doses of chemical fertilizers; use 3–4 splits and heavy organic manure."
    },
    "clay soil": {
        "name": "Clay Soil (चिकनी मिट्टी)",
        "drainage": "Slow",
        "retention": "High",
        "fertility": "Moderate to high",
        "inherent_nutrients": "Good nutrient retention but prone to compaction",
        "p_fixation": "Moderate to high",
        "leaching_risk": "Low",
        "notes": "Incorporate well-rotted FYM or green manure to improve soil aeration and tilth."
    },
    "sandy loam": {
        "name": "Sandy Loam (बलुई दोमट)",
        "drainage": "Good",
        "retention": "Moderate",
        "fertility": "Moderate to good",
        "inherent_nutrients": "Good aeration, moderate nutrient holding",
        "p_fixation": "Low",
        "leaching_risk": "Moderate",
        "notes": "Well suited for tubers, vegetables, pulses, and wheat with split nutrient scheduling."
    },
    "clay loam": {
        "name": "Clay Loam (चिकनी दोमट)",
        "drainage": "Moderate",
        "retention": "High",
        "fertility": "High",
        "inherent_nutrients": "Rich mineral reserve; excellent water holding",
        "p_fixation": "Moderate",
        "leaching_risk": "Low to moderate",
        "notes": "Excellent for wheat, paddy, sugarcane, and cotton."
    }
}

ROTATION_INTERACTION_RULES: Dict[str, Dict[str, Any]] = {
    "rice": {
        "wheat": {
            "depletion": {
                "Nitrogen": "Likely depleted (due to previous paddy puddling and denitrification losses)",
                "Phosphorus": "Possibly depleted (moderate carryover if basal was applied in paddy)",
                "Potassium": "Possibly depleted (rice straw removes large potassium amounts)",
                "Zinc": "Likely depleted (anaerobic submerged paddy conditions immobilize available Zinc)",
                "Sulphur": "Possibly depleted"
            },
            "soil_effect": "Paddy puddling often forms a subsoil hardpan at 15–20 cm depth, impairing initial wheat root penetration. If paddy straw was incorporated, high C:N ratio (~80:1) can cause temporary microbial nitrogen immobilization ('nitrogen hunger').",
            "pest_carryover": "Risk of sheath blight (Rhizoctonia solani) sclerotia carryover; heavy Phalaris minor (Gulli Danda) weed seed bank.",
            "rotational_benefit": "Cereal-after-cereal monoculture; yields lower nitrogen efficiency compared to a legume break.",
            "recommendation_hint": "Ensure basal Zinc supplementation or foliar Zn spray, and apply 15–20% additional starter Nitrogen if rice residue was freshly incorporated."
        },
        "gram": {
            "depletion": {
                "Nitrogen": "Possibly depleted",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Zinc": "Possibly depleted"
            },
            "soil_effect": "Gram's deep taproot helps penetrate the paddy hardpan. Legume nodules fix nitrogen, restoring soil biology.",
            "pest_carryover": "Low common disease overlap; effective break crop.",
            "rotational_benefit": "Excellent restorative rotation. Enriches soil organic nitrogen and breaks cereal weed cycles.",
            "recommendation_hint": "Seed inoculation with Rhizobium culture and Phosphate Solubilizing Bacteria (PSB) is strongly recommended."
        },
        "mustard": {
            "depletion": {
                "Nitrogen": "Likely depleted",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Sulphur": "Likely depleted (both crops require moderate to high S)"
            },
            "soil_effect": "Mustard requires fine tilth; puddling hardpan must be broken through adequate primary tillage.",
            "pest_carryover": "Minimal pest overlap; mustard root exudates suppress some soil-borne nematodes.",
            "rotational_benefit": "Good diversification away from cereal-cereal cycle.",
            "recommendation_hint": "Apply gypsum or Single Super Phosphate (SSP) to satisfy mustard's high sulfur demand."
        }
    },
    "wheat": {
        "rice": {
            "depletion": {
                "Nitrogen": "Likely depleted",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Zinc": "Possibly depleted"
            },
            "soil_effect": "Wheat straw decomposes slowly in submerged paddy conditions. Puddling incorporates organic carbon.",
            "pest_carryover": "Stem borer and leaf folder risks emerge in kharif paddy.",
            "rotational_benefit": "Standard Indo-Gangetic rotation, but long-term continuous rotation causes micronutrient fatigue.",
            "recommendation_hint": "Incorporate green manure (Dhaincha) during the summer window if 45–50 days are available."
        },
        "maize": {
            "depletion": {
                "Nitrogen": "Likely depleted",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Zinc": "Possibly depleted"
            },
            "soil_effect": "Both are heavy feeding cereals. Substantial draw on soil nitrogen and zinc reserves.",
            "pest_carryover": "Fall armyworm risk in maize; stalk rot potential.",
            "rotational_benefit": "Intensive cereal rotation; requires disciplined fertility management.",
            "recommendation_hint": "Add 2–3 tonnes/acre well-rotted FYM and check zinc status before maize sowing."
        }
    },
    "maize": {
        "wheat": {
            "depletion": {
                "Nitrogen": "Likely depleted (Maize is a voracious nitrogen consumer)",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Likely depleted",
                "Zinc": "Likely depleted"
            },
            "soil_effect": "Maize leaves substantial coarse stover that requires adequate time to decompose.",
            "pest_carryover": "Borer and root aphid considerations.",
            "rotational_benefit": "Cereal-cereal rotation requiring balanced NPK and micronutrient replenishment.",
            "recommendation_hint": "Ensure basal phosphorus and zinc sulphate application for the succeeding wheat crop."
        }
    },
    "potato": {
        "wheat": {
            "depletion": {
                "Nitrogen": "Possibly adequate (Potato usually receives heavy basal fertilization)",
                "Phosphorus": "Likely adequate (Residual P from high potato fertilization)",
                "Potassium": "Possibly depleted (Tubers extract massive amounts of potash)",
                "Magnesium": "Possibly depleted"
            },
            "soil_effect": "Soil tilth is exceptionally loose and friable after potato harvest, facilitating excellent seedbed preparation for late-sown wheat.",
            "pest_carryover": "Low disease crossover between potato and wheat.",
            "rotational_benefit": "Economically intensive rotation with good residual fertilizer recovery.",
            "recommendation_hint": "Soil-test for residual N and P; adjust fertilizer doses downward to avoid vegetative lodging."
        }
    },
    "gram": {
        "wheat": {
            "depletion": {
                "Nitrogen": "Likely adequate to Moderate (Symbiotic N fixation leaves 20–40 kg residual N/ha)",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Likely adequate",
                "Sulphur": "Possibly depleted"
            },
            "soil_effect": "Legume nodules and root biomass improve soil structure, microbial respiration, and organic carbon.",
            "pest_carryover": "Very low; breaks cereal fungal pathogen chains.",
            "rotational_benefit": "Highly recommended restorative rotation.",
            "recommendation_hint": "Wheat starter nitrogen dose can be reduced by 15–20% following a healthy pulse crop."
        }
    }
}

PEST_DISEASE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "yellow rust": {
            "scientific_name": "Puccinia striiformis",
            "type": "fungal disease",
            "symptoms": "Yellow or orange pustules arranged in distinct parallel stripes on the leaf blades; yellow powder dusts onto fingers.",
            "favorable_weather": "Cool (10–18°C), moist, humid conditions, intermittent morning dew or light drizzle.",
            "biological_cultural": [
                "Grow resistant wheat cultivars (e.g. HD 3086, PBW 550, DBW 187, DBW 222) recommended by ICAR-IIWBR.",
                "Avoid late sowing and excessive early nitrogen application which causes lush vegetative growth.",
                "Destroy initial localized infection foci ('yellow patches') by mechanical roguing of affected leaves."
            ],
            "chemical_control": {
                "active_ingredient": "Propiconazole 25% EC or Tebuconazole 25.9% m/m",
                "category": "Triazole systemic fungicide (Sterol Demethylation Inhibitor - DMI)",
                "application_stage": "At first appearance of isolated stripe pustules; do NOT delay once stripes emerge",
                "application_method": "High-volume foliar spray with flat fan nozzle (400–500 L water/ha or 160–200 L/acre)",
                "pre_harvest_interval": "30–35 days",
                "ppe_warning": "Wear protective chemical gloves, apron, and organic vapor face mask. Do NOT spray against the wind.",
                "resistance_warning": "Alternate with different modes of action if multiple sprays are required; do not use triazoles more than twice consecutively.",
                "authority_source": "Directorate of Wheat Development (ICAR-IIWBR) & CIBRC Approved Label"
            }
        },
        "aphids": {
            "scientific_name": "Rhopalosiphum padi / Sitobion avenae",
            "type": "insect pest",
            "symptoms": "Clusters of tiny green/brown insects sucking sap from ears and leaves, secreting sticky honeydew that fosters black sooty mold.",
            "favorable_weather": "Cloudy, warm (18–25°C) weather during earhead emergence and grain filling.",
            "biological_cultural": [
                "Install yellow sticky traps (4–5 traps/acre) at canopy height to monitor incoming winged aphids.",
                "Conserve natural predators: Ladybird beetles (Coccinella septempunctata), hoverfly larvae, and chrysoperla.",
                "Apply 5% Neem Seed Kernel Extract (NSKE) or Azadirachtin 0.03% (300 ppm) at initial nymph appearance."
            ],
            "chemical_control": {
                "active_ingredient": "Thiamethoxam 25% WG or Imidacloprid 17.8% SL",
                "category": "Neonicotinoid systemic insecticide (Nicotinic acetylcholine receptor competitive modulator)",
                "application_stage": "When aphid population crosses Economic Threshold Level (ETL: 5–10 aphids per earhead / tiller)",
                "application_method": "Foliar spray targeted at the upper canopy and developing earheads",
                "pre_harvest_interval": "21–25 days",
                "ppe_warning": "Wear protective rubber gloves, eye goggles, and mask. Toxic to bees: NEVER spray during peak morning pollinator activity.",
                "resistance_warning": "Limit to single application per season to prevent neonicotinoid resistance.",
                "authority_source": "ICAR-NCIPM & CIBRC Approved Label"
            }
        },
        "termite": {
            "scientific_name": "Odontotermes obesus",
            "type": "soil insect pest",
            "symptoms": "Wilting and drying of plants in patches; roots show clear hollowed-out gnaw marks filled with mud.",
            "favorable_weather": "Sandy soils, dry spells, unrotted farmyard manure application.",
            "biological_cultural": [
                "Only apply thoroughly decomposed farmyard manure; unrotted dung attracts termites.",
                "Apply biocontrol fungus Metarhizium anisopliae or Beauveria bassiana (2–3 kg/acre mixed with compost) in soil.",
                "Timely irrigation helps deter subterranean termite movement."
            ],
            "chemical_control": {
                "active_ingredient": "Chlorpyrifos 20% EC or Fipronil 0.3% GR",
                "category": "Soil insecticide (Organophosphate / Phenylpyrazole)",
                "application_stage": "Pre-sowing seed treatment or standing crop irrigation water treatment",
                "application_method": "Seed treatment prior to sowing or irrigation canal stream application in standing crop",
                "pre_harvest_interval": "Follow official label strictly",
                "ppe_warning": "Wear heavy chemical-resistant gloves and face shield. Extremely toxic to aquatic life.",
                "resistance_warning": "Do not treat fields where termites are not actively causing economic root injury.",
                "authority_source": "ICAR Recommended Package of Practices"
            }
        }
    },
    "rice": {
        "yellow stem borer": {
            "scientific_name": "Scirpophaga incertulas",
            "type": "insect pest",
            "symptoms": "Vegetative stage: Central shoot drying known as 'Dead Heart'. Reproductive stage: Empty, chaffy white panicles known as 'White Ear'.",
            "favorable_weather": "High humidity (>85%), warm temperatures (25–30°C), dense vegetative tillering.",
            "biological_cultural": [
                "Install pheromone traps with Scirpo-lure (5 traps/acre for monitoring, 8–10 for mass trapping).",
                "Clip seedling leaf tips before transplanting to eliminate stem borer egg masses.",
                "Release egg parasitoid Trichogramma japonicum @ 50,000 to 100,000/ha at weekly intervals."
            ],
            "chemical_control": {
                "active_ingredient": "Chlorantraniliprole 0.4% GR or Cartap Hydrochloride 4% GR",
                "category": "Ryanodine receptor modulator / Neristoxin analogue",
                "application_stage": "At ETL: 1 egg mass per m2 or 5% dead hearts at vegetative stage",
                "application_method": "Broadcasting in standing water (maintain 2–3 cm water depth for 48 hours)",
                "pre_harvest_interval": "Cartap: 21 days; Chlorantraniliprole: 30 days",
                "ppe_warning": "Wear gumboots and waterproof gloves. Do not drain standing water into public irrigation channels.",
                "resistance_warning": "Do not repeat the same diamide chemistries consecutively.",
                "authority_source": "Directorate of Rice Development (ICAR-IIRR) & CIBRC"
            }
        },
        "blast": {
            "scientific_name": "Magnaporthe oryzae (Pyricularia oryzae)",
            "type": "fungal disease",
            "symptoms": "Spindle-shaped elliptical lesions with grayish centers and brown/red borders on leaves; neck rot causing panicle collapse.",
            "favorable_weather": "Intermittent rainfall, cool nights (20–22°C), high relative humidity (>90%), morning fog.",
            "biological_cultural": [
                "Avoid excessive split applications of Nitrogen; balanced Potash application strengthens leaf silica matrix.",
                "Seed treatment with Pseudomonas fluorescens (10g/kg seed) or Trichoderma viride.",
                "Destroy infected crop residues and avoid field-to-field flood irrigation."
            ],
            "chemical_control": {
                "active_ingredient": "Tricyclazole 75% WP or Isoprothiolane 40% EC",
                "category": "Melanin biosynthesis inhibitor (MBI) systemic fungicide",
                "application_stage": "At initial eye-shaped leaf lesions or prophylactic boot-leaf / early panicle emergence",
                "application_method": "Foliar spray with thorough coverage of the foliage and boot sheath",
                "pre_harvest_interval": "Tricyclazole: 30 days",
                "ppe_warning": "Wear protective clothing, gloves, and mask. Avoid inhalation of wettable powder.",
                "resistance_warning": "Alternate with valid broad-spectrum protective fungicides (e.g. Mancozeb) if necessary.",
                "authority_source": "ICAR-IIRR & CIBRC Approved Label"
            }
        },
        "bacterial leaf blight": {
            "scientific_name": "Xanthomonas oryzae pv. oryzae",
            "type": "bacterial disease",
            "symptoms": "Water-soaked streaks starting from leaf margins, developing into wavy yellowish lesions; milky bacterial ooze beads on young lesions.",
            "favorable_weather": "Heavy rainfall, high wind storms, warm temperatures (25–34°C), standing water.",
            "biological_cultural": [
                "Grow resistant varieties (e.g. Improved Samba Mahsuri).",
                "Temporarily drain field water to reduce bacterial dissemination.",
                "Strictly withhold top-dressing of nitrogenous fertilizers until disease progression arrests.",
                "Apply fresh cow dung water supernatant or bio-agent Pseudomonas fluorescens as foliar spray."
            ],
            "chemical_control": {
                "active_ingredient": "Copper Oxychloride 50% WP + Streptomycin Sulphate formulation (where legally authorized by state guidelines)",
                "category": "Bactericide / Copper-based protective complex",
                "application_stage": "At initial symptom onset along margins",
                "application_method": "Directed foliar spray with non-ionic surfactant",
                "pre_harvest_interval": "21 days",
                "ppe_warning": "Wear gloves and protective mask. Avoid chemical contact with skin.",
                "resistance_warning": "Antibiotic formulations must strictly follow state agricultural department advisory to mitigate resistance.",
                "authority_source": "State Agriculture University Plant Pathology Guidelines"
            }
        }
    },
    "mustard": {
        "mustard aphid": {
            "scientific_name": "Lipaphis erysimi",
            "type": "insect pest",
            "symptoms": "Dense colonies of small greenish-yellow aphids smothering inflorescence, flowering buds, and young siliquae, stunting pod filling.",
            "favorable_weather": "Cloudy, humid weather with mild temperatures (15–22°C) during flowering.",
            "biological_cultural": [
                "Early sowing (between October 1 to October 15 in North India) enables crop escape from peak aphid emergence in January/February.",
                "Conserve beneficial predators: Coccinella septempunctata (ladybird beetles) and Syrphid fly larvae.",
                "Install yellow sticky traps (6–8 traps/acre) in the field.",
                "Spray 5% Neem Seed Kernel Extract (NSKE) at initiation of flowering."
            ],
            "chemical_control": {
                "active_ingredient": "Dimethoate 30% EC or Oxydemeton-methyl 25% EC",
                "category": "Organophosphate systemic insecticide",
                "application_stage": "When 10–15% plants show aphid colonies or ETL is crossed (1.5–2.0 cm aphid colony on central shoot)",
                "application_method": "Foliar spray targeted at the flowering twigs in late afternoon to protect foraging honeybees",
                "pre_harvest_interval": "20–25 days",
                "ppe_warning": "CRITICAL: Never spray during morning honeybee pollination hours. Wear protective goggles and gloves.",
                "resistance_warning": "Rotate with different insecticidal classes if secondary spray is needed.",
                "authority_source": "ICAR-DRMR (Directorate of Rapeseed-Mustard Research)"
            }
        }
    },
    "potato": {
        "late blight": {
            "scientific_name": "Phytophthora infestans",
            "type": "oomycete / fungal-like disease",
            "symptoms": "Water-soaked irregular brown lesions on leaves and stems; white cottony downy growth on the underside of leaves during high humidity; tuber rot.",
            "favorable_weather": "Cool temperature (10–20°C), relative humidity >85%, cloudy/foggy weather, recurrent dew.",
            "biological_cultural": [
                "Plant certified disease-free tubers from registered government seed agencies.",
                "Ensure high earthing-up to prevent spores washing down into the soil to infect developing tubers.",
                "Follow ICAR-CPRI's Indo-Blightcast disease forecasting system.",
                "Dehaulm (cut foliage) 10–12 days before harvest if late blight appears near harvest."
            ],
            "chemical_control": {
                "active_ingredient": "Prophylactic: Mancozeb 75% WP; Curative: Cymoxanil 8% + Mancozeb 64% WP or Metalaxyl 8% + Mancozeb 64% WP",
                "category": "Multi-site protective (Dithiocarbamate) + Systemic curative",
                "application_stage": "Prophylactic: before disease onset when weather turns foggy; Curative: immediately upon first sighting of water-soaked spots",
                "application_method": "Uniform canopy spray ensuring complete coverage of both upper and lower leaf surfaces",
                "pre_harvest_interval": "14–21 days",
                "ppe_warning": "Wear respirator mask, rubber gloves, and eye protection. Prevent wash into nearby waterways.",
                "resistance_warning": "Do not apply metalaxyl formulations more than twice per season due to known resistance risk.",
                "authority_source": "ICAR-CPRI (Central Potato Research Institute) & CIBRC"
            }
        }
    },
    "maize": {
        "fall armyworm": {
            "scientific_name": "Spodoptera frugiperda",
            "type": "invasive insect pest",
            "symptoms": "Ragged holes on leaves; whorl destruction filled with moist sawdust-like frass (caterpillar excreta); shot-hole feeding signs.",
            "favorable_weather": "Warm conditions (25–32°C), sporadic rains, staggered multi-date sowing.",
            "biological_cultural": [
                "Install FAW pheromone traps (5 traps/acre) immediately upon germination.",
                "Apply dry sand mixed with neem cake (9:1 ratio) directly into plant whorls to disrupt larval feeding physically.",
                "Release egg parasitoids Trichogramma pretiosum or Telenomus remus @ 50,000/acre.",
                "Apply biocontrol entomopathogenic fungus Metarhizium rileyi or Beauveria bassiana @ 1 kg/acre in early whorl."
            ],
            "chemical_control": {
                "active_ingredient": "Chlorantraniliprole 18.5% SC or Spinetoram 11.7% SC",
                "category": "Ryanodine receptor modulator / Spinosyn insecticide",
                "application_stage": "When 5–10% plants show fresh whorl feeding damage (ETL)",
                "application_method": "High-pressure directed spray targeted directly INSIDE the central plant whorl",
                "pre_harvest_interval": "Chlorantraniliprole: 14 days; Spinetoram: 10 days",
                "ppe_warning": "Wear full PPE. Direct spray only into whorls; do NOT broadcast spray broadly.",
                "resistance_warning": "Strictly alternate modes of action between Spinosyns and Diamides to prevent rapid resistance.",
                "authority_source": "ICAR-IIMR & Ministry of Agriculture Pest Advisory"
            }
        }
    },
    "tomato": {
        "fruit borer": {
            "scientific_name": "Helicoverpa armigera",
            "type": "insect pest",
            "symptoms": "Circular bore holes in developing green and ripe fruits, with the anterior body of caterpillar inside and frass outside; rot sets in.",
            "favorable_weather": "Warm dry weather during flowering and fruit set.",
            "biological_cultural": [
                "Plant African Marigold (Tagetes erecta) as a trap crop (1 row of marigold after every 16 rows of tomato).",
                "Install Helicoverpa pheromone traps (5 traps/acre) to monitor adult male moth flight.",
                "Apply Bacillus thuringiensis (Bt) kurstaki formulation or HaNPV (Helicoverpa nuclear polyhedrosis virus) at 250 LE/ha.",
                "Hand-pick and destroy early instar larvae and bored fruits."
            ],
            "chemical_control": {
                "active_ingredient": "Chlorantraniliprole 18.5% SC or Emamectin Benzoate 5% SG",
                "category": "Diamide / Avermectin derivative",
                "application_stage": "At egg hatch or ETL: 1 larva per plant or 5% fruit damage",
                "application_method": "Thorough foliar spray covering flowering trusses and young fruits",
                "pre_harvest_interval": "Emamectin Benzoate: 3 days; Chlorantraniliprole: 3 days",
                "ppe_warning": "Wear gloves and respirator mask during mixing and spraying. Comply strictly with PHI before plucking tomatoes for market.",
                "resistance_warning": "Never use synthetic pyrethroids repeatedly; alternate with bio-rational chemistries.",
                "authority_source": "ICAR-IIHR & CIBRC Approved Label"
            }
        }
    }
}

# =====================================================================
# 2. NUTRIENT STATUS CLASSIFIERS & BENCHMARKS (Soil Health Card ICAR)
# =====================================================================

def classify_macronutrient(nutrient: str, value: Optional[float], unit: str = "kg/ha") -> Tuple[str, str]:
    """
    Classifies N, P, K into Low, Moderate, Adequate, High, or Unknown.
    Returns (status, benchmark_explanation).
    """
    if value is None:
        return "Unknown", "No measured data provided"
    
    nut = nutrient.upper()
    if nut in ("N", "NITROGEN"):
        # Benchmarks: < 280 kg/ha Low, 280-560 Moderate/Medium, > 560 High (SHC Standard)
        if value < 280:
            return "Low", f"Available N is {value} {unit} (< 280 kg/ha is Low according to Soil Health Card standards)"
        elif value <= 560:
            return "Moderate", f"Available N is {value} {unit} (280–560 kg/ha is Moderate / Medium)"
        else:
            return "High", f"Available N is {value} {unit} (> 560 kg/ha is High / Saturated)"
    elif nut in ("P", "PHOSPHORUS"):
        # Benchmarks: < 10 kg/ha P Low, 10-25 Moderate, > 25 High
        if value < 10:
            return "Low", f"Available P is {value} {unit} (< 10 kg/ha is Low)"
        elif value <= 25:
            return "Moderate", f"Available P is {value} {unit} (10–25 kg/ha is Moderate)"
        else:
            return "High", f"Available P is {value} {unit} (> 25 kg/ha is High)"
    elif nut in ("K", "POTASSIUM"):
        # Benchmarks: < 108 kg/ha K Low, 108-280 Moderate, > 280 High
        if value < 108:
            return "Low", f"Available K is {value} {unit} (< 108 kg/ha is Low)"
        elif value <= 280:
            return "Moderate", f"Available K is {value} {unit} (108–280 kg/ha is Moderate)"
        else:
            return "High", f"Available K is {value} {unit} (> 280 kg/ha is High)"
    
    return "Unknown", "Unknown nutrient parameter"

def classify_micronutrient(nutrient: str, value: Optional[float], unit: str = "ppm / mg/kg") -> Tuple[str, str]:
    """
    Classifies Zinc, Iron, Boron, Manganese, Copper, Sulphur.
    Returns (status, benchmark_explanation).
    """
    if value is None:
        return "Not measured", "No laboratory or sensor measurement available"
    
    nut = nutrient.lower()
    if "zinc" in nut or nut == "zn":
        # DTPA extractable: < 0.6 ppm Low, 0.6-1.2 Moderate, > 1.2 Adequate
        if value < 0.6:
            return "Low", f"Available Zn is {value} {unit} (< 0.6 ppm is Deficient/Low)"
        elif value <= 1.2:
            return "Moderate", f"Available Zn is {value} {unit} (0.6–1.2 ppm is Marginal/Moderate)"
        else:
            return "Adequate", f"Available Zn is {value} {unit} (> 1.2 ppm is Adequate)"
    elif "iron" in nut or nut == "fe":
        # DTPA: < 4.5 Low, 4.5-9.0 Moderate, > 9.0 Adequate
        if value < 4.5:
            return "Low", f"Available Fe is {value} {unit} (< 4.5 ppm is Deficient)"
        elif value <= 9.0:
            return "Moderate", f"Available Fe is {value} {unit} (4.5–9.0 ppm is Marginal)"
        else:
            return "Adequate", f"Available Fe is {value} {unit} (> 9.0 ppm is Adequate)"
    elif "boron" in nut or nut == "b":
        # Hot water soluble: < 0.5 Low, 0.5-1.0 Moderate, > 1.0 Adequate
        if value < 0.5:
            return "Low", f"Available B is {value} {unit} (< 0.5 ppm is Deficient)"
        elif value <= 1.0:
            return "Moderate", f"Available B is {value} {unit} (0.5–1.0 ppm is Marginal)"
        else:
            return "Adequate", f"Available B is {value} {unit} (> 1.0 ppm is Adequate)"
    elif "sulphur" in nut or "sulfur" in nut or nut == "s":
        # CaCl2 extractable: < 10 ppm Low, 10-20 Moderate, > 20 Adequate
        if value < 10.0:
            return "Low", f"Available S is {value} {unit} (< 10 ppm is Deficient)"
        elif value <= 20.0:
            return "Moderate", f"Available S is {value} {unit} (10–20 ppm is Medium)"
        else:
            return "Adequate", f"Available S is {value} {unit} (> 20 ppm is Adequate)"
    elif "calcium" in nut or nut == "ca":
        if value < 1.5:
            return "Low", f"Exchangeable Ca is {value} meq/100g (Deficient)"
        else:
            return "Adequate", f"Exchangeable Ca is {value} meq/100g (Adequate)"
    elif "magnesium" in nut or nut == "mg":
        if value < 1.0:
            return "Low", f"Exchangeable Mg is {value} meq/100g (Deficient)"
        else:
            return "Adequate", f"Exchangeable Mg is {value} meq/100g (Adequate)"
    elif "manganese" in nut or nut == "mn":
        if value < 2.0:
            return "Low", f"Available Mn is {value} {unit} (< 2.0 ppm is Deficient)"
        else:
            return "Adequate", f"Available Mn is {value} {unit} (Adequate)"
    elif "copper" in nut or nut == "cu":
        if value < 0.2:
            return "Low", f"Available Cu is {value} {unit} (< 0.2 ppm is Deficient)"
        else:
            return "Adequate", f"Available Cu is {value} {unit} (Adequate)"

    return "Unknown", "Parameter not calibrated"

# =====================================================================
# 3. MODULAR ANALYSIS FUNCTIONS
# =====================================================================

def analyze_crop(crop_name: str, stage: Optional[str], irrigation: Optional[str]) -> Dict[str, Any]:
    """Analyzes the current crop, growth stage demands, and water compatibility."""
    clean = crop_name.strip().lower() if crop_name else ""
    # Normalize
    crop_info = None
    for k, v in CROP_DATABASE.items():
        if k in clean or clean in k:
            crop_info = v
            break
    
    if not crop_info:
        return {
            "crop": crop_name,
            "recognized": False,
            "summary": f"Crop '{crop_name}' is not in the curated high-evidence agronomic database. Basic agronomic heuristics will apply.",
            "stages": ["Basal", "Vegetative", "Reproductive", "Maturity"],
            "current_stage": stage or "Not specified",
            "heavy_uptake": ["N", "P", "K"],
            "ideal_ph": (6.0, 7.5),
            "water_compatibility": "Ensure adequate soil moisture before any fertilizer application."
        }
    
    current_stage = stage or crop_info["stages"][0]
    water_status = "Adequate" if irrigation in ("available", "assured", "irrigated", None) else "Limited"
    
    return {
        "crop": crop_info["name"],
        "hindi_name": crop_info["hindi_name"],
        "recognized": True,
        "family": crop_info["family"],
        "season": crop_info["season"],
        "stages": crop_info["stages"],
        "current_stage": current_stage,
        "heavy_uptake": crop_info["heavy_uptake"],
        "moderate_uptake": crop_info["moderate_uptake"],
        "ideal_ph": crop_info["ideal_ph"],
        "water_demand": crop_info["water_demand"],
        "water_status": water_status,
        "agronomic_notes": crop_info["notes"],
        "summary": f"{crop_info['name']} ({crop_info['hindi_name']}) at '{current_stage}' stage. Heavy nutritional demand for {', '.join(crop_info['heavy_uptake'])}."
    }

def analyze_previous_crop(
    prev_crop: Optional[str],
    current_crop: str,
    harvest_season: Optional[str] = None,
    residue_handling: Optional[str] = "removed"
) -> Dict[str, Any]:
    """
    Analyzes predecessor crop interaction, nutrient drawdowns, and carryover.
    Uses realistic terms: "Likely depleted", "Possibly depleted", "Likely adequate", "Unknown".
    """
    if not prev_crop or prev_crop.strip().lower() in ("none", "", "fallow"):
        return {
            "previous_crop": "None / Fallow",
            "depletion_tendency": {
                "Nitrogen": "Unknown",
                "Phosphorus": "Unknown",
                "Potassium": "Unknown",
                "Zinc": "Unknown"
            },
            "soil_effect": "No preceding crop exhaustion recorded. Fallow periods allow moderate mineral weathering but no biological nitrogen contribution.",
            "rotational_benefit": "Fallow baseline; requires standard soil-test based basal fertilization.",
            "disease_carryover": "Low immediate crop-specific pest carryover.",
            "confidence_impact": "Medium (history baseline neutral)"
        }
    
    p_clean = prev_crop.strip().lower()
    c_clean = current_crop.strip().lower() if current_crop else ""
    
    p_key = next((k for k in CROP_DATABASE if k in p_clean or p_clean in k), None)
    c_key = next((k for k in CROP_DATABASE if k in c_clean or c_clean in k), None)
    
    interaction = None
    if p_key and c_key and p_key in ROTATION_INTERACTION_RULES and c_key in ROTATION_INTERACTION_RULES[p_key]:
        interaction = ROTATION_INTERACTION_RULES[p_key][c_key]
    
    if interaction:
        depletion = dict(interaction["depletion"])
        soil_effect = interaction["soil_effect"]
        pest_carryover = interaction["pest_carryover"]
        rotational_benefit = interaction["rotational_benefit"]
        hint = interaction.get("recommendation_hint", "")
    else:
        # General agronomic inference
        is_legume = any(leg in p_clean for leg in ("gram", "chickpea", "pulse", "moong", "urad", "lentil", "soybean", "pea"))
        is_cereal = any(cer in p_clean for cer in ("rice", "wheat", "maize", "paddy", "sorghum", "bajra"))
        
        if is_legume:
            depletion = {
                "Nitrogen": "Likely adequate (Legume nodule fixation left residual N)",
                "Phosphorus": "Possibly depleted (Moderate legume P uptake)",
                "Potassium": "Likely adequate",
                "Zinc": "Unknown"
            }
            soil_effect = "Leguminous root residue enriches soil organic nitrogen and improves microbial soil structure."
            pest_carryover = "Low disease carryover to non-legume crops; acts as a sanitation break."
            rotational_benefit = "High restorative agronomic value."
            hint = "Reduce chemical starter nitrogen by 15–20% compared to cereal-cereal rotations."
        elif is_cereal:
            depletion = {
                "Nitrogen": "Likely depleted (Preceding cereal extracted substantial nitrogen)",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Zinc": "Possibly depleted"
            }
            soil_effect = "Continuous cereal rotation tends to draw down soil organic carbon and available micronutrients."
            pest_carryover = "Moderate risk of common soil-borne fungal pathogens or weed seeds."
            rotational_benefit = "Monoculture or cereal-cereal rotation; legume break recommended in next season."
            hint = "Basal NPK and organic manure incorporation strongly advised."
        else:
            depletion = {
                "Nitrogen": "Possibly depleted",
                "Phosphorus": "Possibly depleted",
                "Potassium": "Possibly depleted",
                "Zinc": "Unknown"
            }
            soil_effect = f"Preceding cultivation of '{prev_crop}' extracted seasonal nutrients."
            pest_carryover = "General field sanitation advised."
            rotational_benefit = "Standard rotation."
            hint = "Verify actual nutrient availability with a laboratory Soil Health Card test."

    if residue_handling == "incorporated":
        soil_effect += " Crop residue was incorporated: beneficial for long-term organic carbon, but requires adequate microbial decomposition time and a small starter nitrogen dose to prevent temporary nitrogen immobilization."

    return {
        "previous_crop": prev_crop,
        "harvest_season": harvest_season or "Unspecified",
        "residue_handling": residue_handling,
        "depletion_tendency": depletion,
        "soil_effect": soil_effect,
        "disease_carryover": pest_carryover,
        "rotational_benefit": rotational_benefit,
        "agronomic_hint": hint
    }

def analyze_soil(
    soil_type: Optional[str],
    ph: Optional[float],
    moisture: Optional[float] = None,
    temperature: Optional[float] = None
) -> Dict[str, Any]:
    """
    Analyzes soil physical type and pH.
    Rule: Never block recommendation if pH is missing. Never diagnose soil solely on pH.
    """
    st_clean = soil_type.strip().lower() if soil_type else "alluvial soil"
    soil_info = next((v for k, v in SOIL_CHARACTERISTICS.items() if k in st_clean or st_clean in k), None)
    
    if not soil_info:
        soil_info = SOIL_CHARACTERISTICS["alluvial soil"]
        soil_name = soil_type or "Unspecified (Defaulted to Alluvial)"
    else:
        soil_name = soil_info["name"]
    
    # pH Analysis
    ph_status = {}
    if ph is None:
        ph_status = {
            "value": None,
            "status": "Unavailable",
            "badge": "pH data unavailable",
            "confidence_note": "pH data unavailable. Recommendation confidence reduced.",
            "agronomic_implication": "Soil reaction is not measured. While general soil type characteristics apply, exact nutrient solubility (e.g. Zinc and Phosphorus fixation) cannot be confirmed without laboratory pH."
        }
    else:
        if ph < 5.5:
            ph_status = {
                "value": ph,
                "status": "Strongly Acidic",
                "badge": f"pH {ph} (Strongly Acidic)",
                "confidence_note": "Laboratory / Measured pH available",
                "agronomic_implication": "Phosphorus fixation by iron and aluminum oxides is high. Calcium and Magnesium availability may be reduced. Micronutrients like Fe, Mn, Zn are highly soluble."
            }
        elif ph < 6.5:
            ph_status = {
                "value": ph,
                "status": "Slightly Acidic",
                "badge": f"pH {ph} (Slightly Acidic)",
                "confidence_note": "Laboratory / Measured pH available",
                "agronomic_implication": "Favorable for most pulses, potato, and oilseeds. Optimum microbial activity and nutrient uptake."
            }
        elif ph <= 7.5:
            ph_status = {
                "value": ph,
                "status": "Near Neutral",
                "badge": f"pH {ph} (Near Neutral)",
                "confidence_note": "Laboratory / Measured pH available",
                "agronomic_implication": "Ideal soil reaction for most field crops. Maximizes availability of Nitrogen, Phosphorus, Potassium, and Sulphur."
            }
        elif ph <= 8.5:
            ph_status = {
                "value": ph,
                "status": "Moderately Alkaline",
                "badge": f"pH {ph} (Moderately Alkaline)",
                "confidence_note": "Laboratory / Measured pH available",
                "agronomic_implication": "Phosphorus can precipitate with Calcium into less soluble dicalcium/tricalcium phosphate. Zinc and Iron availability is reduced; foliar zinc or chelated zinc is often necessary."
            }
        else:
            ph_status = {
                "value": ph,
                "status": "Strongly Alkaline / Sodic",
                "badge": f"pH {ph} (Strongly Alkaline)",
                "confidence_note": "Laboratory / Measured pH available",
                "agronomic_implication": "High exchangeable sodium or carbonates. Phosphorus and micronutrient availability is severely locked. Gypsum application and organic matter addition are indicated."
            }

    # Moisture & Temp
    moisture_info = None
    if moisture is not None:
        m_label = "Dry / Moisture Deficit" if moisture < 25 else "Adequate Moisture" if moisture <= 65 else "Saturated / Wet"
        moisture_info = {"value": moisture, "unit": "%", "assessment": m_label}
        
    temp_info = None
    if temperature is not None:
        temp_info = {"value": temperature, "unit": "°C"}

    return {
        "soil_type": soil_name,
        "characteristics": soil_info,
        "ph_analysis": ph_status,
        "moisture": moisture_info,
        "temperature": temp_info
    }

def analyze_nutrients_status(
    n_val: Optional[float],
    p_val: Optional[float],
    k_val: Optional[float],
    secondary: Optional[Dict[str, Optional[float]]] = None,
    micro: Optional[Dict[str, Optional[float]]] = None,
    data_source: str = "farmer_input"
) -> Dict[str, Any]:
    """
    Analyzes primary, secondary, and micronutrients.
    Strictly distinguishes Lab Test vs Sensor vs Farmer vs Estimate.
    If unavailable, shows 'Not measured' or 'Unknown' without fabricating numbers.
    """
    secondary = secondary or {}
    micro = micro or {}
    
    # Source metadata
    source_labels = {
        "laboratory": {
            "label": "Laboratory soil test",
            "confidence": "High",
            "icon": "flask",
            "is_sensor": False
        },
        "sensor": {
            "label": "Sensor-based indicative reading",
            "confidence": "Medium",
            "icon": "cpu",
            "is_sensor": True,
            "caveat": "Real-time IoT sensor readings provide indicative trends and do not substitute for a certified laboratory chemical soil extraction."
        },
        "farmer_input": {
            "label": "Farmer-entered observation",
            "confidence": "Medium-Low",
            "icon": "user",
            "is_sensor": False
        },
        "estimated": {
            "label": "Agronomic estimate / Derived",
            "confidence": "Low",
            "icon": "sparkles",
            "is_sensor": False
        }
    }
    src_meta = source_labels.get(data_source, source_labels["farmer_input"])
    
    # Primary NPK
    n_status, n_desc = classify_macronutrient("N", n_val)
    p_status, p_desc = classify_macronutrient("P", p_val)
    k_status, k_desc = classify_macronutrient("K", k_val)
    
    nutrients_list = [
        {"nutrient": "Nitrogen", "symbol": "N", "category": "Primary Macronutrient", "value": n_val, "unit": "kg/ha" if n_val else "", "status": n_status, "detail": n_desc},
        {"nutrient": "Phosphorus", "symbol": "P", "category": "Primary Macronutrient", "value": p_val, "unit": "kg/ha" if p_val else "", "status": p_status, "detail": p_desc},
        {"nutrient": "Potassium", "symbol": "K", "category": "Primary Macronutrient", "value": k_val, "unit": "kg/ha" if k_val else "", "status": k_status, "detail": k_desc},
    ]
    
    # Secondary: S, Ca, Mg
    sec_keys = [("Sulphur", "S", secondary.get("sulphur") or secondary.get("s")),
                ("Calcium", "Ca", secondary.get("calcium") or secondary.get("ca")),
                ("Magnesium", "Mg", secondary.get("magnesium") or secondary.get("mg"))]
    for name, sym, val in sec_keys:
        st, desc = classify_micronutrient(name, val)
        nutrients_list.append({
            "nutrient": name,
            "symbol": sym,
            "category": "Secondary Nutrient",
            "value": val,
            "unit": "ppm" if val is not None else "",
            "status": st,
            "detail": desc
        })
        
    # Micronutrients: Zn, Fe, B, Mn, Cu
    micro_keys = [("Zinc", "Zn", micro.get("zinc") or micro.get("zn")),
                  ("Iron", "Fe", micro.get("iron") or micro.get("fe")),
                  ("Boron", "B", micro.get("boron") or micro.get("b")),
                  ("Manganese", "Mn", micro.get("manganese") or micro.get("mn")),
                  ("Copper", "Cu", micro.get("copper") or micro.get("cu"))]
    for name, sym, val in micro_keys:
        st, desc = classify_micronutrient(name, val)
        nutrients_list.append({
            "nutrient": name,
            "symbol": sym,
            "category": "Micronutrient",
            "value": val,
            "unit": "ppm" if val is not None else "",
            "status": st,
            "detail": desc
        })

    deficits = [n["nutrient"] for n in nutrients_list if n["status"] == "Low"]
    moderates = [n["nutrient"] for n in nutrients_list if n["status"] == "Moderate"]
    unknowns = [n["nutrient"] for n in nutrients_list if n["status"] in ("Unknown", "Not measured")]

    return {
        "source": src_meta["label"],
        "source_type": data_source,
        "is_sensor": src_meta["is_sensor"],
        "sensor_caveat": src_meta.get("caveat"),
        "confidence": src_meta["confidence"],
        "nutrients": nutrients_list,
        "deficits": deficits,
        "moderates": moderates,
        "unmeasured": unknowns,
        "summary": f"{len(deficits)} nutrients Low/Deficient, {len(moderates)} Moderate, {len(unknowns)} Unmeasured/Unknown."
    }

# =====================================================================
# 4. FERTILIZER RECOMMENDATION ENGINES (CHEMICAL & ORGANIC)
# =====================================================================

def generate_organic_fertilizer_options(
    crop_info: Dict[str, Any],
    soil_info: Dict[str, Any],
    nutrient_info: Dict[str, Any],
    stage: str
) -> List[Dict[str, Any]]:
    """
    Returns scientifically grounded organic and natural soil inputs.
    Never claims organic fertilizer replaces chemical fertilizer 1:1.
    """
    options = []
    
    # 1. FYM / Well-rotted compost (universal soil builder)
    options.append({
        "name": "Well-Decomposed Farmyard Manure (FYM) or Compost",
        "category": "Bulky Organic Manure",
        "active_contribution": "0.5% N, 0.2% P2O5, 0.5% K2O + Humic substances and micronutrients",
        "why_recommended": "Replenishes soil organic carbon, enhances water retention, buffers soil pH, and feeds beneficial rhizospheric microbes.",
        "soil_benefit": f"Crucial for {soil_info['soil_type']} to improve cation exchange capacity (CEC) and prevent nutrient leaching.",
        "application_timing": "Apply 2–3 weeks prior to sowing/planting during primary field preparation and incorporate thoroughly into the top 15 cm.",
        "how_to_use": "Broadcast evenly across the field before final harrowing or apply along crop rows.",
        "limitations": "Slow nutrient release; does not immediately supply concentrated starter nitrogen in cold winter soils. Never claims 1:1 rapid replacement for mineral fertilizer.",
        "confidence": "High",
        "source": "ICAR Soil Organic Carbon Guidelines & National Centre of Organic Farming (NCOF)"
    })
    
    # 2. Vermicompost
    options.append({
        "name": "Vermicompost (वर्मीकम्पोस्ट / केंचुआ खाद)",
        "category": "Concentrated Organic Manure",
        "active_contribution": "1.5–2.0% N, 1.0–1.2% P2O5, 1.5% K2O, enzymes, vitamins, and plant growth promoting auxins",
        "why_recommended": "Provides readily available chelated nutrients and microbial biomass without the weed seeds often found in raw dung.",
        "soil_benefit": "Restores biological activity and promotes root proliferation, especially during early vegetative tillering or transplanting.",
        "application_timing": "At sowing as basal row placement or as top-dressing around root zones during active vegetative stages.",
        "how_to_use": "Band placement near the root zone (approx. 1–2 tonnes/acre depending on soil organic carbon status).",
        "limitations": "Must be kept moist and shaded; exposure to direct summer sunlight degrades microbial cultures.",
        "confidence": "High",
        "source": "KVK Agronomy Handbooks & ICAR-IISS Bhopal"
    })
    
    # 3. Biofertilizers (Crop Specific)
    crop_name = crop_info.get("crop", "").lower()
    is_legume = "gram" in crop_name or "chickpea" in crop_name or "pulse" in crop_name
    
    if is_legume:
        options.append({
            "name": "Rhizobium Legume Biofertilizer + PSB (Phosphate Solubilizing Bacteria)",
            "category": "Biofertilizer / Microbial Inoculant",
            "active_contribution": "Fixes 20–40 kg atmospheric N/ha symbiotically; solubilizes locked insoluble soil phosphorus",
            "why_recommended": "Enables efficient nodulation in pulse crops, drastically reducing synthetic nitrogen dependency.",
            "soil_benefit": "Enriches soil with organic nitrogen reserves for subsequent crops in rotation.",
            "application_timing": "Mandatory Seed Treatment immediately prior to sowing.",
            "how_to_use": "Mix 200g Rhizobium + 200g PSB with jaggery (gur) slurry per 10–12 kg seed; dry under shade for 30 minutes before sowing.",
            "limitations": "Requires live viable bacterial strains; do NOT expose inoculated seed to direct sunlight or mix directly with chemical fungicides.",
            "confidence": "High",
            "source": "Indian Agricultural Research Institute (IARI) Biofertilizer Protocol"
        })
    else:
        options.append({
            "name": "Azotobacter / Azospirillum + PSB (Phosphate Solubilizing Bacteria)",
            "category": "Biofertilizer / Microbial Inoculant",
            "active_contribution": "Free-living N2 fixation (15–25 kg N/ha equivalent) + Organic acid secretion to solubilize fixed soil P",
            "why_recommended": "Improves nitrogen use efficiency (NUE) and unlocks fixed soil phosphorus in neutral to alkaline soils.",
            "soil_benefit": "Stimulates mycorrhizal fungi and enhances root nutrient absorption surface area.",
            "application_timing": "Seed inoculation at sowing, or soil broadcast (mixed with moist vermicompost) at early tillering.",
            "how_to_use": "Slurry seed treatment or blend 2 kg culture with 50 kg moist vermicompost/acre and broadcast over damp soil.",
            "limitations": "Bacterial efficacy drops in severely dry, saline, or chemical-overloaded soil environments.",
            "confidence": "Medium-High",
            "source": "ICAR-IISS (Indian Institute of Soil Science)"
        })
        
    # 4. Neem Cake (Nitrification Inhibitor)
    options.append({
        "name": "Neem Cake (नीम की खली)",
        "category": "Organic Fertilizer & Natural Nitrification Inhibitor",
        "active_contribution": "2.0–3.5% N, 1.0% P, 1.4% K + Azadirachtin and nimbin triterpenoids",
        "why_recommended": "Acts as a natural slow-release nitrogen source while inhibiting Nitrosomonas bacteria to reduce urea leaching by 20–30%. Also protects roots against soil nematodes and subterranean pests.",
        "soil_benefit": "Combines organic plant nutrition with pest deterrence.",
        "application_timing": "Basal application during last ploughing or row placement at sowing.",
        "how_to_use": "Apply 100–150 kg/acre incorporated into the soil, or blend with chemical urea at 1:5 ratio.",
        "limitations": "Higher unit cost compared to bulky manures; requires uniform distribution.",
        "confidence": "High",
        "source": "ICAR Fertilizer & Organic Inputs Compendium"
    })
    
    return options

def generate_chemical_fertilizer_options(
    crop_info: Dict[str, Any],
    soil_info: Dict[str, Any],
    nutrient_info: Dict[str, Any],
    stage: str
) -> List[Dict[str, Any]]:
    """
    CRITICAL RULE: Recommends chemical fertilizer ONLY IF JUSTIFIED by nutrient deficit/evidence.
    Does NOT prescribe rigid fabricated dosages.
    Clearly notes: "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription."
    """
    options = []
    deficits = nutrient_info.get("deficits", [])
    moderates = nutrient_info.get("moderates", [])
    
    # Check if N is Low or Moderate
    needs_n = "Nitrogen" in deficits or "Nitrogen" in moderates or any(n["status"] in ("Low", "Moderate") for n in nutrient_info["nutrients"] if n["symbol"] == "N")
    needs_p = "Phosphorus" in deficits or "Phosphorus" in moderates or any(n["status"] in ("Low", "Moderate") for n in nutrient_info["nutrients"] if n["symbol"] == "P")
    needs_k = "Potassium" in deficits or "Potassium" in moderates or any(n["status"] in ("Low", "Moderate") for n in nutrient_info["nutrients"] if n["symbol"] == "K")
    needs_s = "Sulphur" in deficits or any(n["status"] == "Low" for n in nutrient_info["nutrients"] if n["symbol"] == "S")
    needs_zn = "Zinc" in deficits or any(n["status"] == "Low" for n in nutrient_info["nutrients"] if n["symbol"] == "Zn")
    
    crop_name = crop_info.get("crop", "").lower()
    
    # 1. Nitrogen Fertilizer
    if needs_n:
        options.append({
            "category": "Nitrogenous Fertilizer",
            "name": "Neem-Coated Urea (46% N)",
            "active_nutrient": "Nitrogen (46% Amide N)",
            "why_recommended": "Soil analysis indicates low/moderate available nitrogen. Essential for vegetative biomass, tillering, chlorophyll formation, and canopy development.",
            "problem_addressed": "Stunted crop growth, pale yellow lower leaves (chlorosis), restricted tillering / branching.",
            "appropriate_stage": "Split application: 1/3 at Basal, 1/3 at Tillering/Vigorous Vegetative, and 1/3 at Panicle/Flag Leaf Initiation.",
            "application_method": "Top-dressing or band placement into moist soil. Never broadcast over dry soil.",
            "application_timing": "Morning or late afternoon when soil has adequate moisture. Postpone if heavy rain or storms are forecasted within 24 hours.",
            "precautions": "Excessive nitrogen delays crop maturity, promotes lodging, and invites aphid/foliar disease infestations. Comply strictly with mandatory neem coating.",
            "confidence_level": "High (justified by nutrient deficit)",
            "dosage_note": "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription.",
            "source": "Department of Agriculture & Farmers Welfare, Fertilizer (Control) Order & ICAR Guidelines"
        })
        
    # 2. Phosphatic Fertilizer
    if needs_p:
        is_acidic = soil_info["ph_analysis"].get("status") in ("Strongly Acidic", "Slightly Acidic")
        fertilizer_choice = "Single Super Phosphate - SSP (16% P2O5, 11% S, 19% Ca)" if (is_acidic or needs_s or "mustard" in crop_name) else "Di-Ammonium Phosphate - DAP (18% N, 46% P2O5) or SSP"
        options.append({
            "category": "Phosphatic Fertilizer",
            "name": fertilizer_choice,
            "active_nutrient": "Available Phosphate (P2O5) + Calcium & Sulphur (in SSP)",
            "why_recommended": "Soil phosphorus status is suboptimal. Phosphorus is required for vigorous root elongation, early seedling vigor, tillering, and energy transfer (ATP).",
            "problem_addressed": "Poor root system development, delayed emergence, purplish leaf discoloration on older foliage.",
            "appropriate_stage": "Basal application at sowing / planting time ONLY. Phosphorus is immobile in soil and must be placed near the seed root zone.",
            "application_method": "Deep band placement 3–5 cm below and away from seed line using seed-cum-fertilizer drill.",
            "application_timing": "At final seedbed preparation or simultaneous drilling at sowing.",
            "precautions": "Never top-dress phosphorus on the surface of standing crops; surface-broadcast P gets fixed in top 1 cm and cannot reach active root zones.",
            "confidence_level": "High (justified by phosphorus deficit)",
            "dosage_note": "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription.",
            "source": "ICAR-IISS Soil Health Card Protocols & PAU Package of Practices"
        })
        
    # 3. Potassic Fertilizer
    if needs_k:
        is_tuber = "potato" in crop_name or "tomato" in crop_name
        k_choice = "Sulphate of Potash - SOP (50% K2O, 17.5% S)" if is_tuber else "Muriate of Potash - MOP (60% K2O)"
        options.append({
            "category": "Potassic Fertilizer",
            "name": k_choice,
            "active_nutrient": "Water Soluble Potassium (K2O)",
            "why_recommended": "Potassium deficit detected. Potash regulates stomatal opening, improves crop water-use efficiency, enzyme activation, disease tolerance, and stem strength against lodging.",
            "problem_addressed": "Marginal leaf scorching/firing, weak lodging-prone stems, shriveled grain/tuber quality.",
            "appropriate_stage": "Full basal at sowing, or split: 50% basal + 50% at flowering in sandy/leaching soils.",
            "application_method": "Soil placement during land preparation or drilling.",
            "application_timing": "At sowing or pre-planting.",
            "precautions": "For chloride-sensitive crops like potato, Sulphate of Potash is preferred over MOP to prevent quality reduction in tubers.",
            "confidence_level": "High (justified by potassium deficit)",
            "dosage_note": "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription.",
            "source": "Potash Research Institute of India (PRII) & ICAR Guidelines"
        })

    # 4. Micronutrient: Zinc
    if needs_zn or (soil_info["ph_analysis"].get("value") and soil_info["ph_analysis"]["value"] > 7.8 and "wheat" in crop_name):
        options.append({
            "category": "Micronutrient Fertilizer",
            "name": "Zinc Sulphate Heptahydrate (21% Zn) or Monohydrate (33% Zn)",
            "active_nutrient": "Available Zinc (Zn) + Sulphur",
            "why_recommended": "Suboptimal zinc availability confirmed or inferred from alkaline soil pH and exhaustive rotation (e.g. Rice-Wheat). Crucial for auxin synthesis, protein formation, and internode elongation.",
            "problem_addressed": "Interveinal chlorosis, Khaira disease in paddy, 'White Bud' in maize, bronzing of leaves in wheat.",
            "appropriate_stage": "Basal soil application or foliar spray at early tillering / vegetative stage.",
            "application_method": "Soil broadcast during land prep or foliar spray (0.5% ZnSO4 + 0.25% lime).",
            "application_timing": "At land preparation. If foliar, spray on calm clear days.",
            "precautions": "CRITICAL: NEVER mix Zinc Sulphate directly with DAP or water-soluble phosphate fertilizers in the same tank/application; they react to form insoluble Zinc Phosphate precipitates.",
            "confidence_level": "High",
            "dosage_note": "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription.",
            "source": "ICAR All India Coordinated Research Project on Micro- and Secondary Nutrients"
        })

    # If no deficits detected or soil data completely missing
    if not options:
        if all(n["status"] in ("Adequate", "High") for n in nutrient_info["nutrients"][:3] if n["value"] is not None):
            options.append({
                "category": "Maintenance Guidance",
                "name": "No Synthetic Fertilizer Currently Indicated",
                "active_nutrient": "None Required Immediately",
                "why_recommended": "Current soil test records show adequate available Macronutrients (N, P, K). Adding unnecessary synthetic fertilizer will increase farmer input costs and risk lodging or salinity.",
                "problem_addressed": "Prevents over-fertilization and nitrate leaching.",
                "appropriate_stage": "Maintain standard crop monitoring.",
                "application_method": "Rely on organic maintenance inputs.",
                "application_timing": "Not applicable",
                "precautions": "Monitor crop vigor at key reproductive transition stages.",
                "confidence_level": "High",
                "dosage_note": "Do not apply chemical fertilizers without a confirmed crop demand or deficit.",
                "source": "ICAR Balanced Fertilization Principles"
            })
        else:
            options.append({
                "category": "Indicative Prudence",
                "name": "Soil-Test Confirmation Required",
                "active_nutrient": "Baseline Macronutrient Plan",
                "why_recommended": "Insufficient quantitative laboratory or sensor evidence is available to prescribe a targeted chemical fertilizer recipe without risk of over-fertilization.",
                "problem_addressed": "Prevents blind chemical fertilizer application.",
                "appropriate_stage": "Obtain soil test prior to top-dressing.",
                "application_method": "Soil Health Card test.",
                "application_timing": "Before next crop stage",
                "precautions": "Relying purely on crop name to dump urea or DAP harms soil ecology and wastes money.",
                "confidence_level": "Low",
                "dosage_note": "Exact application rate should follow the local agricultural recommendation/soil-test-based prescription.",
                "source": "Soil Health Card Scheme, Ministry of Agriculture & Farmers Welfare"
            })

    return options

# =====================================================================
# 5. CHEMICAL VS NATURAL COMPARISON MATRIX
# =====================================================================

def generate_comparison_card(crop: str, soil_type: str, stage: str) -> Dict[str, Any]:
    """
    Side-by-side balanced comparison card across 8 agronomic dimensions.
    Does NOT declare one universally superior.
    """
    return {
        "headers": ["Dimension", "Chemical / Synthetic Fertilizer", "Natural / Organic & Bio-Inputs"],
        "rows": [
            {
                "dimension": "Nutrient Availability",
                "chemical": "Immediately soluble in soil water; rapid uptake by roots.",
                "natural": "Gradual, slow-release; requires microbial mineralization."
            },
            {
                "dimension": "Speed of Crop Response",
                "chemical": "Fast (visible vegetative response within 3 to 7 days).",
                "natural": "Moderate to slow (sustained feeding over entire crop season)."
            },
            {
                "dimension": "Soil Organic Matter & Biology",
                "chemical": "No direct carbon addition; high salts can temporarily stress sensitive surface microbes if over-applied.",
                "natural": "Substantially enriches Soil Organic Carbon (SOC), water-holding capacity, and beneficial mycorrhizae/microbes."
            },
            {
                "dimension": "Application Considerations",
                "chemical": "Precise timing and placement needed; split doses required to prevent volatilization and leaching losses.",
                "natural": "Bulky volume required; best incorporated during primary tillage 2–3 weeks before sowing."
            },
            {
                "dimension": "Cost Estimate & Market Access",
                "chemical": "Subsidized prices (e.g. Urea at statutory price; P&K under NBS scheme); immediate retail availability.",
                "natural": "Low cost if farm-produced (FYM/vermicompost); commercial certified organic formulations can carry high transport cost."
            },
            {
                "dimension": "Environmental & Groundwater Impact",
                "chemical": "Risk of groundwater nitrate contamination and nitrous oxide greenhouse gas emissions if over-applied.",
                "natural": "Eco-friendly, minimal leaching risk, improves carbon sequestration in agricultural soils."
            },
            {
                "dimension": "Limitations",
                "chemical": "Does not improve soil physical tilth; repetitive unbalanced use leads to micronutrient depletion.",
                "natural": "Lower nutrient concentration per kg; cannot rapidly cure severe acute crop starvation in high-yield varieties."
            },
            {
                "dimension": "Recommended Situation",
                "chemical": "Targeted corrective top-dressing when acute deficits exist or during critical high-demand reproductive stages.",
                "natural": "Basal foundational soil conditioning, continuous soil fertility maintenance, and integrated nutrient management (INM)."
            }
        ],
        "synthesis": "MAITTRI Agronomic Principle: An Integrated Nutrient Management (INM) strategy combining organic manures with soil-test-based chemical supplements delivers the highest yield, best soil health, and maximum farmer profit."
    }

# =====================================================================
# 6. PEST & DISEASE DECISION SUPPORT (IPM HIERARCHY)
# =====================================================================

def analyze_pest_and_disease(
    crop: str,
    pest_observed: Optional[str] = None,
    disease_observed: Optional[str] = None,
    symptoms: Optional[str] = None,
    affected_area_pct: Optional[float] = None,
    crop_stage: Optional[str] = None
) -> Dict[str, Any]:
    """
    CRITICAL RULE:
    NEVER recommend a pesticide just because a crop is selected.
    First check whether confirmed evidence exists.
    If no evidence: Output 'No confirmed pest/disease evidence. Preventive monitoring is recommended.'
    """
    has_pest = pest_observed and pest_observed.strip().lower() not in ("none", "", "no", "nil")
    has_disease = disease_observed and disease_observed.strip().lower() not in ("none", "", "no", "nil")
    has_symptoms = symptoms and len(symptoms.strip()) > 5
    
    if not (has_pest or has_disease or has_symptoms):
        return {
            "evidence_found": False,
            "status": "No Confirmed Pest / Disease Evidence",
            "verdict": "No confirmed pest/disease evidence. Preventive monitoring is recommended instead of unnecessary pesticide application.",
            "natural_ipm_guidance": [
                "Regular field scouting twice a week across a 'W' or 'Z' walking pattern in the field.",
                "Check the underside of lower and middle leaves for early nymph colonization or spore flecks.",
                "Maintain weed-free field bunds to eliminate alternative host plants.",
                "Conserve resident beneficial predator insects (spiders, dragonflies, ladybird beetles)."
            ],
            "chemical_options": [],
            "message": "Routine chemical pesticide application in the absence of pest thresholds kills natural beneficial predators and accelerates pesticide resistance."
        }

    c_clean = crop.strip().lower() if crop else ""
    crop_registry = next((v for k, v in PEST_DISEASE_REGISTRY.items() if k in c_clean or c_clean in k), None)
    
    # Search for target pest in registry
    target_match = None
    target_name = (pest_observed or disease_observed or symptoms or "").strip().lower()
    
    if crop_registry:
        for p_key, p_val in crop_registry.items():
            if p_key in target_name or target_name in p_key:
                target_match = (p_key, p_val)
                break
    
    # If not found directly in current crop registry, search globally across all crops
    if not target_match:
        for cr_name, cr_dict in PEST_DISEASE_REGISTRY.items():
            for p_key, p_val in cr_dict.items():
                if p_key in target_name or target_name in p_key:
                    target_match = (p_key, p_val)
                    break
            if target_match:
                break
                
    if not target_match:
        # User reported a symptom or pest not specifically in the curated registry
        return {
            "evidence_found": True,
            "target_identified": False,
            "reported_issue": pest_observed or disease_observed or "Unspecified Symptom",
            "symptoms_reported": symptoms or "General field observation",
            "affected_area_pct": affected_area_pct,
            "status": "Unconfirmed Pest / Disease Observation",
            "verdict": "Pest symptoms reported, but specific pathogen/insect could not be conclusively matched with authoritative registered chemistry.",
            "natural_ipm_guidance": [
                "Install sticky traps and inspect plant canopy in early morning.",
                "Collect affected plant sample (leaves/roots in a clean plastic bag) and consult your local Krishi Vigyan Kendra (KVK) or Plant Protection Officer for visual laboratory diagnosis.",
                "Spray 5% Neem Seed Kernel Extract (NSKE) as a safe broad-spectrum deterrent while awaiting formal identification."
            ],
            "chemical_options": [],
            "warning": "Do NOT apply random broad-spectrum chemical pesticides without confirmed identification."
        }

    p_key, p_data = target_match
    
    # Prepare Chemical pesticide recommendation ONLY when evidence exists
    chem_rec = None
    if "chemical_control" in p_data:
        cc = p_data["chemical_control"]
        chem_rec = {
            "pest_or_disease": f"{p_key.title()} ({p_data.get('scientific_name', '')})",
            "crop": crop,
            "active_ingredient": cc["active_ingredient"],
            "mode_of_action": cc["category"],
            "why_appropriate": f"Officially registered for control of {p_key} in {crop}. Proven efficacy when applied at Economic Threshold Levels.",
            "application_timing": cc["application_stage"],
            "application_method": cc["application_method"],
            "label_compliance": "MANDATORY: Verify local product registration, container label, and batch expiration before opening.",
            "ppe_warning": cc["ppe_warning"],
            "pre_harvest_interval": cc.get("pre_harvest_interval", "Follow official label"),
            "resistance_management": cc["resistance_warning"],
            "confidence": "High (authoritative registry match)",
            "source": cc["authority_source"],
            "important_disclaimer": "Do NOT invent pesticide dosage or dilution rates. Exact product brand formulation and dilution rate must be verified against current official label guidance approved by the Central Insecticides Board & Registration Committee (CIBRC)."
        }

    return {
        "evidence_found": True,
        "target_identified": True,
        "pest_name": p_key.title(),
        "scientific_name": p_data.get("scientific_name", ""),
        "type": p_data.get("type", "pest / disease"),
        "symptoms": p_data.get("symptoms", ""),
        "favorable_weather": p_data.get("favorable_weather", ""),
        "affected_area_pct": affected_area_pct,
        "natural_biological_options": p_data.get("biological_cultural", []),
        "chemical_option": chem_rec,
        "ipm_hierarchy": [
            "Level 1: Prevention (Cultural sanitation, certified seed, resistant cultivars)",
            "Level 2: Monitoring (ETL assessment, scouting, pheromone traps)",
            "Level 3: Mechanical & Biological (Sticky traps, predatory insects, NSKE, Trichoderma / Beauveria / Bt)",
            "Level 4: Chemical Control ONLY when Economic Threshold Level is crossed"
        ]
    }

# =====================================================================
# 7. WEATHER INTEGRATION & ADVISORY LOGIC
# =====================================================================

def evaluate_weather_risks(
    weather_data: Optional[Dict[str, Any]],
    crop_info: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluates weather impact on fertilizer and pesticide applications.
    Integrates with live Open-Meteo data.
    """
    advisories = []
    if not weather_data:
        advisories.append({
            "type": "info",
            "title": "Weather Data Not Linked",
            "message": "Local weather forecast is unavailable. Ensure calm wind (<15 km/h) and no imminent rain before applying any foliar spray or top-dressing.",
            "action": "Check local sky and weather report before application."
        })
        return advisories

    current = weather_data.get("current", {})
    hourly = weather_data.get("hourly", {})
    daily = weather_data.get("daily", {})

    temp = current.get("temperature_2m", 25)
    humidity = current.get("relative_humidity_2m", 50)
    wind_speed = current.get("wind_speed_10m", 5)

    # 1. Rain wash-off risk
    rain_probs = [p for p in hourly.get("precipitation_probability", [])[:24] if p is not None]
    max_rain_prob_24h = max(rain_probs) if rain_probs else 0
    precip_sums = [p for p in daily.get("precipitation_sum", [])[:2] if p is not None]
    rain_sum_48h = sum(precip_sums) if precip_sums else 0

    if max_rain_prob_24h > 45 or rain_sum_48h > 3.0:
        advisories.append({
            "type": "warning",
            "severity": "critical",
            "title": "Imminent Rain: High Fertilizer & Chemical Wash-off Hazard",
            "message": f"Rain probability in the next 24 hours is {max_rain_prob_24h}% (expected rain ~{round(rain_sum_48h, 1)} mm). Surface-broadcast Urea or foliar sprays will suffer severe runoff or leaching.",
            "action": "Postpone any foliar spray or urea top-dressing until the rainfall event passes and soil moisture stabilizes."
        })

    # 2. Wind drift hazard
    if wind_speed > 14:
        advisories.append({
            "type": "warning",
            "severity": "high",
            "title": f"High Wind ({wind_speed} km/h): Dangerous Spray Drift Hazard",
            "message": "Wind speed exceeds the safe threshold of 12–15 km/h. Droplets will drift uncontrollably into non-target areas, water channels, or neighboring fields.",
            "action": "Do NOT spray chemical fertilizers, bio-stimulants, or pesticides under high winds. Spray only during early morning calm."
        })

    # 3. High Humidity & Temperature (Fungal Spore Proliferation)
    if humidity > 80 and 16 <= temp <= 28:
        advisories.append({
            "type": "caution",
            "severity": "medium",
            "title": f"Fungal Weather Window (Temp: {temp}°C, Humidity: {humidity}%)",
            "message": "High ambient humidity combined with moderate temperature creates high risk for foliar blight, rust, downy mildew, and blast spore germination.",
            "action": "Inspect dense vegetative canopy twice weekly for early lesion development."
        })

    # 4. Extreme Heat / High Temp
    if temp > 38:
        advisories.append({
            "type": "caution",
            "severity": "medium",
            "title": f"High Temperature ({temp}°C): Evaporation & Scorching Risk",
            "message": "Midday heat causes rapid foliar droplet evaporation and leaf scorching from concentrated chemical deposits.",
            "action": "Spray only after 4:30 PM in late afternoon."
        })

    if not advisories:
        advisories.append({
            "type": "favorable",
            "severity": "low",
            "title": "Weather Favorable for Agricultural Operations",
            "message": f"Moderate temperature ({temp}°C), calm wind ({wind_speed} km/h), and low rain probability provide a good window for planned field operations.",
            "action": "Proceed with recommended field work adhering to label PPE."
        })

    return advisories

# =====================================================================
# 8. CONFIDENCE SCORE & EXPLANATION ENGINE
# =====================================================================

def calculate_recommendation_confidence(
    soil_data: Dict[str, Any],
    nutrient_data: Dict[str, Any],
    pest_data: Dict[str, Any],
    has_weather: bool,
    crop_recognized: bool
) -> Tuple[str, List[str]]:
    """
    Calculates overall recommendation confidence: High / Medium / Low.
    Returns (confidence_level, reasons_list).
    Never shows '99% accurate' unless scientifically validated.
    """
    score = 0
    reasons = []

    # 1. Soil & NPK Source
    source_type = nutrient_data.get("source_type", "farmer_input")
    if source_type == "laboratory":
        score += 35
        reasons.append("Laboratory chemical soil test available (Highest accuracy baseline).")
    elif source_type == "sensor":
        score += 20
        reasons.append("Real-time MAITTRI IoT soil sensor readings available (Indicative trend data).")
    elif source_type == "farmer_input":
        score += 10
        reasons.append("Farmer-reported soil observations (Empirical input).")
    else:
        reasons.append("Soil nutrient values are agronomically estimated (Reduced confidence).")

    # 2. pH Availability
    ph_val = soil_data.get("ph_analysis", {}).get("value")
    if ph_val is not None:
        score += 15
        reasons.append(f"Measured soil pH ({ph_val}) allows precise nutrient availability modeling.")
    else:
        reasons.append("Soil pH data is unavailable; nutrient solubility is estimated.")

    # 3. Crop & Stage
    if crop_recognized:
        score += 20
        reasons.append("Target crop and growth stage verified against ICAR agronomic profiles.")
    else:
        score += 5
        reasons.append("Uncommon or non-standard crop; general agronomic heuristics applied.")

    # 4. Pest / Disease Evidence
    if pest_data.get("evidence_found"):
        if pest_data.get("target_identified"):
            score += 20
            reasons.append(f"Pest/disease '{pest_data.get('pest_name')}' confirmed with registered CIBRC control options.")
        else:
            score += 5
            reasons.append("Pest symptoms observed but specific causal agent requires visual KVK diagnosis.")
    else:
        score += 15
        reasons.append("No active pest symptoms reported; preventive monitoring strategy is sound.")

    # 5. Weather Link
    if has_weather:
        score += 10
        reasons.append("Live meteorological forecast integrated for spray drift and wash-off safety.")
    else:
        reasons.append("Live weather data not connected.")

    # Final Classification
    if score >= 70:
        level = "High"
    elif score >= 45:
        level = "Medium"
    else:
        level = "Low"

    return level, reasons

def build_human_readable_explanation(
    crop_info: Dict[str, Any],
    prev_crop_info: Dict[str, Any],
    soil_info: Dict[str, Any],
    nutrient_info: Dict[str, Any],
    weather_advisories: List[Dict[str, Any]],
    chemical_options: List[Dict[str, Any]],
    pest_data: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Creates the 'Why MAITTRI is recommending this' reasoning steps.
    Transparently explains the agronomic rationale to the farmer.
    """
    steps = []

    # Step 1: Crop sequence
    curr_crop = crop_info.get("crop", "Current Crop")
    prev_crop = prev_crop_info.get("previous_crop", "None")
    steps.append({
        "title": "1. Crop Sequence & Rotation Impact",
        "description": f"Your current crop is '{curr_crop}' following '{prev_crop}'. {prev_crop_info.get('soil_effect', '')}"
    })

    # Step 2: Soil & pH
    soil_type = soil_info.get("soil_type", "Alluvial Soil")
    ph_badge = soil_info.get("ph_analysis", {}).get("badge", "pH unavailable")
    steps.append({
        "title": "2. Soil Texture & Chemical Reaction (pH)",
        "description": f"Field soil is characterized as '{soil_type}'. Soil reaction is {ph_badge}. {soil_info.get('ph_analysis', {}).get('agronomic_implication', '')}"
    })

    # Step 3: Nutrient Status
    deficits = nutrient_info.get("deficits", [])
    data_src = nutrient_info.get("source", "Farmer Input")
    if deficits:
        deficit_str = ", ".join(deficits)
        nut_desc = f"Based on '{data_src}', deficits were observed in: {deficit_str}. These nutrients directly limit root and shoot expansion at the '{crop_info.get('current_stage')}' stage."
    else:
        nut_desc = f"Based on '{data_src}', no severe macronutrient starvation is recorded. Focus is on balanced maintenance and organic soil building."
    steps.append({
        "title": "3. Available Nutrient Status",
        "description": nut_desc
    })

    # Step 4: Fertilizer Strategy
    if any(c["category"] != "Maintenance Guidance" and "Soil-Test" not in c["name"] for c in chemical_options):
        fert_desc = "Chemical options are included strictly to address verified nutrient gaps, combined with organic manures to maintain soil microbiology."
    else:
        fert_desc = "Synthetic chemical fertilizer is withheld or limited to maintenance because soil reserves or lack of test confirmation do not justify heavy chemical application."
    steps.append({
        "title": "4. Fertilizer Management Strategy",
        "description": fert_desc
    })

    # Step 5: Pest / Disease Evidence
    if pest_data.get("evidence_found") and pest_data.get("target_identified"):
        pest_desc = f"Target pest/disease '{pest_data.get('pest_name')}' was verified. Integrated Pest Management (IPM) gives biological and cultural controls first, with registered chemistry reserved as a targeted measure."
    else:
        pest_desc = "No confirmed economic pest infestation was reported. MAITTRI strictly refrains from prescribing chemical pesticides as a routine measure."
    steps.append({
        "title": "5. Pest Management Approach",
        "description": pest_desc
    })

    # Step 6: Weather Precautions
    crit_w = next((w for w in weather_advisories if w.get("severity") in ("critical", "high")), None)
    if crit_w:
        w_desc = f"Weather Alert: {crit_w['title']}. {crit_w['action']}"
    else:
        w_desc = "Current weather window is acceptable for planned field operations."
    steps.append({
        "title": "6. Weather & Environmental Precautions",
        "description": w_desc
    })

    return steps

def generate_step_by_step_roadmap() -> List[Dict[str, str]]:
    """Generates the 8-step farmer action roadmap."""
    return [
        {"step": 1, "title": "Check Soil & Nutrient Status", "desc": "Verify recent Soil Health Card laboratory report or calibrate MAITTRI IoT soil sensor readings before applying any fertilizer."},
        {"step": 2, "title": "Confirm Crop Growth Stage", "desc": "Inspect your field to confirm whether crop is at Basal, Tillering, Jointing, or Flowering stage. Different stages demand distinct nutrient balances."},
        {"step": 3, "title": "Check Weather & Irrigation Window", "desc": "Review local rain, humidity, and wind forecasts. Never spray under winds >15 km/h or top-dress urea immediately prior to heavy rains."},
        {"step": 4, "title": "Select Recommended Management Option", "desc": "Prioritize natural/organic inputs (FYM, vermicompost, biofertilizers) and apply chemical fertilizer only to address verified deficits."},
        {"step": 5, "title": "Apply According to Official / Local Guidance", "desc": "Verify exact application rates with your local KVK or State Agriculture Department package of practices. Use proper PPE when spraying."},
        {"step": 6, "title": "Monitor Crop Response", "desc": "Observe plant foliage color, new tiller growth, and leaf vigor 5 to 7 days post-application."},
        {"step": 7, "title": "Recheck Soil & Sensor Readings", "desc": "Take periodic sensor readings to record soil moisture dynamics and nutrient response."},
        {"step": 8, "title": "Update MAITTRI Farm History", "desc": "Log applied fertilizers, dosages, and pesticide sprays in MAITTRI to continuously refine future season recommendations."}
    ]

def get_authoritative_sources() -> List[Dict[str, str]]:
    """Returns curated authoritative agricultural citations and registries."""
    return [
        {
            "name": "Indian Council of Agricultural Research (ICAR)",
            "role": "National apex body for agricultural research, crop production packages of practices, and nutrient recommendations.",
            "url": "https://icar.org.in"
        },
        {
            "name": "Central Insecticides Board & Registration Committee (CIBRC)",
            "role": "Statutory authority under the Insecticides Act, 1968 for registration, approved crop labels, pre-harvest intervals (PHI), and safety warnings.",
            "url": "http://cibrc.nic.in"
        },
        {
            "name": "Department of Agriculture & Farmers Welfare, Govt. of India",
            "role": "Soil Health Card Scheme benchmarks, Fertilizer (Control) Order (FCO), and Integrated Nutrient Management guidelines.",
            "url": "https://agricoop.nic.in"
        },
        {
            "name": "Krishi Vigyan Kendras (KVK Network)",
            "role": "District-level agricultural science centres providing location-specific crop advisories, soil testing, and pest diagnostics.",
            "url": "https://kvk.icar.gov.in"
        },
        {
            "name": "National Institute of Plant Health Management (NIPHM)",
            "role": "Pesticide management protocols, biopesticide mass-multiplication guidelines, and Integrated Pest Management (IPM) packages.",
            "url": "https://niphm.gov.in"
        },
        {
            "name": "State Agricultural Universities (PAU, TNAU, GBPUAT, CCSHAU)",
            "role": "Agro-climatic zone specific crop production, fertilizer schedules, and varietal recommendations.",
            "url": "https://icar.org.in/state-agricultural-universities"
        }
    ]

# =====================================================================
# 9. PRIMARY MASTER PIPELINE FUNCTION
# =====================================================================

def generate_comprehensive_recommendation(
    current_crop: str,
    previous_crop: Optional[str] = None,
    previous_crop_harvest_season: Optional[str] = None,
    crop_stage: Optional[str] = None,
    soil_type: Optional[str] = None,
    soil_ph: Optional[float] = None,
    soil_moisture: Optional[float] = None,
    soil_temperature: Optional[float] = None,
    soil_n: Optional[float] = None,
    soil_p: Optional[float] = None,
    soil_k: Optional[float] = None,
    secondary_nutrients: Optional[Dict[str, Optional[float]]] = None,
    micronutrients: Optional[Dict[str, Optional[float]]] = None,
    data_source: str = "farmer_input",
    farm_location: Optional[str] = None,
    irrigation: Optional[str] = "available",
    pest_observed: Optional[str] = None,
    disease_observed: Optional[str] = None,
    pest_symptoms: Optional[str] = None,
    affected_area_pct: Optional[float] = None,
    weather_data: Optional[Dict[str, Any]] = None,
    residue_handling: Optional[str] = "removed"
) -> Dict[str, Any]:
    """
    Main entry point for the MAITTRI Evidence-Based Fertilizer & Pest Decision-Support System.
    Synthesizes all 12 sections:
    A. Soil & Crop Analysis
    B. Nutrient Status
    C. Fertilizer Recommendation
    D. Natural/Organic Alternatives
    E. Chemical Fertilizer Options
    F. Pest & Disease Management
    G. Chemical Pesticide Options
    H. Natural/Biological Pest Management
    I. Chemical vs Natural Comparison
    J. Warnings & Safety
    K. Recommendation Confidence & Explanation
    L. Step-by-Step Guidance & Authoritative Sources
    """
    # 1. Validation checks
    if not current_crop or len(current_crop.strip()) == 0:
        raise ValueError("Current crop selection is required.")
    if soil_ph is not None and (soil_ph < 3.0 or soil_ph > 11.5):
        raise ValueError(f"Soil pH value {soil_ph} is out of realistic agricultural range (3.0–11.5).")
    if soil_moisture is not None and (soil_moisture < 0.0 or soil_moisture > 100.0):
        raise ValueError(f"Soil moisture {soil_moisture}% is invalid (must be between 0% and 100%).")
    if affected_area_pct is not None and (affected_area_pct < 0.0 or affected_area_pct > 100.0):
        raise ValueError(f"Affected pest area {affected_area_pct}% is invalid (must be between 0% and 100%).")

    # 2. Crop Analysis
    crop_analysis_res = analyze_crop(current_crop, crop_stage, irrigation)

    # 3. Previous Crop Analysis
    prev_crop_res = analyze_previous_crop(previous_crop, current_crop, previous_crop_harvest_season, residue_handling)

    # 4. Soil Analysis
    soil_analysis_res = analyze_soil(soil_type, soil_ph, soil_moisture, soil_temperature)

    # 5. Nutrient Status
    nutrient_status_res = analyze_nutrients_status(
        soil_n, soil_p, soil_k, secondary_nutrients, micronutrients, data_source
    )

    # 6. Organic Options
    organic_options = generate_organic_fertilizer_options(
        crop_analysis_res, soil_analysis_res, nutrient_status_res, crop_analysis_res["current_stage"]
    )

    # 7. Chemical Fertilizer Options
    chemical_options = generate_chemical_fertilizer_options(
        crop_analysis_res, soil_analysis_res, nutrient_status_res, crop_analysis_res["current_stage"]
    )

    # 8. Comparison Card
    comparison_card = generate_comparison_card(
        current_crop, soil_analysis_res["soil_type"], crop_analysis_res["current_stage"]
    )

    # 9. Pest & Disease Analysis
    pest_res = analyze_pest_and_disease(
        current_crop, pest_observed, disease_observed, pest_symptoms, affected_area_pct, crop_analysis_res["current_stage"]
    )

    # 10. Weather Integration & Advisories
    weather_advisories = evaluate_weather_risks(weather_data, crop_analysis_res)

    # 11. Confidence & Explanation
    confidence_level, confidence_reasons = calculate_recommendation_confidence(
        soil_analysis_res, nutrient_status_res, pest_res, weather_data is not None, crop_analysis_res["recognized"]
    )

    explanation_steps = build_human_readable_explanation(
        crop_analysis_res, prev_crop_res, soil_analysis_res, nutrient_status_res,
        weather_advisories, chemical_options, pest_res
    )

    # 12. Roadmap & Sources
    roadmap = generate_step_by_step_roadmap()
    sources = get_authoritative_sources()

    # Core Strategy Synthesis for Section C
    core_fertilizer_strategy = {
        "title": f"Nutrient Management Plan for {crop_analysis_res['crop']} ({crop_analysis_res['current_stage']})",
        "approach": "Integrated Nutrient Management (INM)",
        "summary": f"Targeting {crop_analysis_res['crop']} in {soil_analysis_res['soil_type']}. " +
                   (f"Address identified deficits in {', '.join(nutrient_status_res['deficits'])}. " if nutrient_status_res['deficits'] else "Maintain balanced fertility. ") +
                   f"Incorporate organic manures as foundation, and apply mineral fertilizers only as justified.",
        "soil_carbon_action": "Incorporate well-rotted FYM or vermicompost to safeguard soil structure and enhance fertilizer use efficiency.",
        "stage_specific_advice": f"At '{crop_analysis_res['current_stage']}', plant demands steady {', '.join(crop_analysis_res['heavy_uptake'])}. Ensure adequate moisture before any root-zone or foliar application."
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "farm_context": {
            "current_crop": crop_analysis_res["crop"],
            "hindi_name": crop_analysis_res.get("hindi_name", ""),
            "crop_stage": crop_analysis_res["current_stage"],
            "previous_crop": prev_crop_res["previous_crop"],
            "location": farm_location or "Unspecified",
            "irrigation": irrigation or "available",
            "data_source_used": nutrient_status_res["source"],
            "is_sensor_based": nutrient_status_res["is_sensor"]
        },
        # Structured Sections A to L
        "section_A_soil_crop_analysis": {
            "current_crop": crop_analysis_res,
            "previous_crop": prev_crop_res,
            "soil": soil_analysis_res
        },
        "section_B_nutrient_status": nutrient_status_res,
        "section_C_fertilizer_recommendation": core_fertilizer_strategy,
        "section_D_organic_alternatives": organic_options,
        "section_E_chemical_fertilizer_options": chemical_options,
        "section_F_pest_disease_analysis": {
            "evidence_found": pest_res["evidence_found"],
            "status": pest_res["status"],
            "verdict": pest_res.get("verdict", ""),
            "target_name": pest_res.get("pest_name") or pest_res.get("reported_issue", "None"),
            "symptoms": pest_res.get("symptoms", ""),
            "favorable_conditions": pest_res.get("favorable_weather", "")
        },
        "section_G_chemical_pesticide_options": [pest_res["chemical_option"]] if pest_res.get("chemical_option") else [],
        "section_H_natural_pest_management": {
            "options": pest_res.get("natural_biological_options") or pest_res.get("natural_ipm_guidance", []),
            "hierarchy": pest_res.get("ipm_hierarchy", [])
        },
        "section_I_chemical_vs_natural_comparison": comparison_card,
        "section_J_warnings_safety": {
            "weather_advisories": weather_advisories,
            "general_safety_rules": [
                "NEVER spray pesticides without complete Personal Protective Equipment (PPE) including chemical-resistant gloves, apron, goggles, and face mask.",
                "Strictly adhere to approved Pre-Harvest Intervals (PHI) to prevent harmful chemical residues on harvested crops.",
                "Never dump empty chemical pesticide containers near village ponds or irrigation canals; puncture and bury containers safely.",
                "Do NOT mix phosphorus fertilizers (DAP) directly with Zinc Sulphate in the same application tank."
            ]
        },
        "section_K_confidence_and_explanation": {
            "confidence_level": confidence_level,
            "confidence_reasons": confidence_reasons,
            "reasoning_steps": explanation_steps
        },
        "section_L_guidance_and_sources": {
            "step_by_step_roadmap": roadmap,
            "sources": sources
        }
    }
