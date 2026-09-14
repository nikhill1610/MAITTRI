// =============================================================
// MAITTRI UNIFIED INTERNATIONALIZATION CORE (i18n)
// "Farmer's Companion, Beginning of Prosperity"
// =============================================================

import enDict from "./en.js";
import hiDict from "./hi.js";

// Helper to flatten nested objects into dot-notated and flat keys
function flattenDictionary(obj, prefix = "", rootObj = null) {
  const root = rootObj || obj;
  const res = {};
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "object" && v !== null && !Array.isArray(v)) {
      Object.assign(res, flattenDictionary(v, key, root));
      // Also attach direct key if no conflict with root dictionary
      for (const [subK, subV] of Object.entries(v)) {
        if (typeof subV === "string" && !res[subK] && !(subK in root)) {
          res[subK] = subV;
        }
      }
    } else {
      res[key] = v;
      if (prefix) {
        // Also map leaf key directly for easy access if no conflict with root
        if (!res[k] && !(k in root)) res[k] = v;
      }
    }
  }
  return res;
}

const enFlat = flattenDictionary(enDict);
const hiFlat = flattenDictionary(hiDict);

// Legacy T object for backward compatibility across existing components
export const T = {
  en: { ...enFlat, ...enDict },
  hi: { ...hiFlat, ...hiDict }
};

/**
 * Universal translation resolver
 * Usage:
 *   t("dashboard.whatShouldIDoToday")
 *   t("common.save")
 *   t("save")
 */
export function t(key, fallback = "", lang = "en") {
  if (!key) return fallback || "";
  const rawDict = lang === "hi" ? hiDict : enDict;

  // 1. Direct top-level match in raw dictionary
  if (rawDict && typeof rawDict[key] === "string") return rawDict[key];

  // 2. Flattened dot-path or unique flat key
  const dict = lang === "hi" ? hiFlat : enFlat;
  if (dict[key] != null && typeof dict[key] === "string") return dict[key];

  // 3. Try dot-path traversal on nested dictionary
  const parts = key.split(".");
  let cur = rawDict;
  for (const part of parts) {
    if (cur && typeof cur === "object" && part in cur) {
      cur = cur[part];
    } else {
      cur = null;
      break;
    }
  }
  if (typeof cur === "string") return cur;

  // 4. Fallback to English if Hindi key is missing
  if (lang === "hi") {
    if (typeof enDict[key] === "string") return enDict[key];
    if (enFlat[key] != null && typeof enFlat[key] === "string") return enFlat[key];
  }

  return fallback || key;
}

// -------------------------------------------------------------
// DOMAIN-SPECIFIC TRANSLATION DICTIONARIES & UTILITIES
// -------------------------------------------------------------

export const CROP_TRANSLATIONS = {
  Wheat: { en: "Wheat", hi: "गेहूं" },
  Mustard: { en: "Mustard", hi: "सरसों" },
  Rice: { en: "Rice", hi: "धान / चावल" },
  Maize: { en: "Maize", hi: "मक्का" },
  Potato: { en: "Potato", hi: "आलू" },
  Tomato: { en: "Tomato", hi: "टमाटर" },
  "Gram/Chickpea": { en: "Gram / Chickpea", hi: "चना" },
  Gram: { en: "Gram", hi: "चना" },
  Cotton: { en: "Cotton", hi: "कपास" },
  Sugarcane: { en: "Sugarcane", hi: "गन्ना" },
  Soybean: { en: "Soybean", hi: "सोयाबीन" },
  Onion: { en: "Onion", hi: "प्याज" },
  Groundnut: { en: "Groundnut", hi: "मूंगफली" },
  "Pigeon Pea": { en: "Pigeon Pea", hi: "अरहर / तूर" },
  Lentil: { en: "Lentil", hi: "मसूर" }
};

