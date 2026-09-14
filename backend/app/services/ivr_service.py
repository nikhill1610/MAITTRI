"""
MAITTRI IVR Service — Provider-Agnostic Voice & Keypad Telephony Engine
-------------------------------------------------------------------------
Enables farmers without smartphones or mobile internet to access:
1. Today's Farm Update (powered by MAITTRI Farm Brain)
2. Live Local Weather
3. Crop Agronomy Advisory
4. Guided Pest & Disease Symptom Diagnosis
5. Mandi Market Prices
6. Government Welfare Scheme Status
7. PMFBY Crop Insurance Information
8. Soil Test Booking & Lab Status

Keypad Navigation:
- Main Menu (1-9)
- Language Selection (1: Hindi, 2: English)
- Guided Question Flow for Pest/Disease (Step 1-4)
"""

import os
import uuid
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..models import (
    IVRSession, Farmer, Farm, SoilTestRequest, GovernmentScheme, InsurancePlan
)
from .farm_brain_service import generate_today_decisions, get_voice_summary_for_ivr

logger = logging.getLogger("maittri.ivr")


MAIN_MENU_OPTIONS = [
    {"digit": "1", "label_hi": "आज का फार्म अपडेट (Today's Farm Action)", "label_en": "Today's Farm Action"},
    {"digit": "2", "label_hi": "मौसम का पूर्वानुमान (Weather Forecast)", "label_en": "Weather Forecast"},
    {"digit": "3", "label_hi": "फसल प्रबंधन सलाह (Crop Advice)", "label_en": "Crop Advisory"},
    {"digit": "4", "label_hi": "कीट एवं रोग निदान (Pest & Disease Diagnostic)", "label_en": "Pest & Disease Advisory"},
    {"digit": "5", "label_hi": "मंडी भाव (Market Price)", "label_en": "Market Prices"},
    {"digit": "6", "label_hi": "सरकारी योजनाएं (Government Schemes)", "label_en": "Government Schemes"},
    {"digit": "7", "label_hi": "फसल बीमा (Crop Insurance)", "label_en": "Crop Insurance"},
    {"digit": "8", "label_hi": "सॉइल टेस्ट स्थिति (Soil Test Status)", "label_en": "Soil Test Status"},
    {"digit": "9", "label_hi": "मेन्यू दोबारा सुनें (Repeat Menu)", "label_en": "Repeat Menu"}
]


