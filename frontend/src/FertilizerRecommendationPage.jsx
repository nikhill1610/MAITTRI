import React, { useState, useEffect } from "react";
import {
  Sprout, AlertTriangle, CheckCircle2, AlertCircle, HelpCircle,
  FlaskConical, ShieldCheck, ShieldAlert, Bug, Leaf, Calendar,
  CloudRain, Wind, Thermometer, Droplets, ExternalLink, FileText,
  Layers, History, Sparkles, TrendingUp, Info, Clock, ArrowRight,
  ChevronDown, ChevronUp, RefreshCw, Send, Radio
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";
import {
  T,
  translateCrop,
  translateSoil,
  translateNutrient,
  translateNutrientStatus,
  translateConfidence,
  translateReason,
  translateStage
} from "./i18n";

export default function FertilizerRecommendationPage() {
  const { lang, t } = useLang();

  // Farm and Field Context
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [loadingFarms, setLoadingFarms] = useState(false);

  // Form Inputs
  const [currentCrop, setCurrentCrop] = useState("Wheat");
  const [cropStage, setCropStage] = useState("Tillering");
  const [previousCrop, setPreviousCrop] = useState("Rice");
  const [prevCropHarvestSeason, setPrevCropHarvestSeason] = useState("Kharif (October/November)");
  const [residueHandling, setResidueHandling] = useState("removed");
  const [farmLocation, setFarmLocation] = useState("Uttar Pradesh");
  const [irrigation, setIrrigation] = useState("available");

  // Soil & Nutrient Inputs
  const [soilType, setSoilType] = useState("Alluvial soil");
  const [soilPh, setSoilPh] = useState("7.4");
  const [soilMoisture, setSoilMoisture] = useState("42");
  const [soilTemp, setSoilTemp] = useState("26");
  const [soilN, setSoilN] = useState("190");
  const [soilP, setSoilP] = useState("22");
  const [soilK, setSoilK] = useState("210");
  const [dataSource, setDataSource] = useState("sensor"); // laboratory, sensor, farmer_input, estimated

  // Secondary & Micronutrients
  const [showSecondaryMicro, setShowSecondaryMicro] = useState(false);
  const [soilS, setSoilS] = useState("");
  const [soilCa, setSoilCa] = useState("");
  const [soilMg, setSoilMg] = useState("");
  const [soilZn, setSoilZn] = useState("0.55");
  const [soilFe, setSoilFe] = useState("");
  const [soilB, setSoilB] = useState("");
  const [soilMn, setSoilMn] = useState("");
  const [soilCu, setSoilCu] = useState("");

  // Pest & Disease Observation
  const [pestObserved, setPestObserved] = useState("");
  const [diseaseObserved, setDiseaseObserved] = useState("");
  const [pestSymptoms, setPestSymptoms] = useState("");
  const [affectedAreaPct, setAffectedAreaPct] = useState("");

  // Weather State
  const [weatherAlerts, setWeatherAlerts] = useState([]);
  const [loadingWeather, setLoadingWeather] = useState(false);

  // Output Recommendation Data
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recommendation, setRecommendation] = useState(null);

  // Farm History Modal & Log
  const [historyRecords, setHistoryRecords] = useState([]);
  const [loggedApplications, setLoggedApplications] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [logSuccess, setLogSuccess] = useState("");

  // Load user's farms on mount
  useEffect(() => {
    loadUserFarms();
  }, []);

  const loadUserFarms = async () => {
    setLoadingFarms(true);
    try {
      const res = await api.get("/farms");
      if (res.data && res.data.length > 0) {
        setFarms(res.data);
        const f0 = res.data[0];
        setSelectedFarmId(String(f0.id));
        applyFarmData(f0);
      }
    } catch {
      // Unauthenticated or offline fallback
    } finally {
      setLoadingFarms(false);
    }
  };

  const applyFarmData = (farm) => {
    if (!farm) return;
    if (farm.soil_type) setSoilType(farm.soil_type);
    if (farm.previous_crop) setPreviousCrop(farm.previous_crop);
    if (farm.current_crop) setCurrentCrop(farm.current_crop);
    if (farm.soil_ph != null) setSoilPh(String(farm.soil_ph));
    if (farm.soil_n != null) setSoilN(String(farm.soil_n));
    if (farm.soil_p != null) setSoilP(String(farm.soil_p));
    if (farm.soil_k != null) setSoilK(String(farm.soil_k));
    if (farm.location_name) setFarmLocation(farm.location_name);
    if (farm.irrigation) setIrrigation(farm.irrigation);
  };

  const handleFarmSelect = (id) => {
    setSelectedFarmId(id);
    const f = farms.find((farm) => String(farm.id) === String(id));
    if (f) applyFarmData(f);
  };

  // Load Sensor Live Reading
  const loadSensorReading = async () => {
    try {
      const url = selectedFarmId ? `/fertilizer/sensor-latest?farm_id=${selectedFarmId}` : "/fertilizer/sensor-latest";
      const res = await api.get(url);
      if (res.data && res.data.values) {
        const v = res.data.values;
        if (v.nitrogen != null) setSoilN(String(v.nitrogen));
        if (v.phosphorus != null) setSoilP(String(v.phosphorus));
        if (v.potassium != null) setSoilK(String(v.potassium));
        if (v.ph != null) setSoilPh(String(v.ph));
        if (v.moisture != null) setSoilMoisture(String(v.moisture));
        if (v.temperature != null) setSoilTemp(String(v.temperature));
        setDataSource("sensor");
      }
    } catch {
      alert(lang === "hi" ? "सेंसर रीडिंग लोड करने में विफल।" : "Failed to load sensor reading.");
    }
  };

  // Run Recommendation Analysis
  const handleGenerateRecommendation = async () => {
    setLoading(true);
    setError("");
    setRecommendation(null);

    const payload = {
      farm_id: selectedFarmId ? Number(selectedFarmId) : null,
      current_crop: currentCrop,
      previous_crop: previousCrop,
      previous_crop_harvest_season: prevCropHarvestSeason,
      crop_stage: cropStage,
      soil_type: soilType,
      soil_ph: soilPh ? parseFloat(soilPh) : null,
      soil_moisture: soilMoisture ? parseFloat(soilMoisture) : null,
      soil_temperature: soilTemp ? parseFloat(soilTemp) : null,
      soil_n: soilN ? parseFloat(soilN) : null,
      soil_p: soilP ? parseFloat(soilP) : null,
      soil_k: soilK ? parseFloat(soilK) : null,
      secondary_nutrients: {
        sulphur: soilS ? parseFloat(soilS) : null,
        calcium: soilCa ? parseFloat(soilCa) : null,
        magnesium: soilMg ? parseFloat(soilMg) : null,
      },
      micronutrients: {
        zinc: soilZn ? parseFloat(soilZn) : null,
        iron: soilFe ? parseFloat(soilFe) : null,
        boron: soilB ? parseFloat(soilB) : null,
        manganese: soilMn ? parseFloat(soilMn) : null,
        copper: soilCu ? parseFloat(soilCu) : null,
      },
      data_source: dataSource,
      farm_location: farmLocation,
      irrigation: irrigation,
      pest_observed: pestObserved,
      disease_observed: diseaseObserved,
      pest_symptoms: pestSymptoms,
      affected_area_pct: affectedAreaPct ? parseFloat(affectedAreaPct) : null,
      residue_handling: residueHandling,
      include_weather: true
    };

    try {
      const res = await api.post("/fertilizer/recommend", payload);
      setRecommendation(res.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        (lang === "hi"
          ? "सिफारिश तैयार करने में असमर्थ। कृपया प्रविष्टियों की जांच करें।"
          : "Failed to generate recommendation. Please check inputs.")
      );
    } finally {
      setLoading(false);
    }
  };

  // Fetch History
  const fetchHistory = async () => {
    setShowHistory(true);
    try {
      const url = selectedFarmId ? `/fertilizer/history?farm_id=${selectedFarmId}` : "/fertilizer/history";
      const res = await api.get(url);
      setHistoryRecords(res.data.recommendations || []);
      setLoggedApplications(res.data.logged_applications || []);
    } catch {
      // silent
    }
  };

  return (
    <div className="content">
      {/* Brand Hero Banner */}
      <div className="fertHero">
        <div className="fertHeroBadge">
          <Sparkles size={14} /> {lang === "hi" ? "मैत्री स्मार्ट कृषि निर्णय प्रणाली" : "MAITTRI Smart Decision Engine"}
        </div>
        <h1 className="fertHeroTitle">
          {lang === "hi" ? "उर्वरक एवं कीट प्रबंधन सिफारिश" : "Evidence-Based Fertilizer & Pest Decision Support"}
        </h1>
        <p className="fertHeroSubtitle">
          {lang === "hi"
            ? "वैज्ञानिक मृदा-परीक्षण, पिछली फसल ह्रास, फसल विकास चरण और मौसम पर आधारित विश्वसनीय निर्णय — बिना अंधाधुंध रासायनिक प्रयोग के।"
            : "Scientific, soil-test grounded decisions based on crop uptake curves, previous rotation depletion, growth stages, and live weather."}
        </p>
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <button className="button secondary" onClick={fetchHistory} style={{ background: "rgba(255,255,255,0.15)", color: "#fff", border: "1px solid rgba(255,255,255,0.3)" }}>
            <History size={15} /> {lang === "hi" ? "खेत का इतिहास देखें" : "View Farm History"}
          </button>
        </div>
      </div>

      {/* Farm Context Bar */}
      <div className="fertContextBar">
        <div className="fertContextLeft">
          <Sprout size={20} style={{ color: "#16a34a" }} />
          <div>
            <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>
              {lang === "hi" ? "खेत का चयन करें" : "SELECT REGISTERED FARM"}
            </div>
            <select
              value={selectedFarmId}
              onChange={(e) => handleFarmSelect(e.target.value)}
              className="fertSelect"
              style={{ padding: "4px 8px", fontSize: "14px", fontWeight: 700 }}
            >
              <option value="">{lang === "hi" ? "-- कस्टम / बिना सहेजा खेत --" : "-- Custom / Ad-hoc Field --"}</option>
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({f.area} {f.area_unit}) · {f.soil_type}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="fertContextRight">
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "12px", color: "#64748b", fontWeight: 600 }}>
              {lang === "hi" ? "डेटा स्रोत:" : "DATA SOURCE:"}
            </span>
            <div className="fertSourceToggle">
              <button
                type="button"
                className={`fertSourceBtn ${dataSource === "laboratory" ? "active" : ""}`}
                onClick={() => setDataSource("laboratory")}
              >
                🧪 {lang === "hi" ? "लैब टेस्ट" : "Lab Test"}
              </button>
              <button
                type="button"
                className={`fertSourceBtn ${dataSource === "sensor" ? "active" : ""}`}
                onClick={() => { setDataSource("sensor"); loadSensorReading(); }}
              >
                <span className="sensorPulseDot" /> 📡 {lang === "hi" ? "IoT सेंसर" : "IoT Sensor"}
              </button>
              <button
                type="button"
                className={`fertSourceBtn ${dataSource === "farmer_input" ? "active" : ""}`}
                onClick={() => setDataSource("farmer_input")}
              >
                👨‍🌾 {lang === "hi" ? "किसान प्रविष्टि" : "Farmer Input"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Input Form Cards */}
      <div className="fertFormGrid">
        {/* Card 1: Crop Context */}
        <div className="fertFormCard">
          <h3 className="fertFormCardTitle">
            <Leaf size={18} /> {lang === "hi" ? "1. वर्तमान फसल विवरण" : "1. Farm & Current Crop"}
          </h3>
          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "वर्तमान फसल" : "Current Crop"}</label>
            <select value={currentCrop} onChange={(e) => setCurrentCrop(e.target.value)} className="fertSelect">
              <option value="Wheat">Wheat (गेहूं)</option>
              <option value="Rice">Rice / Paddy (धान / चावल)</option>
              <option value="Mustard">Mustard (सरसों / राई)</option>
              <option value="Maize">Maize (मक्का)</option>
              <option value="Potato">Potato (आलू)</option>
              <option value="Tomato">Tomato (टमाटर)</option>
              <option value="Gram">Gram / Chickpea (चना)</option>
              <option value="Cotton">Cotton (कपास)</option>
              <option value="Sugarcane">Sugarcane (गन्ना)</option>
            </select>
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "फसल विकास चरण" : "Current Growth Stage"}</label>
            <select value={cropStage} onChange={(e) => setCropStage(e.target.value)} className="fertSelect">
              <option value="Basal / Sowing">Basal / Sowing (बुवाई / रोपाई)</option>
              <option value="Crown Root Initiation (CRI)">Crown Root Initiation - CRI (ताज जड़ निकलना)</option>
              <option value="Tillering">Tillering / Early Vegetative (कल्ले फूटना / वानस्पतिक)</option>
              <option value="Jointing / Formative">Jointing / Formative (गांठ बनना)</option>
              <option value="Flowering / Heading">Flowering / Heading (फूल / बालियां आना)</option>
              <option value="Grain Filling / Bulking">Grain Filling / Bulking (दाना भराव / कंद विकास)</option>
              <option value="Maturity">Maturity (परिपक्वता)</option>
            </select>
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "राज्य / जिला स्थान" : "Location / State"}</label>
            <input
              type="text"
              value={farmLocation}
              onChange={(e) => setFarmLocation(e.target.value)}
              className="fertInput"
              placeholder="e.g. Uttar Pradesh, Lucknow"
            />
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "सिंचाई उपलब्धता" : "Irrigation Status"}</label>
            <select value={irrigation} onChange={(e) => setIrrigation(e.target.value)} className="fertSelect">
              <option value="available">{lang === "hi" ? "सुनिश्चित सिंचाई उपलब्ध" : "Assured / Available"}</option>
              <option value="limited">{lang === "hi" ? "सीमित सिंचाई" : "Limited Irrigation"}</option>
              <option value="rainfed">{lang === "hi" ? "वर्षा आधारित (असिंचित)" : "Rainfed / Unirrigated"}</option>
            </select>
          </div>
        </div>

        {/* Card 2: Previous Crop & Rotation */}
        <div className="fertFormCard">
          <h3 className="fertFormCardTitle">
            <Calendar size={18} /> {lang === "hi" ? "2. पिछली फसल एवं फसल चक्र" : "2. Previous Crop & History"}
          </h3>
          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "पिछली फसल" : "Previous Crop"}</label>
            <select value={previousCrop} onChange={(e) => setPreviousCrop(e.target.value)} className="fertSelect">
              <option value="Rice">Rice / Paddy (धान / चावल)</option>
              <option value="Wheat">Wheat (गेहूं)</option>
              <option value="Maize">Maize (मक्का)</option>
              <option value="Gram">Gram / Chickpea / Legume (चना / दलहन)</option>
              <option value="Potato">Potato (आलू)</option>
              <option value="Mustard">Mustard (सरसों)</option>
              <option value="Cotton">Cotton (कपास)</option>
              <option value="Sugarcane">Sugarcane (गन्ना)</option>
              <option value="Fallow">None / Fallow (परती खेत)</option>
            </select>
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "कटाई का मौसम / समय" : "Harvesting Season / Date"}</label>
            <input
              type="text"
              value={prevCropHarvestSeason}
              onChange={(e) => setPrevCropHarvestSeason(e.target.value)}
              className="fertInput"
              placeholder="e.g. Kharif (October/November)"
            />
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "पराली / अवशेष प्रबंधन" : "Crop Residue Handling"}</label>
            <select value={residueHandling} onChange={(e) => setResidueHandling(e.target.value)} className="fertSelect">
              <option value="removed">{lang === "hi" ? "खेत से बाहर हटाया गया" : "Residue Removed"}</option>
              <option value="incorporated">{lang === "hi" ? "मिट्टी में मिलाया / जोता गया" : "Incorporated in Soil"}</option>
              <option value="mulched">{lang === "hi" ? "सतह पर मल्चिंग की गई" : "Mulched on Surface"}</option>
            </select>
            <span className="fertFormHint">
              {lang === "hi"
                ? "मिट्टी में मिलाए गए अवशेष C:N अनुपात और नाइट्रोजन उपलब्धता को प्रभावित करते हैं।"
                : "Incorporated straw influences initial C:N microbial immobilization."}
            </span>
          </div>
        </div>

        {/* Card 3: Soil & NPK Inputs */}
        <div className="fertFormCard">
          <h3 className="fertFormCardTitle">
            <FlaskConical size={18} /> {lang === "hi" ? "3. मिट्टी एवं पोषक तत्व स्थिति" : "3. Soil & Nutrient Status"}
          </h3>
          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "मिट्टी का प्रकार" : "Soil Type"}</label>
            <select value={soilType} onChange={(e) => setSoilType(e.target.value)} className="fertSelect">
              <option value="Alluvial soil">Alluvial soil (जलोढ़ मिट्टी)</option>
              <option value="Black soil">Black soil (काली मिट्टी / रेगुड़)</option>
              <option value="Red soil">Red soil (लाल मिट्टी)</option>
              <option value="Laterite soil">Laterite soil (लैटेराइट मिट्टी)</option>
              <option value="Desert/arid soil">Desert / Arid soil (मरुस्थलीय मिट्टी)</option>
              <option value="Mountain/forest soil">Mountain / Forest soil (पर्वतीय मिट्टी)</option>
              <option value="Loamy soil">Loamy soil (दोमट मिट्टी)</option>
              <option value="Sandy loam">Sandy loam (बलुई दोमट)</option>
              <option value="Clay loam">Clay loam (चिकनी दोमट)</option>
              <option value="Sandy soil">Sandy soil (बलुई मिट्टी)</option>
              <option value="Clay soil">Clay soil (चिकनी मिट्टी)</option>
            </select>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            <div className="fertFormGroup">
              <label className="fertFormLabel">
                {lang === "hi" ? "मृदा pH" : "Soil pH"}
                <span className="fertFormHint">{lang === "hi" ? "(वैकल्पिक)" : "(Optional)"}</span>
              </label>
              <input
                type="number"
                step="0.1"
                min="3.0"
                max="11.5"
                value={soilPh}
                onChange={(e) => setSoilPh(e.target.value)}
                className="fertInput"
                placeholder="e.g. 7.4"
              />
            </div>
            <div className="fertFormGroup">
              <label className="fertFormLabel">
                {lang === "hi" ? "नमी %" : "Moisture %"}
                <span className="fertFormHint">{lang === "hi" ? "(वैकल्पिक)" : "(Optional)"}</span>
              </label>
              <input
                type="number"
                step="1"
                min="0"
                max="100"
                value={soilMoisture}
                onChange={(e) => setSoilMoisture(e.target.value)}
                className="fertInput"
                placeholder="e.g. 42"
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
            <div className="fertFormGroup">
              <label className="fertFormLabel">N (kg/ha)</label>
              <input
                type="number"
                value={soilN}
                onChange={(e) => setSoilN(e.target.value)}
                className="fertInput"
                placeholder="190"
              />
            </div>
            <div className="fertFormGroup">
              <label className="fertFormLabel">P (kg/ha)</label>
              <input
                type="number"
                value={soilP}
                onChange={(e) => setSoilP(e.target.value)}
                className="fertInput"
                placeholder="22"
              />
            </div>
            <div className="fertFormGroup">
              <label className="fertFormLabel">K (kg/ha)</label>
              <input
                type="number"
                value={soilK}
                onChange={(e) => setSoilK(e.target.value)}
                className="fertInput"
                placeholder="210"
              />
            </div>
          </div>

          <button
            type="button"
            className="button secondary"
            style={{ fontSize: "12px", padding: "6px 10px", marginTop: "4px" }}
            onClick={() => setShowSecondaryMicro(!showSecondaryMicro)}
          >
            {showSecondaryMicro ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {lang === "hi" ? "सूक्ष्म व द्वितीयक पोषक तत्व दर्ज करें" : "Secondary & Micronutrients (Zn, S, etc.)"}
          </button>

          {showSecondaryMicro && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", background: "#f8fafc", padding: "10px", borderRadius: "8px", marginTop: "6px" }}>
              <input type="number" step="0.1" placeholder="Zinc (Zn ppm)" value={soilZn} onChange={e => setSoilZn(e.target.value)} className="fertInput" />
              <input type="number" step="0.1" placeholder="Sulphur (S ppm)" value={soilS} onChange={e => setSoilS(e.target.value)} className="fertInput" />
              <input type="number" step="0.1" placeholder="Iron (Fe ppm)" value={soilFe} onChange={e => setSoilFe(e.target.value)} className="fertInput" />
              <input type="number" step="0.1" placeholder="Boron (B ppm)" value={soilB} onChange={e => setSoilB(e.target.value)} className="fertInput" />
            </div>
          )}
        </div>

        {/* Card 4: Pest & Disease Evidence */}
        <div className="fertFormCard">
          <h3 className="fertFormCardTitle">
            <Bug size={18} /> {lang === "hi" ? "4. कीट एवं रोग अवलोकन (साक्ष्य)" : "4. Pest & Disease Observation"}
          </h3>
          <div className="fertFormGroup">
            <label className="fertFormLabel">
              {lang === "hi" ? "देखा गया कीट (यदि कोई हो)" : "Pest Observed"}
              <span className="fertFormHint">{lang === "hi" ? "(साक्ष्य आवश्यक)" : "(Optional/Evidence)"}</span>
            </label>
            <input
              type="text"
              value={pestObserved}
              onChange={(e) => setPestObserved(e.target.value)}
              className="fertInput"
              placeholder="e.g. Aphids, Yellow Rust, Stem Borer, or None"
            />
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "लक्षणों का विवरण" : "Observed Symptoms"}</label>
            <input
              type="text"
              value={pestSymptoms}
              onChange={(e) => setPestSymptoms(e.target.value)}
              className="fertInput"
              placeholder="e.g. Yellow stripes on leaves, drying tips, leaf holes"
            />
          </div>

          <div className="fertFormGroup">
            <label className="fertFormLabel">{lang === "hi" ? "प्रभावित क्षेत्रफल %" : "Affected Area %"}</label>
            <input
              type="number"
              min="0"
              max="100"
              value={affectedAreaPct}
              onChange={(e) => setAffectedAreaPct(e.target.value)}
              className="fertInput"
              placeholder="e.g. 10%"
            />
          </div>

          <div style={{ background: "#fef3c7", padding: "8px 12px", borderRadius: "8px", fontSize: "12px", color: "#92400e", display: "flex", gap: "6px" }}>
            <AlertTriangle size={16} style={{ flexShrink: 0 }} />
            <span>
              {lang === "hi"
                ? "सुरक्षा नियम: बिना कीट साक्ष्य के कीटनाशक की सिफारिश नहीं की जाएगी। केवल निगरानी की सलाह दी जाएगी।"
                : "Safety Rule: No chemical pesticide is prescribed without verified pest evidence. IPM monitoring is default."}
            </span>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="fertActionBanner">
        <div>
          <div style={{ fontWeight: 700, fontSize: "16px", color: "#14532d" }}>
            {lang === "hi" ? "साक्ष्य-आधारित विश्लेषण प्रारंभ करें" : "Ready for Evidence-Based Agronomic Synthesis?"}
          </div>
          <div style={{ fontSize: "13px", color: "#475569" }}>
            {lang === "hi"
              ? "MAITTRI फसल चक्र, मृदा पोषण, और मौसम का बहु-आयामी वैज्ञानिक विश्लेषण तैयार करेगा।"
              : "MAITTRI will evaluate crop uptake curves, previous rotation exhaustion, and live weather safety."}
          </div>
        </div>
        <button
          className="fertActionBtn"
          onClick={handleGenerateRecommendation}
          disabled={loading}
        >
          {loading ? (
            <>
              <RefreshCw size={18} className="spin" />
              {lang === "hi" ? "विश्लेषण किया जा रहा है..." : "Synthesizing Evidence..."}
            </>
          ) : (
            <>
              <Sparkles size={18} />
              {lang === "hi" ? "उर्वरक एवं कीट सिफारिश प्राप्त करें" : "Generate Recommendation"}
            </>
          )}
        </button>
      </div>

      {error && (
        <div className="feedbackBanner error" style={{ marginBottom: "20px" }}>
          <AlertTriangle size={18} /> {error}
        </div>
      )}

      {/* Output Sections A to L */}
      {recommendation && (
        <div className="fertSectionWrapper">
          {/* Section A: Soil & Crop Analysis */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">A</span>
                {lang === "hi" ? "मृदा एवं फसल विश्लेषण" : "Soil & Crop Analysis"}
              </div>
              <span className="fertHeroBadge">
                {recommendation.farm_context.current_crop} · {recommendation.farm_context.crop_stage}
              </span>
            </div>

            <div className="fertSubgrid">
              <div className="fertInfoCard">
                <div className="fertInfoCardTitle">
                  <Leaf size={16} style={{ color: "#16a34a" }} />
                  {lang === "hi" ? "वर्तमान फसल मांग" : "Current Crop Demands"}
                </div>
                <div style={{ fontSize: "13.5px", lineHeight: "1.5", color: "#334155" }}>
                  {recommendation.section_A_soil_crop_analysis.current_crop.summary}
                </div>
                <div style={{ fontSize: "12px", color: "#64748b" }}>
                  <b>{lang === "hi" ? "मुख्य पोषक तत्व:" : "Heavy Uptake:"}</b> {recommendation.section_A_soil_crop_analysis.current_crop.heavy_uptake.join(", ")}
                </div>
              </div>

              <div className="fertInfoCard">
                <div className="fertInfoCardTitle">
                  <Calendar size={16} style={{ color: "#d97706" }} />
                  {lang === "hi" ? "पिछली फसल का प्रभाव" : "Previous Crop Interaction"}
                </div>
                <div style={{ fontSize: "13.5px", lineHeight: "1.5", color: "#334155" }}>
                  {recommendation.section_A_soil_crop_analysis.previous_crop.soil_effect}
                </div>
                <div style={{ fontSize: "12px", color: "#15803d", fontWeight: 600 }}>
                  💡 {recommendation.section_A_soil_crop_analysis.previous_crop.agronomic_hint}
                </div>
              </div>

              <div className="fertInfoCard">
                <div className="fertInfoCardTitle">
                  <FlaskConical size={16} style={{ color: "#2563eb" }} />
                  {lang === "hi" ? "मृदा विशेषता एवं pH" : "Soil Properties & pH"}
                </div>
                <div style={{ fontSize: "13.5px", color: "#334155" }}>
                  <b>{recommendation.section_A_soil_crop_analysis.soil.soil_type}</b>
                </div>
                <div style={{ fontSize: "13px", color: "#475569" }}>
                  {recommendation.section_A_soil_crop_analysis.soil.characteristics.inherent_nutrients}
                </div>
                <div style={{ fontSize: "12px", color: "#0f766e" }}>
                  {recommendation.section_A_soil_crop_analysis.soil.ph_analysis.badge}: {recommendation.section_A_soil_crop_analysis.soil.ph_analysis.agronomic_implication}
                </div>
              </div>
            </div>
          </div>

          {/* Section B: Available Nutrient Status */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">B</span>
                {lang === "hi" ? "पोषक तत्व स्थिति एवं वर्गीकरण" : "Available Nutrient Status"}
              </div>
              <div style={{ fontSize: "12px", display: "flex", gap: "8px", alignItems: "center" }}>
                <span style={{ fontWeight: 700 }}>{lang === "hi" ? "स्रोत:" : "Source:"}</span>
                <span style={{ background: "#f1f5f9", padding: "3px 8px", borderRadius: "6px", fontWeight: 600, color: "#1e293b" }}>
                  {recommendation.section_B_nutrient_status.source}
                </span>
              </div>
            </div>

            {recommendation.section_B_nutrient_status.is_sensor && (
              <div style={{ background: "#f0fdf4", border: "1px solid #86efac", padding: "8px 14px", borderRadius: "8px", fontSize: "12.5px", color: "#166534", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                <span className="sensorPulseDot" />
                <span><b>{lang === "hi" ? "सेंसर आधारित संकेत:" : "Sensor-based reading:"}</b> {recommendation.section_B_nutrient_status.sensor_caveat}</span>
              </div>
            )}

            <div className="fertNutrientsGrid">
              {recommendation.section_B_nutrient_status.nutrients.map((n) => {
                const st = n.status.toLowerCase();
                return (
                  <div key={n.nutrient} className={`fertNutrientCell ${st}`}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <b style={{ fontSize: "14px", color: "#1e293b" }}>{n.nutrient} ({n.symbol})</b>
                      <span className={`statusBadge ${st}`}>{n.status}</span>
                    </div>
                    <div style={{ fontSize: "16px", fontWeight: 800, color: "#0f2e17" }}>
                      {n.value != null ? `${n.value} ${n.unit}` : (lang === "hi" ? "मापा नहीं गया" : "Not measured")}
                    </div>
                    <div style={{ fontSize: "11.5px", color: "#64748b", lineHeight: "1.3" }}>
                      {n.detail}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section C: Fertilizer Recommendation Strategy */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">C</span>
                {lang === "hi" ? "उर्वरक प्रबंधन रणनीति" : "Core Fertilizer Strategy"}
              </div>
              <span className="statusBadge adequate">{recommendation.section_C_fertilizer_recommendation.approach}</span>
            </div>
            <div style={{ background: "#f0fdf4", border: "1.5px solid #bbf7d0", borderRadius: "12px", padding: "18px", color: "#14532d", lineHeight: "1.5" }}>
              <h4 style={{ margin: "0 0 8px", fontSize: "16px", fontWeight: 800 }}>
                {recommendation.section_C_fertilizer_recommendation.title}
              </h4>
              <p style={{ margin: "0 0 10px", fontSize: "14px" }}>
                {recommendation.section_C_fertilizer_recommendation.summary}
              </p>
              <div style={{ fontSize: "13px", color: "#166534" }}>
                🌿 <b>{lang === "hi" ? "जैविक कार्बन सुरक्षा:" : "Soil Carbon Action:"}</b> {recommendation.section_C_fertilizer_recommendation.soil_carbon_action}
              </div>
              <div style={{ fontSize: "13px", color: "#166534", marginTop: "4px" }}>
                🎯 <b>{lang === "hi" ? "चरण-विशिष्ट सलाह:" : "Stage Specific Advice:"}</b> {recommendation.section_C_fertilizer_recommendation.stage_specific_advice}
              </div>
            </div>
          </div>

          {/* Section D: Natural / Organic Alternatives */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">D</span>
                {lang === "hi" ? "प्राकृतिक एवं जैविक विकल्प" : "Natural & Organic Alternatives"}
              </div>
              <span style={{ fontSize: "12px", color: "#15803d", fontWeight: 700 }}>
                🌱 {lang === "hi" ? "मृदा स्वास्थ्य संवर्धन" : "Soil Health & Carbon First"}
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {recommendation.section_D_organic_alternatives.map((opt, idx) => (
                <div key={idx} className="fertOptionCard organic">
                  <div className="fertOptionTitle">
                    <span>{opt.name}</span>
                    <span className="fertOptionCat">{opt.category}</span>
                  </div>
                  <div style={{ fontSize: "13.5px", color: "#334155" }}>
                    <b>{lang === "hi" ? "पोषक तत्व योगदान:" : "Nutrient Contribution:"}</b> {opt.active_contribution}
                  </div>
                  <div style={{ fontSize: "13px", color: "#475569" }}>
                    <b>{lang === "hi" ? "मृदा को लाभ:" : "Soil Benefit:"}</b> {opt.soil_benefit}
                  </div>
                  <div style={{ fontSize: "13px", color: "#15803d" }}>
                    <b>{lang === "hi" ? "प्रयोग विधि व समय:" : "How & When to Apply:"}</b> {opt.application_timing} — {opt.how_to_use}
                  </div>
                  <div style={{ fontSize: "12px", color: "#991b1b", background: "#fee2e2", padding: "4px 8px", borderRadius: "6px" }}>
                    ⚠️ <b>{lang === "hi" ? "सीमाएं:" : "Limitations:"}</b> {opt.limitations}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>
                    {lang === "hi" ? "स्रोत:" : "Source:"} {opt.source}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section E: Chemical Fertilizer Options */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">E</span>
                {lang === "hi" ? "रासायनिक उर्वरक विकल्प (साक्ष्य आधारित)" : "Chemical Fertilizer Options"}
              </div>
              <span style={{ fontSize: "12px", color: "#0284c7", fontWeight: 700 }}>
                ⚗️ {lang === "hi" ? "केवल आवश्यकतानुसार लक्षित प्रयोग" : "Applied Only If Justified"}
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {recommendation.section_E_chemical_fertilizer_options.map((opt, idx) => (
                <div key={idx} className="fertOptionCard chemical">
                  <div className="fertOptionTitle">
                    <span>{opt.name}</span>
                    <span className="fertOptionCat">{opt.category}</span>
                  </div>
                  <div style={{ fontSize: "13.5px", color: "#334155" }}>
                    <b>{lang === "hi" ? "सक्रिय तत्व:" : "Active Nutrient:"}</b> {opt.active_nutrient}
                  </div>
                  <div style={{ fontSize: "13px", color: "#475569" }}>
                    <b>{lang === "hi" ? "सिफारिश का कारण:" : "Why Recommended:"}</b> {opt.why_recommended}
                  </div>
                  <div style={{ fontSize: "13px", color: "#0369a1" }}>
                    <b>{lang === "hi" ? "प्रयोग का सही चरण व विधि:" : "Stage & Method:"}</b> {opt.appropriate_stage} ({opt.application_method})
                  </div>
                  <div style={{ fontSize: "12px", color: "#b45309", background: "#fef3c7", padding: "6px 10px", borderRadius: "6px" }}>
                    ⚠️ <b>{lang === "hi" ? "सावधानी:" : "Precaution:"}</b> {opt.precautions}
                  </div>
                  <div style={{ fontSize: "12px", color: "#475569", fontStyle: "italic" }}>
                    📋 {opt.dosage_note}
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b" }}>
                    {lang === "hi" ? "स्रोत:" : "Source:"} {opt.source}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section F & G: Pest Management */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">F</span>
                {lang === "hi" ? "कीट एवं रोग प्रबंधन" : "Integrated Pest Management (IPM)"}
              </div>
              <span className={`statusBadge ${recommendation.section_F_pest_disease_analysis.evidence_found ? "warning" : "adequate"}`}>
                {recommendation.section_F_pest_disease_analysis.status}
              </span>
            </div>

            {!recommendation.section_F_pest_disease_analysis.evidence_found ? (
              <div style={{ background: "#f0fdf4", border: "1.5px solid #86efac", borderRadius: "12px", padding: "20px", color: "#14532d" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                  <ShieldCheck size={24} style={{ color: "#16a34a" }} />
                  <h4 style={{ margin: 0, fontSize: "16px", fontWeight: 800 }}>
                    {lang === "hi" ? "कोई पुष्ट कीट/रोग साक्ष्य नहीं पाया गया" : "No Confirmed Pest / Disease Evidence"}
                  </h4>
                </div>
                <p style={{ margin: "0 0 14px", fontSize: "14px", lineHeight: "1.5" }}>
                  {lang === "hi"
                    ? "सुरक्षा नियम: बिना किसी कीट अथवा रोग लक्षण के कीटनाशक का प्रयोग निषिद्ध है। अनावश्यक छिड़काव से मित्र कीट नष्ट होते हैं और खर्च बढ़ता है। नियमित निगरानी जारी रखें।"
                    : "No confirmed pest/disease evidence. Preventive monitoring is recommended instead of unnecessary pesticide application. Routine chemical sprays kill natural beneficial predators and accelerate pest resistance."}
                </p>
                <div style={{ fontSize: "13px", fontWeight: 700, marginBottom: "6px" }}>
                  {lang === "hi" ? "अनुशंसित निवारक कदम:" : "Recommended Preventive Actions:"}
                </div>
                <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "13px", lineHeight: "1.6" }}>
                  {recommendation.section_H_natural_pest_management.options.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div>
                <div style={{ background: "#fffbeb", border: "1.5px solid #fcd34d", borderRadius: "12px", padding: "16px", marginBottom: "16px" }}>
                  <h4 style={{ margin: "0 0 6px", color: "#92400e", fontSize: "16px" }}>
                    🐛 {lang === "hi" ? "लक्षित कीट/रोग:" : "Target Identified:"} {recommendation.section_F_pest_disease_analysis.target_name}
                  </h4>
                  <p style={{ margin: 0, fontSize: "13.5px", color: "#78350f" }}>
                    {recommendation.section_F_pest_disease_analysis.symptoms}
                  </p>
                </div>

                {/* Section H: Biological Controls First */}
                <div style={{ marginBottom: "20px" }}>
                  <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#14532d", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span className="fertSectionLetter">H</span>
                    {lang === "hi" ? "प्राकृतिक व जैविक नियंत्रण (पहले अपनाएं)" : "Natural & Biological Control (Try/Consider First)"}
                  </h4>
                  <ul style={{ paddingLeft: "20px", fontSize: "13.5px", lineHeight: "1.6", color: "#334155" }}>
                    {recommendation.section_H_natural_pest_management.options.map((opt, idx) => (
                      <li key={idx} style={{ marginBottom: "6px" }}>{opt}</li>
                    ))}
                  </ul>
                </div>

                {/* Section G: Chemical Pesticide (Only when justified) */}
                {recommendation.section_G_chemical_pesticide_options.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#991b1b", display: "flex", alignItems: "center", gap: "6px" }}>
                      <span className="fertSectionLetter" style={{ background: "#991b1b" }}>G</span>
                      {lang === "hi" ? "रासायनिक कीटनाशक विकल्प (केवल आर्थिक क्षति सीमा पर)" : "Chemical Pesticide Options (When ETL is Crossed)"}
                    </h4>
                    {recommendation.section_G_chemical_pesticide_options.map((chem, idx) => (
                      <div key={idx} className="fertOptionCard" style={{ borderLeft: "5px solid #ef4444" }}>
                        <div className="fertOptionTitle">
                          <span>{chem.pest_or_disease}</span>
                          <span className="statusBadge low">{chem.mode_of_action}</span>
                        </div>
                        <div style={{ fontSize: "14px", fontWeight: 700, color: "#1e293b" }}>
                          {lang === "hi" ? "सक्रिय रसायन:" : "Active Ingredient:"} {chem.active_ingredient}
                        </div>
                        <div style={{ fontSize: "13px", color: "#334155" }}>
                          <b>{lang === "hi" ? "उपयुक्तता:" : "Appropriate Timing & Method:"}</b> {chem.application_timing} ({chem.application_method})
                        </div>
                        <div style={{ background: "#fee2e2", border: "1px solid #fca5a5", padding: "8px 12px", borderRadius: "8px", fontSize: "12.5px", color: "#991b1b" }}>
                          🛡️ <b>{lang === "hi" ? "सुरक्षा एवं PPE चेतावनी:" : "PPE & Safety Warning:"}</b> {chem.ppe_warning}
                        </div>
                        <div style={{ fontSize: "12.5px", color: "#475569" }}>
                          ⏳ <b>{lang === "hi" ? "कटाई पूर्व प्रतीक्षा अवधि:" : "Pre-Harvest Interval (PHI):"}</b> {chem.pre_harvest_interval}
                        </div>
                        <div style={{ fontSize: "12px", color: "#64748b", fontStyle: "italic" }}>
                          {chem.important_disclaimer}
                        </div>
                        <div style={{ fontSize: "11px", color: "#64748b" }}>
                          {lang === "hi" ? "स्रोत:" : "Source:"} {chem.source}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Section I: Chemical vs Natural Comparison */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">I</span>
                {lang === "hi" ? "रासायनिक बनाम प्राकृतिक तुलनात्मक मूल्यांकन" : "Chemical vs Natural / Organic Comparison"}
              </div>
            </div>

            <div className="fertCompTableWrapper">
              <table className="fertCompTable">
                <thead>
                  <tr>
                    <th style={{ width: "22%" }}>{recommendation.section_I_chemical_vs_natural_comparison.headers[0]}</th>
                    <th style={{ width: "39%" }}>{recommendation.section_I_chemical_vs_natural_comparison.headers[1]}</th>
                    <th style={{ width: "39%" }}>{recommendation.section_I_chemical_vs_natural_comparison.headers[2]}</th>
                  </tr>
                </thead>
                <tbody>
                  {recommendation.section_I_chemical_vs_natural_comparison.rows.map((r, i) => (
                    <tr key={i}>
                      <td className="dimTitle">{r.dimension}</td>
                      <td className="chemCol">{r.chemical}</td>
                      <td className="natCol">{r.natural}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: "14px", padding: "12px 16px", background: "#f8fafc", borderRadius: "10px", fontSize: "13px", color: "#14532d", fontWeight: 600 }}>
              ⚖️ {recommendation.section_I_chemical_vs_natural_comparison.synthesis}
            </div>
          </div>

          {/* Section J: Warnings & Safety */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">J</span>
                {lang === "hi" ? "मौसम चेतावनी एवं सुरक्षा निर्देश" : "Warnings & Safety Alerts"}
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
              {recommendation.section_J_warnings_safety.weather_advisories.map((adv, idx) => (
                <div
                  key={idx}
                  style={{
                    background: adv.severity === "critical" ? "#fee2e2" : adv.severity === "high" ? "#fffbeb" : "#f0fdf4",
                    border: `1.5px solid ${adv.severity === "critical" ? "#fca5a5" : adv.severity === "high" ? "#fcd34d" : "#86efac"}`,
                    padding: "14px 18px",
                    borderRadius: "10px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "4px"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 800, fontSize: "14.5px", color: adv.severity === "critical" ? "#991b1b" : adv.severity === "high" ? "#92400e" : "#14532d" }}>
                    {adv.severity === "critical" ? <CloudRain size={18} /> : adv.severity === "high" ? <Wind size={18} /> : <CheckCircle2 size={18} />}
                    {adv.title}
                  </div>
                  <div style={{ fontSize: "13px", color: "#334155" }}>{adv.message}</div>
                  <div style={{ fontSize: "12.5px", fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>
                    👉 {adv.action}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "14px 18px", borderRadius: "10px" }}>
              <div style={{ fontWeight: 700, fontSize: "13.5px", color: "#1e293b", marginBottom: "6px" }}>
                🛡️ {lang === "hi" ? "अनिवार्य सुरक्षा नियम:" : "Mandatory Application Safety Rules:"}
              </div>
              <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "12.5px", color: "#475569", lineHeight: "1.6" }}>
                {recommendation.section_J_warnings_safety.general_safety_rules.map((rule, i) => (
                  <li key={i}>{rule}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Section K: Confidence & Scientific Reasoning */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">K</span>
                {lang === "hi" ? "सिफारिश विश्वसनीयता एवं वैज्ञानिक कारण" : "Confidence & Scientific Reasoning"}
              </div>
            </div>

            <div className="fertConfidenceCard">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <div style={{ fontSize: "12px", color: "#64748b", fontWeight: 700 }}>
                    {lang === "hi" ? "सिफारिश विश्वसनीयता स्कोर:" : "OVERALL CONFIDENCE RATING:"}
                  </div>
                  <span className={`fertConfBadge ${recommendation.section_K_confidence_and_explanation.confidence_level.toLowerCase()}`}>
                    <ShieldCheck size={16} />
                    {recommendation.section_K_confidence_and_explanation.confidence_level} {lang === "hi" ? "विश्वसनीयता" : "Confidence"}
                  </span>
                </div>
              </div>

              <div style={{ fontSize: "13px", color: "#334155" }}>
                <b>{lang === "hi" ? "विश्वसनीयता का आधार:" : "Scoring Rationale:"}</b>
                <ul style={{ margin: "6px 0 0", paddingLeft: "20px", lineHeight: "1.5" }}>
                  {recommendation.section_K_confidence_and_explanation.confidence_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>

              <div style={{ borderTop: "1px solid #cbd5e1", paddingTop: "12px", marginTop: "4px" }}>
                <h4 style={{ margin: "0 0 10px", fontSize: "15px", color: "#0f2e17", fontWeight: 800 }}>
                  💡 {lang === "hi" ? "मैत्री यह सिफारिश क्यों कर रहा है?" : "Why MAITTRI is Recommending This:"}
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {recommendation.section_K_confidence_and_explanation.reasoning_steps.map((st, i) => (
                    <div key={i} style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                      <div style={{ fontWeight: 700, fontSize: "13px", color: "#14532d" }}>{st.title}</div>
                      <div style={{ fontSize: "12.5px", color: "#475569", marginTop: "2px" }}>{st.description}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Section L: Step-by-Step Guidance & Official Sources */}
          <div className="fertSection">
            <div className="fertSectionHeader">
              <div className="fertSectionTitle">
                <span className="fertSectionLetter">L</span>
                {lang === "hi" ? "चरणबद्ध किसान मार्गदर्शन एवं आधिकारिक स्रोत" : "Farmer Action Roadmap & Sources"}
              </div>
            </div>

            <div className="fertRoadmapTimeline" style={{ marginBottom: "24px" }}>
              {recommendation.section_L_guidance_and_sources.step_by_step_roadmap.map((s) => (
                <div key={s.step} className="fertRoadmapItem">
                  <div className="fertRoadmapNumber">{s.step}</div>
                  <div>
                    <h5 className="fertRoadmapTitle">{s.title}</h5>
                    <p className="fertRoadmapDesc">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <h4 style={{ fontSize: "15px", fontWeight: 800, color: "#14532d", marginBottom: "12px" }}>
              📚 {lang === "hi" ? "प्रमाणित आधिकारिक स्रोत:" : "Authoritative Agronomic & Legal Sources:"}
            </h4>
            <div className="fertSourcesGrid">
              {recommendation.section_L_guidance_and_sources.sources.map((src, i) => (
                <div key={i} className="fertSourceItem">
                  <div className="fertSourceName">
                    <span>{src.name}</span>
                    <a href={src.url} target="_blank" rel="noopener noreferrer" style={{ color: "#166534" }}>
                      <ExternalLink size={14} />
                    </a>
                  </div>
                  <p className="fertSourceRole">{src.role}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* History Slide-over / Modal */}
      {showHistory && (
        <div className="modalOverlay" onClick={() => setShowHistory(false)}>
          <div className="modalContent" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "720px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px" }}>
              <h3 style={{ margin: 0, color: "#14532d", display: "flex", alignItems: "center", gap: "8px" }}>
                <History size={20} /> {lang === "hi" ? "खेत का उर्वरक व छिड़काव इतिहास" : "Farm Application & Recommendation History"}
              </h3>
              <button className="button secondary" onClick={() => setShowHistory(false)} style={{ padding: "4px 8px" }}>✕</button>
            </div>

            <div style={{ maxHeight: "450px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  {lang === "hi" ? "पिछली सिफारिशें:" : "Past Recommendations:"}
                </h4>
                {historyRecords.length === 0 ? (
                  <p style={{ fontSize: "13px", color: "#64748b" }}>{lang === "hi" ? "कोई पूर्व सिफारिश रिकॉर्ड उपलब्ध नहीं।" : "No stored recommendations found."}</p>
                ) : (
                  historyRecords.map((rec) => (
                    <div key={rec.id} style={{ background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "8px", padding: "10px 14px", marginBottom: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <b>{rec.crop} ({rec.stage})</b>
                        <span className="statusBadge adequate">{rec.confidence}</span>
                      </div>
                      <div style={{ fontSize: "12px", color: "#64748b" }}>{rec.created_at?.slice(0, 10)} · {rec.summary}</div>
                    </div>
                  ))
                )}
              </div>

              <div>
                <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#334155", marginBottom: "8px" }}>
                  {lang === "hi" ? "किसान द्वारा दर्ज किए गए प्रयोग:" : "Logged Applications:"}
                </h4>
                {loggedApplications.length === 0 ? (
                  <p style={{ fontSize: "13px", color: "#64748b" }}>{lang === "hi" ? "कोई उर्वरक प्रयोग दर्ज नहीं किया गया।" : "No farmer application logs found."}</p>
                ) : (
                  loggedApplications.map((app) => (
                    <div key={app.id} style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: "8px", padding: "10px 14px", marginBottom: "8px" }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <b>{app.fertilizer_name} ({app.crop})</b>
                        <span className="statusBadge">{app.fertilizer_type}</span>
                      </div>
                      <div style={{ fontSize: "12px", color: "#475569" }}>
                        {app.applied_at?.slice(0, 10)} · {app.rate_per_acre || "Standard rate"} · {app.application_method || "Broadcast"}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