export const SOIL_TRANSLATIONS = {
  "Alluvial Soil": { en: "Alluvial Soil", hi: "जलोढ़ मिट्टी" },
  "Alluvial soil": { en: "Alluvial Soil", hi: "जलोढ़ मिट्टी" },
  "Black Soil": { en: "Black Soil", hi: "काली मिट्टी" },
  "Black soil": { en: "Black Soil", hi: "काली मिट्टी" },
  "Red Soil": { en: "Red Soil", hi: "लाल मिट्टी" },
  "Red soil": { en: "Red Soil", hi: "लाल मिट्टी" },
  "Laterite Soil": { en: "Laterite Soil", hi: "लैटेराइट मिट्टी" },
  "Laterite soil": { en: "Laterite Soil", hi: "लैटेराइट मिट्टी" },
  "Desert/Arid Soil": { en: "Desert / Arid Soil", hi: "मरुस्थलीय / रेतीली मिट्टी" },
  "Mountain/Forest Soil": { en: "Mountain / Forest Soil", hi: "पर्वतीय / वन मिट्टी" },
  "Saline/Alkaline Soil": { en: "Saline / Alkaline Soil", hi: "लवणीय / क्षारीय मिट्टी" },
  "Loamy Soil": { en: "Loamy Soil", hi: "दोमट मिट्टी" },
  "Loamy soil": { en: "Loamy Soil", hi: "दोमट मिट्टी" },
  "Sandy Soil": { en: "Sandy Soil", hi: "बलुई मिट्टी" },
  "Sandy soil": { en: "Sandy Soil", hi: "बलुई मिट्टी" },
  "Clayey Soil": { en: "Clayey Soil", hi: "चिकनी मिट्टी" },
  "Clay soil": { en: "Clay Soil", hi: "चिकनी मिट्टी" },
  "Sandy Loam": { en: "Sandy Loam", hi: "बलुई दोमट" },
  "Sandy loam": { en: "Sandy Loam", hi: "बलुई दोमट" },
  "Clay Loam": { en: "Clay Loam", hi: "चिकनी दोमट" },
  "Clay loam": { en: "Clay Loam", hi: "चिकनी दोमट" },
  "Silty Soil": { en: "Silty Soil", hi: "गाद युक्त मिट्टी" },
  "Silty soil": { en: "Silty Soil", hi: "गाद युक्त मिट्टी" },
  Other: { en: "Other", hi: "अन्य" }
};

export const SEASON_TRANSLATIONS = {
  rabi: { en: "Rabi (Winter)", hi: "रबी (सर्दियों की फसल)" },
  kharif: { en: "Kharif (Monsoon)", hi: "खरीफ (मानसून की फसल)" },
  zaid: { en: "Zaid (Summer)", hi: "जायद (गर्मी की फसल)" }
};

export const WATER_TRANSLATIONS = {
  low: { en: "Low water requirement", hi: "कम जल आवश्यकता" },
  medium: { en: "Medium water requirement", hi: "मध्यम जल आवश्यकता" },
  high: { en: "High water requirement", hi: "अधिक जल आवश्यकता" }
};

export const IRRIGATION_TRANSLATIONS = {
  available: { en: "Available", hi: "उपलब्ध" },
  limited: { en: "Limited", hi: "सीमित" },
  rainfed: { en: "Rainfed", hi: "वर्षा आधारित" },
  tubewell: { en: "Tubewell / Borewell", hi: "नलकूप / बोरवेल" },
  canal: { en: "Canal", hi: "नहर" },
  drip: { en: "Drip / Sprinkler", hi: "ड्रिप / फव्वारा" }
};

export const NUTRIENT_NAME_TRANSLATIONS = {
  Nitrogen: { en: "Nitrogen (N)", hi: "नाइट्रोजन" },
  N: { en: "Nitrogen (N)", hi: "नाइट्रोजन" },
  Phosphorus: { en: "Phosphorus (P)", hi: "फास्फोरस" },
  P: { en: "Phosphorus (P)", hi: "फास्फोरस" },
  Potassium: { en: "Potassium (K)", hi: "पोटैशियम" },
  K: { en: "Potassium (K)", hi: "पोटैशियम" },
  Sulfur: { en: "Sulfur (S)", hi: "सल्फर (गंधक)" },
  S: { en: "Sulfur (S)", hi: "सल्फर (गंधक)" },
  Calcium: { en: "Calcium (Ca)", hi: "कैल्शियम" },
  Ca: { en: "Calcium (Ca)", hi: "कैल्शियम" },
  Magnesium: { en: "Magnesium (Mg)", hi: "मैग्नीशियम" },
  Mg: { en: "Magnesium (Mg)", hi: "मैग्नीशियम" },
  Zinc: { en: "Zinc (Zn)", hi: "जिंक (जस्ता)" },
  Zn: { en: "Zinc (Zn)", hi: "जिंक (जस्ता)" },
  Iron: { en: "Iron (Fe)", hi: "आयरन (लोहा)" },
  Fe: { en: "Iron (Fe)", hi: "आयरन (लोहा)" },
  Boron: { en: "Boron (B)", hi: "बोरॉन" },
  B: { en: "Boron (B)", hi: "बोरॉन" },
  Manganese: { en: "Manganese (Mn)", hi: "मैंगनीज" },
  Mn: { en: "Manganese (Mn)", hi: "मैंगनीज" },
  Copper: { en: "Copper (Cu)", hi: "कॉपर (तांबा)" },
  Cu: { en: "Copper (Cu)", hi: "कॉपर (तांबा)" }
};