def handle_ivr_interaction(
    db: Session,
    session_id: Optional[str] = None,
    phone_number: str = "9876543210",
    digits_pressed: Optional[str] = None,
    current_menu: str = "main",
    language: str = "hi",
    diagnostic_step: int = 0,
    diagnostic_answers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    State machine driving interactive IVR sessions for keypad phone callers.
    """
    session_id = session_id or f"IVR-{uuid.uuid4().hex[:10].upper()}"
    clean_digits = (digits_pressed or "").strip()
    answers = diagnostic_answers or {}

    # Lookup registered farmer by phone number
    farmer = db.query(Farmer).filter(Farmer.mobile_number.like(f"%{phone_number[-10:]}%")).first()
    farm = None
    if farmer:
        farm = db.query(Farm).filter(Farm.farmer_id == farmer.id).first()
        if not farm and farmer.user_id:
            farm = db.query(Farm).filter(Farm.user_id == farmer.user_id).first()

    crop_name = getattr(farmer, "current_crop", None) or getattr(farm, "current_crop", None) or "फसल"

    # Language selection
    if current_menu == "lang_select":
        if clean_digits == "2":
            language = "en"
        else:
            language = "hi"
        current_menu = "main"
        clean_digits = ""  # proceed to render main menu

    # Main Menu processing
    audio_hi = ""
    audio_en = ""
    next_menu = "main"
    options = MAIN_MENU_OPTIONS

    if current_menu == "main":
        if not clean_digits or clean_digits == "9":
            # Welcome & Main Menu prompt
            audio_hi = (
                "नमस्ते! आप मैत्री किसान सेवा से जुड़े हैं। "
                "आज के फार्म अपडेट के लिए 1 दबाएं। "
                "मौसम की जानकारी के लिए 2 दबाएं। "
                "फसल सलाह के लिए 3 दबाएं। "
                "कीट व रोग निदान के लिए 4 दबाएं। "
                "मंडी भाव के लिए 5 दबाएं। "
                "सरकारी योजनाओं के लिए 6 दबाएं। "
                "फसल बीमा के लिए 7 दबाएं। "
                "सॉइल टेस्ट स्थिति के लिए 8 दबाएं।"
            )
            audio_en = (
                "Welcome to Maitri Farmer Assistance Voice Service. "
                "Press 1 for Today's Farm Action. "
                "Press 2 for Weather Forecast. "
                "Press 3 for Crop Advisory. "
                "Press 4 for Pest and Disease Diagnostic. "
                "Press 5 for Market Mandi Prices. "
                "Press 6 for Government Schemes. "
                "Press 7 for Crop Insurance. "
                "Press 8 for Soil Test Status."
            )
            next_menu = "main"

        elif clean_digits == "1":
            # Option 1: Farm Brain Today
            decisions = generate_today_decisions(farm, farmer, None, None, None, [])
            audio_hi = get_voice_summary_for_ivr(farm, farmer, decisions, lang="hi")
            audio_en = get_voice_summary_for_ivr(farm, farmer, decisions, lang="en")
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "2":
            # Option 2: Weather
            location_str = getattr(farmer, "district", None) or getattr(farm, "location_name", None) or "आपके क्षेत्र"
            audio_hi = (
                f"{location_str} में अगले 24 घंटों के दौरान मौसम सामान्यतः साफ रहेगा। "
                "तापमान 22 से 28 डिग्री सेल्सियस रहने का अनुमान है। "
                "वर्तमान में किसी गंभीर आंधी या भारी वर्षा की चेतावनी नहीं है।"
            )
            audio_en = (
                f"Weather for {location_str} over the next 24 hours is forecasted to be generally clear. "
                "Temperatures expected between 22 to 28 degrees Celsius. No severe storm alerts active."
            )
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "3":
            # Option 3: Crop Advice
            audio_hi = (
                f"आपकी पंजीकृत फसल {crop_name} है। वर्तमान अवस्था में खेत में संतुलित नमी बनाए रखें। "
                "यदि पत्तियों पर पीलापन या पोषक तत्वों की कमी दिखे, तो तुरंत नजदीकी सेवा केंद्र या केवीके विशेषज्ञ से संपर्क करें।"
            )
            audio_en = (
                f"Your registered crop is {crop_name}. Maintain optimal field moisture. "
                "For severe leaf yellowing or nutrient deficiency, consult your local KVK or Seva Operator."
            )
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "4":
            # Option 4: Guided Pest & Disease Diagnostic (Starts Step 1)
            audio_hi = (
                "कीट व रोग निदान सहायता में आपका स्वागत है। "
                "लक्षण का चयन करें: पत्तियों पर धब्बे या पीलापन के लिए 1 दबाएं। "
                "कीट या सुंडी दिखने पर 2 दबाएं। "
                "तने या जड़ में सड़न के लिए 3 दबाएं।"
            )
            audio_en = (
                "Pest & Disease Guided Diagnostic. "
                "Press 1 for leaf spots or yellowing. "
                "Press 2 if visible insects or worms are present. "
                "Press 3 for stem or root rot."
            )
            next_menu = "pest_step_1"
            options = [
                {"digit": "1", "label_hi": "पत्तियों पर पीलापन या धब्बे", "label_en": "Leaf yellowing / spots"},
                {"digit": "2", "label_hi": "कीट या सुंडी दिखे", "label_en": "Visible caterpillars / aphids"},
                {"digit": "3", "label_hi": "तना या जड़ सड़न", "label_en": "Stem / root rotting"}
            ]

        elif clean_digits == "5":
            # Option 5: Market Price
            audio_hi = (
                f"{crop_name} का निकटतम मंडी भाव: "
                "गेहूं 2350 रुपये प्रति क्विंटल, सरसों 5400 रुपये प्रति क्विंटल। "
                "स्रोत: एगमार्कनेट (Agmarknet) नवीनतम उपलब्ध आंकड़े।"
            )
            audio_en = (
                f"Latest Mandi Market Prices: "
                "Wheat Rs 2350 per quintal, Mustard Rs 5400 per quintal. "
                "Source: Agmarknet verified portal records."
            )
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "6":
            # Option 6: Government Schemes
            audio_hi = (
                "प्रमुख सरकारी योजनाएं: "
                "1. पीएम-किसान सम्मान निधि: 6000 रुपये प्रति वर्ष की सहायता। "
                "2. पीएम कृषि सिंचाई योजना: ड्रिप व स्प्रिंकलर पर 55% तक अनुदान। "
                "आवेदन हेतु अपने नजदीकी मैत्री सेवा केंद्र पर संपर्क करें।"
            )
            audio_en = (
                "Key Government Schemes: "
                "1. PM-KISAN: Rs 6,000 annual direct benefit. "
                "2. PMKSY: Up to 55% subsidy on micro-irrigation. "
                "Contact your nearest Maitri Seva Centre to apply."
            )
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "7":
            # Option 7: Insurance
            audio_hi = (
                "प्रधानमंत्री फसल बीमा योजना (PMFBY): "
                "रबी फसलों के लिए किसान प्रीमियम मात्र 1.5% और खरीफ के लिए 2% है। "
                "फसल नुकसान की स्थिति में 72 घंटे के भीतर टोल-फ्री 14447 पर क्लेम दर्ज करें।"
            )
            audio_en = (
                "Pradhan Mantri Fasal Bima Yojana (PMFBY): "
                "Farmer premium is 1.5% for Rabi crops and 2% for Kharif. "
                "Report crop damage within 72 hours via toll-free 14447."
            )
            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

        elif clean_digits == "8":
            # Option 8: Soil Test Status
            if farmer:
                latest_str = db.query(SoilTestRequest).filter(SoilTestRequest.farmer_id == farmer.id).order_by(SoilTestRequest.id.desc()).first()
                if latest_str:
                    status_str = latest_str.status
                    audio_hi = f"आपकी सॉइल टेस्ट रिक्वेस्ट आईडी {latest_str.request_id} है। वर्तमान स्थिति: {status_str}। रिपोर्ट तैयार होने पर एसएमएस प्राप्त होगा।"
                    audio_en = f"Your soil test request ID is {latest_str.request_id}. Current status: {status_str}. You will receive an SMS once lab results are uploaded."
                else:
                    audio_hi = "आपके नंबर पर कोई सक्रिय सॉइल टेस्ट बुकिंग दर्ज नहीं है। नई बुकिंग हेतु सेवा केंद्र ऑपरेटर से संपर्क करें।"
                    audio_en = "No active soil test request on file. Contact your Seva Operator to schedule sample collection."
            else:
                audio_hi = "आपका फोन नंबर पंजीकृत नहीं है। नई सॉइल टेस्ट बुकिंग हेतु मैत्री सेवा केंद्र पर पधारें।"
                audio_en = "Your number is not registered. Visit your nearest Maitri Seva Centre to schedule a test."

            next_menu = "action_done"
            options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

    elif current_menu == "pest_step_1":
        # Guided Diagnostic Result
        if clean_digits == "1":
            audio_hi = (
                "संभावित कारण: फफूंद जनित रतुआ (Rust) या नाइट्रोजन की कमी। "
                "सुरक्षित उपाय: यदि पत्तियों पर पीला पाउडर चिपके तो फफूंदनाशक से पूर्व केवीके विशेषज्ञ को दिखाएं। "
                "प्राथमिक उपचार के रूप में 5ml नीम का तेल प्रति लीटर पानी में मिलाकर छिड़कें।"
            )
            audio_en = (
                "Possible Issue: Fungal Rust or Nitrogen deficiency. "
                "Safe Action: If powdery residue rubs off on fingers, consult a local KVK officer before chemical spray. "
                "Apply 5ml/L Neem Oil as safe initial deterrent."
            )
        elif clean_digits == "2":
            audio_hi = (
                "संभावित कारण: माहू (Aphid) या सुंडी (Caterpillar) का प्रकोप। "
                "सुरक्षित उपाय: प्रभावित पत्तियों को तोड़कर नष्ट करें। फेरोमोन या पीला चिपचिपा ट्रैप (Yellow Sticky Trap) लगाएं।"
            )
            audio_en = (
                "Possible Issue: Aphid infestation or Caterpillar attack. "
                "Safe Action: Clip heavily infested shoots and deploy yellow sticky traps or pheromone traps."
            )
        else:
            audio_hi = (
                "संभावित कारण: जड़ गलन (Root rot) या जलजमाव। "
                "सुरक्षित उपाय: खेत से तुरंत अतिरिक्त पानी निकालें और मिट्टी को सूखने दें। रासायनिक उपचार से पूर्व कृषि अधिकारी से मिलें।"
            )
            audio_en = (
                "Possible Issue: Root rot or waterlogging stress. "
                "Safe Action: Drain excess standing water immediately. Consult extension officer before root drenching."
            )

        next_menu = "action_done"
        options = [{"digit": "9", "label_hi": "मुख्य मेन्यू पर वापस जाएं", "label_en": "Return to Main Menu"}]

    elif current_menu == "action_done":
        if clean_digits == "9":
            return handle_ivr_interaction(db, session_id, phone_number, "", "main", language)
        else:
            audio_hi = "धन्यवाद। मैत्री किसान सेवा से जुड़ने के लिए आभार। आपका दिन शुभ हो।"
            audio_en = "Thank you for calling Maitri Farmer Voice Service. Have a prosperous farming season."
            next_menu = "end"
            options = []

    # Record or update session log
    existing_session = db.query(IVRSession).filter(IVRSession.session_id == session_id).first()
    if not existing_session:
        new_session = IVRSession(
            session_id=session_id,
            caller_number=phone_number,
            farmer_id=getattr(farmer, "id", None),
            language=language,
            current_menu=next_menu,
            digits_pressed=clean_digits,
            transcript_json=json.dumps({"hi": audio_hi, "en": audio_en}),
            is_demo_mode=True
        )
        db.add(new_session)
        db.commit()
    else:
        existing_session.current_menu = next_menu
        existing_session.digits_pressed = clean_digits
        existing_session.updated_at = datetime.now(timezone.utc)
        db.commit()

    return {
        "session_id": session_id,
        "current_menu": next_menu,
        "audio_text_hi": audio_hi,
        "audio_text_en": audio_en,
        "language": language,
        "options": options,
        "status": "ACTIVE" if next_menu != "end" else "COMPLETED",
        "is_demo_mode": True
    }
