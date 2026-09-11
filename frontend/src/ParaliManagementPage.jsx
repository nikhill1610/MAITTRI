import React, { useEffect, useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Wheat, Sprout, AlertTriangle, CheckCircle2, AlertCircle, HelpCircle,
  FlaskConical, ArrowRight, ArrowLeft, RefreshCw, ShieldAlert,
  MapPinned, Leaf, Calendar, Info, Tractor, Flame, Check, Sparkles,
  Layers, IndianRupee, Clock, ChevronRight, Wind, CloudSun, Printer
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";

const CROPS_CONFIG = [
  {
    key: "rice",
    name: "Rice / Paddy",
    nameHi: "धान / चावल (Paddy)",
    residue: "Paddy Straw / Rice Straw",
    residueHi: "धान की पराली / पुआल",
    icon: "🌾",
    typicalTonnesPerAcre: "3.0 – 4.2 tonnes/acre",
  },
  {
    key: "wheat",
    name: "Wheat",
    nameHi: "गेहूं (Wheat)",
    residue: "Wheat Straw (Bhusa / Turi)",
    residueHi: "गेहूं का भूसा / तूड़ी",
    icon: "🌾",
    typicalTonnesPerAcre: "2.0 – 3.0 tonnes/acre",
  },
  {
    key: "maize",
    name: "Maize",
    nameHi: "मक्का (Maize)",
    residue: "Maize Stover (Stalks & Leaves)",
    residueHi: "मक्के की कड़बी / डंठल",
    icon: "🌽",
    typicalTonnesPerAcre: "2.5 – 3.8 tonnes/acre",
  },
  {
    key: "sugarcane",
    name: "Sugarcane",
    nameHi: "गन्ना (Sugarcane)",
    residue: "Sugarcane Trash & Dry Leaves",
    residueHi: "गन्ने की सूखी पत्तियां (ट्रैश)",
    icon: "🎋",
    typicalTonnesPerAcre: "3.5 – 5.8 tonnes/acre",
  },
  {
    key: "cotton",
    name: "Cotton",
    nameHi: "कपास (Cotton)",
    residue: "Cotton Stalks (Woody Residue)",
    residueHi: "कपास के डंठल / छड़ियां",
    icon: "☁️",
    typicalTonnesPerAcre: "1.5 – 2.8 tonnes/acre",
  },
  {
    key: "mustard",
    name: "Mustard",
    nameHi: "सरसों / राई (Mustard)",
    residue: "Mustard Stover & Pod Husk",
    residueHi: "सरसों का डंठल एवं भूसा",
    icon: "🌼",
    typicalTonnesPerAcre: "1.2 – 2.4 tonnes/acre",
  },
  {
    key: "soybean",
    name: "Soybean",
    nameHi: "सोयाबीन (Soybean)",
    residue: "Soybean Straw & Pod Shells",
    residueHi: "सोयाबीन का भूसा एवं छिलका",
    icon: "🌱",
    typicalTonnesPerAcre: "1.2 – 2.2 tonnes/acre",
  },
  {
    key: "pulses",
    name: "Pulses (Moong/Chana/Urad)",
    nameHi: "दलहन (मूंग / चना / उड़द)",
    residue: "Pulse Chaff & Stover",
    residueHi: "दलहनी फसलों का भूसा एवं डंठल",
    icon: "🫘",
    typicalTonnesPerAcre: "0.8 – 2.0 tonnes/acre",
  },
  {
    key: "other",
    name: "Other Harvested Crop",
    nameHi: "अन्य फसल (Other Crop)",
    residue: "Crop Residue / Stubble",
    residueHi: "फसल अवशेष / पराली",
    icon: "🌾",
    typicalTonnesPerAcre: "1.5 – 3.0 tonnes/acre",
  },
];

const AREA_UNITS = [
  { key: "acre", labelEn: "Acre", labelHi: "एकड़ (Acre)", factorToAcres: 1.0 },
  { key: "hectare", labelEn: "Hectare", labelHi: "हेक्टेयर (Hectare)", factorToAcres: 2.471 },
  { key: "bigha", labelEn: "Bigha", labelHi: "बीघा (Bigha)", factorToAcres: 0.62 },
  { key: "sq_m", labelEn: "Square Meter", labelHi: "वर्ग मीटर (m²)", factorToAcres: 0.000247 },
  { key: "sq_ft", labelEn: "Square Feet", labelHi: "वर्ग फीट (sq ft)", factorToAcres: 0.0000229 },
];

const GOAL_OPTIONS = [
  {
    key: "recommend_best",
    titleEn: "I am not sure — recommend the best option",
    titleHi: "मुझे निश्चित नहीं है — सर्वोत्तम विकल्प सुझाएं",
    descEn: "MAITTRI will scientifically evaluate your crop, farm size, and machinery to pick the highest-benefit method.",
    descHi: "मैत्री आपकी फसल, क्षेत्रफल और मशीनरी के आधार पर सबसे उपयुक्त वैज्ञानिक विधि का चयन करेगी।",
    icon: "🤖",
  },
  {
    key: "in_field",
    titleEn: "Manage it in the field (In-situ retention)",
    titleHi: "खेत में ही प्रबंधन करें (सीधी बुवाई / मल्च)",
    descEn: "Direct sowing with Happy Seeder or Super Seeder without tillage to save water and suppress weeds.",
    descHi: "हैप्पी/सुपर सीडर से बिना जुताई सीधी बुवाई कर पानी बचाएं और खरपतवार रोकें।",
    icon: "🚜",
  },
  {
    key: "soil_incorporation",
    titleEn: "Incorporate it into soil",
    titleHi: "मिट्टी में जुताई कर मिलाएं (रोटावेटर / प्लाऊ)",
    descEn: "Chop with mulcher and bury into topsoil with rotavator to build long-term soil organic carbon.",
    descHi: "मल्चर और रोटावेटर द्वारा मिट्टी में मिलाकर जैविक जीवांश कार्बन बढ़ाएं।",
    icon: "🌱",
  },
  {
    key: "mulch",
    titleEn: "Use it as surface mulch",
    titleHi: "सतह पर मल्च के रूप में बिछाएं",
    descEn: "Retain residue blanket on soil surface to conserve moisture, shield against heat, and stop evaporation.",
    descHi: "मिट्टी में नमी बनाए रखने और तेज धूप से बचाव हेतु सतह पर बिछाएं।",
    icon: "🍂",
  },
  {
    key: "compost",
    titleEn: "Compost it into organic manure",
    titleHi: "खाद / वर्मीकम्पोस्ट बनाएं",
    descEn: "Convert residue into dark, weed-free humus using farm pits, dung slurry, and microbial cultures.",
    descHi: "गोबर घोल व जैविक जीवाणुओं के सहयोग से गड्ढे में उच्च गुणवत्ता वाली खाद तैयार करें।",
    icon: "♻️",
  },
  {
    key: "biomass",
    titleEn: "Collect and sell / supply as biomass",
    titleHi: "बेलिंग कर बायोमास उद्योग / एथेनॉल को बेचें",
    descEn: "Bale straw with mechanical balers for bio-CNG plants, 2G ethanol refineries, or industrial boilers.",
    descHi: "बेलिंग मशीन से बंडल बनाकर बायो-सीएनजी, एथेनॉल या बायोमास बिजली घर को आपूर्ति करें।",
    icon: "📦",
  },
  {
    key: "livestock",
    titleEn: "Use it for livestock / animal feed",
    titleHi: "पशु आहार / सूखे चारे के रूप में उपयोग",
    descEn: "Harvest as dry Bhusa (wheat/pulses) or 4% urea-treated straw for cattle (where scientifically safe).",
    descHi: "गेहूं/दलहन का भूसा बनाएं या धान के पुआल को यूरिया से उपचारित कर पशुओं को खिलाएं।",
    icon: "🐄",
  },
];

const MACHINERY_OPTIONS = [
  { id: "Happy Seeder", label: "Happy Seeder", labelHi: "हैप्पी सीडर" },
  { id: "Super Seeder", label: "Super Seeder", labelHi: "सुपर सीडर" },
  { id: "Straw Management System / Super SMS", label: "Super SMS (Combine)", labelHi: "सुपर एसएमएस (कंबाइन)" },
  { id: "Mulcher", label: "Tractor Mulcher", labelHi: "ट्रैक्टर मल्चर" },
  { id: "Rotavator", label: "Rotavator", labelHi: "रोटावेटर" },
  { id: "Baler", label: "Straw Baler (Round/Square)", labelHi: "बेलिंग मशीन (Baler)" },
  { id: "Rake", label: "Straw Rake", labelHi: "स्ट्रॉ रेक (Rake)" },
  { id: "Chopper/Shredder", label: "Chopper / Shredder", labelHi: "चॉपर / श्रेडर" },
  { id: "MB Plough", label: "Reversible MB Plough", labelHi: "एम.बी. प्लाऊ" },
  { id: "Chaff Cutter", label: "Chaff Cutter", labelHi: "कुट्टी मशीन" },
];

export default function ParaliManagementPage() {
  const nav = useNavigate();
  const { lang, t } = useLang();

  // Wizard state: 1 to 6 (inputs), 7 (results)
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [analyzingMessage, setAnalyzingMessage] = useState("");
  const [error, setError] = useState("");

  // Existing Farm state
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState(null);

  // Form Inputs
  const [selectedCropKey, setSelectedCropKey] = useState("rice");
  const [areaValue, setAreaValue] = useState(2.5);
  const [areaUnit, setAreaUnit] = useState("acre");
  const [knownResidue, setKnownResidue] = useState("");
  const [useKnownOverride, setUseKnownOverride] = useState(false);
  const [farmerGoal, setFarmerGoal] = useState("recommend_best");
  const [machineryAccess, setMachineryAccess] = useState("not_sure"); // 'yes', 'no', 'not_sure'
  const [selectedMachinery, setSelectedMachinery] = useState([]);
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [locationName, setLocationName] = useState("");
  const [soilType, setSoilType] = useState("");

  // Analysis result
  const [analysisResult, setAnalysisResult] = useState(null);
  const [activeMethodId, setActiveMethodId] = useState(null);
  const [activeActionPlan, setActiveActionPlan] = useState(null);
  const [actionPlanLoading, setActionPlanLoading] = useState(false);

  // Fetch farms on mount
  useEffect(() => {
    api.get("/farms")
      .then((res) => {
        if (res.data && res.data.length > 0) {
          setFarms(res.data);
          const defaultFarm = res.data[0];
          setSelectedFarmId(defaultFarm.id);
          if (defaultFarm.area) setAreaValue(defaultFarm.area);
          if (defaultFarm.area_unit) setAreaUnit(defaultFarm.area_unit);
          if (defaultFarm.latitude) setLatitude(defaultFarm.latitude);
          if (defaultFarm.longitude) setLongitude(defaultFarm.longitude);
          if (defaultFarm.location_name) setLocationName(defaultFarm.location_name);
          if (defaultFarm.soil_type) setSoilType(defaultFarm.soil_type);

          // If farm has previous or current crop
          const fCrop = (defaultFarm.current_crop || defaultFarm.previous_crop || "").toLowerCase();
          const match = CROPS_CONFIG.find((c) => fCrop.includes(c.key));
          if (match) setSelectedCropKey(match.key);
        }
      })
      .catch(() => {});
  }, []);

  // Selected crop profile helper
  const activeCrop = useMemo(() => {
    return CROPS_CONFIG.find((c) => c.key === selectedCropKey) || CROPS_CONFIG[0];
  }, [selectedCropKey]);

  // Live residue estimate range preview for Step 3
  const liveEstimateRange = useMemo(() => {
    const unitObj = AREA_UNITS.find((u) => u.key === areaUnit) || AREA_UNITS[0];
    const acres = Math.max(0.1, (parseFloat(areaValue) || 1.0) * unitObj.factorToAcres);

    let lowRate = 2.8;
    let midRate = 3.4;
    let highRate = 4.2;

    if (selectedCropKey === "wheat") { lowRate = 1.8; midRate = 2.4; highRate = 3.0; }
    else if (selectedCropKey === "maize") { lowRate = 2.2; midRate = 3.0; highRate = 3.8; }
    else if (selectedCropKey === "sugarcane") { lowRate = 3.2; midRate = 4.5; highRate = 5.8; }
    else if (selectedCropKey === "cotton") { lowRate = 1.4; midRate = 2.2; highRate = 2.8; }
    else if (selectedCropKey === "mustard") { lowRate = 1.2; midRate = 1.8; highRate = 2.4; }
    else if (selectedCropKey === "soybean") { lowRate = 1.1; midRate = 1.6; highRate = 2.2; }
    else if (selectedCropKey === "pulses") { lowRate = 0.8; midRate = 1.4; highRate = 2.0; }
    else if (selectedCropKey === "other") { lowRate = 1.5; midRate = 2.2; highRate = 3.0; }

    return {
      low: Math.round(acres * lowRate * 10) / 10,
      mid: Math.round(acres * midRate * 10) / 10,
      high: Math.round(acres * highRate * 10) / 10,
      acres: Math.round(acres * 10) / 10,
    };
  }, [selectedCropKey, areaValue, areaUnit]);

  // Handle farm selection change
  const handleFarmChange = (e) => {
    const fId = parseInt(e.target.value, 10);
    setSelectedFarmId(fId);
    const farm = farms.find((f) => f.id === fId);
    if (farm) {
      if (farm.area) setAreaValue(farm.area);
      if (farm.area_unit) setAreaUnit(farm.area_unit);
      if (farm.latitude) setLatitude(farm.latitude);
      if (farm.longitude) setLongitude(farm.longitude);
      if (farm.location_name) setLocationName(farm.location_name);
      if (farm.soil_type) setSoilType(farm.soil_type);
      const fCrop = (farm.current_crop || farm.previous_crop || "").toLowerCase();
      const match = CROPS_CONFIG.find((c) => fCrop.includes(c.key));
      if (match) setSelectedCropKey(match.key);
    }
  };

  // Machinery chip toggle
  const toggleMachinery = (machId) => {
    setSelectedMachinery((prev) =>
      prev.includes(machId) ? prev.filter((m) => m !== machId) : [...prev, machId]
    );
  };

  // Perform backend analysis
  const runAnalysis = async () => {
    setLoading(true);
    setError("");
    setAnalyzingMessage(
      lang === "hi"
        ? "🌾 मैत्री आपके फसल अवशेष का वैज्ञानिक विश्लेषण कर रही है..."
        : "🌾 MAITTRI is analyzing your crop residue..."
    );

    try {
      const payload = {
        crop: selectedCropKey,
        area: parseFloat(areaValue) || 1.0,
        area_unit: areaUnit,
        residue_quantity: useKnownOverride && knownResidue ? parseFloat(knownResidue) : null,
        residue_quantity_source: useKnownOverride && knownResidue ? "farmer_known" : "estimated",
        farmer_goal: farmerGoal,
        machinery_available: machineryAccess,
        machinery: machineryAccess === "yes" ? selectedMachinery : [],
        latitude: latitude,
        longitude: longitude,
        soil_type: soilType,
        farm_id: selectedFarmId,
      };

      const { data } = await api.post("/parali/analyze", payload);
      setAnalysisResult(data);
      if (data.recommended_method) {
        setActiveMethodId(data.recommended_method.method_id);
        setActiveActionPlan({
          method_name: data.recommended_method.name,
          method_name_hi: data.recommended_method.name_hi,
          steps: data.recommended_method.steps,
        });
      }
      setCurrentStep(7); // Jump to result
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.detail ||
          (lang === "hi"
            ? "पराली विश्लेषण में समस्या आई। कृपया जानकारी की जांच कर पुनः प्रयास करें।"
            : "Failed to analyze crop residue. Please verify your inputs and try again.")
      );
    } finally {
      setLoading(false);
      setAnalyzingMessage("");
    }
  };

  // Switch action plan to a specific method
  const selectActionPlanMethod = async (method) => {
    setActiveMethodId(method.method_id);
    if (method.steps && method.steps.length > 0) {
      setActiveActionPlan({
        method_name: method.name,
        method_name_hi: method.name_hi,
        steps: method.steps,
      });
      return;
    }

    setActionPlanLoading(true);
    try {
      const { data } = await api.post("/parali/action-plan", {
        method_id: method.method_id,
        crop: selectedCropKey,
      });
      setActiveActionPlan(data);
    } catch (err) {
      console.error(err);
    } finally {
      setActionPlanLoading(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="content paraliPageWrapper">
      {/* HEADER SECTION */}
      <div className="hero paraliHero">
        <div>
          <div className="eyebrowBadge">
            <Wheat size={14} />
            <span>{lang === "hi" ? "फसल अवशेष एवं पराली प्रबंधन" : "CROP RESIDUE INTELLIGENCE"}</span>
          </div>
          <h1>{lang === "hi" ? "🌾 पराली / फसल अवशेष प्रबंधन" : "🌾 Parali / Crop Residue Management"}</h1>
          <p className="heroDescription">
            {lang === "hi"
              ? "बिना आग लगाए पराली का वैज्ञानिक, फसल-अनुकूल एवं लाभदायक प्रबंधन। मिट्टी की उर्वरता बचाएं और सही तकनीक चुनें।"
              : "Scientific, crop-aware residue decision-support without open-field burning. Conserve soil fertility and discover high-value management methods."}
          </p>
        </div>

        {farms.length > 0 && (
          <div className="farmSelectCard">
            <span className="farmSelectLabel">
              <MapPinned size={14} /> {lang === "hi" ? "सक्रिय खेत चुनें:" : "Active Farm:"}
            </span>
            <select value={selectedFarmId || ""} onChange={handleFarmChange} className="farmSelectDropdown">
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.area} {f.area_unit || "acre"})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <div className="alertCard critical">
          <AlertTriangle size={18} />
          <div>{error}</div>
        </div>
      )}

      {/* STEP INDICATOR BAR */}
      {currentStep <= 6 && (
        <div className="wizardProgressContainer">
          <div className="wizardProgressBar">
            {[1, 2, 3, 4, 5, 6].map((step) => {
              const isActive = currentStep === step;
              const isCompleted = currentStep > step;
              return (
                <button
                  key={step}
                  type="button"
                  onClick={() => setCurrentStep(step)}
                  className={`wizardStepBtn ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
                >
                  <div className="stepCircle">{isCompleted ? <Check size={14} /> : step}</div>
                  <span className="stepLabel">
                    {step === 1 && (lang === "hi" ? "फसल" : "Crop")}
                    {step === 2 && (lang === "hi" ? "क्षेत्रफल" : "Area")}
                    {step === 3 && (lang === "hi" ? "मात्रा" : "Quantity")}
                    {step === 4 && (lang === "hi" ? "उद्देश्य" : "Goal")}
                    {step === 5 && (lang === "hi" ? "मशीनरी" : "Machinery")}
                    {step === 6 && (lang === "hi" ? "स्थान" : "Location")}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* LOADING OVERLAY */}
      {loading && (
        <div className="card paraliLoadingCard">
          <div className="pulseSpinner">
            <Wheat size={42} className="spinIcon" />
          </div>
          <h3>{analyzingMessage || (lang === "hi" ? "विश्लेषण जारी है..." : "Analyzing crop residue...")}</h3>
          <p>
            {lang === "hi"
              ? "ICAR और PAU वैज्ञानिक मानदंडों के अनुसार सबसे उपयुक्त विधि एवं पोषक तत्व गणना की जा रही है..."
              : "Evaluating ICAR/PAU scientific benchmarks, soil benefits, and custom hiring costs..."}
          </p>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 1: HARVESTED CROP                           */}
      {/* ======================================================= */}
      {!loading && currentStep === 1 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 1 of 6</span>
            <h2>{lang === "hi" ? "🌾 आपने किस फसल की कटाई की है?" : "🌾 Which crop have you harvested?"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "अपनी कटी हुई फसल चुनें ताकि सही अवशेष प्रकार और वैज्ञानिक विधि पहचानी जा सके।"
                : "Select your harvested crop to accurately identify residue type and crop-compatible management methods."}
            </p>
          </div>

          <div className="cropsGrid">
            {CROPS_CONFIG.map((c) => {
              const isSelected = selectedCropKey === c.key;
              return (
                <div
                  key={c.key}
                  className={`cropPickCard ${isSelected ? "selected" : ""}`}
                  onClick={() => setSelectedCropKey(c.key)}
                >
                  <div className="cropPickIcon">{c.icon}</div>
                  <div className="cropPickInfo">
                    <span className="cropPickName">{lang === "hi" ? c.nameHi : c.name}</span>
                    <span className="cropPickResidue">
                      {lang === "hi" ? c.residueHi : c.residue}
                    </span>
                  </div>
                  {isSelected && (
                    <div className="cropPickCheck">
                      <Check size={16} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Dynamic Residue Badge */}
          <div className="dynamicResidueBadge">
            <Info size={18} />
            <div>
              <strong>{lang === "hi" ? "पहचाना गया अवशेष प्रकार: " : "Identified Crop Residue: "}</strong>
              <span className="highlightResidue">
                {lang === "hi" ? activeCrop.residueHi : activeCrop.residue}
              </span>
              <div className="residueSubRate">
                {lang === "hi" ? "सामान्य उपज दर: " : "Typical stubble yield: "} {activeCrop.typicalTonnesPerAcre}
              </div>
            </div>
          </div>

          <div className="wizardNavActions">
            <div></div>
            <button
              type="button"
              className="primaryBtn wizardNextBtn"
              onClick={() => setCurrentStep(2)}
            >
              <span>{lang === "hi" ? "आगे बढ़ें (क्षेत्रफल दर्ज करें)" : "Next: Farm Area"}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 2: FARM AREA                                */}
      {/* ======================================================= */}
      {!loading && currentStep === 2 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 2 of 6</span>
            <h2>{lang === "hi" ? "📐 आपने कितनी भूमि में फसल काटी है?" : "📐 How much land did you harvest?"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "क्षेत्रफल दर्ज करें और अपनी स्थानीय इकाई चुनें। हम इसे आंतरिक रूप से वैज्ञानिक गणना हेतु रूपांतरित कर लेंगे।"
                : "Enter the harvested land area and select your preferred regional measurement unit."}
            </p>
          </div>

          <div className="areaInputGroup">
            <div className="formField areaValField">
              <label>{lang === "hi" ? "क्षेत्रफल मान" : "Harvested Area"}</label>
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={areaValue}
                onChange={(e) => setAreaValue(e.target.value)}
                placeholder="e.g. 5"
                className="largeNumberInput"
              />
            </div>

            <div className="formField areaUnitField">
              <label>{lang === "hi" ? "माप की इकाई" : "Measurement Unit"}</label>
              <select
                value={areaUnit}
                onChange={(e) => setAreaUnit(e.target.value)}
                className="unitSelectDropdown"
              >
                {AREA_UNITS.map((u) => (
                  <option key={u.key} value={u.key}>
                    {lang === "hi" ? u.labelHi : u.labelEn}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Area conversion confirmation note */}
          <div className="areaConversionBox">
            <CheckCircle2 size={18} color="#16a34a" />
            <div>
              <span>
                {lang === "hi"
                  ? `दर्ज भूमि: ${areaValue} ${areaUnit} (लगभग ${liveEstimateRange.acres} एकड़ / ${(liveEstimateRange.acres * 0.4047).toFixed(2)} हेक्टेयर)`
                  : `Normalized Land: ${areaValue} ${areaUnit} (approx. ${liveEstimateRange.acres} Acres / ${(liveEstimateRange.acres * 0.4047).toFixed(2)} Hectares)`}
              </span>
            </div>
          </div>

          <div className="wizardNavActions">
            <button
              type="button"
              className="outlineBtn"
              onClick={() => setCurrentStep(1)}
            >
              <ArrowLeft size={18} />
              <span>{lang === "hi" ? "पिछला" : "Previous"}</span>
            </button>

            <button
              type="button"
              className="primaryBtn wizardNextBtn"
              onClick={() => setCurrentStep(3)}
            >
              <span>{lang === "hi" ? "आगे बढ़ें (पराली मात्रा)" : "Next: Residue Quantity"}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 3: RESIDUE QUANTITY                         */}
      {/* ======================================================= */}
      {!loading && currentStep === 3 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 3 of 6</span>
            <h2>{lang === "hi" ? "🌾 खेत में अवशेष / पराली की मात्रा" : "🌾 Estimated Residue Quantity"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "ICAR अनुसंधान के अनुसार अनुमानित मात्रा। यदि आपके पास वास्तविक वजन ज्ञात है तो आप उसे दर्ज कर सकते हैं।"
                : "Scientifically estimated stubble tonnage based on crop-to-grain ratios. Enter known quantity if weighed."}
            </p>
          </div>

          {/* Live Estimate Card */}
          <div className="estimatePreviewCard">
            <div className="estimateHeader">
              <span className="estCropBadge">{lang === "hi" ? activeCrop.nameHi : activeCrop.name}</span>
              <span className="estResidueName">{lang === "hi" ? activeCrop.residueHi : activeCrop.residue}</span>
            </div>

            <div className="estimateNumbersRow">
              <div className="estNumBox low">
                <span className="estNumLabel">{lang === "hi" ? "न्यूनतम" : "Low Range"}</span>
                <span className="estNumValue">~{liveEstimateRange.low}</span>
                <span className="estNumUnit">{lang === "hi" ? "टन" : "tonnes"}</span>
              </div>
              <div className="estNumBox mid highlight">
                <span className="estNumLabel">{lang === "hi" ? "अनुमानित औसत" : "Likely Estimate"}</span>
                <span className="estNumValue">~{liveEstimateRange.mid}</span>
                <span className="estNumUnit">{lang === "hi" ? "टन (Tonnes)" : "tonnes"}</span>
              </div>
              <div className="estNumBox high">
                <span className="estNumLabel">{lang === "hi" ? "अधिकतम" : "High Range"}</span>
                <span className="estNumValue">~{liveEstimateRange.high}</span>
                <span className="estNumUnit">{lang === "hi" ? "टन" : "tonnes"}</span>
              </div>
            </div>

            <div className="estimateDisclaimer">
              <Info size={15} />
              <span>
                {lang === "hi"
                  ? "अनुमानित मान — वास्तविक मात्रा फसल की उपज, कंबाइन के कटरबार की ऊंचाई और खेत की स्थिति पर निर्भर करती है।"
                  : "Estimated value — actual quantity may vary depending on yield, harvesting method, and field conditions."}
              </span>
            </div>
          </div>

          {/* Farmer Known Override Toggle */}
          <div className="overrideSection">
            <label className="checkboxLabel">
              <input
                type="checkbox"
                checked={useKnownOverride}
                onChange={(e) => setUseKnownOverride(e.target.checked)}
              />
              <span>
                {lang === "hi"
                  ? "मुझे अपनी पराली का वास्तविक वजन मालूम है (वैकल्पिक)"
                  : "Enter known residue quantity if already weighed (optional)"}
              </span>
            </label>

            {useKnownOverride && (
              <div className="overrideInputField animateFadeIn">
                <input
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={knownResidue}
                  onChange={(e) => setKnownResidue(e.target.value)}
                  placeholder={lang === "hi" ? "जैसे: 15.5 टन" : "e.g. 15.5 tonnes"}
                  className="largeNumberInput"
                />
                <span className="inputUnitTag">{lang === "hi" ? "टन" : "tonnes"}</span>
              </div>
            )}
          </div>

          <div className="wizardNavActions">
            <button
              type="button"
              className="outlineBtn"
              onClick={() => setCurrentStep(2)}
            >
              <ArrowLeft size={18} />
              <span>{lang === "hi" ? "पिछला" : "Previous"}</span>
            </button>

            <button
              type="button"
              className="primaryBtn wizardNextBtn"
              onClick={() => setCurrentStep(4)}
            >
              <span>{lang === "hi" ? "आगे बढ़ें (उद्देश्य चुनें)" : "Next: Farmer's Goal"}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 4: FARMER'S GOAL                            */}
      {/* ======================================================= */}
      {!loading && currentStep === 4 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 4 of 6</span>
            <h2>{lang === "hi" ? "🎯 आप फसल अवशेष के साथ क्या करना चाहते हैं?" : "🎯 What do you want to do with the crop residue?"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "अपना प्राथमिक लक्ष्य चुनें। यदि आप असमंजस में हैं तो 'सर्वोत्तम विकल्प सुझाएं' का चयन करें।"
                : "Select your primary objective, or ask MAITTRI to recommend the best agronomic method."}
            </p>
          </div>

          <div className="goalsList">
            {GOAL_OPTIONS.map((g) => {
              const isSelected = farmerGoal === g.key;
              return (
                <div
                  key={g.key}
                  className={`goalCard ${isSelected ? "selected" : ""}`}
                  onClick={() => setFarmerGoal(g.key)}
                >
                  <div className="goalIcon">{g.icon}</div>
                  <div className="goalInfo">
                    <span className="goalTitle">{lang === "hi" ? g.titleHi : g.titleEn}</span>
                    <span className="goalDesc">{lang === "hi" ? g.descHi : g.descEn}</span>
                  </div>
                  <div className="goalRadioCircle">
                    {isSelected && <div className="goalRadioInner"></div>}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="wizardNavActions">
            <button
              type="button"
              className="outlineBtn"
              onClick={() => setCurrentStep(3)}
            >
              <ArrowLeft size={18} />
              <span>{lang === "hi" ? "पिछला" : "Previous"}</span>
            </button>

            <button
              type="button"
              className="primaryBtn wizardNextBtn"
              onClick={() => setCurrentStep(5)}
            >
              <span>{lang === "hi" ? "आगे बढ़ें (मशीनरी उपलब्धता)" : "Next: Machinery"}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 5: MACHINERY / RESOURCES                    */}
      {/* ======================================================= */}
      {!loading && currentStep === 5 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 5 of 6</span>
            <h2>{lang === "hi" ? "🚜 क्या आपके पास कृषि मशीनरी उपलब्ध है?" : "🚜 Do you have access to farm machinery?"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "निजी या किराए (Custom Hiring Center) पर उपलब्ध मशीनें चुनें ताकि व्यवहार्य सिफारिशें मिलें।"
                : "Select machinery you own or can hire locally. Recommendations will prioritize accessible equipment."}
            </p>
          </div>

          {/* Quick Access Selector */}
          <div className="machineryAccessButtons">
            {[
              { key: "yes", labelEn: "Yes, I have access", labelHi: "हाँ, मशीनरी उपलब्ध है" },
              { key: "no", labelEn: "No machinery", labelHi: "नहीं, मशीन उपलब्ध नहीं है" },
              { key: "not_sure", labelEn: "Not sure / Custom Hire", labelHi: "निश्चित नहीं / किराए पर लेंगे" },
            ].map((opt) => (
              <button
                key={opt.key}
                type="button"
                className={`accessChoiceBtn ${machineryAccess === opt.key ? "active" : ""}`}
                onClick={() => setMachineryAccess(opt.key)}
              >
                {opt.key === "yes" && <Tractor size={16} />}
                {opt.key === "no" && <HelpCircle size={16} />}
                {opt.key === "not_sure" && <RefreshCw size={16} />}
                <span>{lang === "hi" ? opt.labelHi : opt.labelEn}</span>
              </button>
            ))}
          </div>

          {/* Machinery Multi-Select Chips (shown if 'yes' or 'not_sure') */}
          {machineryAccess !== "no" && (
            <div className="machineryChipsSection animateFadeIn">
              <label className="machineryChipsTitle">
                {lang === "hi"
                  ? "उपलब्ध उपकरण चुनें (एक या अधिक चुनें):"
                  : "Select available machinery (select all that apply):"}
              </label>

              <div className="machineryChipsGrid">
                {MACHINERY_OPTIONS.map((m) => {
                  const isChecked = selectedMachinery.includes(m.id);
                  return (
                    <button
                      key={m.id}
                      type="button"
                      className={`machChipBtn ${isChecked ? "selected" : ""}`}
                      onClick={() => toggleMachinery(m.id)}
                    >
                      <span className="machCheck">{isChecked ? "✓" : "+"}</span>
                      <span>{lang === "hi" ? m.labelHi : m.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          <div className="wizardNavActions">
            <button
              type="button"
              className="outlineBtn"
              onClick={() => setCurrentStep(4)}
            >
              <ArrowLeft size={18} />
              <span>{lang === "hi" ? "पिछला" : "Previous"}</span>
            </button>

            <button
              type="button"
              className="primaryBtn wizardNextBtn"
              onClick={() => setCurrentStep(6)}
            >
              <span>{lang === "hi" ? "आगे बढ़ें (खेत का स्थान)" : "Next: Location"}</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* WIZARD STEP 6: LOCATION & FARM PROFILE                  */}
      {/* ======================================================= */}
      {!loading && currentStep === 6 && (
        <div className="card wizardStepCard">
          <div className="stepHeader">
            <span className="stepNumBadge">Step 6 of 6</span>
            <h2>{lang === "hi" ? "📍 खेत का स्थान एवं संदर्भ" : "📍 Farm Location & Soil Context"}</h2>
            <p className="stepSubtext">
              {lang === "hi"
                ? "स्थान जानकारी स्थानीय मौसम, कस्टम हायरिंग और सेवा संभावनाओं को जोड़ने में सहायक होती है।"
                : "Location coordinates enhance operational weather advisories and future local custom hiring center links."}
            </p>
          </div>

          {latitude && longitude ? (
            <div className="locationVerifiedCard">
              <div className="locVerifiedHeader">
                <MapPinned size={22} color="#16a34a" />
                <div>
                  <span className="locTitle">
                    {locationName || (lang === "hi" ? "खेत का स्थान निर्धारित" : "Farm Location Attached")}
                  </span>
                  <span className="locCoords">
                    Lat: {latitude.toFixed(4)}, Lon: {longitude.toFixed(4)}
                    {soilType && ` · Soil: ${soilType}`}
                  </span>
                </div>
              </div>
              <p className="locNote">
                {lang === "hi"
                  ? "✓ आपकी सहेजी गई फार्म प्रोफ़ाइल से स्थान डेटा स्वतः उपयोग किया जा रहा है।"
                  : "✓ Automatically reused from your saved MAITTRI farm profile."}
              </p>
            </div>
          ) : (
            <div className="locationOptionalCard">
              <Info size={20} color="#0284c7" />
              <div>
                <strong>{lang === "hi" ? "स्थान वैकल्पिक है" : "Location is optional"}</strong>
                <p>
                  {lang === "hi"
                    ? "यदि स्थान उपलब्ध नहीं है तो भी यह मॉड्यूल पूर्ण सटीकता से कार्य करता है।"
                    : "Residue analysis functions accurately even without GPS coordinates."}
                </p>
              </div>
            </div>
          )}

          {/* FINAL CTA BUTTON */}
          <div className="analysisLaunchBox">
            <div className="launchSummaryText">
              <span>{lang === "hi" ? "विश्लेषण हेतु तैयार: " : "Ready to analyze: "}</span>
              <strong>
                {activeCrop.icon} {lang === "hi" ? activeCrop.nameHi : activeCrop.name} · {areaValue} {areaUnit} (~{liveEstimateRange.mid} t)
              </strong>
            </div>

            <button
              type="button"
              className="primaryBtn largeLaunchBtn"
              onClick={runAnalysis}
              disabled={loading}
            >
              <Sparkles size={20} />
              <span>{lang === "hi" ? "🌾 मैत्री पराली विश्लेषण शुरू करें" : "🌾 Analyze My Crop Residue"}</span>
              <ArrowRight size={20} />
            </button>
          </div>

          <div className="wizardNavActions">
            <button
              type="button"
              className="outlineBtn"
              onClick={() => setCurrentStep(5)}
            >
              <ArrowLeft size={18} />
              <span>{lang === "hi" ? "पिछला" : "Previous"}</span>
            </button>
          </div>
        </div>
      )}

      {/* ======================================================= */}
      {/* STEP 7: MAITTRI ANALYSIS RESULTS                        */}
      {/* ======================================================= */}
      {!loading && currentStep === 7 && analysisResult && (
        <div className="analysisResultsWrapper animateFadeIn">
          {/* TOP SUMMARY BAR */}
          <div className="card residueSummaryCard">
            <div className="residueSummaryHeader">
              <div>
                <span className="eyebrowBadge">
                  <CheckCircle2 size={14} color="#16a34a" />
                  <span>{lang === "hi" ? "विश्लेषण पूर्ण" : "ANALYSIS COMPLETE"}</span>
                </span>
                <h2>{lang === "hi" ? "🌾 आपका फसल अवशेष विश्लेषण" : "🌾 Your Crop Residue Analysis"}</h2>
              </div>

              <div className="summaryActions">
                <button type="button" className="outlineBtn small" onClick={() => setCurrentStep(1)}>
                  <RefreshCw size={14} />
                  <span>{lang === "hi" ? "मान बदलें" : "Change Inputs"}</span>
                </button>
                <button type="button" className="outlineBtn small" onClick={handlePrint}>
                  <Printer size={14} />
                  <span>{lang === "hi" ? "प्रिंट / सेव" : "Print Plan"}</span>
                </button>
              </div>
            </div>

            <div className="summaryMetricsGrid">
              <div className="summaryMetricBox">
                <span className="smLabel">{lang === "hi" ? "कटी हुई फसल" : "Harvested Crop"}</span>
                <span className="smValue">
                  {lang === "hi" ? analysisResult.crop_hi : analysisResult.crop}
                </span>
              </div>

              <div className="summaryMetricBox">
                <span className="smLabel">{lang === "hi" ? "अवशेष प्रकार" : "Residue Type"}</span>
                <span className="smValue highlight">
                  {lang === "hi" ? analysisResult.residue_type_hi : analysisResult.residue_type}
                </span>
              </div>

              <div className="summaryMetricBox">
                <span className="smLabel">{lang === "hi" ? "खेत का क्षेत्रफल" : "Farm Area"}</span>
                <span className="smValue">
                  {analysisResult.area} {analysisResult.area_unit} ({analysisResult.area_normalized_acres} acres)
                </span>
              </div>

              <div className="summaryMetricBox">
                <span className="smLabel">{lang === "hi" ? "अनुमानित पराली मात्रा" : "Estimated Residue"}</span>
                <span className="smValue">
                  ~{analysisResult.estimated_residue_low} – {analysisResult.estimated_residue_high} tonnes
                </span>
                <small className="smConfidence">{analysisResult.estimate_confidence}</small>
              </div>
            </div>

            {/* Livestock Specific Safety Warning (if applicable) */}
            {analysisResult.livestock_warning && (
              <div className="cropSafetyAlertCard">
                <AlertTriangle size={18} color="#d97706" />
                <div>
                  <strong>{lang === "hi" ? "पशु आहार सुरक्षा चेतावनी:" : "Livestock Fodder Safety Advisory:"}</strong>
                  <p>{analysisResult.livestock_warning}</p>
                </div>
              </div>
            )}
          </div>

          {/* =================================================== */}
          {/* SECTION 8: 🚫 DO NOT BURN CROP RESIDUE WARNING CARD  */}
          {/* =================================================== */}
          <div className="card burningWarningCard">
            <div className="burnCardHeader">
              <div className="burnShieldIcon">
                <ShieldAlert size={28} />
              </div>
              <div>
                <h3 className="burnTitle">
                  {lang === "hi" ? analysisResult.burning_warning.title_hi : analysisResult.burning_warning.title}
                </h3>
                <p className="burnFarmerMessage">
                  {lang === "hi"
                    ? analysisResult.burning_warning.farmer_message_hi
                    : analysisResult.burning_warning.farmer_message}
                </p>
              </div>
            </div>

            <div className="burnNutrientLossSection">
              <span className="lossTitle">
                {lang === "hi"
                  ? "🔥 पराली जलाने पर होने वाला संभावित पोषक तत्व नुकसान (ICAR/PAU मानक):"
                  : "🔥 Potential Soil Nutrient Losses if Burned (ICAR/IARI & PAU Benchmarks):"}
              </span>

              <div className="lossCountersGrid">
                <div className="lossCounterItem">
                  <span className="lossNutrientName">Nitrogen (N)</span>
                  <span className="lossAmount">
                    ~{analysisResult.burning_warning.nutrient_losses.nitrogen_kg} kg
                  </span>
                  <span className="lossDesc">{lang === "hi" ? "नष्ट नाइट्रोजन" : "Soil N destroyed"}</span>
                </div>

                <div className="lossCounterItem">
                  <span className="lossNutrientName">Phosphorus (P)</span>
                  <span className="lossAmount">
                    ~{analysisResult.burning_warning.nutrient_losses.phosphorus_kg} kg
                  </span>
                  <span className="lossDesc">{lang === "hi" ? "फास्फोरस नष्ट" : "Soil P destroyed"}</span>
                </div>

                <div className="lossCounterItem">
                  <span className="lossNutrientName">Potassium (K)</span>
                  <span className="lossAmount">
                    ~{analysisResult.burning_warning.nutrient_losses.potassium_kg} kg
                  </span>
                  <span className="lossDesc">{lang === "hi" ? "पोटाश नष्ट" : "Soil K destroyed"}</span>
                </div>

                <div className="lossCounterItem">
                  <span className="lossNutrientName">Sulfur (S)</span>
                  <span className="lossAmount">
                    ~{analysisResult.burning_warning.nutrient_losses.sulfur_kg} kg
                  </span>
                  <span className="lossDesc">{lang === "hi" ? "सल्फर नष्ट" : "Soil S destroyed"}</span>
                </div>

                <div className="lossCounterItem">
                  <span className="lossNutrientName">Organic Carbon</span>
                  <span className="lossAmount">
                    ~{analysisResult.burning_warning.nutrient_losses.organic_carbon_kg} kg
                  </span>
                  <span className="lossDesc">{lang === "hi" ? "जीवांश कार्बन नष्ट" : "Organic Humus"}</span>
                </div>
              </div>
            </div>

            <div className="burnEmissionsRow">
              <div className="emissionTag">
                <Wind size={15} />
                <span>
                  {lang === "hi" ? "बचाया गया CO₂ उत्सर्जन: " : "Prevented CO₂ emissions: "}
                  <strong>~{analysisResult.burning_warning.emissions_released.co2_tonnes} tonnes</strong>
                </span>
              </div>
              <div className="emissionTag">
                <ShieldAlert size={15} />
                <span>
                  {lang === "hi" ? "बचाया गया जहरीला धुआं (PM2.5/PM10): " : "Prevented Particulate Matter: "}
                  <strong>~{analysisResult.burning_warning.emissions_released.particulate_matter_pm_kg} kg</strong>
                </span>
              </div>
            </div>
          </div>

          {/* =================================================== */}
          {/* SECTION 9 & 15: TOP RECOMMENDED MANAGEMENT METHOD   */}
          {/* =================================================== */}
          {analysisResult.recommended_method && (
            <div className="card topRecommendedCard">
              <div className="topRecHeader">
                <div className="topRecLeft">
                  <span className="topRankBadge">
                    🏆 {lang === "hi" ? "सर्वोत्तम अनुशंसित विधि #1" : "RECOMMENDED METHOD #1"}
                  </span>
                  <h3>
                    {lang === "hi"
                      ? analysisResult.recommended_method.name_hi
                      : analysisResult.recommended_method.name}
                  </h3>
                </div>

                <div className="topScoreCircle">
                  <span className="scoreVal">{analysisResult.recommended_method.score}</span>
                  <span className="scoreMax">/100</span>
                  <small className="scoreSuit">
                    {lang === "hi"
                      ? analysisResult.recommended_method.suitability_hi
                      : analysisResult.recommended_method.suitability}
                  </small>
                </div>
              </div>

              <p className="topRecExplanation">{analysisResult.recommended_method.explanation}</p>

              {/* WHY MAITTRI RECOMMENDS THIS SECTION */}
              <div className="whyRecommendedBox">
                <h4>
                  <Sparkles size={16} color="#16a34a" />
                  <span>{lang === "hi" ? "मैत्री इसे क्यों अनुशंसित करती है?" : "Why MAITTRI Recommends This"}</span>
                </h4>
                <ul>
                  {analysisResult.recommended_method.why_recommended.map((reason, idx) => (
                    <li key={idx}>✓ {reason}</li>
                  ))}
                </ul>
              </div>

              {/* METHOD METRICS BAR */}
              <div className="methodMetricsGrid">
                <div className="metricTile">
                  <span className="tileLabel">{lang === "hi" ? "अनुमानित लागत / एकड़" : "Est. Cost / Acre"}</span>
                  <span className="tileValue">{analysisResult.recommended_method.estimated_cost_per_acre}</span>
                  <small>{lang === "hi" ? "कुल: " : "Total: "} {analysisResult.recommended_method.estimated_total_cost}</small>
                </div>

                <div className="metricTile">
                  <span className="tileLabel">{lang === "hi" ? "आवश्यक समय" : "Time Required"}</span>
                  <span className="tileValue">
                    {lang === "hi"
                      ? analysisResult.recommended_method.time_required_hi
                      : analysisResult.recommended_method.time_required}
                  </span>
                </div>

                <div className="metricTile">
                  <span className="tileLabel">{lang === "hi" ? "आवश्यक मशीनरी" : "Required Machinery"}</span>
                  <span className="tileValue machTag">
                    {(lang === "hi"
                      ? analysisResult.recommended_method.machinery_needed_hi
                      : analysisResult.recommended_method.machinery_needed
                    ).join(", ")}
                  </span>
                </div>

                <div className="metricTile">
                  <span className="tileLabel">{lang === "hi" ? "मृदा लाभ" : "Soil Benefit"}</span>
                  <span className="tileValue benefitBadge">
                    {lang === "hi"
                      ? analysisResult.recommended_method.soil_benefit_hi
                      : analysisResult.recommended_method.soil_benefit}
                  </span>
                </div>

                <div className="metricTile fullWidth">
                  <span className="tileLabel">{lang === "hi" ? "आर्थिक एवं पर्यावरणीय प्रभाव" : "Economic & Environmental Benefit"}</span>
                  <span className="tileValue economicText">
                    {lang === "hi"
                      ? analysisResult.recommended_method.economic_potential_hi
                      : analysisResult.recommended_method.economic_potential}
                  </span>
                </div>
              </div>

              <div className="costDisclaimerText">
                <Info size={14} />
                <span>
                  {lang === "hi"
                    ? analysisResult.recommended_method.cost_disclaimer_hi
                    : analysisResult.recommended_method.cost_disclaimer}
                </span>
              </div>
            </div>
          )}

          {/* =================================================== */}
          {/* SECTION 14: ALTERNATIVE METHODS COMPARISON TABLE   */}
          {/* =================================================== */}
          {analysisResult.alternative_methods && analysisResult.alternative_methods.length > 0 && (
            <div className="card methodComparisonCard">
              <div className="compCardHeader">
                <div>
                  <span className="eyebrowBadge">
                    <Layers size={14} />
                    <span>{lang === "hi" ? "तुलनात्मक विश्लेषण" : "METHOD COMPARISON"}</span>
                  </span>
                  <h3>{lang === "hi" ? "अन्य वैकल्पिक प्रबंधन विधियां" : "Alternative Compatible Methods"}</h3>
                </div>
                <p className="compSubtext">
                  {lang === "hi"
                    ? "अपनी परिस्थिति के अनुसार किसी भी विधि की कार्य योजना देखने के लिए उस पर क्लिक करें।"
                    : "Click any alternative method below to view its customized step-by-step action plan."}
                </p>
              </div>

              <div className="tableResponsiveWrapper">
                <table className="comparisonTable">
                  <thead>
                    <tr>
                      <th>{lang === "hi" ? "प्रबंधन विधि" : "Method"}</th>
                      <th>{lang === "hi" ? "स्कोर" : "Score"}</th>
                      <th>{lang === "hi" ? "अनुमानित लागत / एकड़" : "Approx. Cost / Acre"}</th>
                      <th>{lang === "hi" ? "समय" : "Time"}</th>
                      <th>{lang === "hi" ? "मशीनरी" : "Machinery"}</th>
                      <th>{lang === "hi" ? "मृदा लाभ" : "Soil Benefit"}</th>
                      <th>{lang === "hi" ? "कार्य योजना" : "Action Plan"}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Top recommended first in table */}
                    {analysisResult.recommended_method && (
                      <tr className={activeMethodId === analysisResult.recommended_method.method_id ? "activeRow" : ""}>
                        <td>
                          <strong>
                            ⭐ {lang === "hi" ? analysisResult.recommended_method.name_hi : analysisResult.recommended_method.name}
                          </strong>
                          <span className="topPill">{lang === "hi" ? "सर्वोत्तम" : "Top"}</span>
                        </td>
                        <td>
                          <span className="scorePill">{analysisResult.recommended_method.score}</span>
                        </td>
                        <td>{analysisResult.recommended_method.estimated_cost_per_acre}</td>
                        <td>
                          {lang === "hi"
                            ? analysisResult.recommended_method.time_required_hi
                            : analysisResult.recommended_method.time_required}
                        </td>
                        <td>
                          {(lang === "hi"
                            ? analysisResult.recommended_method.machinery_needed_hi
                            : analysisResult.recommended_method.machinery_needed
                          ).slice(0, 2).join(", ")}
                        </td>
                        <td>
                          <span className="badge high">
                            {lang === "hi"
                              ? analysisResult.recommended_method.soil_benefit_hi
                              : analysisResult.recommended_method.soil_benefit}
                          </span>
                        </td>
                        <td>
                          <button
                            type="button"
                            className={`smallActionBtn ${activeMethodId === analysisResult.recommended_method.method_id ? "active" : ""}`}
                            onClick={() => selectActionPlanMethod(analysisResult.recommended_method)}
                          >
                            {activeMethodId === analysisResult.recommended_method.method_id
                              ? (lang === "hi" ? "चयनित ✓" : "Viewing ✓")
                              : (lang === "hi" ? "योजना देखें" : "View Plan")}
                          </button>
                        </td>
                      </tr>
                    )}

                    {/* Alternatives */}
                    {analysisResult.alternative_methods.map((alt) => {
                      const isViewing = activeMethodId === alt.method_id;
                      return (
                        <tr key={alt.method_id} className={isViewing ? "activeRow" : ""}>
                          <td>
                            <strong>{lang === "hi" ? alt.name_hi : alt.name}</strong>
                          </td>
                          <td>
                            <span className="scorePill alt">{alt.score}</span>
                          </td>
                          <td>{alt.estimated_cost_per_acre}</td>
                          <td>{lang === "hi" ? alt.time_required_hi : alt.time_required}</td>
                          <td>
                            {(lang === "hi" ? alt.machinery_needed_hi : alt.machinery_needed).slice(0, 2).join(", ")}
                          </td>
                          <td>
                            <span className="badge med">
                              {lang === "hi" ? alt.soil_benefit_hi : alt.soil_benefit}
                            </span>
                          </td>
                          <td>
                            <button
                              type="button"
                              className={`smallActionBtn ${isViewing ? "active" : ""}`}
                              onClick={() => selectActionPlanMethod(alt)}
                            >
                              {isViewing
                                ? (lang === "hi" ? "चयनित ✓" : "Viewing ✓")
                                : (lang === "hi" ? "योजना देखें" : "View Plan")}
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* =================================================== */}
          {/* SECTION 13: 🌾 STEP-BY-STEP ACTION PLAN             */}
          {/* =================================================== */}
          <div className="card actionPlanCard">
            <div className="actionPlanHeader">
              <div className="actionPlanHeaderLeft">
                <span className="eyebrowBadge">
                  <CheckCircle2 size={14} />
                  <span>{lang === "hi" ? "मार्गदर्शिका" : "FIELD IMPLEMENTATION"}</span>
                </span>
                <h3>
                  {lang === "hi" ? "🌾 आपकी मैत्री कार्य योजना (Action Plan)" : "🌾 Your MAITTRI Action Plan"}
                </h3>
                <span className="activePlanMethodName">
                  {lang === "hi" ? activeActionPlan?.method_name_hi : activeActionPlan?.method_name}
                </span>
              </div>
            </div>

            {actionPlanLoading ? (
              <div className="planLoadingBox">
                <RefreshCw size={24} className="spinIcon" />
                <span>{lang === "hi" ? "कार्य योजना तैयार की जा रही है..." : "Generating custom action plan..."}</span>
              </div>
            ) : (
              <div className="actionStepsTimeline">
                {activeActionPlan?.steps?.map((step, sIdx) => (
                  <div key={sIdx} className="timelineStepItem">
                    <div className="timelineMarker">
                      <span className="stepNumberCircle">{step.step_num || sIdx + 1}</span>
                      {sIdx < activeActionPlan.steps.length - 1 && <div className="timelineLine"></div>}
                    </div>

                    <div className="timelineContent">
                      <h4 className="stepTitle">
                        STEP {step.step_num || sIdx + 1}: {step.title}
                      </h4>
                      <p className="stepDesc">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* =================================================== */}
          {/* SECTION 16 & 17: INTEGRATIONS (SOIL & WEATHER)      */}
          {/* =================================================== */}
          <div className="integrationsRow">
            {/* Soil Connection */}
            <div className="card integrationCard soil">
              <div className="intIconWrap">
                <FlaskConical size={24} color="#16a34a" />
              </div>
              <div className="intContent">
                <h4>{lang === "hi" ? "मृदा एवं पोषक तत्व संबंध" : "Soil & Nutrient Connection"}</h4>
                <p>
                  {lang === "hi"
                    ? "फसल अवशेषों को खेत में मिलाने से दीर्घकालिक जैविक कार्बन और सूक्ष्मजीव बढ़ते हैं। अपने खेत के पोषक तत्वों की स्थिति जानें।"
                    : "Returning organic residue enriches soil humus, biological flora, and moisture retention over cropping cycles."}
                </p>
                <Link to="/crop-farming/soil-nutrients" className="intLinkBtn">
                  <span>{lang === "hi" ? "मृदा एवं पोषक तत्व विश्लेषण देखें →" : "View Soil & Nutrient Analysis →"}</span>
                </Link>
              </div>
            </div>

            {/* Weather Operational Guidance */}
            <div className="card integrationCard weather">
              <div className="intIconWrap">
                <CloudSun size={24} color="#0284c7" />
              </div>
              <div className="intContent">
                <h4>{lang === "hi" ? "मौसम परिचालन सलाह" : "Weather Operational Guidance"}</h4>
                <p>
                  {lang === "hi"
                    ? analysisResult.weather_advisory?.operational_advice_hi
                    : analysisResult.weather_advisory?.operational_advice}
                </p>
                <Link to="/crop-farming/weather" className="intLinkBtn">
                  <span>{lang === "hi" ? "7-दिवसीय मौसम पूर्वानुमान देखें →" : "View 7-Day Weather Forecast →"}</span>
                </Link>
              </div>
            </div>
          </div>

          {/* =================================================== */}
          {/* SECTION 21 & 22: DATA SOURCES & SCIENTIFIC SAFETY   */}
          {/* =================================================== */}
          <div className="card citationsCard">
            <h4>{lang === "hi" ? "📜 प्रामाणिक अनुसंधान स्रोत एवं पारदर्शी सीमाएं" : "📜 Authentic Scientific Sources & Limitations"}</h4>

            <div className="citationsList">
              {analysisResult.scientific_citations?.map((cit, cIdx) => (
                <div key={cIdx} className="citItem">
                  <strong>{cit.organization}</strong>: {cit.topic} ({cit.reference})
                </div>
              ))}
            </div>

            <div className="limitationsBox">
              <strong>{lang === "hi" ? "महत्वपूर्ण वैज्ञानिक सुरक्षा सूचना:" : "Important Scientific Safety Notice:"}</strong>
              <ul>
                {analysisResult.limitations?.map((lim, lIdx) => (
                  <li key={lIdx}>{lim}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
