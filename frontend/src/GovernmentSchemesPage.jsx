import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Landmark, Search, Filter, ExternalLink, Calendar, CheckCircle2,
  AlertTriangle, Clock, ChevronRight, X, Phone, FileText, ArrowRight,
  Sparkles, RefreshCw, Shield, FlaskConical, IndianRupee, Tractor
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";

export default function GovernmentSchemesPage() {
  const [lang] = useLang();
  const [schemes, setSchemes] = useState([]);
  const [states, setStates] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(false);

  // Filters
  const [selectedState, setSelectedState] = useState("Uttar Pradesh");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("all"); // 'all' or 'upcoming'

  // Farmer context for personalized eligibility
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [farmArea, setFarmArea] = useState(2.5);
  const [currentCrop, setCurrentCrop] = useState("Wheat");
  const [eligibilityResults, setEligibilityResults] = useState({});

  // Detail Modal State
  const [activeModalScheme, setActiveModalScheme] = useState(null);

  useEffect(() => {
    // Fetch supported states & categories
    api.get("/government-schemes/states").then(res => setStates(res.data || [])).catch(() => {});
    api.get("/government-schemes/categories").then(res => setCategories(res.data || [])).catch(() => {});

    // Fetch user farms to auto-populate state and crop
    api.get("/farms").then(res => {
      setFarms(res.data || []);
      if (res.data && res.data.length > 0) {
        const first = res.data[0];
        setSelectedFarmId(String(first.id));
        if (first.current_crop) setCurrentCrop(first.current_crop);
        if (first.area) setFarmArea(first.area);
        if (first.location_name) {
          const parts = first.location_name.split(",");
          if (parts.length >= 2) {
            const st = parts[parts.length - 1].trim();
            setSelectedState(st);
          }
        }
      }
    }).catch(() => {});
  }, []);

  // Fetch schemes whenever filters change
  useEffect(() => {
    loadSchemes();
  }, [selectedState, selectedCategory, selectedStatus, searchQuery, activeTab]);

  const loadSchemes = async () => {
    setLoading(true);
    try {
      if (activeTab === "upcoming") {
        const res = await api.get("/government-schemes/upcoming", {
          params: { state: selectedState || undefined }
        });
        setSchemes(res.data || []);
      } else {
        const res = await api.get("/government-schemes", {
          params: {
            state: selectedState || undefined,
            category: selectedCategory !== "all" ? selectedCategory : undefined,
            status: selectedStatus !== "all" ? selectedStatus : undefined,
            search: searchQuery.trim() || undefined
          }
        });
        setSchemes(res.data || []);
      }
      runBulkEligibilityCheck();
    } catch (err) {
      console.error("Failed to load government schemes:", err);
    } finally {
      setLoading(false);
    }
  };

  // Run personalized eligibility evaluation
  const runBulkEligibilityCheck = async () => {
    try {
      const res = await api.post("/government-schemes/check-eligibility", {
        state: selectedState,
        crop: currentCrop,
        farm_size_acres: farmArea,
        farmer_category: "Small/Marginal",
        land_ownership: "Owner"
      });
      if (res.data && res.data.results) {
        const mapping = {};
        res.data.results.forEach(item => {
          mapping[item.scheme_id] = item;
        });
        setEligibilityResults(mapping);
      }
    } catch (err) {
      // Fallback
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "Open":
        return <span className="statusTag open">🟢 {lang === "hi" ? "खुला है" : "Open"}</span>;
      case "Closing Soon":
        return <span className="statusTag warning">🟠 {lang === "hi" ? "जल्द समाप्त" : "Closing Soon"}</span>;
      case "Upcoming":
        return <span className="statusTag upcoming">🟡 {lang === "hi" ? "आगामी" : "Upcoming"}</span>;
      case "Closed":
        return <span className="statusTag closed">🔴 {lang === "hi" ? "बंद है" : "Closed"}</span>;
      default:
        return <span className="statusTag">{status}</span>;
    }
  };

  const openCount = schemes.filter(s => s.status === "Open").length;
  const closingCount = schemes.filter(s => s.status === "Closing Soon").length;
  const upcomingCount = schemes.filter(s => s.status === "Upcoming").length;

  return (
    <div className="content">
      {/* HERO SECTION */}
      <div className="hero">
        <div>
          <span className="eyebrow">
            🏛️ {lang === "hi" ? "कृषि सरकारी योजनाएं" : "GOVERNMENT AGRICULTURAL SCHEMES"}
          </span>
          <h1>{lang === "hi" ? "सरकारी योजनाएं एवं प्रत्यक्ष लाभ" : "Government Schemes & Farmer Subsidies"}</h1>
          <p>
            {lang === "hi"
              ? "आपके राज्य, खेत के आकार और फसल के अनुसार केंद्र और राज्य सरकार की सभी सत्यापित कृषि योजनाएं, सब्सिडी, आवेदन तिथियां और आधिकारिक पोर्टल लिंक।"
              : "State-specific and Central government agriculture schemes, subsidies, mechanization grants, and direct benefit portals tailored to your land and crops."}
          </p>
        </div>
      </div>

      {/* TOP SUMMARY METRIC CARDS */}
      <div className="dashboardOverviewGrid" style={{ marginBottom: "24px" }}>
        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(59, 130, 246, 0.15)", color: "#2563eb" }}>
            <Landmark size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "कुल प्रासंगिक योजनाएं" : "Relevant Schemes"}</span>
            <strong className="metricValue" style={{ fontSize: "20px", color: "#2563eb" }}>{schemes.length}</strong>
            <span className="metricSubtext">{selectedState} + {lang === "hi" ? "केंद्रीय योजनाएं" : "Central"}</span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(34, 197, 94, 0.15)", color: "#16a34a" }}>
            <CheckCircle2 size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "आवेदन जारी (खुला है)" : "Currently Open"}</span>
            <strong className="metricValue" style={{ fontSize: "20px", color: "#16a34a" }}>{openCount}</strong>
            <span className="metricSubtext">{lang === "hi" ? "तत्काल आवेदन योग्य" : "Active Application Window"}</span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(245, 158, 11, 0.15)", color: "#d97706" }}>
            <Clock size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "जल्द समाप्त (Closing Soon)" : "Closing Soon"}</span>
            <strong className="metricValue" style={{ fontSize: "20px", color: "#d97706" }}>{closingCount}</strong>
            <span className="metricSubtext">{lang === "hi" ? "अंतिम तिथि निकट है" : "Quota or Deadline Alert"}</span>
          </div>
        </div>

        <div className="overviewMetricCard">
          <div className="metricIconWrap" style={{ background: "rgba(168, 85, 247, 0.15)", color: "#9333ea" }}>
            <Calendar size={24} />
          </div>
          <div className="metricBody">
            <span className="metricLabel">{lang === "hi" ? "आगामी योजनाएं (Upcoming)" : "Upcoming Schemes"}</span>
            <strong className="metricValue" style={{ fontSize: "20px", color: "#9333ea" }}>{upcomingCount}</strong>
            <span className="metricSubtext">{lang === "hi" ? "अगले सीजन के लिए तैयार रहें" : "Next Season Openings"}</span>
          </div>
        </div>
      </div>

      {/* FILTER & SEARCH TOOLBAR */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "16px" }}>
          {/* State Selector */}
          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>
              📍 {lang === "hi" ? "राज्य चुनें (State Isolation)" : "Select State"}
            </label>
            <select
              value={selectedState}
              onChange={e => setSelectedState(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            >
              <option value="">{lang === "hi" ? "सभी राज्य (केंद्रीय योजनाएं)" : "All (Central Schemes)"}</option>
              {states.map(st => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          {/* Search Box */}
          <div style={{ gridColumn: "span 2" }}>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>
              🔍 {lang === "hi" ? "योजना खोजें (Search Schemes)" : "Search Schemes"}
            </label>
            <div style={{ position: "relative", marginTop: "4px" }}>
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={lang === "hi" ? "योजना का नाम, ट्रैक्टर सब्सिडी, सोलर पंप, सिंचाई..." : "Search scheme name, tractor subsidy, solar pump, drip..."}
                style={{ width: "100%", padding: "8px 12px 8px 36px", borderRadius: "8px", border: "1px solid #cbd5e1" }}
              />
              <Search size={16} style={{ position: "absolute", left: "12px", top: "11px", color: "#94a3b8" }} />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  style={{ position: "absolute", right: "10px", top: "10px", background: "none", border: "none", cursor: "pointer", color: "#94a3b8" }}
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <label style={{ fontSize: "12px", fontWeight: "bold", color: "#475569" }}>
              📊 {lang === "hi" ? "आवेदन स्थिति" : "Application Status"}
            </label>
            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              style={{ width: "100%", padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", marginTop: "4px" }}
            >
              <option value="all">{lang === "hi" ? "सभी स्थितियां" : "All Statuses"}</option>
              <option value="Open">{lang === "hi" ? "खुला है (Open)" : "Open"}</option>
              <option value="Closing Soon">{lang === "hi" ? "जल्द समाप्त (Closing Soon)" : "Closing Soon"}</option>
              <option value="Upcoming">{lang === "hi" ? "आगामी (Upcoming)" : "Upcoming"}</option>
              <option value="Closed">{lang === "hi" ? "बंद है (Closed)" : "Closed"}</option>
            </select>
          </div>
        </div>

        {/* TABS: ALL SCHEMES VS UPCOMING DATES */}
        <div style={{ display: "flex", gap: "10px", borderBottom: "1px solid #e2e8f0", paddingBottom: "12px", marginBottom: "16px" }}>
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`tabButton ${activeTab === "all" ? "active" : ""}`}
            style={{
              padding: "8px 16px",
              borderRadius: "8px",
              border: "none",
              background: activeTab === "all" ? "#16a34a" : "#f1f5f9",
              color: activeTab === "all" ? "#fff" : "#475569",
              fontWeight: "600",
              fontSize: "13px",
              cursor: "pointer"
            }}
          >
            📋 {lang === "hi" ? "सभी योजनाएं" : "All Available Schemes"} ({schemes.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("upcoming")}
            className={`tabButton ${activeTab === "upcoming" ? "active" : ""}`}
            style={{
              padding: "8px 16px",
              borderRadius: "8px",
              border: "none",
              background: activeTab === "upcoming" ? "#16a34a" : "#f1f5f9",
              color: activeTab === "upcoming" ? "#fff" : "#475569",
              fontWeight: "600",
              fontSize: "13px",
              cursor: "pointer"
            }}
          >
            ⏰ {lang === "hi" ? "आगामी एवं महत्वपूर्ण तिथियां" : "Upcoming & Important Dates"}
          </button>
        </div>

        {/* CATEGORY PILL BUTTONS */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
          {categories.map(cat => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setSelectedCategory(cat.id)}
              style={{
                padding: "5px 12px",
                borderRadius: "20px",
                border: selectedCategory === cat.id ? "1px solid #16a34a" : "1px solid #e2e8f0",
                background: selectedCategory === cat.id ? "#f0fdf4" : "#ffffff",
                color: selectedCategory === cat.id ? "#16a34a" : "#475569",
                fontSize: "12px",
                fontWeight: selectedCategory === cat.id ? "bold" : "normal",
                cursor: "pointer",
                transition: "all 0.15s ease"
              }}
            >
              {lang === "hi" ? cat.hindi : cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* SCHEMES GRID / LIST */}
      {loading ? (
        <div className="card empty" style={{ padding: "40px" }}>
          <RefreshCw size={36} className="spin" style={{ color: "#16a34a", margin: "0 auto 12px auto" }} />
          <p>{lang === "hi" ? "सरकारी योजनाएं खोजी जा रही हैं..." : "Retrieving official verified schemes..."}</p>
        </div>
      ) : schemes.length === 0 ? (
        <div className="card empty">
          <Landmark size={48} style={{ color: "#94a3b8" }} />
          <h2>{lang === "hi" ? "कोई योजना नहीं मिली" : "No Schemes Found"}</h2>
          <p>{lang === "hi" ? "कृपया अपने राज्य या श्रेणी फ़िल्टर को बदल कर पुनः प्रयास करें।" : "Try broadening your state or category filters."}</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "20px", marginBottom: "32px" }}>
          {schemes.map(s => {
            const elig = eligibilityResults[s.id];
            const isStateScheme = s.level === "state";

            return (
              <div
                key={s.id}
                className="card"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  position: "relative",
                  border: isStateScheme ? "1px solid #e9d5ff" : "1px solid #bfdbfe",
                  background: isStateScheme ? "linear-gradient(180deg, #faf5ff 0%, #ffffff 100%)" : "linear-gradient(180deg, #f0f9ff 0%, #ffffff 100%)"
                }}
              >
                <div>
                  {/* Card Header Badges */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px", marginBottom: "8px" }}>
                    <span
                      style={{
                        fontSize: "11px",
                        fontWeight: "bold",
                        padding: "3px 8px",
                        borderRadius: "4px",
                        background: isStateScheme ? "#f3e8ff" : "#dbeafe",
                        color: isStateScheme ? "#7e22ce" : "#1d4ed8"
                      }}
                    >
                      {isStateScheme ? `🟣 ${s.state} Scheme` : "🔵 Central Scheme"}
                    </span>
                    {getStatusBadge(s.status)}
                  </div>

                  {/* Scheme Name */}
                  <h3 style={{ fontSize: "16px", margin: "0 0 6px 0", color: "#0f172a", lineHeight: "1.3" }}>
                    {s.scheme_name}
                  </h3>

                  {/* Department */}
                  <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "8px" }}>
                    🏢 {s.department}
                  </div>

                  {/* Personalized Match Badge */}
                  {elig && elig.eligibility_status === "Potentially Eligible" && (
                    <div style={{ background: "#dcfce7", border: "1px solid #86efac", color: "#166534", padding: "6px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: "600", marginBottom: "10px", display: "flex", alignItems: "center", gap: "6px" }}>
                      <CheckCircle2 size={14} />
                      <span>{lang === "hi" ? "🟢 आपकी प्रोफाइल से संभावित उपयुक्त (Match: " : "🟢 Potentially Suitable (Match: "}{elig.match_percentage}%)</span>
                    </div>
                  )}

                  {/* MAITTRI Explains Section */}
                  <div style={{ background: "#f8fafc", borderLeft: "3px solid #16a34a", padding: "8px 10px", borderRadius: "0 6px 6px 0", fontSize: "12px", color: "#334155", lineHeight: "1.4", marginBottom: "12px" }}>
                    <b>{lang === "hi" ? "मैत्री सरल भाषा में:" : "MAITTRI Explains:"}</b> {s.maittri_explains}
                  </div>

                  {/* Benefits highlight */}
                  <div style={{ fontSize: "12px", color: "#475569", marginBottom: "8px", lineHeight: "1.5" }}>
                    <strong>{lang === "hi" ? "मुख्य लाभ / सब्सिडी:" : "Key Benefits:"}</strong>{" "}
                    {s.benefits?.financial || s.benefits?.subsidy || s.benefits?.coverage || (lang === "hi" ? "सरकारी अनुदान उपलब्ध" : "Government Assistance Available")}
                  </div>

                  {/* Cross Module Links where applicable */}
                  {s.category === "Crop Insurance" && (
                    <div style={{ marginBottom: "10px" }}>
                      <Link to="/insurance-planning" style={{ fontSize: "12px", color: "#16a34a", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <Shield size={13} /> {lang === "hi" ? "विस्तृत बीमा योजना देखें →" : "View Full Insurance Planner →"}
                      </Link>
                    </div>
                  )}
                  {s.category === "Soil & Nutrient" && (
                    <div style={{ marginBottom: "10px" }}>
                      <Link to="/crop-farming/soil-nutrients" style={{ fontSize: "12px", color: "#2563eb", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <FlaskConical size={13} /> {lang === "hi" ? "मृदा पोषण मॉड्यूल देखें →" : "Explore Soil & Nutrient Module →"}
                      </Link>
                    </div>
                  )}
                  {s.category === "Storage & Market" && (
                    <div style={{ marginBottom: "10px" }}>
                      <Link to="/crop-farming/market-price" style={{ fontSize: "12px", color: "#d97706", fontWeight: "600", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <IndianRupee size={13} /> {lang === "hi" ? "मंडी भाव विश्लेषण देखें →" : "Explore Market Price Module →"}
                      </Link>
                    </div>
                  )}
                </div>

                {/* Card Action Buttons */}
                <div style={{ marginTop: "16px", borderTop: "1px solid #f1f5f9", paddingTop: "12px", display: "flex", gap: "8px" }}>
                  <button
                    type="button"
                    onClick={() => setActiveModalScheme(s)}
                    style={{
                      flex: 1,
                      padding: "7px 10px",
                      borderRadius: "6px",
                      border: "1px solid #cbd5e1",
                      background: "#ffffff",
                      color: "#334155",
                      fontSize: "12px",
                      fontWeight: "600",
                      cursor: "pointer"
                    }}
                  >
                    {lang === "hi" ? "विवरण देखें" : "View Details"}
                  </button>

                  <a
                    href={s.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="button"
                    style={{
                      flex: 1.2,
                      padding: "7px 10px",
                      borderRadius: "6px",
                      fontSize: "12px",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "4px"
                    }}
                  >
                    <ExternalLink size={13} /> {lang === "hi" ? "आधिकारिक पोर्टल" : "Official Portal"}
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* PERSONALIZED FARMER ACTION PLAN */}
      <div className="card" style={{ background: "#f8fafc", border: "1px solid #cbd5e1", marginBottom: "24px" }}>
        <h3 style={{ fontSize: "16px", margin: "0 0 12px 0", color: "#1e293b", display: "flex", alignItems: "center", gap: "8px" }}>
          <span>🚀</span> {lang === "hi" ? "मैत्री सरकारी योजना कार्ययोजना (Step-by-Step Action Plan)" : "MAITTRI Scheme Action Plan"}
        </h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>1. {lang === "hi" ? "योजना की पहचान:" : "Identify Scheme:"}</b> {lang === "hi" ? "अपनी ज़मीन, फसल और आवश्यकता के अनुसार उपयुक्त योजना चुनें।" : "Select schemes matching your state and farm size."}
          </div>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>2. {lang === "hi" ? "पात्रता जांचें:" : "Check Eligibility:"}</b> {lang === "hi" ? "नियम व शर्तें देख कर सुनिश्चित करें कि ज़मीन आपके नाम पर दर्ज है।" : "Ensure land records and category criteria match official rules."}
          </div>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>3. {lang === "hi" ? "दस्तावेज तैयार करें:" : "Prepare Documents:"}</b> {lang === "hi" ? "आधार, खतौनी, बैंक पासबुक और मोबाइल नंबर तैयार रखें।" : "Keep Aadhaar, land record (Khatauni), and bank passbook ready."}
          </div>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>4. {lang === "hi" ? "आधिकारिक पोर्टल पर आवेदन:" : "Apply on Official Portal:"}</b> {lang === "hi" ? "केवल सरकारी वेबसाइट या सीएससी केंद्र से आवेदन करें।" : "Submit application directly on verified official portals."}
          </div>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>5. {lang === "hi" ? "रसीद सुरक्षित रखें:" : "Keep Receipt:"}</b> {lang === "hi" ? "आवेदन संख्या (Application / Registration ID) सुरक्षित रखें।" : "Save application acknowledgement docket for tracking."}
          </div>
          <div style={{ fontSize: "13px", color: "#334155" }}>
            <b>6. {lang === "hi" ? "स्थिति ट्रैक करें:" : "Track Status:"}</b> {lang === "hi" ? "कृषि अधिकारी या पोर्टल पर समय-समय पर स्थिति जांचें।" : "Monitor approval and DBT disbursement updates."}
          </div>
        </div>
      </div>

      {/* OFFICIAL LEGAL DISCLAIMER */}
      <div className="card" style={{ background: "#fef3c7", border: "1px solid #fde68a", color: "#92400e", fontSize: "12px", lineHeight: "1.5" }}>
        <b>⚖️ {lang === "hi" ? "आधिकारिक वैधानिक अस्वीकरण:" : "Official Institutional Disclaimer:"}</b>{" "}
        {lang === "hi"
          ? "मैत्री कृषि मंच केवल आधिकारिक स्रोतों से संकलित सूचना और निर्णय-सहायता प्रदान करता है। अंतिम पात्रता, वित्तीय स्वीकृति, सब्सिडी आवंटन और योजना का लाभ संबंधित सरकारी विभाग, नोडल एजेंसी या अधिकृत अधिकारी के सत्यापन पर निर्भर करता है। मैत्री कोई वित्तीय गारंटी नहीं देती।"
          : "MAITTRI provides decision-support based on officially published government schemes. Final eligibility, subsidy sanction, and benefit disbursements are determined by the respective government department or authorized nodal agency. MAITTRI does not issue legal or financial guarantees."}
      </div>

      {/* SCHEME DETAIL MODAL */}
      {activeModalScheme && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px"
          }}
          onClick={() => setActiveModalScheme(null)}
        >
          <div
            className="card"
            style={{
              maxWidth: "650px",
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              position: "relative",
              padding: "24px"
            }}
            onClick={e => e.stopPropagation()}
          >
            <button
              onClick={() => setActiveModalScheme(null)}
              style={{ position: "absolute", right: "16px", top: "16px", background: "none", border: "none", cursor: "pointer", color: "#64748b" }}
            >
              <X size={20} />
            </button>

            <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" }}>
              <span className={`statusTag ${activeModalScheme.level === "state" ? "upcoming" : "open"}`}>
                {activeModalScheme.level === "state" ? `🟣 ${activeModalScheme.state} Scheme` : "🔵 Central Scheme"}
              </span>
              {getStatusBadge(activeModalScheme.status)}
            </div>

            <h2 style={{ fontSize: "18px", margin: "0 0 8px 0", color: "#0f172a" }}>
              {activeModalScheme.scheme_name}
            </h2>
            <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "16px" }}>
              🏢 {activeModalScheme.department}
            </div>

            <div style={{ fontSize: "13px", lineHeight: "1.6", color: "#334155" }}>
              <p><b>{lang === "hi" ? "उद्देश्य एवं विवरण:" : "Purpose & Description:"}</b> {activeModalScheme.description}</p>

              <div style={{ background: "#f0fdf4", borderLeft: "3px solid #16a34a", padding: "10px", borderRadius: "4px", margin: "12px 0" }}>
                <b>{lang === "hi" ? "मैत्री व्याख्या:" : "MAITTRI Explains:"}</b> {activeModalScheme.maittri_explains}
              </div>

              <p><b>{lang === "hi" ? "अनुदान एवं लाभ:" : "Benefits & Subsidy:"}</b></p>
              <ul>
                {Object.entries(activeModalScheme.benefits || {}).map(([k, v]) => (
                  <li key={k}><b>{k.replace(/_/g, " ").toUpperCase()}:</b> {v}</li>
                ))}
              </ul>

              <p><b>{lang === "hi" ? "कौन आवेदन कर सकता है (पात्रता):" : "Eligibility Criteria:"}</b></p>
              <ul>
                {Object.entries(activeModalScheme.eligibility_criteria || {}).map(([k, v]) => (
                  <li key={k}><b>{k.replace(/_/g, " ").toUpperCase()}:</b> {v}</li>
                ))}
              </ul>

              <p><b>{lang === "hi" ? "आवश्यक दस्तावेज:" : "Required Documents:"}</b></p>
              <ul>
                {(activeModalScheme.documents || []).map((doc, i) => (
                  <li key={i}>{doc}</li>
                ))}
              </ul>

              <p><b>{lang === "hi" ? "हेल्पलाइन:" : "Helpline:"}</b> {activeModalScheme.helpline || "1800-180-1551"}</p>
              <p style={{ fontSize: "11px", color: "#64748b" }}>
                {lang === "hi" ? "अंतिम सत्यापन:" : "Last Verified:"} {activeModalScheme.last_verified}
              </p>
            </div>

            <div style={{ marginTop: "20px", display: "flex", justifyContent: "flex-end", gap: "12px" }}>
              <button
                type="button"
                onClick={() => setActiveModalScheme(null)}
                style={{ padding: "8px 16px", borderRadius: "8px", border: "1px solid #cbd5e1", background: "#f8fafc", cursor: "pointer" }}
              >
                {lang === "hi" ? "बंद करें" : "Close"}
              </button>
              <a
                href={activeModalScheme.official_url}
                target="_blank"
                rel="noopener noreferrer"
                className="button"
                style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}
              >
                <ExternalLink size={14} /> {lang === "hi" ? "आधिकारिक पोर्टल पर आवेदन करें" : "Apply on Official Portal"}
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
