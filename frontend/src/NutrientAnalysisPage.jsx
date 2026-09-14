import React, { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  Sprout, AlertTriangle, CheckCircle2, AlertCircle, HelpCircle,
  FlaskConical, ArrowRight, Pencil, RefreshCw, ShieldAlert,
  MapPinned, Leaf, Calendar, Info
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
  translateReason
} from "./i18n";

export default function NutrientAnalysisPage() {
  const { farmId } = useParams();
  const nav = useNavigate();
  const { lang, t } = useLang();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    loadAnalysis();
  }, [farmId]);

  const loadAnalysis = async () => {
    setLoading(true);
    setError("");
    try {
      if (farmId) {
        // Fetch saved or computed analysis for farm
        const { data } = await api.get(`/nutrients/${farmId}`);
        setAnalysis(data);
      } else {
        // Look in localStorage for temporarily analyzed data from the form
        const cached = localStorage.getItem("pending_nutrient_analysis");
        if (cached) {
          setAnalysis(JSON.parse(cached));
        } else {
          // Fetch most recent user farm
          const farmsRes = await api.get("/farms");
          if (farmsRes.data && farmsRes.data.length > 0) {
            const latestFarm = farmsRes.data[0];
            const { data } = await api.get(`/nutrients/${latestFarm.id}`);
            setAnalysis(data);
          } else {
            setError(lang === "hi" ? "कोई खेत नहीं मिला। कृपया पहले एक खेत जोड़ें।" : "No farm profile found. Please add a farm first.");
          }
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || (lang === "hi" ? "मिट्टी और पोषक तत्व विश्लेषण लोड करने में विफल।" : "Failed to load soil and nutrient analysis."));
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const label = translateNutrientStatus(status, lang);
    switch (status) {
      case "Likely depleted":
        return <span className="statusBadge critical"><AlertTriangle size={13}/> {label}</span>;
      case "Possibly depleted":
        return <span className="statusBadge warning"><AlertCircle size={13}/> {label}</span>;
      case "Likely adequate":
        return <span className="statusBadge favorable"><CheckCircle2 size={13}/> {label}</span>;
      default:
        return <span className="statusBadge normal"><HelpCircle size={13}/> {label}</span>;
    }
  };

  const getConfidenceBadge = (confidence) => {
    const isHigh = confidence?.toLowerCase().includes("high");
    const isMed = confidence?.toLowerCase().includes("medium");
    const label = translateConfidence(confidence, lang);
    return (
      <span className={`confidenceTag ${isHigh ? "high" : isMed ? "medium" : "low"}`}>
        {label} {lang === "hi" ? "विश्वसनीयता" : "Confidence"}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="content">
        <div className="card empty">
          <RefreshCw size={44} className="spin" style={{ color: "#2f7d32" }}/>
          <h2>{t.analyzingSoil || (lang === "hi" ? "मिट्टी एवं पोषक तत्वों का विश्लेषण किया जा रहा है..." : "Analyzing Soil & Nutrient Depletion...")}</h2>
          <p>{lang === "hi" ? "फसल अवशोषण वक्र, मिट्टी के प्रकार और फसल अनुक्रम का वैज्ञानिक मूल्यांकन हो रहा है..." : "Evaluating crop uptake curves, soil type properties, and cropping sequence..."}</p>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="content">
        <div className="card empty">
          <AlertTriangle size={48} style={{ color: "#eab308" }}/>
          <h2>{error || (lang === "hi" ? "कोई पोषक तत्व विश्लेषण उपलब्ध नहीं है" : "No nutrient analysis available")}</h2>
          <p>{lang === "hi" ? "सटीक विश्लेषण के लिए कृपया अपने खेत का स्थान, मिट्टी का प्रकार और पिछली फसल दर्ज करें।" : "Please enter your farm location, soil type, and previous crop to generate an intelligent analysis."}</p>
          <Link to="/farm" className="button"><Sprout size={16}/> {t.addFarm || (lang === "hi" ? "खेत जोड़ें" : "Add Farm")}</Link>
        </div>
      </div>
    );
  }

  const { farm_context, summary, nutrients, soil_vulnerability_notes, disclaimer } = analysis;
  const macronutrients = nutrients.filter(n => n.category === "Macronutrient");
  const secondaryNutrients = nutrients.filter(n => n.category === "Secondary Nutrient");
  const micronutrients = nutrients.filter(n => n.category === "Micronutrient");

  return (
    <div className="content">
      {/* Hero Header */}
      <div className="hero">
        <div>
          <span className="eyebrow">{lang === "hi" ? "मैत्री मृदा एवं पोषण सेवा" : "MAITTRI AGRONOMIC INTELLIGENCE"}</span>
          <h1>{t.nutrientAnalysisTitle || (lang === "hi" ? "मिट्टी एवं पोषक तत्व विश्लेषण" : "Soil & Nutrient Depletion Intelligence")}</h1>
          <p>{t.nutrientAnalysisSubtitle || (lang === "hi" ? "फसल चक्र और मिट्टी विज्ञान के आधार पर पोषक तत्वों की कमी, पर्याप्तता और आवश्यक परीक्षण का सटीक अनुमान।" : "Estimates which nutrients are depleted, adequate, or require testing based on cropping sequence and soil science.")}</p>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button
            className="button"
            onClick={() => nav("/recommend")}
            title="Continue to recommended crops and profit estimates"
          >
            {t.proceedToRecommendations || (lang === "hi" ? "फसल सिफारिशों पर जाएं" : "Proceed to Crop Recommendations")} <ArrowRight size={16}/>
          </button>
        </div>
      </div>

      {/* Farm Context Bar */}
      <div className="farmContextBar">
        <div className="contextItem">
          <MapPinned size={18} color="#15803d"/>
          <div>
            <span className="contextLabel">{t.location}</span>
            <strong>{analysis.location_name || (analysis.latitude ? `${analysis.latitude.toFixed(2)}, ${analysis.longitude.toFixed(2)}` : translateSoil(farm_context?.soil_type, lang))}</strong>
            <small style={{ display: "block", color: "#64748b", fontSize: 11 }}>
              {analysis.location_source === "gps" ? (lang === "hi" ? "📍 जीपीएस द्वारा पहचाना गया" : "📍 GPS Detected") : analysis.location_source === "map_click" ? (lang === "hi" ? "🗺️ इंटरैक्टिव मानचित्र" : "🗺️ Interactive Map") : (lang === "hi" ? "मैन्युअल प्रविष्टि" : "Manual Input")}
            </small>
          </div>
        </div>

        <div className="contextItem">
          <Leaf size={18} color="#15803d"/>
          <div>
            <span className="contextLabel">{t.soil}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <strong>{translateSoil(farm_context?.soil_type, lang)}</strong>
              <span className={`sourcePill ${farm_context?.soil_type_source === "farmer_selected" ? "manual" : "auto"}`}>
                {farm_context?.soil_type_source === "farmer_selected" ? (t.farmerSelected || (lang === "hi" ? "किसान द्वारा चयनित" : "Farmer selected")) : (t.autoDetected || (lang === "hi" ? "स्वतः पहचाना गया" : "Auto-detected"))}
              </span>
            </div>
            <small style={{ color: "#64748b", fontSize: 11 }}>
              {farm_context?.soil_ph_status || (lang === "hi" ? "pH मान दर्ज नहीं" : "pH not provided")}
            </small>
          </div>
        </div>

        <div className="contextItem">
          <Calendar size={18} color="#15803d"/>
          <div>
            <span className="contextLabel">{lang === "hi" ? "फसल अनुक्रम (चक्र)" : "Cropping Sequence"}</span>
            <strong>{translateCrop(farm_context?.previous_crop, lang) || (lang === "hi" ? "कोई नहीं" : "None")} → {translateCrop(farm_context?.current_crop, lang) || (lang === "hi" ? "परती" : "Fallow")}</strong>
            <small style={{ display: "block", color: "#64748b", fontSize: 11 }}>
              {farm_context?.previous_crop_period || (lang === "hi" ? "एकल मौसम" : "Single season")} {farm_context?.cultivation_count > 1 ? `(${farm_context.cultivation_count}x ${lang === "hi" ? "चक्र" : "cycles"})` : ""}
            </small>
          </div>
        </div>

        <div className="contextItem">
          <FlaskConical size={18} color="#0284c7"/>
          <div>
            <span className="contextLabel">{lang === "hi" ? "सत्यापन स्तर" : "Verification Mode"}</span>
            <strong>{farm_context?.is_lab_verified ? (lang === "hi" ? "प्रयोगशाला परीक्षण आधारित" : "Laboratory Grounded") : (lang === "hi" ? "कृषि एआई अनुमानित" : "Agronomic AI Estimate")}</strong>
            <small style={{ display: "block", color: "#64748b", fontSize: 11 }}>
              {farm_context?.is_lab_verified ? (lang === "hi" ? "मृदा परीक्षण मान लागू" : "Soil test values applied") : (lang === "hi" ? "कोई लैब टेस्ट उपलब्ध नहीं" : "No lab test provided")}
            </small>
          </div>
        </div>
      </div>

      {/* Farmer Friendly Summary Strip */}
      <div className="nutrientSummaryCard">
        <h3>📊 {t.quickNutrientSummary || (lang === "hi" ? "त्वरित पोषक तत्व स्थिति सारांश" : "Quick Nutrient Status Summary")}</h3>
        <div className="summaryStripGrid">
          <div className="summaryBlock critical">
            <span className="summaryLabel">{t.potentiallyDepleted || (lang === "hi" ? "संभावित रूप से कम" : "Potentially Depleted")}</span>
            <div className="symbolChips">
              {summary.potentially_depleted.length > 0 ? (
                summary.potentially_depleted.map(s => <span key={s} className="symChip critical">{translateNutrient(s, lang)}</span>)
              ) : (
                <small>{lang === "hi" ? "कोई नहीं" : "None identified"}</small>
              )}
            </div>
            <small className="summaryHint">{lang === "hi" ? "पिछली फसलों द्वारा अवशोषण या मिट्टी में बंधने के कारण कमी की संभावना।" : "Likely drawn down by previous crops or severe soil fixation."}</small>
          </div>

          <div className="summaryBlock warning">
            <span className="summaryLabel">{t.possiblyDepleted || (lang === "hi" ? "संभवतः कम" : "Possibly Depleted")}</span>
            <div className="symbolChips">
              {summary.possibly_depleted.length > 0 ? (
                summary.possibly_depleted.map(s => <span key={s} className="symChip warning">{translateNutrient(s, lang)}</span>)
              ) : (
                <small>{lang === "hi" ? "कोई नहीं" : "None identified"}</small>
              )}
            </div>
            <small className="summaryHint">{lang === "hi" ? "मध्यम आवश्यकता या निक्षालन जोखिम; अगली बुवाई से पहले जांच करें।" : "Moderate demand or leaching risk; verify before next sowing."}</small>
          </div>

          <div className="summaryBlock favorable">
            <span className="summaryLabel">{t.likelyAdequate || (lang === "hi" ? "संभवतः पर्याप्त" : "Likely Adequate")}</span>
            <div className="symbolChips">
              {summary.likely_adequate.length > 0 ? (
                summary.likely_adequate.map(s => <span key={s} className="symChip favorable">{translateNutrient(s, lang)}</span>)
              ) : (
                <small>{lang === "hi" ? "कोई नहीं" : "None"}</small>
              )}
            </div>
            <small className="summaryHint">{lang === "hi" ? "मृदा प्रकार या संतुलित भंडार से अच्छी उपलब्धता की उम्मीद।" : "Good baseline expected from soil type or balanced reserves."}</small>
          </div>

          <div className="summaryBlock normal">
            <span className="summaryLabel">{t.requiresTesting || (lang === "hi" ? "मृदा परीक्षण आवश्यक" : "Requires Soil Test")}</span>
            <div className="symbolChips">
              {summary.requires_testing.length > 0 ? (
                summary.requires_testing.map(s => <span key={s} className="symChip normal">{translateNutrient(s, lang)}</span>)
              ) : (
                <small>{lang === "hi" ? "कोई नहीं" : "None"}</small>
              )}
            </div>
            <small className="summaryHint">{lang === "hi" ? "सूक्ष्म पोषक तत्व जिनमें खेत में उच्च परिवर्तनशीलता होती है।" : "Micronutrients with high field variability."}</small>
          </div>
        </div>
      </div>

      {/* Soil Test Advisory Disclaimer Box */}
      <div className="soilTestAdvisoryBox">
        <div className="advisoryIconCol">
          <FlaskConical size={32} color="#0284c7"/>
        </div>
        <div className="advisoryContentCol">
          <h4>{lang === "hi" ? "⚠️ महत्वपूर्ण मृदा परीक्षण सूचना" : "⚠️ Important Soil Testing Notice"}</h4>
          <p>
            {lang === "hi" ? (
              <>यह फसल पोषक तत्व अवशोषण चक्र, फसल अनुक्रम और क्षेत्रीय मिट्टी की विशेषताओं पर आधारित एक <strong>एआई कृषि विज्ञान अनुमान</strong> है। यह वास्तविक भौतिक प्रयोगशाला <strong>मृदा स्वास्थ्य कार्ड</strong> का विकल्प नहीं है।</>
            ) : (
              <>This is an <strong>AI-based agronomic estimate</strong> utilizing crop nutrient extraction curves, cropping sequences, and regional soil characteristics. It does <strong>not</strong> substitute for an actual physical laboratory Soil Health Card measurement.</>
            )}
          </p>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "#475569" }}>
            {lang === "hi"
              ? "सटीक और प्रमाणित उर्वरक खुराक सिफारिशों के लिए, किसान अपने स्थानीय कृषि विज्ञान केंद्र (केवीके) या सरकारी मृदा परीक्षण प्रयोगशाला से जांच अवश्य कराएं।"
              : "For accurate, certified fertilizer dosage recommendations, farmers should obtain a laboratory soil test from their local Krishi Vigyan Kendra (KVK) or government soil testing laboratory."}
          </p>
        </div>
      </div>

      {/* Section 1: Macronutrients */}
      <div className="nutrientCategorySection">
        <div className="categoryHeader">
          <h2>{lang === "hi" ? "1. प्राथमिक मुख्य पोषक तत्व (नाइट्रोजन, फास्फोरस, पोटाश)" : "1. Primary Macronutrients (N, P, K)"}</h2>
          <p>{lang === "hi" ? "फसल की वृद्धि, जड़ों के विकास और उपज के लिए सबसे बड़ी मात्रा में आवश्यक पोषक तत्व।" : "Essential nutrients absorbed in largest quantities for crop growth, rooting, and yield."}</p>
        </div>
        <div className="nutrientCardsGrid">
          {macronutrients.map(item => (
            <NutrientCard key={item.symbol} item={item} lang={lang} getStatusBadge={getStatusBadge} getConfidenceBadge={getConfidenceBadge}/>
          ))}
        </div>
      </div>

      {/* Section 2: Secondary Nutrients */}
      <div className="nutrientCategorySection">
        <div className="categoryHeader">
          <h2>{lang === "hi" ? "2. द्वितीयक पोषक तत्व (सल्फर, कैल्शियम, मैग्नीशियम)" : "2. Secondary Nutrients (S, Ca, Mg)"}</h2>
          <p>{lang === "hi" ? "क्लोरोफिल निर्माण, कोशिका भित्ति की मजबूती और तिलहन उत्पादन के लिए महत्वपूर्ण।" : "Vital for chlorophyll synthesis, cell wall strength, and oilseed production."}</p>
        </div>
        <div className="nutrientCardsGrid">
          {secondaryNutrients.map(item => (
            <NutrientCard key={item.symbol} item={item} lang={lang} getStatusBadge={getStatusBadge} getConfidenceBadge={getConfidenceBadge}/>
          ))}
        </div>
      </div>

      {/* Section 3: Micronutrients */}
      <div className="nutrientCategorySection">
        <div className="categoryHeader">
          <h2>{lang === "hi" ? "3. आवश्यक सूक्ष्म पोषक तत्व (जिंक, लोहा, बोरॉन, मैंगनीज, तांबा)" : "3. Essential Micronutrients (Zn, Fe, B, Mn, Cu)"}</h2>
          <p>{lang === "hi" ? "सूक्ष्म मात्रा में आवश्यक तत्व जो महत्वपूर्ण जैव रासायनिक एंजाइम उत्प्रेरक के रूप में कार्य करते हैं।" : "Trace elements required in small quantities that act as critical biochemical enzyme activators."}</p>
        </div>
        <div className="nutrientCardsGrid">
          {micronutrients.map(item => (
            <NutrientCard key={item.symbol} item={item} lang={lang} getStatusBadge={getStatusBadge} getConfidenceBadge={getConfidenceBadge}/>
          ))}
        </div>
      </div>

      {/* Soil Vulnerability Insights */}
      {soil_vulnerability_notes && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="cardTitle">
            <Leaf color="#16a34a"/>
            <h3>{lang === "hi" ? `कृषि मृदा व्यवहार: ${translateSoil(farm_context?.soil_type, lang)}` : `Agronomic Soil Behavior: ${farm_context?.soil_type}`}</h3>
          </div>
          <p style={{ color: "#334155", fontSize: 14.5, lineHeight: 1.6 }}>
            {translateReason(soil_vulnerability_notes, lang)}
          </p>
        </div>
      )}

      {/* Bottom Action Footer */}
      <div className="nutrientBottomActions">
        <Link to={farmId ? `/farm/edit/${farmId}` : "/farm"} className="button secondary">
          <Pencil size={16}/> {lang === "hi" ? "खेत विवरण बदलें" : "Edit Farm Profile"}
        </Link>
        <button className="button" onClick={() => nav("/recommend")}>
          {t.proceedToRecommendations || (lang === "hi" ? "फसल सिफारिशों पर जाएं" : "Proceed to Crop Recommendations")} <ArrowRight size={16}/>
        </button>
      </div>
    </div>
  );
}

