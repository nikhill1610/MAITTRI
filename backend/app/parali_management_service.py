"""
parali_management_service.py
Provides bounded, academically defensible crop residue / parali decision-support.
Designed strictly around authentic agronomic sources (ICAR-IARI, PAU Ludhiana,
ICAR-CRIDA, Ministry of Agriculture & Farmers Welfare).

Core Principles:
1. Anti-Burning Principle: Never encourage, validate, or facilitate open-field burning.
2. Honest Uncertainty: Distinguish estimated residue tonnages from verified measurements.
3. Crop-Awareness: Strictly prevent invalid cross-crop recommendations
   (e.g., cotton stalks as livestock feed, or untreated rice straw as sole fodder).
4. Realistic Economics: Always output ranges with transparent assumptions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import math

# =====================================================================
# CROP RESIDUE SCIENTIFIC BENCHMARKS
# Sources: ICAR-IARI, PAU Ludhiana, ICAR-CRIDA, ICAR-CIRCOT, ICAR-NDRI
# =====================================================================

CROP_RESIDUE_DATABASE: Dict[str, Dict[str, Any]] = {
    "rice": {
        "crop_name": "Rice / Paddy",
        "crop_name_hi": "धान / चावल",
        "residue_name": "Paddy Straw / Rice Straw",
        "residue_name_hi": "धान की पराली / पुआल",
        "residue_to_grain_ratio": 1.4,
        "low_t_per_acre": 2.8,
        "mid_t_per_acre": 3.4,
        "high_t_per_acre": 4.2,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 5.5,
            "phosphorus_kg": 2.3,
            "potassium_kg": 25.0,
            "sulfur_kg": 1.2,
            "organic_carbon_kg": 400.0,
            "co2_emissions_kg": 1460.0,
            "co_emissions_kg": 60.0,
            "pm_emissions_kg": 3.0,
        },
        "description": "Rice harvesting (especially with combine harvesters) leaves 3–4.5 tonnes of straw per acre. Paddy straw has high silica (13–16%) and a high C:N ratio (80:1), requiring deliberate mechanical or biological management.",
        "compatible_methods": [
            "in_situ_mulch_direct_seeding",
            "in_situ_incorporation",
            "bio_decomposer_spray",
            "ex_situ_baling",
            "on_farm_composting",
            "treated_livestock_fodder",
        ],
        "livestock_warning": "CRITICAL: Untreated paddy straw has high silica (13–16%) and oxalates which bind dietary calcium and impair digestion. It should NOT be fed as sole fodder. Recommended only if chopped and treated with 4% urea-ammoniation, or mixed in small proportions (<25%) with green legume fodder.",
    },
    "wheat": {
        "crop_name": "Wheat",
        "crop_name_hi": "गेहूं",
        "residue_name": "Wheat Straw (Bhusa / Turi)",
        "residue_name_hi": "गेहूं का भूसा / तूड़ी",
        "residue_to_grain_ratio": 1.1,
        "low_t_per_acre": 1.8,
        "mid_t_per_acre": 2.4,
        "high_t_per_acre": 3.0,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 4.8,
            "phosphorus_kg": 1.9,
            "potassium_kg": 18.0,
            "sulfur_kg": 1.0,
            "organic_carbon_kg": 380.0,
            "co2_emissions_kg": 1400.0,
            "co_emissions_kg": 55.0,
            "pm_emissions_kg": 2.8,
        },
        "description": "Wheat straw is traditionally harvested as high-value livestock dry fodder (Bhusa) using straw reapers or combine harvesters with reapers. Stubble left in fields can be incorporated before summer moong or dhaincha.",
        "compatible_methods": [
            "untreated_livestock_fodder",
            "in_situ_incorporation",
            "in_situ_mulch_direct_seeding",
            "ex_situ_baling",
            "on_farm_composting",
            "bio_decomposer_spray",
        ],
        "livestock_warning": None,
    },
    "maize": {
        "crop_name": "Maize",
        "crop_name_hi": "मक्का",
        "residue_name": "Maize Stover (Stalks & Leaves)",
        "residue_name_hi": "मक्के की कड़बी / डंठल",
        "residue_to_grain_ratio": 1.3,
        "low_t_per_acre": 2.2,
        "mid_t_per_acre": 3.0,
        "high_t_per_acre": 3.8,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 5.0,
            "phosphorus_kg": 2.0,
            "potassium_kg": 20.0,
            "sulfur_kg": 1.1,
            "organic_carbon_kg": 390.0,
            "co2_emissions_kg": 1420.0,
            "co_emissions_kg": 58.0,
            "pm_emissions_kg": 2.9,
        },
        "description": "Maize generates substantial fibrous stover (stalks, husks, cobs). It decomposes well when chopped and incorporated with a mulcher and rotavator, or can be used as chopped cattle roughage.",
        "compatible_methods": [
            "in_situ_incorporation",
            "untreated_livestock_fodder",
            "in_situ_mulch_direct_seeding",
            "on_farm_composting",
            "ex_situ_baling",
            "bio_decomposer_spray",
        ],
        "livestock_warning": None,
    },
    "sugarcane": {
        "crop_name": "Sugarcane",
        "crop_name_hi": "गन्ना",
        "residue_name": "Sugarcane Trash & Dry Leaves",
        "residue_name_hi": "गन्ने की सूखी पत्तियां (ट्रैश)",
        "residue_to_grain_ratio": 0.15,
        "low_t_per_acre": 3.2,
        "mid_t_per_acre": 4.5,
        "high_t_per_acre": 5.8,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 6.0,
            "phosphorus_kg": 2.1,
            "potassium_kg": 22.0,
            "sulfur_kg": 1.3,
            "organic_carbon_kg": 420.0,
            "co2_emissions_kg": 1500.0,
            "co_emissions_kg": 65.0,
            "pm_emissions_kg": 3.2,
        },
        "description": "Sugarcane trash left after cane harvest amounts to 8–10 tonnes/hectare. Burning damages the ratoon root buds, dries out topsoil moisture, and destroys natural predators of pyrilla and shoot borer.",
        "compatible_methods": [
            "sugarcane_trash_mulch",
            "in_situ_incorporation",
            "on_farm_composting",
            "bio_decomposer_spray",
            "ex_situ_baling",
        ],
        "livestock_warning": "Not recommended for primary livestock fodder due to very high fiber content and low palatability.",
    },
    "cotton": {
        "crop_name": "Cotton",
        "crop_name_hi": "कपास",
        "residue_name": "Cotton Stalks (Woody Residue)",
        "residue_name_hi": "कपास के डंठल / छड़ियां",
        "residue_to_grain_ratio": 3.0,
        "low_t_per_acre": 1.4,
        "mid_t_per_acre": 2.2,
        "high_t_per_acre": 2.8,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 6.2,
            "phosphorus_kg": 1.8,
            "potassium_kg": 16.0,
            "sulfur_kg": 1.0,
            "organic_carbon_kg": 450.0,
            "co2_emissions_kg": 1520.0,
            "co_emissions_kg": 70.0,
            "pm_emissions_kg": 3.5,
        },
        "description": "Cotton stalks are woody, lignified biomass (1.5–3 cm thick). Farmers traditionally burn them to control overwintering pink bollworm, but shredding with tractor slashers or pelleting creates high-value bio-fuel without burning.",
        "compatible_methods": [
            "cotton_stalk_shredding_incorporation",
            "cotton_stalk_briquetting_industrial",
            "on_farm_composting",
            "bio_decomposer_spray",
        ],
        "livestock_warning": "STRICTLY UNFIT FOR LIVESTOCK: Cotton stalks contain toxic gossypol polyphenols and woody lignocellulose. Never feed cotton stalks to cattle.",
    },
    "mustard": {
        "crop_name": "Mustard",
        "crop_name_hi": "सरसों / राई",
        "residue_name": "Mustard Stover & Pod Husk",
        "residue_name_hi": "सरसों का डंठल एवं भूसा",
        "residue_to_grain_ratio": 1.8,
        "low_t_per_acre": 1.2,
        "mid_t_per_acre": 1.8,
        "high_t_per_acre": 2.4,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 4.5,
            "phosphorus_kg": 1.7,
            "potassium_kg": 15.0,
            "sulfur_kg": 2.5,
            "organic_carbon_kg": 410.0,
            "co2_emissions_kg": 1410.0,
            "co_emissions_kg": 52.0,
            "pm_emissions_kg": 2.6,
        },
        "description": "Mustard stover is rich in sulfur and glucosinolates. When incorporated with a rotavator, it decomposes to release natural volatile bio-fumigants that suppress soil-borne fungal pathogens.",
        "compatible_methods": [
            "in_situ_incorporation",
            "on_farm_composting",
            "ex_situ_baling",
            "bio_decomposer_spray",
        ],
        "livestock_warning": "Not preferred as primary fodder due to pungent glucosinolates; acceptable only in minimal chopped quantities blended with sweeter fodders.",
    },
    "soybean": {
        "crop_name": "Soybean",
        "crop_name_hi": "सोयाबीन",
        "residue_name": "Soybean Straw & Pod Shells",
        "residue_name_hi": "सोयाबीन का भूसा एवं छिलका",
        "residue_to_grain_ratio": 1.2,
        "low_t_per_acre": 1.1,
        "mid_t_per_acre": 1.6,
        "high_t_per_acre": 2.2,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 8.5,
            "phosphorus_kg": 2.0,
            "potassium_kg": 14.0,
            "sulfur_kg": 1.4,
            "organic_carbon_kg": 400.0,
            "co2_emissions_kg": 1390.0,
            "co_emissions_kg": 50.0,
            "pm_emissions_kg": 2.4,
        },
        "description": "Soybean straw is leguminous and contains higher nitrogen (1.2–1.5% N). When incorporated directly or retained as mulch, it enriches soil nitrogen rapidly for the following wheat or chickpea crop.",
        "compatible_methods": [
            "in_situ_incorporation",
            "untreated_livestock_fodder",
            "in_situ_mulch_direct_seeding",
            "on_farm_composting",
            "ex_situ_baling",
        ],
        "livestock_warning": None,
    },
    "pulses": {
        "crop_name": "Pulses (Moong / Chana / Urad / Arhar)",
        "crop_name_hi": "दलहन (मूंग / चना / उड़द / अरहर)",
        "residue_name": "Pulse Chaff & Stover",
        "residue_name_hi": "दलहनी फसलों का भूसा एवं डंठल",
        "residue_to_grain_ratio": 1.0,
        "low_t_per_acre": 0.8,
        "mid_t_per_acre": 1.4,
        "high_t_per_acre": 2.0,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 12.0,
            "phosphorus_kg": 2.5,
            "potassium_kg": 16.0,
            "sulfur_kg": 1.5,
            "organic_carbon_kg": 410.0,
            "co2_emissions_kg": 1380.0,
            "co_emissions_kg": 48.0,
            "pm_emissions_kg": 2.3,
        },
        "description": "Pulse stover and chaff have a narrow C:N ratio (20–30:1) and high crude protein content. It makes nutritious dry fodder or can be directly disked into soil to return biologically fixed nitrogen.",
        "compatible_methods": [
            "untreated_livestock_fodder",
            "in_situ_incorporation",
            "on_farm_composting",
            "in_situ_mulch_direct_seeding",
        ],
        "livestock_warning": None,
    },
    "other": {
        "crop_name": "Other Harvested Crop",
        "crop_name_hi": "अन्य फसल",
        "residue_name": "Crop Residue / Stubble",
        "residue_name_hi": "फसल अवशेष / पराली",
        "residue_to_grain_ratio": 1.2,
        "low_t_per_acre": 1.5,
        "mid_t_per_acre": 2.2,
        "high_t_per_acre": 3.0,
        "burn_loss_per_tonne": {
            "nitrogen_kg": 5.0,
            "phosphorus_kg": 2.0,
            "potassium_kg": 18.0,
            "sulfur_kg": 1.2,
            "organic_carbon_kg": 400.0,
            "co2_emissions_kg": 1420.0,
            "co_emissions_kg": 56.0,
            "pm_emissions_kg": 2.8,
        },
        "description": "General crop residue biomass. Managing residue in-field or through composting conserves organic matter and shields topsoil from erosion.",
        "compatible_methods": [
            "in_situ_incorporation",
            "on_farm_composting",
            "in_situ_mulch_direct_seeding",
            "bio_decomposer_spray",
            "ex_situ_baling",
        ],
        "livestock_warning": "Ensure crop type is verified safe for livestock consumption before feeding.",
    },
}

# =====================================================================
# SCIENTIFIC RESIDUE MANAGEMENT METHODS MASTER
# =====================================================================

RESIDUE_METHODS_CATALOG: Dict[str, Dict[str, Any]] = {
    "in_situ_mulch_direct_seeding": {
        "method_id": "in_situ_mulch_direct_seeding",
        "name": "In-situ Surface Mulching & Direct Seeding",
        "name_hi": "सतही मल्चिंग एवं सीधी बुवाई (हैप्पी/सुपर सीडर)",
        "category": "in_situ",
        "machinery_needed": ["Happy Seeder", "Super Seeder", "Super SMS Combine"],
        "machinery_needed_hi": ["हैप्पी सीडर", "सुपर सीडर", "सुपर एसएमएस कंबाइन"],
        "estimated_cost_per_acre_min": 1600,
        "estimated_cost_per_acre_max": 2400,
        "time_required": "2–4 hours per acre",
        "time_required_hi": "2–4 घंटे प्रति एकड़",
        "soil_benefit": "Very High",
        "soil_benefit_hi": "अत्यधिक लाभदायक",
        "environmental_benefit": "Maximum (Zero Smoke & High Water Savings)",
        "environmental_benefit_hi": "सर्वोत्तम (धुआं रहित एवं जल संरक्षण)",
        "economic_potential": "Saves ₹1,500–₹2,000/acre in field preparation & 1 pre-sowing irrigation",
        "economic_potential_hi": "जुताई खर्च में ₹1,500–₹2,000/एकड़ व 1 पलेवा की बचत",
        "confidence": "High",
        "applicable_crops": ["rice", "wheat", "maize", "soybean", "pulses", "other"],
        "explanation": "Directly sows the succeeding crop into standing stubble while chopped straw is spread evenly as a protective surface mulch. Retains soil moisture by 15–20%, regulates soil temperature, and suppresses seasonal weed germination by 40–60%.",
        "steps": [
            {"step_num": 1, "title": "Combine Harvest with Super SMS", "desc": "Ensure the combine harvester is fitted with a Straw Management System (Super SMS) so loose straw is chopped and spread uniformly across the field."},
            {"step_num": 2, "title": "Check Soil Moisture (Vattar Condition)", "desc": "Inspect field moisture. Direct seeding performs optimally under optimum moisture ('Vattar') to ensure uniform seed placement and germination."},
            {"step_num": 3, "title": "Calibrate Seeder Depth & Seed Rate", "desc": "Set Happy Seeder or Super Seeder depth to 3.5–5.0 cm and calibrate seed rate (typically 40–45 kg wheat seed per acre)."},
            {"step_num": 4, "title": "Simultaneous Seeding & Basal Fertilizer", "desc": "Drill seed along with recommended basal phosphorus/potassium fertilizer in a single pass without any prior tillage."},
            {"step_num": 5, "title": "Inspect Furrows & Mulch Cover", "desc": "Verify that seeds are placed cleanly in soil furrows and covered with chopped residue mulch without bunching."},
            {"step_num": 6, "title": "Apply First Irrigation at 21 Days", "desc": "Because the mulch retains moisture, the first post-sowing irrigation (CRI stage) can typically be delayed by 5–7 days compared to conventional tilled fields."},
            {"step_num": 7, "title": "Monitor Weed Suppression & Decomposition", "desc": "Observe surface mulch as earthworm activity steadily breaks down the straw over 45–60 days into beneficial soil organic matter."},
            {"step_num": 8, "title": "Follow Standard Crop Advisory", "desc": "Proceed with standard nitrogen top-dressing and crop calendar guidance from MAITTRI."},
        ],
    },
    "in_situ_incorporation": {
        "method_id": "in_situ_incorporation",
        "name": "In-situ Soil Incorporation & Chopping",
        "name_hi": "खेत में जुताई द्वारा अवशेष मिलाना (मल्चर / रोटावेटर)",
        "category": "in_situ",
        "machinery_needed": ["Mulcher / Chopper", "Rotavator", "Reversible MB Plough"],
        "machinery_needed_hi": ["मल्चर / चॉपर", "रोटावेटर", "एम.बी. प्लाऊ"],
        "estimated_cost_per_acre_min": 2000,
        "estimated_cost_per_acre_max": 3200,
        "time_required": "1–2 days per farm",
        "time_required_hi": "1–2 दिन प्रति खेत",
        "soil_benefit": "High",
        "soil_benefit_hi": "उच्च (मिट्टी की बनावट में सुधार)",
        "environmental_benefit": "High (Zero Smoke & Recycles Carbon)",
        "environmental_benefit_hi": "उच्च (शून्य धुआं एवं कार्बन पुनर्प्रवाह)",
        "economic_potential": "Builds long-term organic carbon; requires 15–20 kg starter N/acre",
        "economic_potential_hi": "मिट्टी में दीर्घकालिक जीवांश कार्बन वृद्धि",
        "confidence": "High",
        "applicable_crops": ["rice", "wheat", "maize", "sugarcane", "cotton", "mustard", "soybean", "pulses", "other"],
        "explanation": "Residues are shredded into fine pieces with a tractor-drawn mulcher or chopper, then buried into the top 10–15 cm of soil with a rotavator or mouldboard plough. Recycles all biomass carbon into the soil, improving porosity and water infiltration.",
        "steps": [
            {"step_num": 1, "title": "Shred Standing Stubble", "desc": "Operate a tractor-mounted mulcher or chopper to shred tall stubble into 5–10 cm fragments."},
            {"step_num": 2, "title": "Distribute Starter Nitrogen (Optional)", "desc": "Broadcast 15–20 kg urea per acre before ploughing to narrow the initial C:N ratio and prevent temporary nitrogen lockup by soil microbes."},
            {"step_num": 3, "title": "Mix into Soil with Rotavator / MB Plough", "desc": "Run a rotavator or reversible mouldboard plough to thoroughly incorporate the shredded residue into the top 12–15 cm of soil."},
            {"step_num": 4, "title": "Apply Light Irrigation", "desc": "Provide a light irrigation to moisten the soil and stimulate rapid indigenous fungal and bacterial decomposition."},
            {"step_num": 5, "title": "Planking for Moisture Retention", "desc": "Run a wooden or iron planker (Sohaga) to level the field and conserve sub-surface moisture."},
            {"step_num": 6, "title": "Allow 10–14 Days Incubation (if window allows)", "desc": "If cropping schedule permits, let the residue incubate for 10–14 days before sowing to allow partial microbial decomposition."},
            {"step_num": 7, "title": "Prepare Final Seedbed", "desc": "Perform final shallow harrowing or seeding pass once soil arrives at workable moisture."},
            {"step_num": 8, "title": "Track Soil Fertility in MAITTRI", "desc": "Review updated soil nutrient status on MAITTRI's Soil & Nutrient Depletion Intelligence page."},
        ],
    },
    "bio_decomposer_spray": {
        "method_id": "bio_decomposer_spray",
        "name": "Microbial Bio-Decomposer Acceleration (Pusa Spray)",
        "name_hi": "माइक्रोबियल बायो-डीकंपोज़र छिड़काव (पूसा कैप्सूल / स्प्रे)",
        "category": "biological",
        "machinery_needed": ["Boom Sprayer / Tractor Sprayer", "Rotavator"],
        "machinery_needed_hi": ["ट्रैक्टर चालित स्प्रेयर / बूम स्प्रेयर", "रोटावेटर"],
        "estimated_cost_per_acre_min": 450,
        "estimated_cost_per_acre_max": 850,
        "time_required": "15–25 days decomposition cycle",
        "time_required_hi": "15–25 दिन अपघटन अवधि",
        "soil_benefit": "Very High",
        "soil_benefit_hi": "अत्यधिक लाभदायक (ह्यूमस निर्माण)",
        "environmental_benefit": "Maximum (Biological Humification)",
        "environmental_benefit_hi": "सर्वोत्तम (जैविक खाद निर्माण)",
        "economic_potential": "Very cost-effective; converts residue into active compost in-situ",
        "economic_potential_hi": "अत्यंत किफायती; खेत में ही खाद का निर्माण",
        "confidence": "High",
        "applicable_crops": ["rice", "wheat", "maize", "sugarcane", "cotton", "mustard", "other"],
        "explanation": "Sprays an authentic microbial fungal consortium (such as ICAR-IARI Pusa Bio-decomposer capsules or certified liquid consortia). Fungal enzymes (cellulase, pectinase, xylanase) rapidly break down tough cellulose and lignin into dark fertile humus in 20–25 days under moist soil conditions.",
        "steps": [
            {"step_num": 1, "title": "Prepare Bio-decomposer Culture Solution", "desc": "Dissolve microbial capsules or liquid consortium in 25 liters of water with 150g jaggery and 50g gram flour (besan). Let it ferment for 4–5 days until a thick fungal mat forms on top."},
            {"step_num": 2, "title": "Shred Stubble Mechanically", "desc": "Chop tall residue using a mulcher or cutter to maximize the surface area exposed to the microbial spray."},
            {"step_num": 3, "title": "Dilute for Field Spraying", "desc": "Dilute the mother culture in 200 liters of water per acre."},
            {"step_num": 4, "title": "Spray Uniformly over Residue", "desc": "Use a tractor-mounted boom sprayer or power sprayer to coat all stubble and straw evenly across the field."},
            {"step_num": 5, "title": "Shallow Soil Tillage", "desc": "Run a rotavator or disk harrow within 24 hours to gently mix the sprayed residue with moist topsoil."},
            {"step_num": 6, "title": "Maintain Field Moisture", "desc": "Ensure the soil remains consistently moist (not submerged, but damp) for 15–20 days so fungi can thrive."},
            {"step_num": 7, "title": "Observe Straw Softening & Color Change", "desc": "Residue turns soft, dark brown, and brittle as lignin decomposes."},
            {"step_num": 8, "title": "Proceed with Sowing", "desc": "Sow the subsequent crop using standard drills or direct seeders."},
        ],
    },
    "ex_situ_baling": {
        "method_id": "ex_situ_baling",
        "name": "Ex-situ Mechanical Baling & Biomass Supply",
        "name_hi": "बेलिंग तकनीक द्वारा पराली बंडल बनाना (बायोमास उद्योग हेतु)",
        "category": "ex_situ",
        "machinery_needed": ["Rake / Swather", "Square or Round Baler", "Tractor-Trolley"],
        "machinery_needed_hi": ["रेक (Rake)", "बेलिंग मशीन (Baler)", "ट्रैक्टर-ट्रॉली"],
        "estimated_cost_per_acre_min": 1800,
        "estimated_cost_per_acre_max": 2800,
        "time_required": "1–2 days per farm",
        "time_required_hi": "1–2 दिन प्रति खेत",
        "soil_benefit": "Moderate (Leaves root biomass; clears field instantly)",
        "soil_benefit_hi": "मध्यम (जड़ें मिट्टी में रहती हैं; खेत तुरंत खाली)",
        "environmental_benefit": "High (Provides clean feedstock for Bio-CNG / 2G Ethanol / Power plants)",
        "environmental_benefit_hi": "उच्च (बायो-सीएनजी व एथेनॉल हेतु कच्चा माल)",
        "economic_potential": "Potential biomass gate rate: ₹1,200–₹1,800/tonne delivered (requires local aggregator)",
        "economic_potential_hi": "संभावित बिक्री दर: ₹1,200–₹1,800/टन (स्थानीय मांग पर निर्भर)",
        "confidence": "Medium",
        "applicable_crops": ["rice", "wheat", "maize", "sugarcane", "mustard", "soybean", "other"],
        "explanation": "Collects loose straw with a tractor-drawn rake and compresses it into high-density square or round bales (15–30 kg per bale). Bales can be sold or supplied to nearby Bio-CNG plants, 2G ethanol refineries, pellet manufacturers, or thermal power plants.",
        "steps": [
            {"step_num": 1, "title": "Harvest & Field Drying", "desc": "Allow cut straw to dry in the field for 24–48 hours until straw moisture drops below 20%."},
            {"step_num": 2, "title": "Windrowing with Straw Rake", "desc": "Operate a tractor-mounted wheel rake or rotary rake to gather scattered straw into tidy, continuous windrows."},
            {"step_num": 3, "title": "High-Density Baling", "desc": "Run a square or round baler along the windrows to compress straw into tight, twine-tied bales."},
            {"step_num": 4, "title": "Count & Stack Bales", "desc": "Aggregate bales into roadside stacks using front-end loaders or manual labor."},
            {"step_num": 5, "title": "Moisture & Weight Check", "desc": "Sample bale moisture (must be under 18–20% for storage and bio-refinery acceptance)."},
            {"step_num": 6, "title": "Transport to Aggregator / Industrial Buyer", "desc": "Coordinate dispatch with custom hiring centers, FPOs, or biomass supply contractors."},
            {"step_num": 7, "title": "Field Immediate Preparation", "desc": "With the field completely clear of surface residue, proceed immediately to land preparation or sowing."},
            {"step_num": 8, "title": "Plan Organic Matter Maintenance", "desc": "Because straw was removed ex-situ, plan to incorporate green manure (dhaincha) or FYM in the next rotation to maintain soil organic carbon."},
        ],
    },
    "on_farm_composting": {
        "method_id": "on_farm_composting",
        "name": "On-Farm Pit / Windrow Composting & Vermicomposting",
        "name_hi": "खेत पर खाद / वर्मीकम्पोस्ट निर्माण",
        "category": "on_farm",
        "machinery_needed": ["Residue Chopper", "Water Sprinkler / Hose", "Compost Pit"],
        "machinery_needed_hi": ["कुट्टी मशीन / चॉपर", "पानी का पंप", "कम्पोस्ट गड्ढा"],
        "estimated_cost_per_acre_min": 800,
        "estimated_cost_per_acre_max": 1800,
        "time_required": "45–60 days maturation",
        "time_required_hi": "45–60 दिन परिपक्वता समय",
        "soil_benefit": "Maximum (Generates rich organic compost)",
        "soil_benefit_hi": "सर्वोत्तम (समृद्ध जैविक खाद की प्राप्ति)",
        "environmental_benefit": "Maximum (Zero Emissions & Recycles Nutrients)",
        "environmental_benefit_hi": "सर्वोत्तम (शून्य प्रदूषण एवं पोषक तत्व संचय)",
        "economic_potential": "Saves ₹3,000–₹5,000 in commercial organic manure / FYM purchases",
        "economic_potential_hi": "₹3,000–₹5,000 मूल्य की जैविक खाद तैयार",
        "confidence": "High",
        "applicable_crops": ["rice", "wheat", "maize", "sugarcane", "cotton", "mustard", "soybean", "pulses", "other"],
        "explanation": "Collects crop residue into farm-side pits or surface windrows, layering with animal dung slurry, water, and microbial decomposing inoculants. Within 60–75 days, residue is converted into rich, weed-seed-free organic manure that can be returned to any farm plot.",
        "steps": [
            {"step_num": 1, "title": "Chop Residue into Short Lengths", "desc": "Chop collected straw or stalks into 5–10 cm lengths using a chaff cutter to accelerate microbial contact."},
            {"step_num": 2, "title": "Excavate Pit or Mark Surface Windrow", "desc": "Dig a pit (3m wide × 1.5m deep × length as needed) or prepare an elevated, well-drained surface windrow."},
            {"step_num": 3, "title": "Layering Residue with Dung Slurry", "desc": "Place a 20–30 cm layer of residue, followed by a 5–10 cm layer of fresh cow dung slurry (1:4 dung to water ratio) and garden topsoil."},
            {"step_num": 4, "title": "Inoculate with Trichoderma or Compost Starter", "desc": "Sprinkle Trichoderma viride or consortia culture across each layer to accelerate lignin degradation."},
            {"step_num": 5, "title": "Maintain 50–60% Moisture", "desc": "Sprinkle water periodically. Moisture is adequate when a handful of compost feels damp like a wrung-out sponge without dripping."},
            {"step_num": 6, "title": "Periodic Aeration & Turning (Day 21 & 42)", "desc": "Turn the pile at 3 weeks and 6 weeks to introduce oxygen and maintain aerobic thermophilic breakdown (55–65°C)."},
            {"step_num": 7, "title": "Check Maturity (Dark & Earthy Odor)", "desc": "Compost is mature when the pile cools down, shrinks by 40–50%, turns dark crumbly brown, and smells like fresh forest earth."},
            {"step_num": 8, "title": "Apply to Fields or Horticulture Beds", "desc": "Incorporate mature compost into vegetable plots or orchards at 2–3 tonnes per acre during land preparation."},
        ],
    },
    "treated_livestock_fodder": {
        "method_id": "treated_livestock_fodder",
        "name": "4% Urea-Ammoniated Fodder Treatment (Paddy Straw)",
        "name_hi": "4% यूरिया उपचारित पौष्टिक पशु चारा (पुआल)",
        "category": "livestock",
        "machinery_needed": ["Chaff Cutter", "Water Tank", "Plastic Tarpaulin"],
        "machinery_needed_hi": ["कुट्टी मशीन", "पानी की टंकी", "प्लास्टिक तिरपाल"],
        "estimated_cost_per_acre_min": 700,
        "estimated_cost_per_acre_max": 1400,
        "time_required": "21 days airtight fermentation",
        "time_required_hi": "21 दिन बंद हवा में उपचार",
        "soil_benefit": "Moderate (Returns dung/FYM to soil after animal digestion)",
        "soil_benefit_hi": "मध्यम (गोबर/खाद के रूप में खेत में वापसी)",
        "environmental_benefit": "High (Prevents burning & feeds dairy animals)",
        "environmental_benefit_hi": "उच्च (आग लगने से बचाव एवं चारे की बचत)",
        "economic_potential": "Transforms poor straw into nutritious fodder; saves green fodder and concentrate costs",
        "economic_potential_hi": "चारे की लागत में बचत व पशु दुग्ध वृद्धि",
        "confidence": "High",
        "applicable_crops": ["rice"],
        "explanation": "Developed by ICAR-NDRI (National Dairy Research Institute, Karnal). Raw paddy straw cannot be fed as primary feed due to silica and oxalates. Treating 100 kg chopped straw with 4 kg urea dissolved in 40 liters of water and sealing under a plastic sheet for 21 days breaks lignin-cellulose bonds, doubles crude protein (from 3.5% to 7.5%), and eliminates oxalates safely.",
        "steps": [
            {"step_num": 1, "title": "Chop Clean Dry Paddy Straw", "desc": "Chop mold-free dry paddy straw into 2–3 inch pieces using a chaff cutter."},
            {"step_num": 2, "title": "Prepare 4% Urea Solution", "desc": "Dissolve 4 kg fertilizer-grade urea thoroughly in 40 liters of clean water per 100 kg of straw."},
            {"step_num": 3, "title": "Spread & Spray Uniformly", "desc": "Spread 100 kg straw on a clean cemented floor or polythene sheet and sprinkle the 40L urea solution evenly while mixing thoroughly."},
            {"step_num": 4, "title": "Stack & Tramp Firmly", "desc": "Stack the sprayed straw in layers and tramp down firmly with clean boots to expel air pockets."},
            {"step_num": 5, "title": "Airtight Sealing with Tarpaulin", "desc": "Cover the entire stack with a thick polythene sheet and seal edges with soil or sandbags to make it completely airtight."},
            {"step_num": 6, "title": "Incubate for 21 Days", "desc": "Allow the stack to ferment for 21 days (28 days during cold winter months) as ammonia gas breaks down hard silica bonds."},
            {"step_num": 7, "title": "Aeration Before Feeding", "desc": "Uncover required daily quantity and spread in open shade for 15–20 minutes to allow excess free ammonia gas to evaporate."},
            {"step_num": 8, "title": "Feed Blended with Green Fodder", "desc": "Feed to adult ruminants mixed with green fodder and mineral mixture. (Note: Never feed to calves under 6 months)."},
        ],
    },
    "untreated_livestock_fodder": {
        "method_id": "untreated_livestock_fodder",
        "name": "Dry Livestock Fodder Harvesting (Bhusa / Turi)",
        "name_hi": "सूखा पशु चारा / तूड़ी निर्माण (भूसा)",
        "category": "livestock",
        "machinery_needed": ["Straw Reaper / Thresher", "Tractor-Trolley"],
        "machinery_needed_hi": ["स्ट्रॉ रीपर", "ट्रैक्टर-ट्रॉली"],
        "estimated_cost_per_acre_min": 1500,
        "estimated_cost_per_acre_max": 2400,
        "time_required": "2–4 hours per acre",
        "time_required_hi": "2–4 घंटे प्रति एकड़",
        "soil_benefit": "Moderate (Leaves root stubble; provides organic manure via livestock)",
        "soil_benefit_hi": "मध्यम (पशुओं द्वारा गोबर खाद की प्राप्ति)",
        "environmental_benefit": "High (Zero Smoke & Essential Dairy Nutrition)",
        "environmental_benefit_hi": "उच्च (धुआं रहित एवं दुग्ध पशुओं का आहार)",
        "economic_potential": "High market value: Bhusa sells for ₹5,000–₹9,000/tonne in dairy belts",
        "economic_potential_hi": "उच्च बाजार भाव: ₹5,000–₹9,000/टन तक तूड़ी का भाव",
        "confidence": "High",
        "applicable_crops": ["wheat", "maize", "pulses", "soybean"],
        "explanation": "Wheat straw, maize stover, and pulse chaff are nutritious dry roughages for cattle and buffaloes. Using a tractor-drawn straw reaper harvests stubble cleanly and grinds it into soft, digestible Bhusa stored for year-round animal maintenance.",
        "steps": [
            {"step_num": 1, "title": "Field Inspection After Grain Harvest", "desc": "Ensure the crop was harvested dry without rain soaking to prevent fungal mold or aflatoxin contamination."},
            {"step_num": 2, "title": "Deploy Tractor Straw Reaper", "desc": "Operate a straw reaper behind the tractor during daytime when stubble is dry and crisp."},
            {"step_num": 3, "title": "Blow Bhusa Directly into Mesh Trolley", "desc": "Use a closed wire-mesh tractor trolley attached behind the reaper to catch fine pulverized Bhusa without field loss."},
            {"step_num": 4, "title": "Transport to Dry Farm Store (Dhar)", "desc": "Transport to a rainproof, elevated storage shed or construct a traditional thatched Bhusa mound (Kup / Dhar)."},
            {"step_num": 5, "title": "Maintain Safe Storage", "desc": "Ensure the store is protected from moisture and rodent ingress."},
            {"step_num": 6, "title": "Daily Ration Mixing", "desc": "Mix required daily quantity with chopped green fodder, mustard cake/concentrates, and 50g mineral mixture per cow/buffalo."},
            {"step_num": 7, "title": "Field Ready for Next Crop", "desc": "Fields are immediately cleared for timely summer sowing (e.g. green gram / moong / dhaincha)."},
            {"step_num": 8, "title": "Recycle Manure to Field", "desc": "Return animal dung and farmyard manure to your fields to preserve soil organic carbon."},
        ],
    },
    "sugarcane_trash_mulch": {
        "method_id": "sugarcane_trash_mulch",
        "name": "Sugarcane Trash Ratoon Mulching & Shredding",
        "name_hi": "गन्ने के अवशेष (ट्रैश) की मल्चिंग एवं रतून प्रबंधन",
        "category": "in_situ",
        "machinery_needed": ["Trash Shredder / Cutter", "Furrow Opener"],
        "machinery_needed_hi": ["ट्रैश श्रेडर / कटर", "फरो ओपनर"],
        "estimated_cost_per_acre_min": 1400,
        "estimated_cost_per_acre_max": 2200,
        "time_required": "1 day per farm",
        "time_required_hi": "1 दिन प्रति खेत",
        "soil_benefit": "Very High (Conserves 25–30% irrigation water)",
        "soil_benefit_hi": "अत्यधिक लाभदायक (25–30% सिंचाई जल की बचत)",
        "environmental_benefit": "Maximum (Protects Ratoon Buds & Eliminates Toxic Cane Smoke)",
        "environmental_benefit_hi": "सर्वोत्तम (रतून की सुरक्षा एवं प्रदूषण रहित)",
        "economic_potential": "Saves ₹2,500/acre in weedicide, manual weeding, and 2 irrigations",
        "economic_potential_hi": "निराई-गुड़ाई एवं सिंचाई खर्च में भारी बचत",
        "confidence": "High",
        "applicable_crops": ["sugarcane"],
        "explanation": "Spreads sugarcane dry leaves in alternate inter-row spaces or shreds them with a tractor trash shredder. Trash mulch conserves soil moisture, lowers soil temperature during hot summer months, suppresses aggressive weeds, and enriches ratoon sugarcane.",
        "steps": [
            {"step_num": 1, "title": "Clear Trash from Stubble Rows", "desc": "Manually or mechanically pull dry cane leaves off the sugarcane stubble stools into the inter-row furrows so emerging ratoon shoots receive direct sunlight."},
            {"step_num": 2, "title": "Stubble Shaving & Off-barring", "desc": "Shave old cane stubble flush with the ground using a sharp stubble shaver to trigger deep, vigorous new tillers."},
            {"step_num": 3, "title": "Operate Tractor Trash Shredder", "desc": "Run a trash shredder along the furrows to chop dry leaves into small 5–10 cm pieces."},
            {"step_num": 4, "title": "Spread Mulch in Alternate Rows", "desc": "Distribute chopped trash uniformly as a 7–10 cm mulch blanket in inter-row spaces."},
            {"step_num": 5, "title": "Apply Basal Fertilizer Along Rows", "desc": "Place recommended ratoon nitrogen, phosphorus, and potassium fertilizer along the exposed cane rows."},
            {"step_num": 6, "title": "Inoculate with Trichoderma or Urea Spray", "desc": "Spray 10 kg urea and 1 kg Trichoderma per acre dissolved in 200L water over the mulch to accelerate decomposition."},
            {"step_num": 7, "title": "Irrigate Along Furrows", "desc": "Run irrigation water through the furrows. The trash blanket prevents evaporation and keeps soil cool."},
            {"step_num": 8, "title": "Observe Weed Suppression & Cane Vigour", "desc": "Enjoy strong ratoon growth with zero open-field burning damage."},
        ],
    },
    "cotton_stalk_shredding_incorporation": {
        "method_id": "cotton_stalk_shredding_incorporation",
        "name": "Mechanical Cotton Stalk Shredding & Soil Incorporation",
        "name_hi": "कपास के डंठल की कटाई व मिट्टी में मिलाना (श्रेडर / रोटावेटर)",
        "category": "in_situ",
        "machinery_needed": ["Cotton Stalk Slasher / Shredder", "Reversible MB Plough"],
        "machinery_needed_hi": ["कपास डंठल श्रेडर / स्लेशर", "एम.बी. प्लाऊ"],
        "estimated_cost_per_acre_min": 1800,
        "estimated_cost_per_acre_max": 2800,
        "time_required": "1–2 days per farm",
        "time_required_hi": "1–2 दिन प्रति खेत",
        "soil_benefit": "High (Destroys pink bollworm pupae & adds organic carbon)",
        "soil_benefit_hi": "उच्च (गुलाबी सुंडी के कीटों का नाश एवं जीवांश वृद्धि)",
        "environmental_benefit": "High (Eliminates intense woody smoke)",
        "environmental_benefit_hi": "उच्च (धुआं रहित पर्यावरण)",
        "economic_potential": "Adds organic matter; eliminates labor needed for manual uprooting",
        "economic_potential_hi": "डंठल उखाड़ने की मजदूरी में बचत",
        "confidence": "High",
        "applicable_crops": ["cotton"],
        "explanation": "Developed in collaboration with ICAR-CIRCOT. Heavy tractor-operated rotary slashers shred woody cotton stalks into fine chips in the field. Deep ploughing with a mouldboard plough buries the chips and exposes overwintering pink bollworm pupae to sunlight and predators without burning.",
        "steps": [
            {"step_num": 1, "title": "Terminate Crop Timely", "desc": "Conclude cotton picking by late December/January to break the lifecycle of pink bollworm."},
            {"step_num": 2, "title": "Operate Tractor Rotary Slasher", "desc": "Run a heavy-duty tractor slasher or stalk shredder directly over the standing cotton stalks to pulverize them into small chips."},
            {"step_num": 3, "title": "Deep Ploughing with Reversible MB Plough", "desc": "Perform deep ploughing (20–25 cm depth) with an MB plough to invert the soil, burying shredded stalks and bringing pest larvae to the surface."},
            {"step_num": 4, "title": "Allow Solarization for 3–5 Days", "desc": "Leave inverted soil exposed to sunlight so birds and heat destroy pest pupae naturally."},
            {"step_num": 5, "title": "Broadcast Urea / Decomposer", "desc": "Broadcast 15 kg urea per acre to supply microbial nitrogen for breaking down woody lignin."},
            {"step_num": 6, "title": "Planking & Watering", "desc": "Level with a planker and provide light irrigation to initiate decomposition."},
            {"step_num": 7, "title": "Rotary Tillage for Seedbed", "desc": "Run a rotavator after 10–14 days for a smooth, clod-free seedbed."},
            {"step_num": 8, "title": "Sow Next Rabi / Summer Crop", "desc": "Sow the succeeding wheat, mustard, or summer crop cleanly."},
        ],
    },
    "cotton_stalk_briquetting_industrial": {
        "method_id": "cotton_stalk_briquetting_industrial",
        "name": "Cotton Stalk Uprooting for Biomass Briquettes / Pellets",
        "name_hi": "कपास डंठल ब्रिकेट्स / छर्रे निर्माण (औद्योगिक उपयोग)",
        "category": "ex_situ",
        "machinery_needed": ["Tractor Stalk Puller / Chipper", "Trolley"],
        "machinery_needed_hi": ["डंठल पुलर / चिपर", "ट्रॉली"],
        "estimated_cost_per_acre_min": 1400,
        "estimated_cost_per_acre_max": 2200,
        "time_required": "1–2 days per farm",
        "time_required_hi": "1–2 दिन प्रति खेत",
        "soil_benefit": "Moderate (Leaves roots; clears field)",
        "soil_benefit_hi": "मध्यम (खेत तुरंत साफ)",
        "environmental_benefit": "High (Substitutes coal in industrial boilers, 4000 kcal/kg)",
        "environmental_benefit_hi": "उच्च (कोयले का स्वच्छ विकल्प, 4000 किलोकैलोरी)",
        "economic_potential": "Stalks fetch ₹1,500–₹2,200/tonne at local pelleting / brick kiln aggregators",
        "economic_potential_hi": "बायोमास उद्योग से संभावित आमदनी",
        "confidence": "Medium",
        "applicable_crops": ["cotton"],
        "explanation": "Cotton stalks possess an impressive gross calorific value of ~4,000 kcal/kg, comparable to high-grade coal. Stalks are uprooted, chipped, and sent to biomass briquette plants or industrial boilers, creating revenue for farmers while avoiding open burning.",
        "steps": [
            {"step_num": 1, "title": "Uproot Stalks with Tractor Puller", "desc": "Use a tractor-drawn mechanical stalk puller to remove cotton stalks along with main taproots."},
            {"step_num": 2, "title": "Field Bundling & Sun Drying", "desc": "Bundle stalks and leave them along field bunds for 3–5 days to dry below 15% moisture content."},
            {"step_num": 3, "title": "On-Farm Chipping (Optional)", "desc": "If an aggregator chipper is available, chip stalks into coarse fragments to reduce transportation volume by 60%."},
            {"step_num": 4, "title": "Transport to Aggregator / Briquetting Unit", "desc": "Load bundles or chips onto trolleys for delivery to local biomass pellet plants, plywood units, or brick kilns."},
            {"step_num": 5, "title": "Receive Biomass Payment", "desc": "Settle payment based on net weighed tonnage and moisture specification."},
            {"step_num": 6, "title": "Immediate Seedbed Preparation", "desc": "Fields are completely clear of woody debris for subsequent crop sowing."},
        ],
    },
}

# =====================================================================
# AREA UNIT CONVERSION HELPERS
# =====================================================================

def convert_to_acres(area: float, unit: str) -> float:
    """
    Normalizes any supported land unit to standard acres.
    1 Acre = 0.404686 Hectare = 1.613 Bigha (standard Northern India)
    1 Acre = 4046.86 sq meters = 43560 sq feet.
    """
    u = (unit or "acre").lower().strip()
    if u in ["acre", "acres", "एकड़"]:
        return area
    elif u in ["hectare", "hectares", "ha", "हेक्टेयर"]:
        return area * 2.47105
    elif u in ["bigha", "bighas", "बीघा"]:
        # Standard benchmark: 1 acre ~ 1.613 bigha (Punjab/Haryana/UP standard pucca bigha ~ 0.62 acre)
        return area * 0.62
    elif u in ["sq_m", "sqm", "square meter", "square meters", "वर्ग मीटर"]:
        return area * 0.000247105
    elif u in ["sq_ft", "sqft", "square feet", "square foot", "वर्ग फीट"]:
        return area * 0.0000229568
    return area

def convert_acres_to_hectares(acres: float) -> float:
    return acres * 0.404686

# =====================================================================
# RECOMMENDATION SCORING ENGINE
# =====================================================================

def compute_method_score(
    method_id: str,
    crop_key: str,
    crop_profile: Dict[str, Any],
    area_acres: float,
    farmer_goal: str,
    machinery_available: str,
    selected_machinery: List[str],
) -> int:
    """
    Calculates an objective score (0–100) for a residue management method
    based on agronomic suitability, farmer preferences, farm size, and machinery access.
    """
    method = RESIDUE_METHODS_CATALOG.get(method_id)
    if not method:
        return 0

    # Hard Filter: Crop applicability
    if crop_key not in method.get("applicable_crops", []):
        return 0

    # Base agronomic baseline
    score = 65

    # 1. Farmer Goal Alignment (+15 to +30 points)
    goal = (farmer_goal or "").lower().strip()
    if goal == "in_field" or goal == "manage it in the field":
        if method["category"] in ["in_situ", "biological"]:
            score += 25
        elif method["category"] == "ex_situ":
            score -= 20
    elif goal == "mulch" or goal == "use it as mulch":
        if method_id in ["in_situ_mulch_direct_seeding", "sugarcane_trash_mulch"]:
            score += 30
        elif method["category"] == "in_situ":
            score += 15
        else:
            score -= 15
    elif goal == "soil_incorporation" or goal == "incorporate it into soil":
        if method_id in ["in_situ_incorporation", "cotton_stalk_shredding_incorporation"]:
            score += 30
        elif method_id == "bio_decomposer_spray":
            score += 20
        elif method["category"] == "ex_situ":
            score -= 20
    elif goal == "compost" or goal == "compost it":
        if method_id == "on_farm_composting":
            score += 35
        elif method_id == "bio_decomposer_spray":
            score += 20
    elif goal == "biomass" or goal == "use/sell it as biomass":
        if method_id in ["ex_situ_baling", "cotton_stalk_briquetting_industrial"]:
            score += 35
        elif method["category"] == "ex_situ":
            score += 20
        else:
            score -= 10
    elif goal == "livestock" or goal == "use it for livestock/feed where appropriate":
        if method_id in ["untreated_livestock_fodder", "treated_livestock_fodder"]:
            score += 35
        else:
            score -= 15
    elif goal == "recommend_best" or "not sure" in goal:
        # Default intelligent weighting: prefer conservation agriculture
        if method_id in ["in_situ_mulch_direct_seeding", "sugarcane_trash_mulch", "cotton_stalk_shredding_incorporation"]:
            score += 15
        elif method_id in ["in_situ_incorporation", "untreated_livestock_fodder"]:
            score += 12

    # 2. Machinery Availability Matching (+10 to +20 points)
    mach_access = (machinery_available or "").lower().strip()
    available_mach_lower = [m.lower() for m in selected_machinery]

    if mach_access == "yes" and selected_machinery:
        method_mach_lower = [m.lower() for m in method.get("machinery_needed", [])]
        # Check overlap
        matched = False
        for req in method_mach_lower:
            for avail in available_mach_lower:
                if any(term in avail for term in req.split()) or any(term in req for term in avail.split()):
                    matched = True
                    break
            if matched:
                break
        if matched:
            score += 18
        else:
            # Farmer has machines, but maybe not specifically this one (can still custom hire)
            score += 5
    elif mach_access == "no":
        # Low-machinery methods get a boost; heavy specialized machines lose slight preference
        if method_id in ["on_farm_composting", "bio_decomposer_spray"]:
            score += 12
        elif method_id == "ex_situ_baling":
            score -= 10

    # 3. Farm Area Compatibility
    if area_acres < 2.0:
        # Smallholdings: Composting & mulching are very feasible; balers may have high mobilization fee
        if method_id in ["on_farm_composting", "bio_decomposer_spray"]:
            score += 8
        elif method_id == "ex_situ_baling":
            score -= 8
    elif area_acres >= 5.0:
        # Larger landholdings: High mechanization (Happy Seeder, Super Seeder, Baler) is optimal
        if method_id in ["in_situ_mulch_direct_seeding", "ex_situ_baling", "in_situ_incorporation"]:
            score += 10
        elif method_id == "on_farm_composting":
            # Very labor intensive to compost 20+ tonnes manually
            score -= 5

    # 4. Crop Specific Agronomic Logic
    if crop_key == "wheat" and method_id == "untreated_livestock_fodder":
        # Wheat Bhusa is universally valued and high demand
        score += 10
    if crop_key == "sugarcane" and method_id == "sugarcane_trash_mulch":
        # Top recommended practice by ICAR-IISR Lucknow
        score += 15
    if crop_key == "cotton" and method_id == "cotton_stalk_shredding_incorporation":
        # Top pest-management practice recommended by ICAR-CICR Nagpur
        score += 15

    # Cap score between 30 and 98
    return max(35, min(98, score))

# =====================================================================
# MAIN RESIDUE ANALYSIS SERVICE
# =====================================================================

def analyze_crop_residue(
    crop: str,
    area: float,
    area_unit: str = "acre",
    residue_quantity: Optional[float] = None,
    residue_quantity_source: Optional[str] = "estimated",
    farmer_goal: Optional[str] = "recommend_best",
    machinery_available: Optional[str] = "not_sure",
    machinery: Optional[List[str]] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    soil_type: Optional[str] = None,
    previous_crop: Optional[str] = None,
    current_crop: Optional[str] = None,
    farm_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Orchestrates the complete, bounded agronomic residue analysis.
    Returns structured data for the farmer-friendly MAITTRI frontend.
    """
    # 1. Normalize Crop Key
    c_raw = (crop or "rice").lower().strip()
    crop_key = "other"
    for key in CROP_RESIDUE_DATABASE.keys():
        if key in c_raw:
            crop_key = key
            break
    if "paddy" in c_raw:
        crop_key = "rice"
    elif "cane" in c_raw:
        crop_key = "sugarcane"
    elif "gram" in c_raw or "moong" in c_raw or "chana" in c_raw or "dal" in c_raw:
        crop_key = "pulses"

    profile = CROP_RESIDUE_DATABASE.get(crop_key, CROP_RESIDUE_DATABASE["other"])

    # 2. Normalize Area
    safe_area = max(0.1, float(area) if area else 1.0)
    norm_acres = convert_to_acres(safe_area, area_unit or "acre")
    norm_hectares = convert_acres_to_hectares(norm_acres)

    # 3. Residue Quantity Estimation or Farmer Override
    is_farmer_override = False
    if residue_quantity and float(residue_quantity) > 0:
        known_qty = float(residue_quantity)
        is_farmer_override = True
        est_tonnes_mid = round(known_qty, 2)
        est_tonnes_low = round(known_qty * 0.85, 2)
        est_tonnes_high = round(known_qty * 1.15, 2)
        estimate_confidence = "High (Farmer Provided Measurement)"
    else:
        est_tonnes_low = round(norm_acres * profile["low_t_per_acre"], 2)
        est_tonnes_mid = round(norm_acres * profile["mid_t_per_acre"], 2)
        est_tonnes_high = round(norm_acres * profile["high_t_per_acre"], 2)
        estimate_confidence = "Medium (Agronomic Benchmark Estimate)"

    # 4. Total Burning Destruction Impact (Nutrient & Environmental Losses)
    burn_rates = profile["burn_loss_per_tonne"]
    n_loss_kg = round(est_tonnes_mid * burn_rates["nitrogen_kg"], 1)
    p_loss_kg = round(est_tonnes_mid * burn_rates["phosphorus_kg"], 1)
    k_loss_kg = round(est_tonnes_mid * burn_rates["potassium_kg"], 1)
    s_loss_kg = round(est_tonnes_mid * burn_rates["sulfur_kg"], 1)
    c_loss_kg = round(est_tonnes_mid * burn_rates["organic_carbon_kg"], 1)
    co2_loss_kg = round(est_tonnes_mid * burn_rates["co2_emissions_kg"], 1)
    co_loss_kg = round(est_tonnes_mid * burn_rates["co_emissions_kg"], 1)
    pm_loss_kg = round(est_tonnes_mid * burn_rates["pm_emissions_kg"], 1)

    burning_warning = {
        "title": "🚫 DO NOT BURN CROP RESIDUE",
        "title_hi": "🚫 फसल अवशेष / पराली कभी न जलाएं",
        "farmer_message": (
            f"Open-field burning damages your topsoil biology, causes severe air pollution, and destroys "
            f"valuable organic biomass. If burned, your {safe_area} {area_unit} of {profile['crop_name']} "
            f"residue (~{est_tonnes_mid} tonnes) will destroy critical soil nutrients and organic carbon."
        ),
        "farmer_message_hi": (
            f"खेत में पराली जलाने से मिट्टी के मित्र कीट नष्ट होते हैं, धुआं व वायु प्रदूषण फैलता है और "
            f"कीमती जैविक खाद का नुकसान होता है। आपके {safe_area} {area_unit} {profile['crop_name_hi']} "
            f"के अवशेष (~{est_tonnes_mid} टन) जलाने से मिट्टी की भारी उर्वरता नष्ट हो जाएगी।"
        ),
        "soil_temperature_warning": "Soil surface temperatures exceed 400°C during burning, destroying beneficial rhizobia, mycorrhiza, and earthworms in the top 5 cm.",
        "nutrient_losses": {
            "nitrogen_kg": n_loss_kg,
            "phosphorus_kg": p_loss_kg,
            "potassium_kg": k_loss_kg,
            "sulfur_kg": s_loss_kg,
            "organic_carbon_kg": c_loss_kg,
        },
        "emissions_released": {
            "co2_tonnes": round(co2_loss_kg / 1000.0, 2),
            "co_kg": co_loss_kg,
            "particulate_matter_pm_kg": pm_loss_kg,
        },
        "scientific_source": "ICAR - Indian Agricultural Research Institute (IARI), New Delhi & PAU Ludhiana",
    }

    # 5. Evaluate and Rank Compatible Methods
    selected_mach = machinery or []
    candidate_methods: List[Dict[str, Any]] = []

    for method_id in profile.get("compatible_methods", []):
        method_spec = RESIDUE_METHODS_CATALOG.get(method_id)
        if not method_spec:
            continue

        score = compute_method_score(
            method_id=method_id,
            crop_key=crop_key,
            crop_profile=profile,
            area_acres=norm_acres,
            farmer_goal=farmer_goal or "recommend_best",
            machinery_available=machinery_available or "not_sure",
            selected_machinery=selected_mach,
        )

        cost_min_total = int(round(norm_acres * method_spec["estimated_cost_per_acre_min"]))
        cost_max_total = int(round(norm_acres * method_spec["estimated_cost_per_acre_max"]))

        # Build "Why Recommended" rationale
        reasons: List[str] = []
        reasons.append(f"Directly compatible with {profile['crop_name']} ({profile['residue_name']}).")
        if norm_acres >= 4.0:
            reasons.append("Economically feasible for medium to large farm holdings.")
        else:
            reasons.append("Manageable for small and marginal landholdings.")

        if method_id == "in_situ_mulch_direct_seeding":
            reasons.append("Permits zero-tillage direct sowing into standing stubble without losing turnaround time.")
            reasons.append("Conserves sub-surface moisture and suppresses seasonal weeds by 40–60%.")
        elif method_id == "bio_decomposer_spray":
            reasons.append("Very cost-effective biological breakdown converting residue into rich in-situ humus.")
        elif method_id == "ex_situ_baling":
            reasons.append("Clears the field immediately while supplying clean biomass to green energy facilities.")
        elif method_id == "on_farm_composting":
            reasons.append("Creates organic weed-free compost that reduces subsequent synthetic fertilizer dependency.")
        elif method_id == "treated_livestock_fodder":
            reasons.append("Urea ammoniation safely hydrolyzes tough silica bonds and doubles crude protein content.")
        elif method_id == "untreated_livestock_fodder":
            reasons.append("Harvests high-value nutritious dry Bhusa for dairy livestock.")
        elif method_id == "sugarcane_trash_mulch":
            reasons.append("Mulching inter-row furrows saves 25–30% irrigation water and preserves ratoon stools.")
        elif method_id == "cotton_stalk_shredding_incorporation":
            reasons.append("Mechanical shredding destroys pink bollworm pupae without open field burning.")

        method_card = {
            "method_id": method_id,
            "name": method_spec["name"],
            "name_hi": method_spec["name_hi"],
            "category": method_spec["category"],
            "score": score,
            "suitability": "Highly Recommended" if score >= 85 else ("Recommended" if score >= 70 else "Alternative Option"),
            "suitability_hi": "अत्यधिक अनुशंसित" if score >= 85 else ("अनुशंसित" if score >= 70 else "वैकल्पिक उपाय"),
            "estimated_cost_per_acre": f"₹{method_spec['estimated_cost_per_acre_min']:,} – ₹{method_spec['estimated_cost_per_acre_max']:,}",
            "estimated_total_cost": f"₹{cost_min_total:,} – ₹{cost_max_total:,}",
            "cost_disclaimer": "Cost varies by location and machinery rental rates.",
            "cost_disclaimer_hi": "लागत स्थान और मशीनरी किराए की दरों के अनुसार बदल सकती है।",
            "time_required": method_spec["time_required"],
            "time_required_hi": method_spec["time_required_hi"],
            "machinery_needed": method_spec["machinery_needed"],
            "machinery_needed_hi": method_spec["machinery_needed_hi"],
            "soil_benefit": method_spec["soil_benefit"],
            "soil_benefit_hi": method_spec["soil_benefit_hi"],
            "environmental_benefit": method_spec["environmental_benefit"],
            "environmental_benefit_hi": method_spec["environmental_benefit_hi"],
            "economic_potential": method_spec["economic_potential"],
            "economic_potential_hi": method_spec["economic_potential_hi"],
            "confidence": method_spec["confidence"],
            "explanation": method_spec["explanation"],
            "why_recommended": reasons,
            "steps": method_spec["steps"],
        }
        candidate_methods.append(method_card)

    # Sort candidate methods by score descending
    candidate_methods.sort(key=lambda m: m["score"], reverse=True)

    recommended_method = candidate_methods[0] if candidate_methods else None
    alternative_methods = candidate_methods[1:] if len(candidate_methods) > 1 else []

    # 6. Action Plan (Default to top recommended method, customizable by user)
    action_plan = {
        "method_name": recommended_method["name"] if recommended_method else "Recommended Residue Management",
        "method_name_hi": recommended_method["name_hi"] if recommended_method else "अनुशंसित पराली प्रबंधन",
        "steps": recommended_method["steps"] if recommended_method else [],
    }

    # 7. Weather Advisory Connection
    # Provide operational weather guidance (e.g. check dry conditions for baler or moisture for decomposer)
    weather_advisory = {
        "status": "available",
        "operational_advice": (
            "Field operational note: Ensure 2–3 sunny dry days if planning mechanical baling or dry straw harvesting. "
            "For bio-decomposer spray or soil incorporation, ensure light moisture is present or irrigate immediately."
        ),
        "operational_advice_hi": (
            "मौसम आधारित सलाह: यदि बेलिंग मशीन या सूखा भूसा बनाना हो तो 2–3 दिन खिली धूप आवश्यक है। "
            "बायो-डीकंपोज़र या मिट्टी में मिलाने के लिए खेत में हल्की नमी रखें अथवा तुरंत हल्की सिंचाई करें।"
        ),
    }

    # 8. Local Service Availability Note
    local_services = {
        "status": "info",
        "message": "Local custom hiring center (CHC) and bio-refinery aggregator listings can be mapped for your district.",
        "message_hi": "आपके जिले के लिए कस्टम हायरिंग सेंटर (CHC) और बायोमास एग्रीगेटर की जानकारी शीघ्र जोड़ी जा रही है।",
        "verified_centers_count": 0,
    }

    # 9. Response Object
    return {
        "crop": profile["crop_name"],
        "crop_hi": profile["crop_name_hi"],
        "residue_type": profile["residue_name"],
        "residue_type_hi": profile["residue_name_hi"],
        "crop_description": profile["description"],
        "livestock_warning": profile.get("livestock_warning"),
        "area": safe_area,
        "area_unit": area_unit,
        "area_normalized_acres": round(norm_acres, 2),
        "area_normalized_hectares": round(norm_hectares, 2),
        "estimated_residue_low": est_tonnes_low,
        "estimated_residue_mid": est_tonnes_mid,
        "estimated_residue_high": est_tonnes_high,
        "estimated_residue_unit": "tonnes",
        "is_farmer_override": is_farmer_override,
        "estimate_confidence": estimate_confidence,
        "burning_warning": burning_warning,
        "recommended_method": recommended_method,
        "alternative_methods": alternative_methods,
        "action_plan": action_plan,
        "weather_advisory": weather_advisory,
        "local_services": local_services,
        "scientific_citations": [
            {
                "organization": "ICAR - Indian Agricultural Research Institute (IARI)",
                "topic": "Crop Residue Management & Pusa Bio-decomposer",
                "reference": "IARI Agricultural Extension Bulletin No. 112 / Division of Microbiology",
            },
            {
                "organization": "Punjab Agricultural University (PAU), Ludhiana",
                "topic": "In-situ Stubble Management with Happy Seeder & Super Seeder",
                "reference": "Package of Practices for Rabi Crops, PAU Dept of Farm Machinery & Power Engineering",
            },
            {
                "organization": "ICAR - Central Research Institute for Dryland Agriculture (CRIDA)",
                "topic": "Conservation Agriculture & Residue Retention in Crop Sequences",
                "reference": "CRIDA Technical Report on Soil Organic Carbon & Climate Resilient Agriculture",
            },
            {
                "organization": "ICAR - National Dairy Research Institute (NDRI), Karnal",
                "topic": "Urea Ammoniation of Paddy Straw for Cattle Fodder",
                "reference": "NDRI Animal Nutrition Division Advisory on Crop Residue Feeding",
            },
        ],
        "limitations": [
            "Residue quantity is an agronomic estimate calculated from average residue-to-grain ratios. Actual field quantity varies with plant height, combine cutter-bar height, and grain yield.",
            "Machinery operational costs reflect prevailing custom hiring benchmarks and may fluctuate with local diesel rates and contractor availability.",
            "Crop residue recycling enriches soil organic matter over consecutive cycles; it complements but does not immediately replace balanced basal fertilizers. A certified laboratory soil test is recommended for precise field NPK requirements.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

def get_all_residue_methods() -> List[Dict[str, Any]]:
    """Returns catalog of all registered scientific management methods."""
    return list(RESIDUE_METHODS_CATALOG.values())

def get_supported_parali_crops() -> List[Dict[str, Any]]:
    """Returns list of crops supported by the residue management module."""
    crops_list = []
    for key, val in CROP_RESIDUE_DATABASE.items():
        crops_list.append({
            "key": key,
            "crop_name": val["crop_name"],
            "crop_name_hi": val["crop_name_hi"],
            "residue_name": val["residue_name"],
            "residue_name_hi": val["residue_name_hi"],
            "description": val["description"],
            "livestock_warning": val.get("livestock_warning"),
        })
    return crops_list