export const NUTRIENT_STATUS_TRANSLATIONS = {
  "Likely depleted": { en: "Likely Depleted", hi: "संभावित रूप से कम" },
  "Possibly depleted": { en: "Possibly Depleted", hi: "हल्की कमी संभव" },
  "Likely adequate": { en: "Likely Adequate", hi: "पर्याप्त उपलब्ध" },
  "Unknown / requires soil test": { en: "Requires Soil Test", hi: "मिट्टी परीक्षण आवश्यक" },
  low: { en: "Low", hi: "कम" },
  adequate: { en: "Adequate", hi: "पर्याप्त" },
  high: { en: "High", hi: "अधिक" },
  unknown: { en: "Requires Test", hi: "परीक्षण आवश्यक" }
};

export const CONFIDENCE_TRANSLATIONS = {
  High: { en: "High Confidence", hi: "उच्च विश्वसनीयता" },
  Medium: { en: "Medium Confidence", hi: "मध्यम विश्वसनीयता" },
  Low: { en: "Normal Confidence", hi: "सामान्य विश्वसनीयता" },
  HIGH: { en: "High Confidence", hi: "उच्च विश्वसनीयता" },
  MEDIUM: { en: "Medium Confidence", hi: "मध्यम विश्वसनीयता" },
  LOW: { en: "Normal Confidence", hi: "सामान्य विश्वसनीयता" }
};

export const REASON_TRANSLATIONS = {
  "Suitable for the selected season.": "चयनित सीजन/मौसम के लिए अत्यधिक उपयुक्त फसल है।",
  "Season suitability is weaker.": "वर्तमान मौसम के लिए फसल की अनुकूलता कम है।",
  "Soil type is compatible.": "खेत की मिट्टी का प्रकार इस फसल के विकास के लिए पूर्णतः अनुकूल है।",
  "Soil compatibility is less favorable.": "मिट्टी की अनुकूलता इस फसल के लिए मध्यम स्तर की है।",
  "High water requirement conflicts with limited irrigation.": "फसल की अधिक जल आवश्यकता सीमित सिंचाई व्यवस्था के साथ मेल नहीं खाती।",
  "Growing the same crop repeatedly may be less desirable for rotation.": "एक ही फसल को बार-बार उगाने से मिट्टी में पोषक तत्वों की कमी और कीटों का प्रकोप बढ़ सकता है।",
  "Nutrient correction may be needed before or during cultivation.": "बुवाई से पहले या फसल चक्र के दौरान पोषक तत्वों की पूर्ति आवश्यक हो सकती है।",
  "Lower estimated production cost in the demo model.": "इस फसल में शुरुआती उत्पादन लागत अपेक्षाकृत कम और किफायती है।"
};

export const STAGE_TRANSLATIONS = {
  "Before sowing": "बुवाई से पूर्व (खेत की तैयारी)",
  "Land preparation": "भूमि की तैयारी एवं जुताई",
  Sowing: "बुवाई एवं बीज उपचार",
  "Early growth": "प्रारंभिक बढ़वार एवं अंकुरण",
  "Vegetative growth": "वानस्पतिक वृद्धि एवं पोषण प्रबंधन",
  "Reproductive stage": "फूल आना एवं दाना भरना",
  "Flowering and grain formation": "फूल आना एवं दाना विकास",
  Harvest: "फसल कटाई एवं भंडारण",
  "Harvesting and post-harvest": "कटाई एवं सुरक्षित भंडारण"
};

