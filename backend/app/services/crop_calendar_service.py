"""
crop_calendar_service.py
MAITTRI Agricultural Decision Support System
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Authoritative Crop Calendar & Agronomic Stage Intelligence.
Grounded in ICAR, State Agricultural Universities (PAU, CCS HAU, GBPUAT),
and KVK Packages of Practices.

Provides stage-by-stage day ranges, physiological milestones,
critical irrigation windows, fertilizer split timings, weed management,
and pest/disease scouting advisories.
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import date, datetime, timedelta

CROP_CALENDARS: Dict[str, Dict[str, Any]] = {
    "wheat": {
        "crop_key": "wheat",
        "name": "Wheat",
        "hindi_name": "गेहूं",
        "scientific_name": "Triticum aestivum",
        "family": "Poaceae (Cereal)",
        "season": "rabi",
        "typical_duration_days": 125,
        "duration_range": (115, 140),
        "water_demand": "moderate",
        "ideal_soils": ["Alluvial soil", "Loamy soil", "Sandy loam", "Clay loam"],
        "recommended_sowing_window": "15 October to 25 November (Timely sown), up to 15 December (Late sown)",
        "official_sources": [
            "ICAR - Indian Agricultural Research Institute (IARI), New Delhi",
            "ICAR - Indian Institute of Wheat and Barley Research (IIWBR), Karnal",
            "Punjab Agricultural University (PAU) Package of Practices for Rabi Crops"
        ],
        "stages": [
            {
                "stage_id": "sowing",
                "name": "Sowing & Germination",
                "hindi_name": "बुवाई एवं अंकुरण",
                "start_day": 0,
                "end_day": 12,
                "description": "Seed germination, coleoptile emergence and radical establishment.",
                "hindi_description": "बीज अंकुरण, प्रथम प्ररोह का निकलना और प्राथमिक जड़ों की स्थापना।",
                "critical_irrigation": False,
                "irrigation_note": "Ensure adequate pre-sowing moisture (Palewa / Rauni). Avoid stagnation.",
                "fertilizer_guidance": "Apply full basal dose of Phosphorus (P2O5), Potassium (K2O), and 1/3rd to 1/2 of total Nitrogen at sowing. Apply Zinc Sulphate if deficient.",
                "weeding_guidance": "Ensure field is level and weed-free prior to seed drill sowing.",
                "pest_disease_scouting": "Check for termite activity in sandy soils or seedling rot / damping off.",
                "actions": [
                    "Sow treated certified seed at 4-5 cm depth with recommended row-to-row spacing (20-22.5 cm).",
                    "Apply basal fertilizer dose in bands 2-3 cm below seed depth.",
                    "Monitor uniform seedling emergence 6 to 10 days after sowing."
                ]
            },
            {
                "stage_id": "cri",
                "name": "Crown Root Initiation (CRI)",
                "hindi_name": "ताज जड़ / मुकुट जड़ निकलना (CRI)",
                "start_day": 13,
                "end_day": 25,
                "description": "Most critical stage in wheat. Crown roots develop ~2 cm below soil surface.",
                "hindi_description": "गेहूं का सबसे संवेदनशील चरण। जमीन के 2 सेमी नीचे ताज जड़ें विकसित होती हैं।",
                "critical_irrigation": True,
                "irrigation_note": "Most critical irrigation window (20-25 DAS). Moisture stress at CRI causes permanent yield loss.",
                "fertilizer_guidance": "First split of Nitrogen (Urea) top-dressing right before or immediately following first irrigation.",
                "weeding_guidance": "First weeding or herbicide application window begins around day 25-30 if weeds emerge.",
                "pest_disease_scouting": "Inspect for early signs of foot rot or termite patches.",
                "actions": [
                    "Inspect crown root development at 20-25 days after sowing.",
                    "Apply first critical irrigation unless significant rainfall occurs or soil moisture is high.",
                    "Broadcast 1st top-dressing dose of Urea (around 1/3rd total recommended N)."
                ]
            },
            {
                "stage_id": "tillering",
                "name": "Tillering & Early Vegetative",
                "hindi_name": "कल्ले फूटना (टिल्लरिंग)",
                "start_day": 26,
                "end_day": 45,
                "description": "Rapid formation of productive tillers and secondary root network expansion.",
                "hindi_description": "शाखाओं/कल्लों का तेजी से विकास और जड़ों का विस्तार।",
                "critical_irrigation": True,
                "irrigation_note": "Second irrigation (around 40-45 DAS) during late tillering.",
                "fertilizer_guidance": "Second split of Nitrogen top-dressing at late tillering.",
                "weeding_guidance": "Crucial weed control window. Remove broadleaf and grassy weeds (Phalaris minor) before crop canopy closes.",
                "pest_disease_scouting": "Scout for Yellow Rust (Puccinia striiformis) on leaf surfaces (yellow powder pustules), aphids, and armyworms.",
                "actions": [
                    "Count tillers per plant to evaluate crop stand density.",
                    "Perform manual weeding or apply approved post-emergence weed control.",
                    "Scout leaves closely for yellow rust stripes in cooler/humid mornings."
                ]
            },
            {
                "stage_id": "jointing",
                "name": "Jointing & Stem Elongation",
                "hindi_name": "गांठ बनना (ज्वाइंटिंग)",
                "start_day": 46,
                "end_day": 65,
                "description": "Stem internodes elongate rapidly; spikelet initiation occurs within flag leaf sheath.",
                "hindi_description": "तने की गांठों का विस्तार और बालियों का तने के अंदर निर्माण।",
                "critical_irrigation": True,
                "irrigation_note": "Third irrigation (60-65 DAS) supports rapid stem elongation.",
                "fertilizer_guidance": "Complete all soil Nitrogen applications by early jointing to avoid delayed maturity and lodging.",
                "weeding_guidance": "Hand rogue stray weeds to prevent weed seed contamination.",
                "pest_disease_scouting": "Scout for powdery mildew, brown rust, and foliar blight.",
                "actions": [
                    "Monitor internode elongation and plant vigor.",
                    "Ensure adequate soil moisture to support rapid biomass accumulation.",
                    "Avoid excessive late nitrogen that increases lodging risk."
                ]
            },
            {
                "stage_id": "flowering",
                "name": "Booting, Heading & Flowering",
                "hindi_name": "बाली निकलना एवं फूल आना (हेडिंग/पुष्पन)",
                "start_day": 66,
                "end_day": 85,
                "description": "Earhead emergence from boot leaf, anthesis and pollination.",
                "hindi_description": "गोभ से बालियां बाहर आना और परागण होना।",
                "critical_irrigation": True,
                "irrigation_note": "Fourth critical irrigation (80-85 DAS). Water stress causes sterile florets and poor grain set.",
                "fertilizer_guidance": "Optional micronutrient foliar spray (1% Potassium Nitrate or 0.2% Boron) if advised by soil/leaf test.",
                "weeding_guidance": "Prevent late weed competition.",
                "pest_disease_scouting": "Scout for head blight, loose smut, and ear-head caterpillar or aphids.",
                "actions": [
                    "Inspect pollen shedding and uniform earhead emergence.",
                    "Avoid spraying chemicals during peak noon pollination hours.",
                    "Ensure light irrigation on calm (low-wind) days to prevent crop lodging."
                ]
            },
            {
                "stage_id": "grain_filling",
                "name": "Milking & Dough (Grain Filling)",
                "hindi_name": "दुग्धावस्था एवं दाना भराव (मिल्किंग/डो)",
                "start_day": 86,
                "end_day": 105,
                "description": "Starch accumulation inside grain; transition from milky liquid to firm dough.",
                "hindi_description": "दानों में स्टार्च भराव, दूधिया अवस्था से कड़े दाने की ओर बढ़ना।",
                "critical_irrigation": True,
                "irrigation_note": "Fifth irrigation at early dough stage. Avoid irrigation during strong winds.",
                "fertilizer_guidance": "No soil fertilizer application. Stored nutrients translocate to grains.",
                "weeding_guidance": "Roguing of off-types and weeds.",
                "pest_disease_scouting": "Monitor for terminal heat stress and aphid clusters on ripening heads.",
                "actions": [
                    "Examine grain development by pressing developing kernels.",
                    "Monitor weather forecast for untimely rain, hail, or heat spikes.",
                    "Protect crop from bird damage and stray animal grazing."
                ]
            },
            {
                "stage_id": "maturity",
                "name": "Ripening & Physiological Maturity",
                "hindi_name": "परिपक्वता (पकाव अवस्था)",
                "start_day": 106,
                "end_day": 120,
                "description": "Leaves turn golden-yellow, chlorophyll degrades, grain moisture drops below 18%.",
                "hindi_description": "पत्तियां और बालियां सुनहरी पीली होना, दानों की नमी 18% से कम होना।",
                "critical_irrigation": False,
                "irrigation_note": "Completely stop irrigation 10-15 days before intended harvest.",
                "fertilizer_guidance": "No application.",
                "weeding_guidance": "Field clean-up before harvester entry.",
                "pest_disease_scouting": "Inspect for storage pests and grain discoloration.",
                "actions": [
                    "Stop all field irrigations to allow uniform drying of crop and soil.",
                    "Check grain hardness with thumbnail (nail dent test).",
                    "Inspect combine harvester / threshing equipment and arrange tarpaulins."
                ]
            },
            {
                "stage_id": "harvest",
                "name": "Harvest & Post-Harvest",
                "hindi_name": "कटाई, गहाई एवं भंडारण",
                "start_day": 121,
                "end_day": 135,
                "description": "Grain moisture at 12-14%, combine harvesting or manual reapers, clean storage.",
                "hindi_description": "12-14% दाना नमी पर कटाई, सुरक्षित भंडारण एवं अवशेष प्रबंधन।",
                "critical_irrigation": False,
                "irrigation_note": "None.",
                "fertilizer_guidance": "Plan soil testing and green manuring / summer legume post-harvest.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Fumigate and clean storage bins (kuthla / metal bins) against weevils (Sitophilus oryzae).",
                "actions": [
                    "Harvest during dry sunny weather when grain moisture is 12-14%.",
                    "Thresh and clean grains to eliminate chaff, broken seeds, and dust.",
                    "Manage wheat straw (bhusa) with straw reaper for cattle feed — avoid open burning.",
                    "Check mandi prices on MAITTRI Market Price module before selling."
                ]
            }
        ]
    },
    "rice": {
        "crop_key": "rice",
        "name": "Rice / Paddy",
        "hindi_name": "धान / चावल",
        "scientific_name": "Oryza sativa",
        "family": "Poaceae (Cereal)",
        "season": "kharif",
        "typical_duration_days": 135,
        "duration_range": (120, 150),
        "water_demand": "high",
        "ideal_soils": ["Clay soil", "Clay loam", "Alluvial soil"],
        "recommended_sowing_window": "Nursery in May-June; Transplanting 20-30 days later (June-July)",
        "official_sources": [
            "ICAR - National Rice Research Institute (NRRI), Cuttack",
            "ICAR - Indian Institute of Rice Research (IIRR), Hyderabad",
            "State Agricultural University Packages of Practices for Kharif Rice"
        ],
        "stages": [
            {
                "stage_id": "nursery",
                "name": "Nursery / Sowing & Seedling",
                "hindi_name": "नर्सरी / बुवाई एवं पौध तैयारी",
                "start_day": 0,
                "end_day": 25,
                "description": "Nursery bed seed germination, seedling vigor and root elongation before transplanting.",
                "hindi_description": "नर्सरी में बीज अंकुरण, पौध की बढ़वार और रोपाई पूर्व तैयारी।",
                "critical_irrigation": True,
                "irrigation_note": "Keep nursery bed saturated with a shallow film of water (1-2 cm).",
                "fertilizer_guidance": "Apply well-decomposed FYM and modest DAP/Urea in nursery bed. Zinc application prevents seedling Khaira.",
                "weeding_guidance": "Hand weed nursery bed 10-12 days after sowing.",
                "pest_disease_scouting": "Scout for thrips, blast, and brown spot on tender seedlings.",
                "actions": [
                    "Treat seed with Carbendazim / Trichoderma before sowing in wet nursery bed.",
                    "Maintain optimum water depth in nursery.",
                    "Prepare main field by thorough puddling and leveling 2-3 days before transplanting."
                ]
            },
            {
                "stage_id": "transplanting_tillering",
                "name": "Transplanting & Active Tillering",
                "hindi_name": "रोपाई एवं कल्ले फूटना (टिलरिंग)",
                "start_day": 26,
                "end_day": 55,
                "description": "Seedling recovery, root anchorage, and rapid production of productive tillers.",
                "hindi_description": "पौध की जड़ जमाव और कल्ले निकलने का मुख्य चरण।",
                "critical_irrigation": True,
                "irrigation_note": "Maintain 2-5 cm standing water during initial establishment, then alternate wetting and drying (AWD).",
                "fertilizer_guidance": "Full basal dose of P & K + Zinc Sulphate at transplanting. Top-dress 1st split of Nitrogen (Urea) at 20-25 days after transplanting.",
                "weeding_guidance": "Apply pre-emergence herbicide (Pretilachlor / Pyrazosulfuron) within 3-5 days after transplanting, or use cono-weeder.",
                "pest_disease_scouting": "Scout for Yellow Stem Borer (dead hearts), Gall Midge, Leaf Folder, and Khaira disease (rusty brown spots from Zn deficiency).",
                "actions": [
                    "Transplant 21-25 day old seedlings (2-3 seedlings per hill) at 20x15 cm spacing.",
                    "Broadcast 1st top-dress Urea.",
                    "Check hills for folded leaves or central dead shoots."
                ]
            },
            {
                "stage_id": "panicle_initiation",
                "name": "Panicle Initiation & Stem Elongation",
                "hindi_name": "गाभा बनना / बाली निर्माण (पैनिकल इनीशिएशन)",
                "start_day": 56,
                "end_day": 80,
                "description": "Panicle primordium differentiates inside boot; rapid stem internode elongation.",
                "hindi_description": "तने के अंदर बाली का निर्माण और पौधे की लंबाई बढ़ना।",
                "critical_irrigation": True,
                "irrigation_note": "Extremely critical irrigation phase. Maintain 3-5 cm water. Never let soil dry out.",
                "fertilizer_guidance": "Apply 2nd Nitrogen split (and optional MOP top-dress) at panicle initiation.",
                "weeding_guidance": "Remove stray weeds by hand to prevent interference with panicles.",
                "pest_disease_scouting": "Scout for Bacterial Leaf Blight (BLB), Sheath Blight, and Brown Planthopper (BPH) at base of hills.",
                "actions": [
                    "Dissect sample stem to verify panicle initiation (green sponge-like tip visible).",
                    "Apply final Nitrogen top-dress dose.",
                    "Part rice hills and inspect base of plants for BPH hoppers."
                ]
            },
            {
                "stage_id": "flowering",
                "name": "Booting, Heading & Flowering",
                "hindi_name": "बाली निकलना एवं फूल खिलना",
                "start_day": 81,
                "end_day": 100,
                "description": "Exertion of panicles, anthesis, pollination, and early fertilization.",
                "hindi_description": "बाली का पूर्ण निकास और परागण प्रक्रिया।",
                "critical_irrigation": True,
                "irrigation_note": "Critical phase. Moisture stress induces sterile spikelets ('white heads').",
                "fertilizer_guidance": "No soil fertilizer. Optional 1% Potassium Nitrate spray in deficit soils.",
                "weeding_guidance": "Field should be weed-free.",
                "pest_disease_scouting": "Inspect for False Smut (yellow/green velvet balls), Neck Blast, and Gundhi Bug (sucking sap).",
                "actions": [
                    "Maintain continuous thin film of water in the field.",
                    "Inspect early morning or dusk for Gundhi bug sweet aroma or pest clusters.",
                    "Avoid spraying during morning flowering hours (9 AM - 12 PM)."
                ]
            },
            {
                "stage_id": "grain_fill",
                "name": "Milk & Dough (Grain Filling)",
                "hindi_name": "दुग्धावस्था एवं दाना सख्त होना",
                "start_day": 101,
                "end_day": 120,
                "description": "Grain weight gain, milky caryopsis firms into soft dough then hard dough.",
                "hindi_description": "दानों में चावल का भराव और कड़ापन आना।",
                "critical_irrigation": True,
                "irrigation_note": "Maintain saturated soil; drain standing water 10-12 days before planned harvest.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Monitor for rodent burrows and late sheath rot.",
                "actions": [
                    "Gradually drain field water to promote uniform grain ripening and ease combine movement.",
                    "Check lower grains in panicle for yellowing.",
                    "Plan residue / parali management machinery early (Super SMS, Happy Seeder, Baler)."
                ]
            },
            {
                "stage_id": "maturity_harvest",
                "name": "Maturity, Harvest & Parali Management",
                "hindi_name": "कटाई, मड़ाई एवं पराली प्रबंधन",
                "start_day": 121,
                "end_day": 140,
                "description": "85% panicles turn straw-colored, grain moisture 20-22% (harvest) and 12-14% (storage).",
                "hindi_description": "85% बालियां सुनहरी होना, कटाई और पराली का सुरक्षित प्रबंधन।",
                "critical_irrigation": False,
                "irrigation_note": "Field must be completely dry for combine harvester entry.",
                "fertilizer_guidance": "Incorporate paddy stubble with bio-decomposer or sow wheat directly with Happy Seeder.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Protect harvested paddy bags from dampness and rats.",
                "actions": [
                    "Harvest when grains are firm and golden (moisture 20-22%).",
                    "Do NOT burn paddy straw — utilize Super-SMS fitted combine or bale straw for biomass plants.",
                    "Check government custom hiring centers (CHCs) for CRM subsidies on MAITTRI Government Schemes module.",
                    "Dry paddy to 13-14% moisture before bagging or marketing."
                ]
            }
        ]
    },
    "mustard": {
        "crop_key": "mustard",
        "name": "Mustard / Rapeseed",
        "hindi_name": "सरसों / राई",
        "scientific_name": "Brassica juncea",
        "family": "Brassicaceae (Oilseed)",
        "season": "rabi",
        "typical_duration_days": 115,
        "duration_range": (105, 130),
        "water_demand": "low-to-moderate",
        "ideal_soils": ["Sandy loam", "Loamy soil", "Alluvial soil"],
        "recommended_sowing_window": "October 1 to October 25 (optimum for aphid escape)",
        "official_sources": [
            "ICAR - Directorate of Rapeseed-Mustard Research (DRMR), Bharatpur",
            "Chaudhary Charan Singh Haryana Agricultural University (CCSHAU), Hisar",
            "ICAR Package of Practices for Oilseed Crops"
        ],
        "stages": [
            {
                "stage_id": "sowing_emergence",
                "name": "Sowing & Seedling Emergence",
                "hindi_name": "बुवाई एवं अंकुरण",
                "start_day": 0,
                "end_day": 15,
                "description": "Seed germination, cotyledon emergence and primary root establishment.",
                "hindi_description": "बीज का अंकुरण और प्रथम दो पत्तियां निकलना।",
                "critical_irrigation": False,
                "irrigation_note": "Sow in conserved soil moisture after pre-sowing irrigation.",
                "fertilizer_guidance": "Basal application of N, P, K and mandatory Sulphur (20-40 kg S/ha via SSP or elemental sulphur).",
                "weeding_guidance": "Pre-emergence herbicide (Pendimethalin) within 48 hours of sowing.",
                "pest_disease_scouting": "Scout for painted bug (Bagrada hilaris) and flea beetles on tender seedlings.",
                "actions": [
                    "Sow treated seed at 3-4 cm depth at 45x15 cm spacing.",
                    "Thin seedlings to 10-15 cm intra-row distance at 15-20 DAS for robust branching.",
                    "Ensure adequate sulphur nutrition for higher oil synthesis."
                ]
            },
            {
                "stage_id": "vegetative_branching",
                "name": "Rosette & Branching",
                "hindi_name": "शाखाएं निकलना (ब्रांचिंग)",
                "start_day": 16,
                "end_day": 40,
                "description": "Rosette leaf expansion and initiation of primary and secondary branches.",
                "hindi_description": "शाखाओं का फैलाव और पत्तियों का विकास।",
                "critical_irrigation": True,
                "irrigation_note": "First critical irrigation at pre-flowering / branching stage (28-35 DAS).",
                "fertilizer_guidance": "Top-dress remaining 1/2 Nitrogen (Urea) prior to first irrigation.",
                "weeding_guidance": "One intercultural hoeing (khurpi/wheel hoe) at 20-25 DAS.",
                "pest_disease_scouting": "Scout for sawfly larvae and white rust pustules on leaf underside.",
                "actions": [
                    "Thin out dense patches to maintain uniform plant population.",
                    "Apply first irrigation at 30-35 DAS.",
                    "Broadcast remaining Nitrogen."
                ]
            },
            {
                "stage_id": "flowering",
                "name": "Flowering & Early Podding",
                "hindi_name": "फूल खिलना एवं फली बनना",
                "start_day": 41,
                "end_day": 70,
                "description": "Abundant yellow bloom, honeybee pollination, and young siliqua (pod) formation.",
                "hindi_description": "पीले फूल खिलना, परागण और फलियों का बनना।",
                "critical_irrigation": True,
                "irrigation_note": "Second irrigation at pod formation (60-65 DAS) if winter rain is absent.",
                "fertilizer_guidance": "Foliar spray of 1% water-soluble fertilizer or Boron (0.1%) if deficiency exists.",
                "weeding_guidance": "None (crop canopy covers ground).",
                "pest_disease_scouting": "CRITICAL: Daily scouting for Mustard Aphid (Lipaphis erysimi) colonies on twigs and flower buds. White rust / Alternaria blight.",
                "actions": [
                    "Scout for aphid colonies (economic threshold: 20-25 aphids/10 cm terminal shoot).",
                    "Protect pollinating honeybees — avoid daytime chemical spraying.",
                    "Apply light irrigation at siliqua development if soil is dry."
                ]
            },
            {
                "stage_id": "pod_filling_maturity",
                "name": "Pod Filling & Ripening",
                "hindi_name": "फली में दाना भराव एवं पकाव",
                "start_day": 71,
                "end_day": 105,
                "description": "Seed development inside pods, oil synthesis, pods turn yellowish-brown.",
                "hindi_description": "फलियों में तेल का निर्माण और फलियों का पीला-भूरा होना।",
                "critical_irrigation": False,
                "irrigation_note": "Stop irrigation to prevent delayed maturity and lodging.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Monitor for powdery mildew and late Alternaria blight.",
                "actions": [
                    "Inspect seed color inside pods (turns from green to brown/black).",
                    "Watch for pod shatter risk if harvesting is excessively delayed."
                ]
            },
            {
                "stage_id": "harvest",
                "name": "Harvesting & Threshing",
                "hindi_name": "कटाई एवं मड़ाई",
                "start_day": 106,
                "end_day": 120,
                "description": "75-80% pods turn golden-yellow; harvest in early morning hours to prevent shattering.",
                "hindi_description": "75-80% फलियां पीली होने पर सुबह के समय कटाई।",
                "critical_irrigation": False,
                "irrigation_note": "None.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Store clean dry seed at 8% moisture to prevent mold and oil rancidity.",
                "actions": [
                    "Harvest early in the morning when dew softens pods, minimizing shattering losses.",
                    "Sun-dry bundled stalks in the threshing yard for 4-6 days.",
                    "Thresh, clean, and dry seeds down to 8% moisture.",
                    "Track oilseed mandi prices on MAITTRI Market Price page."
                ]
            }
        ]
    },
    "maize": {
        "crop_key": "maize",
        "name": "Maize / Corn",
        "hindi_name": "मक्का",
        "scientific_name": "Zea mays",
        "family": "Poaceae (Cereal)",
        "season": "kharif",
        "typical_duration_days": 100,
        "duration_range": (90, 115),
        "water_demand": "moderate",
        "ideal_soils": ["Loamy soil", "Sandy loam", "Alluvial soil", "Clay loam"],
        "recommended_sowing_window": "June-July (Kharif) or October-November (Rabi Maize)",
        "official_sources": [
            "ICAR - Indian Institute of Maize Research (IIMR), Ludhiana",
            "Directorate of Maize Development, Government of India"
        ],
        "stages": [
            {
                "stage_id": "sowing_seedling",
                "name": "Sowing & Seedling (V2-V4)",
                "hindi_name": "बुवाई एवं प्रारंभिक पौध",
                "start_day": 0,
                "end_day": 18,
                "description": "Emergence of coleoptile, 2 to 4 leaf collar formation.",
                "hindi_description": "अंकुरण और 2-4 पत्तियों का विकास।",
                "critical_irrigation": False,
                "irrigation_note": "Sensitive to waterlogging. Ensure excellent field drainage.",
                "fertilizer_guidance": "Basal application of 1/3rd N, full P, full K and Zinc Sulphate (25 kg/ha).",
                "weeding_guidance": "Pre-emergence herbicide Atrazine (1 kg a.i./ha) within 2 days of sowing.",
                "pest_disease_scouting": "CRITICAL: Scout for Fall Armyworm (Spodoptera frugiperda) pinhole damage in leaf whorls.",
                "actions": [
                    "Sow on ridges or flat beds at 60x20 cm spacing.",
                    "Inspect whorls for FAW egg masses or sawdust-like frass.",
                    "Maintain open drainage furrows during kharif monsoon showers."
                ]
            },
            {
                "stage_id": "knee_high",
                "name": "Knee-High Stage (V6-V8)",
                "hindi_name": "घुटने की ऊंचाई (नी-हाई)",
                "start_day": 19,
                "end_day": 40,
                "description": "Rapid vegetative elongation and brace root initiation.",
                "hindi_description": "पौधों का तेजी से बढ़ना और सहायक जड़ों का विकास।",
                "critical_irrigation": True,
                "irrigation_note": "Critical irrigation stage (around 30-35 DAS) if dry spell occurs.",
                "fertilizer_guidance": "First top-dressing of Nitrogen (1/3rd Urea) beside the plant rows followed by earthing up.",
                "weeding_guidance": "Intercultural hoeing and earthing up (mitti chadhana) at 30 DAS.",
                "pest_disease_scouting": "Fall Armyworm and stem borer (Chilo partellus).",
                "actions": [
                    "Perform earthing up around base of plants to anchor roots and suppress weeds.",
                    "Apply Urea split alongside rows; avoid dropping fertilizer directly into leaf whorl.",
                    "Pheromone traps for FAW monitoring."
                ]
            },
            {
                "stage_id": "tasseling_silking",
                "name": "Tasseling & Silking",
                "hindi_name": "मंजर (टेसल) एवं भुट्टे में बाल (सिल्क) निकलना",
                "start_day": 41,
                "end_day": 65,
                "description": "Male flowers (tassels) release pollen; silks emerge from cob ears to catch pollen.",
                "hindi_description": "नर फूल (मंजर) और मादा फूल (सिल्क) का निकलना तथा परागण।",
                "critical_irrigation": True,
                "irrigation_note": "MOST CRITICAL WATER STAGE. Drought during silking causes barren cobs.",
                "fertilizer_guidance": "Apply final 1/3rd Nitrogen top-dressing at early tasseling.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Banded leaf and sheath blight, cob borer.",
                "actions": [
                    "Ensure adequate soil moisture throughout the pollination window.",
                    "Inspect silk emergence and uniform cob development.",
                    "Top-dress final dose of Urea."
                ]
            },
            {
                "stage_id": "grain_fill_dough",
                "name": "Grain Filling & Milk / Dough",
                "hindi_name": "भुट्टे में दाना भराव (मिल्क/डो)",
                "start_day": 66,
                "end_day": 85,
                "description": "Kernels fill with starch; transition from milk stage to denting/dough stage.",
                "hindi_description": "दानों में स्टार्च भराव और कड़ा होना।",
                "critical_irrigation": True,
                "irrigation_note": "Maintain moisture until late dough stage.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Check for ear rot and bird attack.",
                "actions": [
                    "Peel back husk tip of sample cobs to monitor kernel fullness.",
                    "Erect bird scares or shiny ribbons to minimize parrot/bird damage."
                ]
            },
            {
                "stage_id": "maturity_harvest",
                "name": "Physiological Maturity & Harvest",
                "hindi_name": "परिपक्वता एवं कटाई",
                "start_day": 86,
                "end_day": 105,
                "description": "Husk turns papery brown, black layer forms at kernel tip base, moisture drops below 20%.",
                "hindi_description": "भुट्टे का छिलका सूखना, दाने के आधार पर काली परत (ब्लैक लेयर) बनना।",
                "critical_irrigation": False,
                "irrigation_note": "None.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Store shelled grain at 12% moisture to prevent Aspergillus aflatoxin.",
                "actions": [
                    "Confirm physiological maturity via black layer formation at kernel attachment.",
                    "Harvest cobs, de-husk and sun dry for 3-5 days before mechanical sheller.",
                    "Utilize green maize stover for nutritious cattle fodder."
                ]
            }
        ]
    },
    "potato": {
        "crop_key": "potato",
        "name": "Potato",
        "hindi_name": "आलू",
        "scientific_name": "Solanum tuberosum",
        "family": "Solanaceae (Tuber)",
        "season": "rabi",
        "typical_duration_days": 100,
        "duration_range": (85, 115),
        "water_demand": "moderate-to-high",
        "ideal_soils": ["Sandy loam", "Loamy soil", "Alluvial soil"],
        "recommended_sowing_window": "15 October to 5 November (Indo-Gangetic plains)",
        "official_sources": [
            "ICAR - Central Potato Research Institute (CPRI), Shimla",
            "National Horticulture Board (NHB) Potato Guidelines"
        ],
        "stages": [
            {
                "stage_id": "planting_sprouting",
                "name": "Planting & Sprouting / Emergence",
                "hindi_name": "बुवाई एवं अंकुरण / जमाव",
                "start_day": 0,
                "end_day": 20,
                "description": "Tuber sprout growth, root emergence from eye nodes, shoot emergence above ground.",
                "hindi_description": "कंदों से आंखें फूटना, जड़ें और कोपलें जमीन से बाहर आना।",
                "critical_irrigation": False,
                "irrigation_note": "Light irrigation immediately after planting if ridge soil is dry.",
                "fertilizer_guidance": "Heavy basal feeder: Full P2O5, half N, and half K2O (prefer SOP over MOP) at planting.",
                "weeding_guidance": "Pre-emergence herbicide (Metribuzin / Pendimethalin) within 3-4 days after planting.",
                "pest_disease_scouting": "Inspect seed tubers for black scurf or bacterial soft rot.",
                "actions": [
                    "Plant well-sprouted, disease-free seed tubers (30-45g size) on ridges (60x20 cm).",
                    "Ensure tubers are covered with 5-7 cm loose friable soil.",
                    "Monitor emergence 10-15 days after planting."
                ]
            },
            {
                "stage_id": "stolon_tuber_initiation",
                "name": "Stolonization & Tuber Initiation",
                "hindi_name": "स्टोलन एवं कंद बनना (ट्यूबर इनीशिएशन)",
                "start_day": 21,
                "end_day": 45,
                "description": "Lateral underground stolon tips swell to form miniature tubers (hooking/marble stage).",
                "hindi_description": "जमीन के अंदर धागेनुमा शाखाओं (स्टोलन) के सिरों पर नन्हे कंद बनना।",
                "critical_irrigation": True,
                "irrigation_note": "CRITICAL WATER WINDOW: Maintain uniform soil moisture. Water deficit reduces tuber count.",
                "fertilizer_guidance": "First top-dressing: remaining half Nitrogen and half Potassium before earthing up.",
                "weeding_guidance": "Earthing up (mitti chadhana) at 30-35 DAS is mandatory to prevent tuber greening.",
                "pest_disease_scouting": "Scout for cutworms, aphids, and early blight concentric leaf spots.",
                "actions": [
                    "Carry out thorough earthing up to create high broad ridges.",
                    "Apply remaining Nitrogen and Potassium alongside ridges.",
                    "Maintain light, frequent irrigations (never submerge ridge tops)."
                ]
            },
            {
                "stage_id": "tuber_bulking",
                "name": "Tuber Bulking & Canopy Growth",
                "hindi_name": "कंद का फूलना / बड़ा होना (ट्यूबर बल्किंग)",
                "start_day": 46,
                "end_day": 75,
                "description": "Rapid cell enlargement and starch accumulation in tubers; high potassium demand.",
                "hindi_description": "कंदों में स्टार्च का तेजी से भराव और आकार बढ़ना।",
                "critical_irrigation": True,
                "irrigation_note": "Regular light irrigations at 7-10 day intervals.",
                "fertilizer_guidance": "Optional foliar spray of 1% 00-52-34 or 13-00-45 for tuber size enhancement.",
                "weeding_guidance": "Hand pull large solitary weeds.",
                "pest_disease_scouting": "CRITICAL: Late Blight (Phytophthora infestans) alert if foggy/cloudy cold weather persists.",
                "actions": [
                    "Monitor weather for overcast cold conditions (high humidity + low night temp = Late Blight risk).",
                    "Ensure tubers remain buried under ridges to avoid greening from sunlight.",
                    "Check tuber size sample by carefully digging near outer ridge margin."
                ]
            },
            {
                "stage_id": "dehaulming_maturity",
                "name": "Dehaulming & Skin Curing",
                "hindi_name": "बेल कटाई (डीहौल्मिंग) एवं छिलका पकना",
                "start_day": 76,
                "end_day": 90,
                "description": "Cutting off green vines (dehaulming) 10-15 days before harvest to harden tuber skin.",
                "hindi_description": "कंदों का छिलका कड़ा करने के लिए कटाई से 10-15 दिन पहले बेल काटना।",
                "critical_irrigation": False,
                "irrigation_note": "Completely stop irrigation 10 days before dehaulming.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Dehaulming stops aphid vector transmission of viral diseases.",
                "actions": [
                    "Cut off haulms (vines) at ground level with sickle or shredder 10-15 days before digging.",
                    "Allow tubers to remain undisturbed in dry soil so the periderm (skin) hardens.",
                    "Prevent skin peeling during mechanical digging."
                ]
            },
            {
                "stage_id": "harvest_storage",
                "name": "Harvest, Curing & Storage",
                "hindi_name": "खुदाई, सुखाना एवं कोल्ड स्टोरेज",
                "start_day": 91,
                "end_day": 105,
                "description": "Digging with potato digger, sorting, curing in shade, and storage/marketing.",
                "hindi_description": "आलू की खुदाई, छंटाई और छाया में सुखाना।",
                "critical_irrigation": False,
                "irrigation_note": "None.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Inspect for tuber moth, rot, and mechanical cuts before bagging.",
                "actions": [
                    "Dig tubers during bright weather when soil is dry.",
                    "Cure tubers in heaps covered with paddy straw in a cool shaded area for 10 days.",
                    "Sort into seed, table, and chat size; discard cut or rotten tubers.",
                    "Check cold storage booking or local mandi rates on MAITTRI Market Price page."
                ]
            }
        ]
    },
    "tomato": {
        "crop_key": "tomato",
        "name": "Tomato",
        "hindi_name": "टमाटर",
        "scientific_name": "Solanum lycopersicum",
        "family": "Solanaceae (Vegetable)",
        "season": "rabi",
        "typical_duration_days": 110,
        "duration_range": (95, 130),
        "water_demand": "moderate",
        "ideal_soils": ["Loamy soil", "Sandy loam", "Alluvial soil", "Red soil"],
        "recommended_sowing_window": "Nursery in Sept-Oct for Rabi; Transplanting in Oct-Nov",
        "official_sources": [
            "ICAR - Indian Institute of Horticultural Research (IIHR), Bengaluru",
            "ICAR - Indian Institute of Vegetable Research (IIVR), Varanasi"
        ],
        "stages": [
            {
                "stage_id": "nursery_transplanting",
                "name": "Nursery & Transplanting",
                "hindi_name": "नर्सरी एवं पौध रोपाई",
                "start_day": 0,
                "end_day": 25,
                "description": "Raising healthy seedlings in raised beds and transplanting into main field.",
                "hindi_description": "नर्सरी में पौध तैयार करना और खेत में रोपाई।",
                "critical_irrigation": True,
                "irrigation_note": "Light irrigation immediately after transplanting.",
                "fertilizer_guidance": "Basal application of FYM, 1/3rd N, full P, and half K.",
                "weeding_guidance": "Mulching with silver-black plastic mulch suppresses weeds and conserves moisture.",
                "pest_disease_scouting": "Scout for damping off in nursery and whitefly (vector of Tomato Leaf Curl Virus).",
                "actions": [
                    "Transplant 25-30 day old sturdy seedlings on raised beds (60-75 cm row spacing).",
                    "Dip seedling roots in Trichoderma/Pseudomonas bio-agent solution.",
                    "Provide immediate post-transplant irrigation."
                ]
            },
            {
                "stage_id": "vegetative_staking",
                "name": "Vegetative Growth & Staking",
                "hindi_name": "वानस्पतिक बढ़वार एवं सहारा देना (स्टेकिंग)",
                "start_day": 26,
                "end_day": 50,
                "description": "Branching, side shoot pruning and bamboo/trellis staking for indeterminate varieties.",
                "hindi_description": "पौधे का फैलाव, शाखाओं की छंटाई और बांस-तार का सहारा देना।",
                "critical_irrigation": True,
                "irrigation_note": "Irrigate at 5-7 day intervals; avoid waterlogging.",
                "fertilizer_guidance": "First top-dressing of Nitrogen (1/3rd Urea) and Calcium Nitrate at 30 DAT.",
                "weeding_guidance": "Shallow weeding or weed wiping between rows.",
                "pest_disease_scouting": "Scout for leaf miner serpentine mines, early blight, and bacterial wilt.",
                "actions": [
                    "Stake plants with bamboo sticks and twine to keep fruits off moist ground.",
                    "Prune bottom suckers touching the soil to improve air circulation.",
                    "Apply Calcium Nitrate to prevent Blossom End Rot (BER)."
                ]
            },
            {
                "stage_id": "flowering_fruitset",
                "name": "Flowering & Fruit Setting",
                "hindi_name": "फूल खिलना एवं फल लगना",
                "start_day": 51,
                "end_day": 75,
                "description": "Flower cluster formation, self-pollination, and fruit set expansion.",
                "hindi_description": "फूलों के गुच्छे आना और नन्हें फलों का निर्माण।",
                "critical_irrigation": True,
                "irrigation_note": "Maintain uniform moisture. Moisture fluctuation causes fruit cracking and flower drop.",
                "fertilizer_guidance": "Second top-dressing with Potassium and Boron foliar spray (0.1%) for fruit retention.",
                "weeding_guidance": "Hand weeding.",
                "pest_disease_scouting": "CRITICAL: Tomato Fruit Borer (Helicoverpa armigera) and Tuta absoluta (pinworm).",
                "actions": [
                    "Inspect flowers and tiny fruits for fruit borer bore holes.",
                    "Install yellow sticky traps for whitefly and pheromone traps for fruit borer.",
                    "Spray Boron (20% disodium octaborate @ 1g/L) to enhance fruit setting."
                ]
            },
            {
                "stage_id": "fruit_development_harvest",
                "name": "Fruit Bulking, Multiple Pickings & Marketing",
                "hindi_name": "फल का विकास, तुड़ाई एवं विपणन",
                "start_day": 76,
                "end_day": 115,
                "description": "Green fruits enlarge, breaker stage turning pink/red, multiple pickings at 3-4 day intervals.",
                "hindi_description": "फलों का आकार बढ़ना, रंग बदलना और निरंतर तुड़ाई।",
                "critical_irrigation": True,
                "irrigation_note": "Regular light watering.",
                "fertilizer_guidance": "Water-soluble Potassium Nitrate (13-0-45) foliar spray for color and shelf-life.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Check for fruit rot, buckeye rot, and sunscald.",
                "actions": [
                    "Harvest at 'Breaker stage' (first sign of pink color) for distant markets.",
                    "Harvest at full red ripe stage for local processing or nearby mandis.",
                    "Grade by size and pack in plastic crates with paper lining.",
                    "Check dynamic mandi tomato rates on MAITTRI Market Price module."
                ]
            }
        ]
    },
    "gram": {
        "crop_key": "gram",
        "name": "Gram / Chickpea",
        "hindi_name": "चना",
        "scientific_name": "Cicer arietinum",
        "family": "Fabaceae (Pulse)",
        "season": "rabi",
        "typical_duration_days": 115,
        "duration_range": (105, 125),
        "water_demand": "low",
        "ideal_soils": ["Sandy loam", "Clay loam", "Black soil", "Alluvial soil"],
        "recommended_sowing_window": "15 October to 10 November",
        "official_sources": [
            "ICAR - Indian Institute of Pulses Research (IIPR), Kanpur",
            "State Agricultural University Packages of Practices for Pulses"
        ],
        "stages": [
            {
                "stage_id": "sowing_emergence",
                "name": "Sowing & Seedling Emergence",
                "hindi_name": "बुवाई एवं अंकुरण",
                "start_day": 0,
                "end_day": 18,
                "description": "Deep taproot development, seedling emergence, and early nodulation.",
                "hindi_description": "गहरी मूसला जड़ का विकास और अंकुरण।",
                "critical_irrigation": False,
                "irrigation_note": "Sow in residual moisture after pre-sowing irrigation.",
                "fertilizer_guidance": "Starter dose only: 20 kg N + 40-50 kg P2O5 + 20 kg S/ha. Inoculate seed with Rhizobium and PSB.",
                "weeding_guidance": "Pre-emergence Pendimethalin within 48 hours of sowing.",
                "pest_disease_scouting": "Collar rot and dry root rot in hot dry soils.",
                "actions": [
                    "Treat seed with Rhizobium ciceri culture and Trichoderma.",
                    "Sow at 8-10 cm depth to place seed in moist soil layer.",
                    "Avoid excessive chemical nitrogen which suppresses root nodules."
                ]
            },
            {
                "stage_id": "branching_nipping",
                "name": "Vegetative Branching & Nipping",
                "hindi_name": "शाखाएं निकलना एवं खोटाई (निपिंग)",
                "start_day": 19,
                "end_day": 50,
                "description": "Canopy branching and active atmospheric Nitrogen fixation in root nodules.",
                "hindi_description": "शाखाओं का फैलाव और जड़ों में वायुमंडलीय नत्रजन स्थिरीकरण।",
                "critical_irrigation": True,
                "irrigation_note": "First irrigation (if needed) at pre-flowering / late branching (40-45 DAS). Avoid flooding.",
                "fertilizer_guidance": "Foliar spray of 2% Urea at 45 DAS in rainfed areas.",
                "weeding_guidance": "One hand weeding / hoeing at 25-30 DAS.",
                "pest_disease_scouting": "Cutworms and collar rot. Inspect nodules on dug-up roots (should be healthy pink inside).",
                "actions": [
                    "Nipping (plucking terminal shoots) at 30-35 DAS induces profuse lateral branching and higher pod count.",
                    "Dig 2-3 sample roots to check active pink leghaemoglobin in Rhizobium nodules.",
                    "Never over-irrigate chickpea — excessive moisture causes vegetative rank growth and wilt."
                ]
            },
            {
                "stage_id": "flowering_podding",
                "name": "Flowering & Pod Formation",
                "hindi_name": "फूल आना एवं फलियां बनना",
                "start_day": 51,
                "end_day": 85,
                "description": "Profuse flowering, self-pollination, and green pod development.",
                "hindi_description": "फूल खिलना और हरी फलियों का निर्माण।",
                "critical_irrigation": True,
                "irrigation_note": "Light irrigation at pod development stage (70-75 DAS). DO NOT irrigate during peak flowering.",
                "fertilizer_guidance": "Foliar spray of 2% DAP or Potassium Nitrate at pod initiation.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "CRITICAL: Gram Pod Borer (Helicoverpa armigera) and Fusarium Wilt.",
                "actions": [
                    "Install 'T' shaped bird perches (40-50/ha) for natural bird predation of pod borer larvae.",
                    "Install pheromone traps for Helicoverpa monitoring (ETL: 2-3 larvae per meter row).",
                    "Avoid irrigation during peak flowering to prevent flower abortion."
                ]
            },
            {
                "stage_id": "maturity_harvest",
                "name": "Maturity, Harvest & Storage",
                "hindi_name": "परिपक्वता, कटाई एवं भंडारण",
                "start_day": 86,
                "end_day": 115,
                "description": "Plants shed leaves, pods turn golden-yellow, seeds rattle inside dry pods.",
                "hindi_description": "पत्तियां झड़ना, फलियों में खड़खड़ की आवाज आना और कटाई।",
                "critical_irrigation": False,
                "irrigation_note": "None.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Protect stored gram from pulse beetle (Callosobruchus chinensis).",
                "actions": [
                    "Harvest when pods turn brownish-yellow and seeds rattle upon shaking.",
                    "Sun-dry harvested plants in threshing yard for 5-7 days.",
                    "Thresh and store seed at 9-10% moisture with a thin layer of inert dust or neem oil coating.",
                    "Check pulse MSP and mandi prices on MAITTRI Market Price module."
                ]
            }
        ]
    },
    "cotton": {
        "crop_key": "cotton",
        "name": "Cotton",
        "hindi_name": "कपास",
        "scientific_name": "Gossypium hirsutum",
        "family": "Malvaceae (Fiber)",
        "season": "kharif",
        "typical_duration_days": 165,
        "duration_range": (150, 185),
        "water_demand": "moderate-to-high",
        "ideal_soils": ["Black soil", "Alluvial soil", "Clay loam"],
        "recommended_sowing_window": "Mid April to May (North India); June-July (Central/South)",
        "official_sources": [
            "ICAR - Central Institute for Cotton Research (CICR), Nagpur",
            "All India Coordinated Research Project on Cotton"
        ],
        "stages": [
            {
                "stage_id": "sowing_seedling",
                "name": "Sowing & Seedling Establishment",
                "hindi_name": "बुवाई एवं पौध स्थापना",
                "start_day": 0,
                "end_day": 25,
                "description": "Germination, deep taproot formation, and first true leaves.",
                "hindi_description": "अंकुरण और गहरी मूसला जड़ की स्थापना।",
                "critical_irrigation": False,
                "irrigation_note": "Sow on ridges with adequate soil moisture.",
                "fertilizer_guidance": "Basal application of P2O5, K2O and 1/4th Nitrogen.",
                "weeding_guidance": "Pre-emergence herbicide Pendimethalin within 48 hours.",
                "pest_disease_scouting": "Scout for sucking pests: jassids, thrips, and aphids.",
                "actions": [
                    "Sow delinted treated seed at 90x60 cm or 67.5x60 cm spacing.",
                    "Gap fill within 7-10 days of sowing to ensure 100% plant stand.",
                    "Monitor for seedling damping off and jassid hopperburn."
                ]
            },
            {
                "stage_id": "square_formation",
                "name": "Square Formation (Squaring)",
                "hindi_name": "टिंडे की कली (स्क्वायर) बनना",
                "start_day": 26,
                "end_day": 60,
                "description": "Flower buds (squares) develop on fruiting branches (sympodia).",
                "hindi_description": "शाखाओं पर कलियों का निर्माण।",
                "critical_irrigation": True,
                "irrigation_note": "Irrigation required at square initiation if monsoon rains pause.",
                "fertilizer_guidance": "First top-dressing of 1/2 Nitrogen at squaring.",
                "weeding_guidance": "Intercultural cultivation and earthing up.",
                "pest_disease_scouting": "CRITICAL: Pink Bollworm (Pectinophora gossypiella) rosette flowers and whitefly.",
                "actions": [
                    "Install pheromone traps for Pink Bollworm (8 traps/ha).",
                    "Inspect flower squares for rosette symptoms (closed unbloomed flower).",
                    "Apply first Nitrogen top-dressing."
                ]
            },
            {
                "stage_id": "flowering_boll_dev",
                "name": "Flowering & Boll Development",
                "hindi_name": "फूल एवं टिंडे का विकास (बॉल डेवलपमेंट)",
                "start_day": 61,
                "end_day": 120,
                "description": "Flowering, boll enlargement, and fiber cell elongation inside bolls.",
                "hindi_description": "फूलों से टिंडे बनना और अंदर रुई के रेशे का विकास।",
                "critical_irrigation": True,
                "irrigation_note": "Peak water demand. Moisture stress causes severe square and boll shedding.",
                "fertilizer_guidance": "Remaining 1/4th Nitrogen top-dress + 1% Potassium Nitrate & Boron foliar spray.",
                "weeding_guidance": "Hand roguing of weeds.",
                "pest_disease_scouting": "Pink bollworm, American bollworm, Spodoptera, and Grey mildew.",
                "actions": [
                    "Destructively sample green bolls (20 bolls) to inspect for internal pink bollworm tunneling.",
                    "Spray Magnesium Sulphate (1%) and Potassium Nitrate (1%) to prevent leaf reddening (Lal Patti).",
                    "Ensure adequate soil moisture."
                ]
            },
            {
                "stage_id": "boll_bursting_picking",
                "name": "Boll Bursting & Multiple Pickings",
                "hindi_name": "टिंडे खिलना एवं कपास की चुगाई",
                "start_day": 121,
                "end_day": 165,
                "description": "Mature bolls dehisce, white lint fluffs out, 3-4 pickings done at dry intervals.",
                "hindi_description": "टिंडों का फूटना, सफेद रुई का बाहर आना और साफ चुगाई।",
                "critical_irrigation": False,
                "irrigation_note": "Stop irrigation as bolls start opening to prevent lint staining and rot.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "None.",
                "pest_disease_scouting": "Pick clean; avoid trash and bract contamination.",
                "actions": [
                    "Pick clean cotton in sunny dry weather after dew has dried up.",
                    "Keep pickings free from leaf bits, stained lint, and moisture.",
                    "Store seed cotton (Kapas) in a dry ventilated shed; check mandi prices on MAITTRI."
                ]
            }
        ]
    },
    "sugarcane": {
        "crop_key": "sugarcane",
        "name": "Sugarcane",
        "hindi_name": "गन्ना",
        "scientific_name": "Saccharum officinarum",
        "family": "Poaceae (Sugar)",
        "season": "annual",
        "typical_duration_days": 330,
        "duration_range": (300, 365),
        "water_demand": "high",
        "ideal_soils": ["Loamy soil", "Clay loam", "Alluvial soil"],
        "recommended_sowing_window": "Autumn (Oct-Nov) or Spring (Feb-March)",
        "official_sources": [
            "ICAR - Indian Institute of Sugarcane Research (IISR), Lucknow",
            "ICAR - Sugarcane Breeding Institute (SBI), Coimbatore"
        ],
        "stages": [
            {
                "stage_id": "germination",
                "name": "Germination & Sprouting",
                "hindi_name": "जमाव अवस्था (अंकुरण)",
                "start_day": 0,
                "end_day": 45,
                "description": "Bud sprouting from setts, sett root formation and primary shoot emergence.",
                "hindi_description": "गन्ने की पोरियों से आंखों का फूटना और प्रारंभिक जमाव।",
                "critical_irrigation": True,
                "irrigation_note": "First irrigation 7-10 days after planting, followed by 10-15 day intervals.",
                "fertilizer_guidance": "Full basal dose of P2O5, K2O and 1/3rd Nitrogen in planting furrows.",
                "weeding_guidance": "Blind hoeing at 20-25 days; pre-emergence Atrazine spray.",
                "pest_disease_scouting": "Early shoot borer (Chilo infuscatellus) dead hearts and termites.",
                "actions": [
                    "Treat 3-budded setts in fungicide solution before planting in 90 cm trenches.",
                    "Inspect uniform sprouting at 30-40 days; gap fill with sprouted setts.",
                    "Check for dead hearts caused by early shoot borer."
                ]
            },
            {
                "stage_id": "tillering",
                "name": "Tillering & Formative Phase",
                "hindi_name": "कल्ले फूटना (टिलरिंग)",
                "start_day": 46,
                "end_day": 120,
                "description": "Production of mother shoot tillers, crown root expansion, and clump formation.",
                "hindi_description": "शाखाओं का निकलना और गन्ने के झुंड का विकास।",
                "critical_irrigation": True,
                "irrigation_note": "Summer irrigation every 8-10 days is vital for formative survival.",
                "fertilizer_guidance": "Second Nitrogen top-dressing (1/3rd Urea) at 60-70 DAS.",
                "weeding_guidance": "Intercultural hoeing and early earthing up.",
                "pest_disease_scouting": "Top borer, root borer, and black bug.",
                "actions": [
                    "Mulch furrows with trash (dry leaves) to conserve soil moisture in hot dry months.",
                    "Apply second Nitrogen split.",
                    "Maintain irrigation frequency during peak summer."
                ]
            },
            {
                "stage_id": "grand_growth",
                "name": "Grand Growth & Cane Elongation",
                "hindi_name": "तीव्र बढ़वार अवस्था (ग्रैंड ग्रोथ)",
                "start_day": 121,
                "end_day": 240,
                "description": "Rapid cane stalk elongation, internode formation, and heavy biomass accumulation.",
                "hindi_description": "गन्ने की लंबाई तेजी से बढ़ना और पोरियों का निर्माण।",
                "critical_irrigation": True,
                "irrigation_note": "Monsoon supported; irrigate during prolonged rain breaks.",
                "fertilizer_guidance": "Final Nitrogen split (1/3rd) applied by onset of monsoon; complete before earthing up.",
                "weeding_guidance": "Thorough earthing up (julai) and cane propping/tying to prevent lodging.",
                "pest_disease_scouting": "Pyrilla (leaf hopper), red rot (red discoloration in split stalk), and white grub.",
                "actions": [
                    "Perform heavy earthing up in June/July before monsoon winds.",
                    "Tie clumps of sugarcane stalks together (propping) in August-September to prevent lodging.",
                    "Monitor for Red Rot (Colletotrichum falcatum) — immediately rogue diseased clumps."
                ]
            },
            {
                "stage_id": "ripening_harvest",
                "name": "Ripening, Sugar Accumulation & Harvest",
                "hindi_name": "शर्करा परिपक्वता एवं कटाई",
                "start_day": 241,
                "end_day": 330,
                "description": "Vegetative growth slows, sucrose accumulates in stalks, brix reaches 18-20%.",
                "hindi_description": "गन्ने में चीनी की मात्रा बढ़ना और मिल के लिए कटाई।",
                "critical_irrigation": False,
                "irrigation_note": "Stop irrigation 15-20 days before intended cane harvest.",
                "fertilizer_guidance": "None.",
                "weeding_guidance": "Detrash dry lower leaves to improve sunlight and ease cutting.",
                "pest_disease_scouting": "Inspect for stalk borer and scale insects.",
                "actions": [
                    "Test sucrose brix using hand refractometer (optimum > 18% Brix).",
                    "Harvest close to ground level using sharp cane knife (maximum sugar is in bottom internodes).",
                    "Transport to sugar mill within 24-48 hours to minimize sucrose inversion losses."
                ]
            }
        ]
    }
}


def normalize_crop_key(name: str) -> str:
    """Normalizes arbitrary crop name or Hindi/alias string to standard key."""
    if not name:
        return "wheat"
    clean = name.strip().lower()
    mapping = {
        "wheat": "wheat", "गेहूं": "wheat", "gehun": "wheat", "gehu": "wheat",
        "rice": "rice", "धान": "rice", "चावल": "rice", "paddy": "rice", "chawal": "rice",
        "mustard": "mustard", "सरसों": "mustard", "sarson": "mustard", "rai": "mustard",
        "maize": "maize", "मक्का": "maize", "corn": "maize", "makka": "maize",
        "potato": "potato", "आलू": "potato", "aalu": "potato", "alu": "potato",
        "tomato": "tomato", "टमाटर": "tomato", "tamatar": "tomato",
        "gram": "gram", "चना": "gram", "chana": "gram", "chickpea": "gram", "gram/chickpea": "gram",
        "cotton": "cotton", "कपास": "cotton", "kapas": "cotton",
        "sugarcane": "sugarcane", "गन्ना": "sugarcane", "ganna": "sugarcane"
    }
    if clean in mapping:
        return mapping[clean]
    for k, v in mapping.items():
        if k in clean:
            return v
    return "wheat"


def get_crop_calendar(crop_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves authoritative crop calendar for specified crop."""
    key = normalize_crop_key(crop_name)
    return CROP_CALENDARS.get(key)