function NutrientCard({ item, lang, getStatusBadge, getConfidenceBadge }) {
  const categoryTranslated = item.category === "Macronutrient"
    ? (lang === "hi" ? "प्राथमिक मुख्य पोषक तत्व" : "Macronutrient")
    : item.category === "Secondary Nutrient"
    ? (lang === "hi" ? "द्वितीयक पोषक तत्व" : "Secondary Nutrient")
    : (lang === "hi" ? "सूक्ष्म पोषक तत्व" : "Micronutrient");

  return (
    <div className={`nutrientDetailCard ${item.status === "Likely depleted" ? "border-critical" : item.status === "Possibly depleted" ? "border-warning" : item.status === "Likely adequate" ? "border-favorable" : "border-normal"}`}>
      <div className="cardTop">
        <div className="nutrientIdentity">
          <span className="nutrientSymbolCircle">{item.symbol}</span>
          <div>
            <strong>{translateNutrient(item.nutrient, lang)}</strong>
            <small>{categoryTranslated}</small>
          </div>
        </div>
        <div className="badgesRight">
          {getStatusBadge(item.status)}
          {getConfidenceBadge(item.confidence)}
        </div>
      </div>

      <div className="cardWhySection">
        <span className="whyLabel">{lang === "hi" ? "कारण:" : "Why?"}</span>
        <p className="whyText">{translateReason(item.reason, lang)}</p>
      </div>

      <div className="cardVerificationSection">
        <span className="verifyLabel">{lang === "hi" ? "अनुशंसित सत्यापन:" : "Recommended Verification:"}</span>
        <p className="verifyText">{translateReason(item.verification, lang)}</p>
      </div>

      <div className="cardSourceFooter">
        <span>
          {lang === "hi"
            ? `स्रोत: ${item.source === "soil_type_baseline" ? "मृदा प्रकार आधार" : item.source === "crop_depletion" ? "फसल अवशोषण विश्लेषण" : item.source === "ph_fixation" ? "पीएच प्रभाव" : item.source}`
            : `Source: ${item.source}`}
        </span>
      </div>
    </div>
  );
}