export const ACTION_TRANSLATIONS = {
  "Prepare field according to soil condition": "मिट्टी की नमी व प्रकार के अनुसार खेत की 2-3 बार गहरी जुताई करें।",
  "Use quality seed/planting material": "प्रमाणित एवं रोगमुक्त उच्च गुणवत्ता वाले बीजों का ही उपयोग करें।",
  "Follow validated soil-test based nutrient plan": "मिट्टी परीक्षण कार्ड के अनुसार संतुलित मात्रा में खाद एवं उर्वरक डालें।",
  "Follow recommended sowing window": "मौसम के अनुसार अनुशंसित समय सीमा में ही बुवाई संपन्न करें।",
  "Maintain crop-specific spacing and seed rate": "कतार से कतार की उचित दूरी और सही बीज दर बनाए रखें।",
  "Monitor germination": "अंकुरण का निरीक्षण करें और आवश्यकतानुसार गैप-फिलिंग करें।",
  "Control weeds at the appropriate stage": "खरपतवारों का समय रहते निराई-गुड़ाई या सुरक्षित नियंत्रण करें।",
  "Irrigate according to crop and soil moisture": "मिट्टी में नमी की स्थिति और क्रांतिक अवस्थाओं के अनुसार सिंचाई करें।",
  "Monitor nutrients": "पत्तियों के रंग और बढ़वार के आधार पर पोषण स्थिति की निगरानी करें।",
  "Scout for pests and diseases": "नियमित रूप से कीट एवं रोगों के लक्षणों की जांच करते रहें।",
  "Follow weather-based precautions": "मौसम के पूर्वानुमान के अनुसार ही सिंचाई या कीटनाशक छिड़काव करें।",
  "Maintain appropriate moisture": "फूल आने और दाना भरते समय खेत में पर्याप्त नमी बनाए रखें।",
  "Monitor crop health frequently": "फसल के स्वास्थ्य और दाने के भराव की नियमित जांच करें।",
  "Harvest at crop-appropriate maturity": "जब फसल परिपक्व हो जाए और दाने कड़े हो जाएं तभी कटाई करें।",
  "Plan storage/transport to reduce losses": "दानों को अच्छी तरह सुखाकर सुरक्षित स्थान पर भंडारित करें।"
};

export const WEATHER_CONDITION_TRANSLATIONS = {
  "Clear Sky": "साफ आसमान",
  "Mainly Clear": "मुख्यतः साफ",
  "Partly Cloudy": "आंशिक रूप से बादल",
  Overcast: "घने बादल छाए रहेंगे",
  Fog: "कोहरा",
  "Depositing Rime Fog": "सघन कोहरा",
  "Light Drizzle": "हल्की बूंदाबांदी",
  "Moderate Drizzle": "मध्यम बूंदाबांदी",
  "Dense Drizzle": "तेज बूंदाबांदी",
  "Slight Rain": "हल्की बारिश",
  "Moderate Rain": "मध्यम बारिश",
  "Heavy Rain": "भारी बारिश",
  "Slight Snow": "हल्की बर्फबारी",
  "Moderate Snow": "मध्यम बर्फबारी",
  "Heavy Snow": "भारी बर्फबारी",
  "Slight Rain Showers": "हल्की बौछारें",
  "Moderate Rain Showers": "मध्यम बौछारें",
  "Violent Rain Showers": "तेज बारिश की बौछारें",
  Thunderstorm: "गरज के साथ बारिश",
  "Thunderstorm with Slight Hail": "गरज-चमक के साथ ओलावृष्टि",
  "Thunderstorm with Heavy Hail": "तेज ओलावृष्टि एवं आंधी"
};

