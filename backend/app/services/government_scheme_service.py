"""
Government Scheme Service for MAITTRI Platform
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Strict Guardrail:
- Sourced exclusively from official Government portals (PM-KISAN, PMFBY, PMKSY, SMAM, State Portals).
- No fabricated scheme names, subsidy amounts, deadlines, or claims.
- Strictly separates state-specific schemes: UP schemes appear only for UP; Punjab only for Punjab, etc.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

# Curated, authoritative list of Indian Agricultural Schemes
VERIFIED_SCHEMES: List[Dict[str, Any]] = [
    # =========================================================================
    # CENTRAL GOVERNMENT SCHEMES (PAN-INDIA)
    # =========================================================================
    {
        "id": 1,
        "scheme_name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "level": "central",
        "state": None,
        "department": "Ministry of Agriculture & Farmers Welfare, GoI",
        "category": "Financial Support",
        "scheme_type": "direct_benefit",
        "description": "Central Sector Scheme providing income support of ₹6,000 per year in three equal installments of ₹2,000 every four months to all landholding farmer families.",
        "benefits": {
            "financial": "₹6,000 per year transferred directly into Aadhaar-linked bank accounts (DBT).",
            "installments": "3 installments of ₹2,000 each (April-July, August-November, December-March).",
            "type": "Direct Income Transfer"
        },
        "eligibility_criteria": {
            "landholding": "All landholding farmer families having cultivable land registered in their name.",
            "exclusions": "Institutional landholders, constitutional post holders, serving/retired government employees, pensioners receiving ₹10,000+/month, professionals, income tax payers.",
            "mandatory_kyc": "Aadhaar e-KYC and land seeding are mandatory on the portal."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All (Marginal, Small, Medium, Large)",
        "application_start": "Continuous Open",
        "application_end": "Continuous Open",
        "status": "Open",
        "official_source": "Department of Agriculture & Farmers Welfare, GoI",
        "official_url": "https://pmkisan.gov.in/",
        "documents": [
            "Aadhaar Card (Mandatory)",
            "Land Ownership Records (Khasra/Khatauni/ROR)",
            "Aadhaar-seeded Bank Account Passbook",
            "Mobile Number linked with Aadhaar"
        ],
        "helpline": "155261 / 011-24300606 (Toll Free: 1800-115-526)",
        "last_verified": "01/08/2026",
        "maittri_explains": "यह योजना किसानों को बीज, खाद और आकस्मिक कृषि खर्चों के लिए साल में ₹6,000 की सीधी आर्थिक सहायता देती है। यदि आपके नाम पर खेती योग्य ज़मीन दर्ज है, तो आप इसका लाभ ले सकते हैं।"
    },
    {
        "id": 2,
        "scheme_name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "level": "central",
        "state": None,
        "department": "Ministry of Agriculture & Farmers Welfare, GoI",
        "category": "Crop Insurance",
        "scheme_type": "insurance",
        "description": "Comprehensive yield-based and localized crop insurance scheme protecting farmers against non-preventable natural risks from pre-sowing to post-harvest.",
        "benefits": {
            "coverage": "Prevented sowing/planting, mid-season adversity, standing crop yield loss, localized calamities (hail, landslide, inundation), post-harvest losses up to 14 days.",
            "premium_farmer": "Maximum 2% for Kharif foodgrains/oilseeds, 1.5% for Rabi foodgrains/oilseeds, 5% for Annual Commercial/Horticultural crops.",
            "subsidy": "Balance actuarial premium subsidized 50:50 by Central and State Governments."
        },
        "eligibility_criteria": {
            "notified_areas": "Farmers growing notified crops in notified insurance units/villages.",
            "farmer_type": "Both loanee and non-loanee, owner cultivators and tenant/sharecropper farmers."
        },
        "crop_applicability": "Notified Foodgrains, Oilseeds, and Annual Commercial/Horticultural Crops",
        "season": "Kharif & Rabi",
        "farm_size_rule": "All",
        "application_start": "Kharif: April 1 | Rabi: October 1",
        "application_end": "Kharif: July 31 | Rabi: December 31",
        "status": "Open",
        "official_source": "PMFBY Official Portal, GoI",
        "official_url": "https://pmfby.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Land Records (ROR / Khatauni) or Tenancy Agreement",
            "Sowing Certificate / Declaration from Revenue/Agri Officer or Self-declaration",
            "Bank Passbook (IFSC & Account details)"
        ],
        "helpline": "14447 (National Toll Free Kisan Call Center for Crop Insurance)",
        "last_verified": "01/08/2026",
        "maittri_explains": "सूखा, बाढ़, ओलावृष्टि या बेमौसम बारिश से फसल बर्बाद होने पर यह बीमा क्षतिपूर्ति देता है। किसान को केवल 1.5% से 2% प्रीमियम देना होता है, बाकी सरकार देती है।"
    },
    {
        "id": 3,
        "scheme_name": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY) - Per Drop More Crop",
        "level": "central",
        "state": None,
        "department": "Department of Agriculture & Farmers Welfare, GoI",
        "category": "Irrigation",
        "scheme_type": "subsidy",
        "description": "Focuses on enhancing water use efficiency at the farm level through micro-irrigation technologies (Drip and Sprinkler irrigation systems).",
        "benefits": {
            "subsidy_small_marginal": "Up to 55% financial assistance on indicative benchmark cost for Small & Marginal farmers.",
            "subsidy_other": "Up to 45% financial assistance for other landholder farmers.",
            "water_saving": "Saves 30% to 50% water and increases crop productivity by 20% to 40%."
        },
        "eligibility_criteria": {
            "landholding": "Farmers possessing cultivable land with an assured water source (borewell, open well, farm pond, or canal).",
            "priority": "Small and marginal farmers, SC/ST, and women farmers."
        },
        "crop_applicability": "Horticulture, Sugarcane, Cotton, Maize, Vegetables, Pulses, Oilseeds",
        "season": "All Seasons",
        "farm_size_rule": "All (Higher subsidy for Small/Marginal <= 2 ha)",
        "application_start": "Annual State Windows",
        "application_end": "Subject to District Allocation",
        "status": "Open",
        "official_source": "PMKSY Official Portal / State Horticulture Departments",
        "official_url": "https://pmksy.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Land Ownership Document (Khasra/Khatauni)",
            "Electricity connection bill or proof of water source",
            "Bank Account Passbook",
            "Field Map/Sketch"
        ],
        "helpline": "1800-180-1551 (Kisan Call Center)",
        "last_verified": "15/07/2026",
        "maittri_explains": "ड्रिप और स्प्रिंकलर (फव्वारा) सिंचाई प्रणाली लगाने के लिए सरकार 45% से 55% तक सब्सिडी देती है। इससे कम पानी में अधिक उपज मिलती है।"
    },
    {
        "id": 4,
        "scheme_name": "Sub-Mission on Agricultural Mechanization (SMAM)",
        "level": "central",
        "state": None,
        "department": "Ministry of Agriculture & Farmers Welfare, GoI",
        "category": "Machinery",
        "scheme_type": "subsidy",
        "description": "Promotes agricultural mechanization among small and marginal farmers and in regions with low farm power availability.",
        "benefits": {
            "individual_farmers": "40% to 50% financial assistance for purchasing tractors, power tillers, rotavators, seed drills, multi-crop threshers.",
            "custom_hiring_centers": "Up to 80% project cost assistance for establishing Custom Hiring Centers (CHCs) and Farm Machinery Banks (FMBs) by FPOs/Panchayats."
        },
        "eligibility_criteria": {
            "criteria": "Individual farmers with active land records. Priority given to SC/ST, women, and small/marginal farmers.",
            "limit": "One machinery type per farmer within a specified 3-5 year block."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "State Portal Notification Dependent",
        "application_end": "Quota Exhaustion Basis",
        "status": "Open",
        "official_source": "Direct Benefit Transfer in Agriculture Mechanization Portal",
        "official_url": "https://agrimachinery.nic.in/",
        "documents": [
            "Aadhaar Card",
            "Land Records (Khatauni)",
            "Bank Account Passbook",
            "Caste Certificate (if SC/ST subsidy claimed)",
            "Quotation from Authorized Equipment Dealer"
        ],
        "helpline": "011-23382937",
        "last_verified": "20/07/2026",
        "maittri_explains": "ट्रैक्टर, रोटावेटर, कल्टीवेटर या थ्रेशर जैसे कृषि यंत्र खरीदने पर 40% से 50% की सरकारी छूट मिलती है। आवेदन राज्य के डीबीटी पोर्टल से होता है।"
    },
    {
        "id": 5,
        "scheme_name": "PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan)",
        "level": "central",
        "state": None,
        "department": "Ministry of New and Renewable Energy (MNRE), GoI",
        "category": "Solar/Energy",
        "scheme_type": "subsidy",
        "description": "Provides clean energy solutions to farmers by subsidizing standalone solar agriculture pumps (Component B) and solarizing existing grid-connected agriculture pumps (Component C).",
        "benefits": {
            "subsidy_share": "Up to 60% capital subsidy (30% Central Government + 30% State Government).",
            "farmer_share": "Farmer pays 10% to 40% (remaining can be bank financed).",
            "pump_capacity": "Standalone DC/AC solar pumps from 3 HP to 10 HP."
        },
        "eligibility_criteria": {
            "water_source": "Farmers with agriculture land and dependable water source without electrical grid connection (Component B).",
            "grid_pumps": "Farmers with existing electric tube-wells (Component C)."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "State Energy Development Agency Windows",
        "application_end": "Open across State allocations",
        "status": "Open",
        "official_source": "Ministry of New and Renewable Energy, GoI",
        "official_url": "https://pmkusum.mnre.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Land Records (Jamabandi/Khasra/Khatauni)",
            "Bank Passbook",
            "Proof of Water Source / Self-declaration"
        ],
        "helpline": "1800-180-3333",
        "last_verified": "10/08/2026",
        "maittri_explains": "खेत में सौर ऊर्जा वाला सोलर पंप लगाने के लिए 60% तक सरकारी अनुदान मिलता है। इससे बिजली बिल और डीजल का खर्च पूरी तरह समाप्त हो जाता है।"
    },
    {
        "id": 6,
        "scheme_name": "Soil Health Card Scheme (SHC)",
        "level": "central",
        "state": None,
        "department": "Department of Agriculture & Farmers Welfare, GoI",
        "category": "Soil & Nutrient",
        "scheme_type": "advisory_and_testing",
        "description": "Provides printed soil health report cards to all farmers cyclically, analyzing 12 essential soil parameters with crop-wise nutrient recommendations.",
        "benefits": {
            "parameters_tested": "N, P, K (Macro), S (Secondary), Zn, Fe, Cu, Mn, Bo (Micro), and pH, EC, OC (Physical).",
            "cost_to_farmer": "100% Free of Cost laboratory testing and card issuance.",
            "advisory": "Scientific fertilizer dosing to prevent wasteful chemical over-application."
        },
        "eligibility_criteria": {
            "eligibility": "All landholding farmers in all villages across India."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous / Periodic Village Drives",
        "application_end": "Continuous",
        "status": "Open",
        "official_source": "Soil Health Card Portal, GoI",
        "official_url": "https://soilhealth.dac.gov.in/",
        "documents": [
            "Farmer Name, Mobile Number, Khasra Number",
            "Soil Sample collected by village agricultural assistant / KVK"
        ],
        "helpline": "011-24305591 / 1800-180-1551",
        "last_verified": "01/08/2026",
        "maittri_explains": "आपके खेत की मिट्टी की मुफ्त जांच करके 12 पोषक तत्वों का रिपोर्ट कार्ड दिया जाता है, जिससे पता चलता है कि कौन-सी खाद कितनी मात्रा में डालनी चाहिए।"
    },
    {
        "id": 7,
        "scheme_name": "Paramparagat Krishi Vikas Yojana (PKVY) / Organic Farming",
        "level": "central",
        "state": None,
        "department": "Ministry of Agriculture & Farmers Welfare, GoI",
        "category": "Organic/Natural Farming",
        "scheme_type": "subsidy",
        "description": "Sub-component of National Mission on Sustainable Agriculture promoting organic and natural farming through cluster approach and Participatory Guarantee System (PGS) certification.",
        "benefits": {
            "financial_assistance": "₹50,000 per hectare over 3 years.",
            "direct_inputs": "₹31,000/ha transferred directly to farmer for organic inputs (seeds, bio-fertilizers, vermicompost).",
            "certification": "Free PGS-India organic certification and packaging support."
        },
        "eligibility_criteria": {
            "cluster_formation": "Farmers willing to form clusters of 20 or more farmers covering 50 acres.",
            "commitment": "Commitment to zero synthetic fertilizer and pesticide use."
        },
        "crop_applicability": "All Crops, Millets, Pulses, Spices, Vegetables",
        "season": "All Seasons",
        "farm_size_rule": "All (Cluster based)",
        "application_start": "Through District Agriculture Office / Jaivik Kheti Portal",
        "application_end": "Annual Allocation Basis",
        "status": "Open",
        "official_source": "Jaivik Kheti Portal, GoI",
        "official_url": "https://www.jaivikkheti.in/",
        "documents": [
            "Aadhaar Card",
            "Land Records",
            "Bank Passbook",
            "Cluster Member Agreement"
        ],
        "helpline": "1800-180-1551",
        "last_verified": "12/08/2026",
        "maittri_explains": "जैविक और प्राकृतिक खेती अपनाने वाले किसानों के समूह को 3 साल में ₹50,000 प्रति हेक्टेयर की सहायता और मुफ्त जैविक प्रमाणीकरण दिया जाता है।"
    },
    {
        "id": 8,
        "scheme_name": "Kisan Credit Card (KCC)",
        "level": "central",
        "state": None,
        "department": "Department of Financial Services & MoA&FW, GoI",
        "category": "Credit/Finance",
        "scheme_type": "credit",
        "description": "Timely and affordable institutional credit for crop cultivation expenses, post-harvest expenses, produce marketing, and maintenance of farm assets.",
        "benefits": {
            "effective_interest": "4% per annum for prompt repayment on loans up to ₹3 Lakh (7% baseline with 3% prompt repayment subvention).",
            "collateral_free": "Collateral-free agricultural loan up to ₹1.60 Lakh.",
            "atm_enabled": "RuPay Kisan Card for easy ATM and POS withdrawals."
        },
        "eligibility_criteria": {
            "farmers": "Individual farmers, joint borrowers, tenant farmers, oral lessees, and sharecroppers.",
            "allied_activities": "Animal husbandry, dairy, and fisheries farmers are also eligible up to ₹2 Lakh."
        },
        "crop_applicability": "All Crops & Allied Sectors",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous Open",
        "application_end": "Continuous Open",
        "status": "Open",
        "official_source": "Reserve Bank of India / NABARD / Commercial Banks",
        "official_url": "https://www.nabard.org/",
        "documents": [
            "Duly filled KCC application form",
            "Aadhaar Card and PAN Card",
            "Land Records (Khasra/Khatauni) with crop details",
            "Passport size photos"
        ],
        "helpline": "1800-180-1551 / Contact Nearest Bank Branch",
        "last_verified": "01/08/2026",
        "maittri_explains": "खेती के खर्च, बीज, खाद और कीटनाशक के लिए केवल 4% के सस्ते ब्याज पर बैंक से किसान क्रेडिट कार्ड लोन मिलता है।"
    },
    {
        "id": 9,
        "scheme_name": "Agriculture Infrastructure Fund (AIF)",
        "level": "central",
        "state": None,
        "department": "Department of Agriculture & Farmers Welfare, GoI",
        "category": "Storage & Market",
        "scheme_type": "credit_linked_subsidy",
        "description": "Medium-long term debt financing facility for investment in viable projects for post-harvest management infrastructure and community farming assets.",
        "benefits": {
            "interest_subvention": "3% per annum interest subvention on loans up to ₹2 Crore for a maximum of 7 years.",
            "credit_guarantee": "Credit guarantee coverage under CGTMSE for loans up to ₹2 Crore.",
            "projects": "Warehouses, silos, cold storage, pack houses, assaying units, sorting and grading units."
        },
        "eligibility_criteria": {
            "beneficiaries": "Primary Agricultural Credit Societies (PACS), Marketing Cooperative Societies, FPOs, SHGs, Joint Liability Groups, and individual Agricultural Entrepreneurs."
        },
        "crop_applicability": "All Crops, Perishables, Grains",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous Online Portal",
        "application_end": "Operational through FY 2032-33",
        "status": "Open",
        "official_source": "Agriculture Infrastructure Fund Portal, GoI",
        "official_url": "https://agriinfra.dac.gov.in/",
        "documents": [
            "Detailed Project Report (DPR)",
            "Aadhaar and PAN Card",
            "Land Title / Lease Agreement for infrastructure site",
            "Bank Loan Sanction Letter"
        ],
        "helpline": "011-23382012",
        "last_verified": "05/08/2026",
        "maittri_explains": "गोदाम, कोल्ड स्टोरेज, ग्रेडिंग और पैकेजिंग यूनिट लगाने के लिए ₹2 करोड़ तक के बैंक लोन पर 3% ब्याज की सरकारी छूट मिलती है।"
    },
    {
        "id": 10,
        "scheme_name": "National Agriculture Market (e-NAM)",
        "level": "central",
        "state": None,
        "department": "Small Farmers Agri-Business Consortium (SFAC), MoA&FW, GoI",
        "category": "Storage & Market",
        "scheme_type": "market_linkage",
        "description": "Pan-India electronic trading portal networking physical APMC mandis to create a unified national market for agricultural commodities.",
        "benefits": {
            "transparent_price": "Real-time transparent online auction discovery without middleman collusion.",
            "direct_payment": "Online settlement directly into the farmer's bank account.",
            "free_assaying": "Quality testing and assaying labs available at integrated mandis."
        },
        "eligibility_criteria": {
            "traders_farmers": "Any farmer producing commodities traded in e-NAM integrated regulated wholesale markets."
        },
        "crop_applicability": "200+ Agricultural & Horticultural Commodities",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous Open",
        "application_end": "Continuous Open",
        "status": "Open",
        "official_source": "e-NAM Official Portal, GoI",
        "official_url": "https://enam.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Bank Passbook Details",
            "Mandi Registration Slip / Farmer Registration"
        ],
        "helpline": "1800-270-0224 (Toll Free)",
        "last_verified": "01/08/2026",
        "maittri_explains": "अपनी फसल को देश भर की 1,400 से अधिक मंडियों में ऑनलाइन बेचकर सबसे अच्छा भाव पाने की राष्ट्रीय व्यवस्था। भुगतान सीधे खाते में आता है।"
    },
    {
        "id": 11,
        "scheme_name": "Mission for Integrated Development of Horticulture (MIDH)",
        "level": "central",
        "state": None,
        "department": "Ministry of Agriculture & Farmers Welfare, GoI",
        "category": "Horticulture",
        "scheme_type": "subsidy",
        "description": "Centrally Sponsored Scheme for holistic growth of horticulture sector covering fruits, vegetables, root and tuber crops, mushrooms, spices, flowers, and aromatic plants.",
        "benefits": {
            "protected_cultivation": "Up to 50% subsidy on Polyhouses, Shade Net Houses, Plastic Mulching.",
            "orchards": "Assistance for establishing high-density orchards and rejuvenation of senile orchards.",
            "nursery": "Support for quality planting material and tissue culture labs."
        },
        "eligibility_criteria": {
            "farmers": "Farmers with cultivable land suitable for horticulture and assured irrigation."
        },
        "crop_applicability": "Fruits, Vegetables, Flowers, Spices, Medicinal Plants",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "State Horticulture Mission Notifications",
        "application_end": "Annual Quota Allocation",
        "status": "Open",
        "official_source": "MIDH Official Portal, GoI",
        "official_url": "https://midh.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Land Records (Khatauni)",
            "Bank Account Passbook",
            "Detailed estimate for polyhouse/orchard"
        ],
        "helpline": "011-23381012",
        "last_verified": "25/07/2026",
        "maittri_explains": "पॉलीहाउस, शेडनेट, बागवानी फसलें और फलदार पेड़ लगाने पर सरकार 50% तक अनुदान देती है।"
    },

    # =========================================================================
    # STATE-SPECIFIC GOVERNMENT SCHEMES
    # Strictly isolated by state: UP, Punjab, Maharashtra, Rajasthan, MP, Haryana, Bihar
    # =========================================================================

    # --- UTTAR PRADESH SCHEMES ---
    {
        "id": 101,
        "scheme_name": "UP Krishi Yantra Anudan Yojana (Agricultural Mechanization Portal)",
        "level": "state",
        "state": "Uttar Pradesh",
        "department": "Department of Agriculture, Government of Uttar Pradesh",
        "category": "Machinery",
        "scheme_type": "subsidy",
        "description": "State subsidy scheme in Uttar Pradesh providing financial assistance on purchase of agricultural implements like rotavators, power tillers, laser levellers, and seed drills through online token booking.",
        "benefits": {
            "subsidy": "40% to 50% subsidy on verified equipment list directly credited to bank account via DBT.",
            "token_system": "Transparent online token booking system on upagriculture portal."
        },
        "eligibility_criteria": {
            "residency": "Registered farmers of Uttar Pradesh holding valid farmer registration ID on upagriculture.com.",
            "token_deposit": "Mandatory security deposit token (refundable/adjustable on bill verification)."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Announced via Portal Periodic Tokens",
        "application_end": "Closing Soon (Current Token Window)",
        "status": "Closing Soon",
        "official_source": "UP Agriculture Department (Kisan Sahayata)",
        "official_url": "http://upagriculture.com/",
        "documents": [
            "UP Agriculture Farmer Registration ID",
            "Aadhaar Card",
            "Khatauni (Land Record)",
            "Bank Passbook",
            "GST Bill of authorized machinery dealer"
        ],
        "helpline": "0522-2204550 (Lucknow HQ)",
        "last_verified": "10/08/2026",
        "maittri_explains": "उत्तर प्रदेश के किसानों को कृषि यंत्र (रोटावेटर, लेजर लेवलर, रीपर आदि) पर 40-50% तक सीधी छूट मिलती है। इसके लिए upagriculture.com पर टोकन लेना होता है।"
    },
    {
        "id": 102,
        "scheme_name": "UP Mukhyamantri Laghu Sinchayee Yojana (Borewell Subsidy)",
        "level": "state",
        "state": "Uttar Pradesh",
        "department": "Minor Irrigation Department, Government of Uttar Pradesh",
        "category": "Irrigation",
        "scheme_type": "subsidy",
        "description": "Subsidy program for shallow, medium, and deep tubewells/borewells for small and marginal farmers in Uttar Pradesh.",
        "benefits": {
            "shallow_borewell": "Grant up to ₹10,000 for shallow tubewells.",
            "medium_deep": "Grant up to ₹75,000 to ₹1,00,000 for medium and deep tubewells for small/marginal farmers.",
            "pump_grant": "Additional grant for pump set purchase."
        },
        "eligibility_criteria": {
            "residency": "Permanent resident farmer of Uttar Pradesh.",
            "farm_size": "Small & Marginal farmers owning up to 2 hectares (5 acres) cultivable land.",
            "water_table": "Applicable in non-dark / safe groundwater assessment blocks."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "Marginal (<1 ha) & Small (1-2 ha)",
        "application_start": "May-June Annual Drive",
        "application_end": "Open through Block Minor Irrigation Office",
        "status": "Open",
        "official_source": "Minor Irrigation Department, UP",
        "official_url": "http://www.minirrigationup.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Khasra/Khatauni showing landholding <= 2 ha",
            "Caste Certificate (if SC/ST)",
            "Bank Passbook"
        ],
        "helpline": "0522-2286780",
        "last_verified": "05/08/2026",
        "maittri_explains": "उत्तर प्रदेश के छोटे और सीमांत किसानों को निजी नलकूप (बोरवेल) कराने के लिए ₹10,000 से ₹1,00,000 तक का सरकारी अनुदान दिया जाता है।"
    },
    {
        "id": 103,
        "scheme_name": "UP Certified Seed Subsidy (Beej Anudan Yojana)",
        "level": "state",
        "state": "Uttar Pradesh",
        "department": "Department of Agriculture, Government of Uttar Pradesh",
        "category": "Seeds & Inputs",
        "scheme_type": "subsidy",
        "description": "Provides certified and high-yielding variety (HYV) seeds of Wheat, Paddy, Mustard, and Pulses at 50% subsidized cost to UP farmers.",
        "benefits": {
            "subsidy_rate": "50% direct subsidy on certified seed bag cost via state seed stores.",
            "distribution": "Delivered through Government Block Agriculture Seed Stores (Kisan Seva Kendra)."
        },
        "eligibility_criteria": {
            "residency": "Registered farmer on UP Agriculture Portal.",
            "limit": "Max seed allocation based on verified land area up to 5 acres."
        },
        "crop_applicability": "Wheat, Rice, Mustard, Gram, Pea, Lentil",
        "season": "Kharif & Rabi",
        "farm_size_rule": "All",
        "application_start": "Rabi Season Distribution: October 15",
        "application_end": "December 15 (Or Stock Exhaustion)",
        "status": "Upcoming",
        "official_source": "UP Agriculture Department",
        "official_url": "http://upagriculture.com/",
        "documents": [
            "Farmer Registration Number (UP Agri)",
            "Aadhaar Card",
            "Khatauni"
        ],
        "helpline": "1800-180-1551",
        "last_verified": "01/08/2026",
        "maittri_explains": "उत्तर प्रदेश के राजकीय कृषि बीज भंडारों से गेहूं, धान और दलहन के प्रमाणित बीज 50% छूट पर मिलते हैं। रबी सीजन के लिए वितरण जल्द शुरू होगा।"
    },

    # --- PUNJAB SCHEMES ---
    {
        "id": 201,
        "scheme_name": "Punjab Crop Residue Management (CRM) Subsidy",
        "level": "state",
        "state": "Punjab",
        "department": "Department of Agriculture & Farmers Welfare, Government of Punjab",
        "category": "Machinery",
        "scheme_type": "subsidy",
        "description": "Special state subsidy in Punjab for in-situ crop residue management machinery (Super Seeder, Happy Seeder, Smart Seeder, Paddy Straw Chopper, Baler) to eliminate stubble burning.",
        "benefits": {
            "individual": "50% subsidy for individual farmers on approved residue machines.",
            "cooperative_chc": "Up to 80% subsidy for Primary Agricultural Cooperative Societies (PACS), Panchayats, and FPOs.",
            "target": "Zero stubble burning in Kharif paddy harvest."
        },
        "eligibility_criteria": {
            "state_farmer": "Paddy growing farmers in Punjab with valid land record verification on agrimachinerypb portal."
        },
        "crop_applicability": "Rice (Paddy Stubble Management)",
        "season": "Kharif to Rabi Transition",
        "farm_size_rule": "All",
        "application_start": "July 1",
        "application_end": "Closing Soon (Targeting Harvest Season)",
        "status": "Closing Soon",
        "official_source": "Department of Agriculture, Punjab",
        "official_url": "https://agrimachinerypb.com/",
        "documents": [
            "Aadhaar Card",
            "Fard / Jamabandi (Punjab Land Record)",
            "Bank Passbook",
            "Undertaking of not burning crop residue"
        ],
        "helpline": "0172-2970605",
        "last_verified": "15/08/2026",
        "maittri_explains": "पंजाब के किसानों को पराली प्रबंधन वाले कृषि यंत्रों (सुपर सीडर, हैप्पी सीडर, बेलर) पर 50% और समितियों को 80% तक की छूट दी जाती है।"
    },
    {
        "id": 202,
        "scheme_name": "Punjab Direct Seeded Rice (DSR) Incentive Scheme",
        "level": "state",
        "state": "Punjab",
        "department": "Department of Agriculture & Farmers Welfare, Government of Punjab",
        "category": "Crop Support",
        "scheme_type": "incentive",
        "description": "Financial cash incentive to encourage farmers to adopt Direct Seeding of Rice (Tar-Vattar DSR) technique instead of conventional puddled transplanting to save groundwater.",
        "benefits": {
            "cash_incentive": "₹1,500 per acre direct cash incentive transferred via DBT upon field satellite and physical verification.",
            "water_saving": "Saves up to 15-20% groundwater."
        },
        "eligibility_criteria": {
            "practice": "Farmers cultivating paddy through DSR verified by field agriculture officers."
        },
        "crop_applicability": "Rice / Paddy",
        "season": "Kharif",
        "farm_size_rule": "All",
        "application_start": "May 15",
        "application_end": "Closed for Current Kharif Sowing",
        "status": "Closed",
        "official_source": "Agri Department Punjab DSR Portal",
        "official_url": "https://agri.punjab.gov.in/",
        "documents": [
            "Aadhaar Card",
            "Land Jamabandi",
            "Aadhaar-linked Bank Account"
        ],
        "helpline": "1800-180-1551",
        "last_verified": "01/08/2026",
        "maittri_explains": "धान की सीधी बिजाई (DSR) करने वाले पंजाब के किसानों को ₹1,500 प्रति एकड़ की सीधी प्रोत्साहन राशि दी जाती है। इस सीजन का आवेदन पूरा हो चुका है।"
    },

    # --- MAHARASHTRA SCHEMES ---
    {
        "id": 301,
        "scheme_name": "Magel Tyala Shet Tale (Farm Pond Scheme Maharashtra)",
        "level": "state",
        "state": "Maharashtra",
        "department": "Department of Agriculture, Government of Maharashtra",
        "category": "Irrigation",
        "scheme_type": "subsidy",
        "description": "Flagship scheme in Maharashtra guaranteeing farm ponds to any farmer demanding water storage structure on cultivable land.",
        "benefits": {
            "financial_grant": "Subsidy up to ₹50,000 for excavation and ₹75,000 with plastic film lining.",
            "water_security": "Protective irrigation during dry spells for kharif and rabi crops."
        },
        "eligibility_criteria": {
            "residency": "Farmer possessing at least 0.60 hectare (1.5 acres) land in Maharashtra.",
            "priority": "Drought-prone suicide-affected and rainfed agrarian districts."
        },
        "crop_applicability": "Soybean, Cotton, Pulses, Sugarcane, Pomegranate, Grapes",
        "season": "All Seasons",
        "farm_size_rule": "Minimum 0.60 Hectare",
        "application_start": "Continuous on MahaDBT Portal",
        "application_end": "Continuous Open",
        "status": "Open",
        "official_source": "MahaDBT Shetkari Portal, Maharashtra",
        "official_url": "https://mahadbt.maharashtra.gov.in/",
        "documents": [
            "7/12 Extract (Saat Baara)",
            "8-A Land Record",
            "Aadhaar Card",
            "Bank Passbook",
            "Self-declaration"
        ],
        "helpline": "022-49150800",
        "last_verified": "10/08/2026",
        "maittri_explains": "महाराष्ट्र में खेत में शेततळे (खेत तालाब) बनाने के लिए ₹50,000 से ₹75,000 तक का सरकारी अनुदान महाडीबीटी पोर्टल पर सीधे मिलता है।"
    },
    {
        "id": 302,
        "scheme_name": "Dr. Babasaheb Ambedkar Krishi Swavalamban Yojana",
        "level": "state",
        "state": "Maharashtra",
        "department": "Agriculture Department, Government of Maharashtra",
        "category": "Irrigation",
        "scheme_type": "subsidy",
        "description": "Special financial assistance for Scheduled Caste (SC) and Neo-Buddhist farmers in Maharashtra for new wells, solar pumps, in-well borings, and micro-irrigation.",
        "benefits": {
            "new_well": "Up to ₹2,50,000 for digging a new well.",
            "drip_system": "Up to ₹50,000 for drip irrigation.",
            "solar_pump": "Up to ₹25,000 additional power connection support."
        },
        "eligibility_criteria": {
            "caste": "SC / Neo-Buddhist category farmer in Maharashtra.",
            "income": "Annual family income up to ₹1,50,000.",
            "landholding": "Land ownership between 0.20 ha to 6.00 ha."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "0.20 ha to 6 ha",
        "application_start": "Annual Portal Window",
        "application_end": "Open on MahaDBT",
        "status": "Open",
        "official_source": "MahaDBT Shetkari, Maharashtra",
        "official_url": "https://mahadbt.maharashtra.gov.in/",
        "documents": [
            "Caste Certificate",
            "Income Certificate (Tehsildar)",
            "7/12 and 8-A Extracts",
            "Aadhaar and Bank details"
        ],
        "helpline": "1800-120-8040",
        "last_verified": "05/08/2026",
        "maittri_explains": "महाराष्ट्र के अनुसूचित जाति के किसानों को नया कुआं खोदने के लिए ₹2.5 लाख और ड्रिप सिंचाई के लिए विशेष सहायता दी जाती है।"
    },

    # --- RAJASTHAN SCHEMES ---
    {
        "id": 401,
        "scheme_name": "Rajasthan Krishi Yantra Anudan (RajKisan Sathi)",
        "level": "state",
        "state": "Rajasthan",
        "department": "Department of Agriculture, Government of Rajasthan",
        "category": "Machinery",
        "scheme_type": "subsidy",
        "description": "Capital subsidy on approved farm implements (Rotavator, Thresher, Seed-cum-Fertilizer Drill, Ploughs) through the RajKisan Sathi single-window portal.",
        "benefits": {
            "subsidy_sc_st_women": "Up to 50% subsidy (maximum ₹50,000 depending on tool).",
            "subsidy_general": "Up to 40% subsidy for other farmers."
        },
        "eligibility_criteria": {
            "residency": "Farmer registered with Jan Aadhaar Card in Rajasthan.",
            "land_criteria": "Minimum cultivable land in the name of the applicant farmer."
        },
        "crop_applicability": "Mustard, Wheat, Bajra, Guar, Gram",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous via RajKisan",
        "application_end": "Open through RajKisan Sathi",
        "status": "Open",
        "official_source": "RajKisan Sathi Portal, Rajasthan",
        "official_url": "https://rajkisan.rajasthan.gov.in/",
        "documents": [
            "Jan Aadhaar Card (Mandatory)",
            "Jamabandi (Land Record not older than 6 months)",
            "Bank Account linked with Jan Aadhaar",
            "Quotation from registered dealer"
        ],
        "helpline": "0141-2927047 / 181",
        "last_verified": "08/08/2026",
        "maittri_explains": "राजस्थान के किसानों को रोटावेटर, थ्रेशर और सीड ड्रिल खरीदने पर 40% से 50% तक की छूट राजकिसान साथी पोर्टल के माध्यम से मिलती है।"
    },
    {
        "id": 402,
        "scheme_name": "Rajasthan Tarbandi Yojana (Crop Fence Subsidy)",
        "level": "state",
        "state": "Rajasthan",
        "department": "Department of Agriculture, Government of Rajasthan",
        "category": "Crop Support",
        "scheme_type": "subsidy",
        "description": "Financial assistance for barbed wire fencing (tarbandi) along field boundaries to protect standing crops from nilgai, stray cattle, and wild animals.",
        "benefits": {
            "subsidy": "Up to 50% of the cost or maximum ₹40,000 (up to ₹48,000 for small/marginal farmers) for 400 meters of fencing.",
            "group_fencing": "Group of farmers with 5+ hectares can apply jointly."
        },
        "eligibility_criteria": {
            "landholding": "Individual farmer owning at least 1.5 hectares cultivable land (or group of farmers with combined 5 ha).",
            "jan_aadhaar": "Must possess Jan Aadhaar Card."
        },
        "crop_applicability": "All Crops (Protection against crop damage)",
        "season": "All Seasons",
        "farm_size_rule": "Minimum 1.5 ha (individual)",
        "application_start": "RajKisan Annual Targets",
        "application_end": "Open on RajKisan Sathi",
        "status": "Open",
        "official_source": "RajKisan Sathi, Rajasthan",
        "official_url": "https://rajkisan.rajasthan.gov.in/",
        "documents": [
            "Jan Aadhaar Card",
            "Jamabandi (Revenue Record)",
            "Bank Passbook",
            "Map and Boundary declaration"
        ],
        "helpline": "0141-2227365",
        "last_verified": "05/08/2026",
        "maittri_explains": "नीलगाय और आवारा पशुओं से फसल बचाने के लिए खेत की तारबंदी (कांटेदार तार) पर सरकार 50% या ₹40,000 तक की सब्सिडी देती है।"
    },

    # --- MADHYA PRADESH SCHEMES ---
    {
        "id": 501,
        "scheme_name": "MP Mukhya Mantri Kisan Kalyan Yojana",
        "level": "state",
        "state": "Madhya Pradesh",
        "department": "Revenue & Agriculture Department, Government of Madhya Pradesh",
        "category": "Financial Support",
        "scheme_type": "direct_benefit",
        "description": "State income top-up in Madhya Pradesh providing ₹6,000 per year in two installments of ₹3,000 to all farmers registered under PM-KISAN (making total ₹12,000/yr).",
        "benefits": {
            "amount": "₹6,000 per year directly credited to the farmer's bank account.",
            "combined_benefit": "Combined with PM-KISAN ₹6,000, farmer receives total ₹12,000 per year."
        },
        "eligibility_criteria": {
            "prerequisite": "Farmer must be a permanent resident of MP and actively receiving PM-KISAN installments."
        },
        "crop_applicability": "All Crops",
        "season": "All Seasons",
        "farm_size_rule": "All",
        "application_start": "Continuous Open via Patwari / SAARA Portal",
        "application_end": "Continuous Open",
        "status": "Open",
        "official_source": "SAARA Portal, Government of Madhya Pradesh",
        "official_url": "https://saara.mp.gov.in/",
        "documents": [
            "PM-KISAN Registration ID",
            "Samagra ID (MP)",
            "Aadhaar Card",
            "Khasra Record"
        ],
        "helpline": "0755-2555564",
        "last_verified": "12/08/2026",
        "maittri_explains": "मध्य प्रदेश के किसानों को पीएम-किसान के ₹6,000 के अलावा राज्य सरकार अलग से ₹6,000 देती है, जिससे कुल ₹12,000 सालाना मदद मिलती है।"
    },

    # --- HARYANA SCHEMES ---
    {
        "id": 601,
        "scheme_name": "Haryana Mera Pani Meri Virasat Yojana",
        "level": "state",
        "state": "Haryana",
        "department": "Department of Agriculture & Farmers Welfare, Government of Haryana",
        "category": "Crop Support",
        "scheme_type": "incentive",
        "description": "Groundwater conservation incentive encouraging Haryana farmers to switch from high-water paddy to alternate crops like Maize, Cotton, Pulses, Millets, or Horticulture.",
        "benefits": {
            "incentive_amount": "₹7,000 per acre financial incentive transferred directly via DBT.",
            "seed_support": "Free or subsidized seeds of alternative crops like Hybrid Maize and Pulses."
        },
        "eligibility_criteria": {
            "residency": "Farmers registered on Meri Fasal Mera Byora (MFMB) portal in Haryana.",
            "condition": "Must replace paddy with non-paddy alternative crops in designated blocks."
        },
        "crop_applicability": "Maize, Cotton, Moong, Arhar, Vegetables instead of Paddy",
        "season": "Kharif",
        "farm_size_rule": "All",
        "application_start": "May 1",
        "application_end": "June 30 (Post-Sowing Verification Pending)",
        "status": "Closed",
        "official_source": "Meri Fasal Mera Byora Portal, Haryana",
        "official_url": "https://fasal.haryana.gov.in/",
        "documents": [
            "Parivar Pehchan Patra (PPP / Family ID)",
            "Meri Fasal Mera Byora (MFMB) Registration",
            "Aadhaar Card",
            "Bank Account"
        ],
        "helpline": "1800-180-2117",
        "last_verified": "01/08/2026",
        "maittri_explains": "हरियाणा में धान की जगह मक्का, कपास, दलहन या बागवानी लगाने वाले किसानों को ₹7,000 प्रति एकड़ की सीधी प्रोत्साहन राशि दी जाती है।"
    },

    # --- BIHAR SCHEMES ---
    {
        "id": 701,
        "scheme_name": "Bihar Rajya Fasal Sahayata Yojana (BRFSY)",
        "level": "state",
        "state": "Bihar",
        "department": "Cooperative Department, Government of Bihar",
        "category": "Crop Insurance",
        "scheme_type": "state_compensation",
        "description": "Zero-premium state-funded crop assistance scheme protecting Bihar farmers against natural yield losses in lieu of PMFBY.",
        "benefits": {
            "loss_up_to_20": "₹7,500 per hectare for crop yield loss up to 20%.",
            "loss_above_20": "₹10,000 per hectare for crop yield loss greater than 20% (up to 2 hectares).",
            "zero_cost": "Farmers pay ₹0 premium (entire cost borne by State Government)."
        },
        "eligibility_criteria": {
            "residency": "Resident farmers of Bihar (both landowning Ryot and Non-Ryot tenant farmers)."
        },
        "crop_applicability": "Paddy, Wheat, Maize, Gram, Mustard",
        "season": "Kharif & Rabi",
        "farm_size_rule": "Up to 2 Hectares per season",
        "application_start": "Kharif: June 1 | Rabi: November 15",
        "application_end": "Rabi Window: Dec 31 (Upcoming for Rabi)",
        "status": "Upcoming",
        "official_source": "Cooperative Department, Bihar (BRFSY Portal)",
        "official_url": "https://state.bihar.gov.in/cooperative/",
        "documents": [
            "Aadhaar Card",
            "Land Possession Certificate (LPC) or Revenue Receipt for Ryot",
            "Self-declaration verified by Ward Member / Mukhiya for Non-Ryot",
            "Bank Passbook"
        ],
        "helpline": "1800-1800-110",
        "last_verified": "05/08/2026",
        "maittri_explains": "बिहार में बिना किसी प्रीमियम के फसल क्षति पर ₹7,500 से ₹10,000 प्रति हेक्टेयर की सीधी सरकारी सहायता मिलती है। रबी फसलों के लिए रजिस्ट्रेशन जल्द खुलेगा।"
    }
]

ALL_CATEGORIES = [
    {"id": "all", "label": "All", "hindi": "सभी"},
    {"id": "crop_support", "label": "🌾 Crop Support", "hindi": "🌾 फसल सहायता"},
    {"id": "financial_support", "label": "💰 Financial Support", "hindi": "💰 आर्थिक सहायता"},
    {"id": "irrigation", "label": "💧 Irrigation", "hindi": "💧 सिंचाई"},
    {"id": "machinery", "label": "🚜 Machinery", "hindi": "🚜 कृषि यंत्र"},
    {"id": "seeds_inputs", "label": "🌱 Seeds & Inputs", "hindi": "🌱 बीज एवं खाद"},
    {"id": "soil_nutrient", "label": "🧪 Soil & Nutrient", "hindi": "🧪 मृदा एवं पोषण"},
    {"id": "organic_natural", "label": "🌿 Organic/Natural Farming", "hindi": "🌿 जैविक/प्राकृतिक खेती"},
    {"id": "crop_insurance", "label": "🛡️ Crop Insurance", "hindi": "🛡️ फसल बीमा"},
    {"id": "solar_energy", "label": "☀️ Solar/Energy", "hindi": "☀️ सोलर ऊर्जा"},
    {"id": "storage_market", "label": "🏪 Storage & Market", "hindi": "🏪 भंडारण एवं बाज़ार"},
    {"id": "horticulture", "label": "🍎 Horticulture", "hindi": "🍎 बागवानी"},
    {"id": "training", "label": "🎓 Training", "hindi": "🎓 प्रशिक्षण"},
    {"id": "credit_finance", "label": "🏦 Credit/Finance", "hindi": "🏦 ऋण एवं साख"},
    {"id": "other", "label": "Other", "hindi": "अन्य"}
]

SUPPORTED_STATES = [
    "Uttar Pradesh",
    "Punjab",
    "Maharashtra",
    "Rajasthan",
    "Madhya Pradesh",
    "Haryana",
    "Bihar",
    "Gujarat",
    "Karnataka",
    "Andhra Pradesh",
    "Tamil Nadu",
    "West Bengal",
    "Odisha"
]

def get_supported_states() -> List[str]:
    """Return all supported Indian states."""
    return sorted(SUPPORTED_STATES)

def get_scheme_categories() -> List[Dict[str, str]]:
    """Return verified scheme category definitions."""
    return ALL_CATEGORIES

def get_government_schemes(
    state: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    crop: Optional[str] = None,
    level: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve government schemes with strict isolation:
    - If `state` is provided (e.g. 'Uttar Pradesh'), returns Central schemes + UP schemes ONLY.
    - Never returns Punjab or Maharashtra state schemes when UP is selected.
    - If search is provided, filters across title, description, benefits, and category.
    """
    results = []
    norm_state = state.strip().lower() if state else None
    norm_cat = category.strip().lower() if category and category != "all" else None
    norm_status = status.strip().lower() if status and status != "all" else None
    norm_search = search.strip().lower() if search else None
    norm_crop = crop.strip().lower() if crop else None

    for s in VERIFIED_SCHEMES:
        # State isolation filter:
        # Central schemes (level == 'central' and state is None) are applicable to all states.
        # State schemes are ONLY included if they match the selected state.
        if norm_state:
            if s["level"] == "state":
                if not s["state"] or s["state"].strip().lower() != norm_state:
                    continue
        else:
            # If no state is specified, include Central schemes and all state schemes
            pass

        # Level filter (central or state)
        if level:
            if s["level"].lower() != level.strip().lower():
                continue

        # Category filter
        if norm_cat:
            cat_str = s["category"].lower().replace("&", "").replace("/", "").replace(" ", "_")
            if norm_cat not in cat_str and norm_cat not in s["category"].lower():
                match = False
                for c in ALL_CATEGORIES:
                    if c["id"] == norm_cat and c["label"].lower() in s["category"].lower():
                        match = True
                        break
                if not match:
                    continue

        # Status filter
        if norm_status:
            if s["status"].lower() != norm_status:
                continue

        # Crop filter
        if norm_crop:
            crop_app = s.get("crop_applicability", "").lower()
            if "all" not in crop_app and norm_crop not in crop_app:
                continue

        # Search filter
        if norm_search:
            benefits_str = " ".join(str(v) for v in s.get("benefits", {}).values())
            elig_str = " ".join(str(v) for v in s.get("eligibility_criteria", {}).values())
            docs_str = " ".join(s.get("documents", []))
            searchable_text = f"{s['scheme_name']} {s['description']} {s['category']} {s.get('department', '')} {s.get('maittri_explains', '')} {s.get('crop_applicability', '')} {benefits_str} {elig_str} {docs_str}".lower()
            stemmed_search = norm_search[:-1] if norm_search.endswith("s") and len(norm_search) > 3 else norm_search
            if norm_search not in searchable_text and stemmed_search not in searchable_text:
                continue

        results.append(s)

    return results

def get_upcoming_schemes(state: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve schemes with active deadlines or upcoming openings.
    Statuses: 'Open', 'Upcoming', 'Closing Soon'.
    """
    all_schemes = get_government_schemes(state=state)
    upcoming = [
        s for s in all_schemes
        if s["status"] in ["Upcoming", "Closing Soon", "Open"]
    ]
    # Sort by urgency: Closing Soon first, then Upcoming, then Open
    priority_map = {"Closing Soon": 1, "Upcoming": 2, "Open": 3}
    upcoming.sort(key=lambda x: priority_map.get(x["status"], 4))
    return upcoming

def get_scheme_by_id(scheme_id: int) -> Optional[Dict[str, Any]]:
    """Fetch single verified scheme by its unique identifier."""
    for s in VERIFIED_SCHEMES:
        if s["id"] == scheme_id:
            return s
    return None