def list_crop_calendars() -> List[Dict[str, Any]]:
    """Returns a list of all available crop calendars."""
    return list(CROP_CALENDARS.values())


def get_crop_stage_for_day(crop_name: str, day_after_sowing: int) -> Dict[str, Any]:
    """
    Finds the exact growth stage for a given crop age (days after sowing).
    Clamps gracefully to last stage if age exceeds typical duration.
    """
    calendar = get_crop_calendar(crop_name)
    if not calendar or not calendar.get("stages"):
        return {
            "stage_id": "active_growth",
            "name": "Active Growth",
            "hindi_name": "सक्रिय वृद्धि",
            "start_day": 0,
            "end_day": 120,
            "description": "Crop is undergoing standard agronomic development.",
            "hindi_description": "फसल का सामान्य वानस्पतिक एवं उत्पादक विकास जारी है।"
        }

    stages = calendar["stages"]
    day = max(0, int(day_after_sowing))

    for s in stages:
        if s["start_day"] <= day <= s["end_day"]:
            return s

    # If day is beyond the last stage, return harvest / post-harvest stage
    return stages[-1]


def calculate_calendar_dates(crop_name: str, sowing_date: date) -> List[Dict[str, Any]]:
    """
    Converts stage day intervals into real calendar date ranges
    based on the farmer's actual sowing date.
    Handles leap years, month boundaries, and year rollover safely.
    """
    calendar = get_crop_calendar(crop_name)
    if not calendar:
        return []

    results = []
    for s in calendar["stages"]:
        s_date = sowing_date + timedelta(days=s["start_day"])
        e_date = sowing_date + timedelta(days=s["end_day"])
        results.append({
            **s,
            "start_date": s_date.isoformat(),
            "end_date": e_date.isoformat(),
            "start_date_display": s_date.strftime("%d/%m/%Y"),
            "end_date_display": e_date.strftime("%d/%m/%Y"),
            "duration_days": (s["end_day"] - s["start_day"]) + 1
        })
    return results