export const ADVISORY_TRANSLATIONS = {
  Favorable: "अनुकूल",
  Unfavorable: "प्रतिकूल",
  Caution: "सावधानी",
  Low: "कम",
  Moderate: "मध्यम",
  High: "उच्च",
  Critical: "गंभीर",
  "Optimal Spraying Conditions": "छिड़काव के लिए आदर्श समय",
  "Unfavorable for Spraying (Rain Risk)": "छिड़काव के लिए प्रतिकूल (बारिश का जोखिम)",
  "High Wind Risk for Spraying": "छिड़काव के लिए प्रतिकूल (तेज हवा का खतरा)",
  "Rain Expected — Delay Irrigation": "बारिश की संभावना — सिंचाई स्थगित करें",
  "Irrigation Recommended": "सिंचाई की संस्तुति",
  "Soil Moisture Adequate": "मिट्टी में पर्याप्त नमी उपलब्ध",
  "Elevated Fungal / Blight Risk": "फफूंद / झुलसा रोग का बढ़ा हुआ जोखिम",
  "Low Disease Pressure": "रोग का कम जोखिम"
};

// -------------------------------------------------------------
// TRANSLATION HELPER FUNCTIONS
// -------------------------------------------------------------

export function translateCrop(cropName, lang = "en") {
  if (!cropName) return "";
  if (lang !== "hi") return cropName;
  const match = Object.keys(CROP_TRANSLATIONS).find(k => k.toLowerCase() === cropName.toLowerCase().trim());
  return match ? CROP_TRANSLATIONS[match].hi : cropName;
}

export function translateSoil(soilName, lang = "en") {
  if (!soilName) return "";
  if (lang !== "hi") return soilName;
  const match = Object.keys(SOIL_TRANSLATIONS).find(k => k.toLowerCase() === soilName.toLowerCase().trim());
  return match ? SOIL_TRANSLATIONS[match].hi : soilName;
}

export function translateSeason(seasonName, lang = "en") {
  if (!seasonName) return "";
  if (lang !== "hi") return seasonName;
  const clean = seasonName.toLowerCase().trim();
  return SEASON_TRANSLATIONS[clean]?.hi || seasonName;
}

export function translateWater(waterReq, lang = "en") {
  if (!waterReq) return "";
  if (lang !== "hi") return `${waterReq} water`;
  const clean = waterReq.toLowerCase().trim();
  return WATER_TRANSLATIONS[clean]?.hi || waterReq;
}

export function translateIrrigation(irrigation, lang = "en") {
  if (!irrigation) return "";
  if (lang !== "hi") return irrigation;
  const clean = irrigation.toLowerCase().trim();
  return IRRIGATION_TRANSLATIONS[clean]?.hi || irrigation;
}

export function translateNutrient(nutrientName, lang = "en") {
  if (!nutrientName) return "";
  if (lang !== "hi") return nutrientName;
  const clean = nutrientName.trim();
  return NUTRIENT_NAME_TRANSLATIONS[clean]?.hi || nutrientName;
}

export function translateNutrientStatus(status, lang = "en") {
  if (!status) return "";
  if (lang !== "hi") return status;
  return NUTRIENT_STATUS_TRANSLATIONS[status]?.hi || status;
}

export function translateConfidence(confidence, lang = "en") {
  if (!confidence) return "";
  if (lang !== "hi") return confidence;
  return CONFIDENCE_TRANSLATIONS[confidence]?.hi || confidence;
}

export function translateReason(reason, lang = "en") {
  if (!reason) return "";
  if (lang !== "hi") return reason;
  return REASON_TRANSLATIONS[reason] || reason;
}

export function translateStage(stage, lang = "en") {
  if (!stage) return "";
  if (lang !== "hi") return stage;
  return STAGE_TRANSLATIONS[stage] || stage;
}

export function translateAction(action, lang = "en") {
  if (!action) return "";
  if (lang !== "hi") return action;
  return ACTION_TRANSLATIONS[action] || action;
}

export function translateWeatherCondition(condition, lang = "en") {
  if (!condition) return "";
  if (lang !== "hi") return condition;
  return WEATHER_CONDITION_TRANSLATIONS[condition] || condition;
}

export function translateAdvisoryText(text, lang = "en") {
  if (!text) return "";
  if (lang !== "hi") return text;
  return ADVISORY_TRANSLATIONS[text] || text;
}

export default {
  T,
  t,
  translateCrop,
  translateSoil,
  translateSeason,
  translateWater,
  translateIrrigation,
  translateNutrient,
  translateNutrientStatus,
  translateConfidence,
  translateReason,
  translateStage,
  translateAction,
  translateWeatherCondition,
  translateAdvisoryText
};
