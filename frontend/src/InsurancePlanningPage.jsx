import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Shield, AlertTriangle, CheckCircle2, Clock, FileText, Phone,
  ExternalLink, ChevronRight, Calendar, Info, CloudRain, Droplets,
  ThermometerSun, Wind, RefreshCw, Check, ArrowRight, HelpCircle
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";

export default function InsurancePlanningPage() {
  const [lang] = useLang();
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [weather, setWeather] = useState(null);

  // Form Inputs (Pre-filled from farm profile or defaulted)
  const [stateName, setStateName] = useState("Uttar Pradesh");
  const [district, setDistrict] = useState("Lucknow");
  const [crop, setCrop] = useState("Wheat");
  const [season, setSeason] = useState("rabi");
  const [farmArea, setFarmArea] = useState(2.5);
  const [sowingDate, setSowingDate] = useState("");
  const [expectedHarvest, setExpectedHarvest] = useState("");
  const [irrigation, setIrrigation] = useState("available");
  const [farmType, setFarmType] = useState("Owner");
  const [farmerCategory, setFarmerCategory] = useState("Small/Marginal");
  const [checkedDocs, setCheckedDocs] = useState({});

  // Fetch farmer's saved farms
  useEffect(() => {
    api.get("/farms").then(res => {
      setFarms(res.data || []);
      if (res.data && res.data.length > 0) {
        const first = res.data[0];
        setSelectedFarmId(String(first.id));
        applyFarmProfile(first);
      } else {
        runAnalysis();
      }
    }).catch(() => {
      runAnalysis();
    });
  }, []);

  // When selected farm changes, auto-populate details
  const applyFarmProfile = (farm) => {
    if (!farm) return;
    if (farm.location_name) {
      const parts = farm.location_name.split(",");
      if (parts.length >= 2) {
        setDistrict(parts[0].trim());
        setStateName(parts[parts.length - 1].trim());
      }
    }
    if (farm.current_crop) setCrop(farm.current_crop);
    if (farm.area) setFarmArea(farm.area);
    if (farm.irrigation) setIrrigation(farm.irrigation);

    // If farm has coordinates, fetch live weather
    if (farm.latitude && farm.longitude) {
      api.post("/weather", {
        latitude: farm.latitude,
        longitude: farm.longitude,
        location_name: farm.location_name || farm.name
      }).then(w => setWeather(w.data)).catch(() => {});
    }
  };

  const handleFarmSelect = (e) => {
    const fId = e.target.value;
    setSelectedFarmId(fId);
    const found = farms.find(f => String(f.id) === String(fId));
    if (found) {
      applyFarmProfile(found);
    }
  };

  const runAnalysis = async () => {
    setLoading(true);
    try {
      const payload = {
        farm_id: selectedFarmId ? Number(selectedFarmId) : null,
        state: stateName,
        district: district,
        crop: crop,
        season: season,
        farm_area: Number(farmArea) || 2.5,
        sowing_date: sowingDate,
        expected_harvest: expectedHarvest,
        irrigation: irrigation,
        farm_type: farmType,
        farmer_category: farmerCategory,
        include_weather_risk: true
      };
      const res = await api.post("/insurance/analyze", payload);
      setAnalysis(res.data);
    } catch (err) {
      console.error("Insurance analysis failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleDoc = (docName) => {
    setCheckedDocs(prev => ({ ...prev, [docName]: !prev[docName] }));
  };

  return (
    <div className="content">
      {/* HERO SECTION */}
      <div className="hero">
        <div>
          <span className="eyebrow">
            🛡️ {lang === "hi" ? "फसल बीमा एवं जोखिम सुरक्षा" : "CROP INSURANCE & RISK PROTECTION"}
          </span>
          <h1>{lang === "hi" ? "कृषि बीमा योजना एवं निर्णय-सहायता" : "Agricultural Insurance Planning"}</h1>
          <p>
            {lang === "hi"
              ? "अपनी फसल, राज्य और मौसम के अनुसार सरकारी फसल बीमा (PMFBY), प्रीमियम दर, 72 घंटे की क्लेम प्रक्रिया और आवश्यक दस्तावेजों की विस्तृत जानकारी।"
              : "Intelligent decision-support for PMFBY, statutory farmer premium caps, 72-hour claim notification workflow, and document checklists tailored to your crop and land."}
          </p>
        </div>
      </div>

      {/* TOP DASHBOARD METRICS SUMMARY */}
      <div className="dashboardOverviewGrid" style={{ marginBottom: "24px" }}>
        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#16a34a" }}>
            <Shield size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "लागू बीमा योजना" : "Relevant Insurance"}</span>
            <strong className="metricValue" style={{ fontSize: "16px", color: "#16a34a" }}>
              {stateName.toLowerCase().includes("bihar") ? "BRFSY (₹0 Premium)" : "PMFBY"}
            </strong>
            <span className="metricSubtext">
              {analysis?.section_E_relevant_insurance?.primary_scheme?.status || (lang === "hi" ? "सत्यापित अधिसूचना" : "Notified Unit")}
            </span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#d97706" }}>
            <Clock size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "आवेदन अंतिम तिथि" : "Cut-off Deadline"}</span>
            <strong className="metricValue" style={{ fontSize: "16px", color: "#d97706" }}>
              {season === "rabi" ? "31 December" : "31 July"}
            </strong>
            <span className="metricSubtext">{lang === "hi" ? "कट-ऑफ तारीख से पहले नामांकन" : "Strict Enrollment Cut-off"}</span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#dc2626" }}>
            <AlertTriangle size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "स्थानीय आपदा क्लेम" : "Claim Reporting Window"}</span>
            <strong className="metricValue" style={{ fontSize: "16px", color: "#dc2626" }}>
              72 {lang === "hi" ? "घंटे के भीतर" : "Hours Max"}
            </strong>
            <span className="metricSubtext">{lang === "hi" ? "ओलावृष्टि/जलभराव पर 14447 पर कॉल" : "Call 14447 or App within 72h"}</span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#2563eb" }}>
            <FileText size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "किसान प्रीमियम अंश" : "Farmer Premium Share"}</span>
            <strong className="metricValue" style={{ fontSize: "16px", color: "#2563eb" }}>
              {analysis?.section_G_premium_information?.farmer_share_statutory_pct || (season === "rabi" ? "1.5%" : "2.0%")}
            </strong>
            <span className="metricSubtext">{lang === "hi" ? "बाकी 100% केंद्र व राज्य सरकार" : "Balance fully subsidized"}</span>
          </div>
        </div>
      </div>

      {/* SECTION A: FARMER & FARM PROFILE CONTROLS */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", marginBottom: "16px" }}>
          <div>
            <h2 style={{ fontSize: "18px", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
              <span>[A]</span> {lang === "hi" ? "खेत एवं फसल प्रोफाइल" : "Farmer & Farm Profile"}
            </h2>
            <p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "13px" }}>
              {lang === "hi" ? "मैत्री फार्म प्रोफाइल से स्वचालित भरा गया। आप इसे बदल भी सकते हैं।" : "Auto-retrieved from your MAITTRI farm profile. Fully editable."}
            </p>
          </div>

          {farms.length > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "13px", color: "#64748b" }}>{lang === "hi" ? "खेत चुनें:" : "Select Farm:"}</span>
              <select
                value={selectedFarmId}
                onChange={handleFarmSelect}
                style={{ padding: "6px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "13px" }}
              >
                {farms.map(f => (
                  <option key={f.id} value={f.id}>{f.name} ({f.location_name || f.area + " " + f.area_unit})</option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px" }}>
          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "राज्य (State)" : "State"}</label>
            <input
              type="text"
              value={stateName}
              onChange={e => setStateName(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "जिला (District)" : "District"}</label>
            <input
              type="text"
              value={district}
              onChange={e => setDistrict(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "फसल (Crop)" : "Crop"}</label>
            <input
              type="text"
              value={crop}
              onChange={e => setCrop(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "मौसम (Season)" : "Season"}</label>
            <select
              value={season}
              onChange={e => setSeason(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            >
              <option value="rabi">{lang === "hi" ? "रबी (Rabi)" : "Rabi"}</option>
              <option value="kharif">{lang === "hi" ? "खरीफ (Kharif)" : "Kharif"}</option>
              <option value="zaid">{lang === "hi" ? "जायद (Zaid)" : "Zaid"}</option>
              <option value="commercial">{lang === "hi" ? "वार्षिक / व्यावसायिक (Commercial)" : "Annual Commercial"}</option>
            </select>
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "खेत का क्षेत्रफल (Acres)" : "Farm Area (Acres)"}</label>
            <input
              type="number"
              step="0.1"
              value={farmArea}
              onChange={e => setFarmArea(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            />
          </div>

          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>{lang === "hi" ? "भू-स्वामित्व (Land Type)" : "Land Ownership"}</label>
            <select
              value={farmType}
              onChange={e => setFarmType(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            >
              <option value="Owner">{lang === "hi" ? "भूमि स्वामी (Owner Cultivator)" : "Owner Cultivator"}</option>
              <option value="Tenant">{lang === "hi" ? "बटाईदार / पट्टेदार (Tenant / Sharecropper)" : "Tenant / Sharecropper"}</option>
            </select>
          </div>
        </div>

        <div style={{ marginTop: "16px", display: "flex", justifyContent: "flex-end" }}>
          <button
            className="button"
            onClick={runAnalysis}
            disabled={loading}
            style={{ display: "flex", alignItems: "center", gap: "8px" }}
          >
            <RefreshCw size={16} className={loading ? "spin" : ""} />
            {loading ? (lang === "hi" ? "विश्लेषण हो रहा है..." : "Analyzing...") : (lang === "hi" ? "बीमा विश्लेषण अपडेट करें" : "Update Insurance Analysis")}
          </button>
        </div>
      </div>

      {/* MANDATORY WARNING BANNER */}
      <div className="feedbackBanner" style={{ background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a", marginBottom: "24px" }}>
        <AlertTriangle size={20} style={{ flexShrink: 0 }} />
        <div style={{ fontSize: "13px", lineHeight: "1.5" }}>
          <b>{lang === "hi" ? "महत्वपूर्ण सुरक्षा सूचना:" : "Important Agronomic & Legal Notice:"}</b>{" "}
          {analysis?.section_D_risk_analysis?.mandatory_risk_disclaimer || (
            "बीमा पात्रता एवं क्लेम निपटान संबंधित अधिसूचना, पटवारी/कृषि सर्वेक्षक के नुकसान आकलन और आधिकारिक पोर्टल नियमों पर निर्भर करता है। मौसम संबंधी अनुमान क्लेम की गारंटी नहीं हैं।"
          )}
        </div>
      </div>

      {analysis && (
        <>
          {/* SECTIONS B, C, D: CROP, SEASON & RISK GRID */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "24px", marginBottom: "24px" }}>
            {/* [B] & [C] Crop & Season Details */}
            <div className="card">
              <h3 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>[B & C]</span> {lang === "hi" ? "फसल एवं सीजन स्थिति" : "Crop & Season Notification"}
              </h3>
              <div style={{ fontSize: "14px", lineHeight: "1.6" }}>
                <p><b>{lang === "hi" ? "फसल:" : "Crop:"}</b> {analysis.section_B_current_crop.crop_name} ({analysis.section_B_current_crop.crop_category})</p>
                <p><b>{lang === "hi" ? "अधिसूचना स्थिति:" : "Notification Status:"}</b>{" "}
                  <span className={`statusTag ${analysis.section_B_current_crop.verified_coverage ? "open" : "upcoming"}`}>
                    {analysis.section_B_current_crop.notified_in_state}
                  </span>
                </p>
                <p><b>{lang === "hi" ? "सीजन:" : "Season:"}</b> {analysis.section_C_season.season}</p>
                <p><b>{lang === "hi" ? "बुवाई अवधि:" : "Sowing Window:"}</b> {analysis.section_C_season.standard_sowing_window}</p>
                <p><b>{lang === "hi" ? "नामांकन कट-ऑफ तिथि:" : "Enrollment Deadline:"}</b>{" "}
                  <strong style={{ color: "#dc2626" }}>{analysis.section_C_season.enrollment_cut_off_date}</strong>
                </p>
                <div style={{ background: "#f8fafc", padding: "10px", borderRadius: "8px", fontSize: "12px", color: "#475569", marginTop: "12px" }}>
                  ℹ️ {analysis.section_B_current_crop.notification_note}
                </div>
              </div>
            </div>

            {/* [D] Risk Analysis */}
            <div className="card">
              <h3 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: "6px" }}>
                <span>[D]</span> {lang === "hi" ? "जोखिम विश्लेषण (मौसम एवं कृषि)" : "Agricultural Risk Analysis"}
              </h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 12px 0" }}>
                {analysis.section_D_risk_analysis.weather_risk_alert}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {analysis.section_D_risk_analysis.potential_risks_detected.map((r, idx) => (
                  <div key={idx} style={{ background: "#fef2f2", borderLeft: "4px solid #ef4444", padding: "8px 12px", borderRadius: "4px" }}>
                    <div style={{ fontWeight: "600", fontSize: "13px", color: "#991b1b" }}>⚠️ {r.peril}</div>
                    <div style={{ fontSize: "12px", color: "#475569" }}>
                      {lang === "hi" ? "गंभीरता:" : "Severity:"} <b>{r.severity}</b> · {r.coverage_status}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION E, F, G: RELEVANT INSURANCE, COVERAGE & PREMIUM */}
          <div className="card" style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "18px", margin: "0 0 16px 0", color: "#1e293b" }}>
              <span>[E, F & G]</span> {lang === "hi" ? "लागू बीमा योजना, कवरेज एवं प्रीमियम विवरण" : "Applicable Insurance Scheme, Coverage & Premium"}
            </h2>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "20px" }}>
              {/* Primary Scheme Card */}
              <div style={{ background: "#f0fdf4", border: "1px solid #bbf7d0", padding: "16px", borderRadius: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
                  <h4 style={{ margin: 0, fontSize: "16px", color: "#166534" }}>
                    🛡️ {analysis.section_E_relevant_insurance.primary_scheme.name}
                  </h4>
                  <span className="statusTag open">{analysis.section_E_relevant_insurance.primary_scheme.status}</span>
                </div>
                <p style={{ fontSize: "13px", color: "#334155", margin: "4px 0" }}>
                  <b>{lang === "hi" ? "नोडल एजेंसी:" : "Agency:"}</b> {analysis.section_E_relevant_insurance.primary_scheme.implementing_agency}
                </p>
                <p style={{ fontSize: "13px", color: "#334155", margin: "4px 0" }}>
                  <b>{lang === "hi" ? "हेल्पलाइन:" : "Helpline:"}</b> 📞 {analysis.section_E_relevant_insurance.primary_scheme.helpline}
                </p>
                <div style={{ marginTop: "12px" }}>
                  <a
                    href={analysis.section_E_relevant_insurance.primary_scheme.portal}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button"
                    style={{ fontSize: "13px", padding: "6px 12px", display: "inline-flex", alignItems: "center", gap: "6px" }}
                  >
                    <ExternalLink size={14} /> {lang === "hi" ? "आधिकारिक पोर्टल खोलें" : "Open Official Portal"}
                  </a>
                </div>
              </div>

              {/* Premium Breakdown */}
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: "16px", borderRadius: "12px" }}>
                <h4 style={{ margin: "0 0 8px 0", fontSize: "15px", color: "#1e293b" }}>
                  💰 {lang === "hi" ? "प्रीमियम संरचना (वैधानिक सीमा)" : "Premium Breakdown (Statutory Capped)"}
                </h4>
                <div style={{ fontSize: "13px", lineHeight: "1.8" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #e2e8f0", paddingBottom: "4px" }}>
                    <span>{lang === "hi" ? "किसान का अंश:" : "Farmer Statutory Share:"}</span>
                    <strong style={{ color: "#16a34a", fontSize: "15px" }}>{analysis.section_G_premium_information.farmer_share_statutory_pct}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #e2e8f0", padding: "4px 0" }}>
                    <span>{lang === "hi" ? "अनुमानित बीमा राशि:" : "Estimated Sum Insured:"}</span>
                    <strong>{analysis.section_G_premium_information.indicative_sum_insured}</strong>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #e2e8f0", padding: "4px 0" }}>
                    <span>{lang === "hi" ? "अनुमानित किसान प्रीमियम:" : "Estimated Farmer Premium:"}</span>
                    <strong style={{ color: "#2563eb" }}>{analysis.section_G_premium_information.indicative_farmer_payable_premium}</strong>
                  </div>
                  <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px" }}>
                    *{analysis.section_G_premium_information.premium_note}
                  </div>
                </div>
              </div>
            </div>

            {/* Coverage Scope List */}
            <div style={{ marginTop: "20px" }}>
              <h4 style={{ fontSize: "15px", margin: "0 0 12px 0", color: "#1e293b" }}>
                📋 {lang === "hi" ? "कवरेज का दायरा (फसल के 5 चरण)" : "Coverage Scope (5 Stages of Crop Life)"}
              </h4>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
                {analysis.section_F_coverage_explanation.stages_covered.map((stg, i) => (
                  <div key={i} style={{ background: "#ffffff", border: "1px solid #e2e8f0", padding: "12px", borderRadius: "8px" }}>
                    <div style={{ fontWeight: "600", fontSize: "13px", color: "#1e293b", marginBottom: "4px" }}>
                      {stg.stage}
                    </div>
                    <div style={{ fontSize: "12px", color: "#64748b", lineHeight: "1.4" }}>
                      {stg.description}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* SECTION I: 7-STEP CLAIM ROADMAP */}
          <div className="card" style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "18px", margin: "0 0 16px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>[I]</span> {lang === "hi" ? "फसल क्षति क्लेम प्रक्रिया (7-चरणीय रोडमैप)" : analysis.section_I_claim_process.title}
            </h2>
            <div className="timeline">
              {analysis.section_I_claim_process.steps.map((st) => (
                <div className="timelineItem" key={st.step}>
                  <div className="dot">{st.step}</div>
                  <div className="card" style={{ margin: 0, padding: "12px 16px" }}>
                    <h4 style={{ margin: "0 0 4px 0", fontSize: "14px", color: "#1e293b" }}>{st.title}</h4>
                    <p style={{ margin: 0, fontSize: "13px", color: "#475569" }}>{st.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION J: REQUIRED DOCUMENTS CHECKLIST */}
          <div className="card" style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "18px", margin: "0 0 8px 0", color: "#1e293b" }}>
              <span>[J]</span> {lang === "hi" ? "आवश्यक दस्तावेज चेकलिस्ट (Dynamic Checklist)" : "Required Documents Checklist"}
            </h2>
            <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 16px 0" }}>
              {analysis.section_J_required_documents.document_rule_disclaimer}
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
              {analysis.section_J_required_documents.documents.map((doc, idx) => (
                <div
                  key={idx}
                  onClick={() => toggleDoc(doc.name)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "12px",
                    padding: "12px 16px",
                    borderRadius: "8px",
                    border: checkedDocs[doc.name] ? "1px solid #16a34a" : "1px solid #cbd5e1",
                    background: checkedDocs[doc.name] ? "#f0fdf4" : "#ffffff",
                    cursor: "pointer",
                    transition: "all 0.2s ease"
                  }}
                >
                  <div
                    style={{
                      width: "22px",
                      height: "22px",
                      borderRadius: "6px",
                      border: "2px solid",
                      borderColor: checkedDocs[doc.name] ? "#16a34a" : "#94a3b8",
                      background: checkedDocs[doc.name] ? "#16a34a" : "transparent",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#fff",
                      flexShrink: 0
                    }}
                  >
                    {checkedDocs[doc.name] && <Check size={14} />}
                  </div>
                  <div>
                    <div style={{ fontSize: "13px", fontWeight: "600", color: "#1e293b" }}>
                      {doc.name} {doc.mandatory && <span style={{ color: "#dc2626" }}>*</span>}
                    </div>
                    <div style={{ fontSize: "11px", color: "#64748b" }}>{doc.required_for}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION L: INSURANCE SCHEMES COMPARISON MATRIX */}
          <div className="card" style={{ marginBottom: "24px" }}>
            <h2 style={{ fontSize: "18px", margin: "0 0 16px 0", color: "#1e293b" }}>
              <span>[L]</span> {lang === "hi" ? "प्रमुख कृषि बीमा योजनाओं की तुलना" : "Agricultural Insurance Comparison Matrix"}
            </h2>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px", textAlign: "left" }}>
                <thead>
                  <tr style={{ background: "#f1f5f9", borderBottom: "2px solid #cbd5e1" }}>
                    <th style={{ padding: "10px 12px", color: "#334155" }}>{lang === "hi" ? "योजना (Scheme)" : "Scheme"}</th>
                    <th style={{ padding: "10px 12px", color: "#334155" }}>{lang === "hi" ? "मूल स्वरूप (Model)" : "Model"}</th>
                    <th style={{ padding: "10px 12px", color: "#334155" }}>{lang === "hi" ? "किसान प्रीमियम" : "Farmer Premium"}</th>
                    <th style={{ padding: "10px 12px", color: "#334155" }}>{lang === "hi" ? "क्लेम निपटान आधार" : "Claim Settlement Basis"}</th>
                    <th style={{ padding: "10px 12px", color: "#334155" }}>{lang === "hi" ? "सूचना समय-सीमा" : "Intimation Deadline"}</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.section_L_insurance_comparison.comparison_table.map((row, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #e2e8f0" }}>
                      <td style={{ padding: "10px 12px", fontWeight: "600", color: "#166534" }}>{row.scheme}</td>
                      <td style={{ padding: "10px 12px", color: "#475569" }}>{row.approach}</td>
                      <td style={{ padding: "10px 12px", fontWeight: "bold", color: "#16a34a" }}>{row.farmer_premium}</td>
                      <td style={{ padding: "10px 12px", color: "#475569" }}>{row.claim_settlement}</td>
                      <td style={{ padding: "10px 12px", color: "#dc2626", fontWeight: "600" }}>{row.intimation_deadline}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* PERSONALIZED ACTION PLAN */}
          <div className="card" style={{ background: "#f8fafc", border: "1px solid #cbd5e1", marginBottom: "24px" }}>
            <h3 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>🚀</span> {lang === "hi" ? "मैत्री किसान कार्ययोजना (Personalized Action Plan)" : "MAITTRI Action Plan"}
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {analysis.maittri_action_plan.map((step, idx) => (
                <div key={idx} style={{ display: "flex", alignItems: "flex-start", gap: "10px", fontSize: "13px", color: "#334155" }}>
                  <span style={{ background: "#22c55e", color: "#fff", width: "20px", height: "20px", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "11px", flexShrink: 0 }}>
                    {idx + 1}
                  </span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>

          {/* SECTION M: OFFICIAL SOURCES & CITATIONS */}
          <div className="card">
            <h3 style={{ fontSize: "15px", margin: "0 0 8px 0", color: "#1e293b" }}>
              <span>[M]</span> {lang === "hi" ? "सत्यापित आधिकारिक स्रोत एवं साक्ष्य" : "Official Sources & Evidence"}
            </h3>
            <p style={{ fontSize: "12px", color: "#64748b", margin: "0 0 12px 0" }}>
              {lang === "hi" ? "अंतिम सत्यापन तिथि: 01/08/2026 · कृषि एवं किसान कल्याण मंत्रालय, भारत सरकार" : "Last Verified: 01/08/2026 · Ministry of Agriculture & Farmers Welfare, GoI"}
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              {analysis.section_M_official_sources.sources.map((s, i) => (
                <a
                  key={i}
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "#f1f5f9",
                    padding: "8px 14px",
                    borderRadius: "8px",
                    fontSize: "12px",
                    color: "#0f172a",
                    textDecoration: "none"
                  }}
                >
                  <ExternalLink size={13} />
                  <b>{s.portal_name}</b> ({s.helpline})
                </a>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
