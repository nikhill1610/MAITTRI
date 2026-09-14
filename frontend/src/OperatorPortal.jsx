import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, UserPlus, Search, UserCheck, Tractor, Sprout,
  FlaskConical, FileText, LifeBuoy, CloudRain, IndianRupee, ShieldAlert,
  Landmark, Shield, PhoneCall, BarChart3, History, CheckCircle2,
  Clock, AlertTriangle, RefreshCw, Send, Phone, ArrowRight,
  LogOut, Languages, ChevronRight, X, Eye, Upload, Download, QrCode
} from "lucide-react";
import api, { clearAuthSession } from "./api";
import Logo from "./Logo";
import { useLang } from "./LanguageContext";

export default function OperatorPortal() {
  const [lang, setLang, t] = useLang();
  const nav = useNavigate();
  const [activeTab, setActiveTab] = useState("dashboard");

  // Global operator state
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState({ text: "", type: "success" });

  // Farmers state
  const [searchQuery, setSearchQuery] = useState("");
  const [farmers, setFarmers] = useState([]);
  const [selectedFarmer, setSelectedFarmer] = useState(null);

  // Assisted Registration form state
  const [regForm, setRegForm] = useState({
    name: "",
    mobile_number: "",
    alternate_mobile: "",
    state: "Uttar Pradesh",
    district: "Varanasi",
    block: "",
    village: "",
    farm_area: 2.0,
    area_unit: "acre",
    land_ownership: "owner",
    irrigation: "tubewell",
    soil_type: "Alluvial Soil",
    current_crop: "Wheat",
    previous_crop: "Rice",
    planned_crop: "Maize",
    sowing_date: "",
    crop_variety: "",
    preferred_language: "hi",
    sms_consent: true,
    ivr_consent: true
  });

  // Soil test state
  const [soilTests, setSoilTests] = useState([]);
  const [newSoilTest, setNewSoilTest] = useState({ farmer_id: "", location: "", crop: "", notes: "" });
  const [labReportModal, setLabReportModal] = useState(null);
  const [labReportData, setLabReportData] = useState({
    lab_name: "KVK Regional Soil Testing Lab",
    test_date: new Date().toISOString().split("T")[0],
    nitrogen: 210,
    phosphorus: 16,
    potassium: 180,
    ph: 7.2,
    ec: 0.45,
    organic_carbon: 0.42,
    zinc: 0.7
  });

  // Service requests state
  const [serviceRequests, setServiceRequests] = useState([]);
  const [newServiceReq, setNewServiceReq] = useState({ farmer_id: "", service_type: "SOIL_TEST", description: "" });
  const [resolveReqId, setResolveReqId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState("");

  // Documents state
  const [documents, setDocuments] = useState([]);
  const [uploadDoc, setUploadDoc] = useState({ farmer_id: "", document_name: "", category: "Land Record" });
  const [selectedFile, setSelectedFile] = useState(null);

  // SMS & IVR state
  const [smsForm, setSmsForm] = useState({ mobile: "", message: "", category: "weather_warning" });
  const [smsLogs, setSmsLogs] = useState([]);
  const [ivrSimInput, setIvrSimInput] = useState({ phone: "9876543210", menu: "main", digits: "" });
  const [ivrSimState, setIvrSimState] = useState(null);
  const [activityLogs, setActivityLogs] = useState([]);

  // Load operator overview stats
  const loadStats = async () => {
    try {
      const { data } = await api.get("/operators/dashboard-stats");
      setStats(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadFarmers = async (query = "") => {
    try {
      setLoading(true);
      const { data } = await api.get("/operators/farmers", { params: { q: query } });
      setFarmers(data);
      if (data.length > 0 && !selectedFarmer) {
        setSelectedFarmer(data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadSoilTests = async () => {
    try {
      const { data } = await api.get("/soil-tests");
      setSoilTests(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadServiceRequests = async () => {
    try {
      const { data } = await api.get("/service-requests");
      setServiceRequests(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadDocuments = async () => {
    try {
      const { data } = await api.get("/documents");
      setDocuments(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadSmsLogs = async () => {
    try {
      const { data } = await api.get("/communications/sms/logs");
      setSmsLogs(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadActivityLogs = async () => {
    try {
      const { data } = await api.get("/operators/activity-logs");
      setActivityLogs(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadStats();
    loadFarmers();
    loadSoilTests();
    loadServiceRequests();
    loadDocuments();
    loadSmsLogs();
    loadActivityLogs();
  }, []);

  const showMsg = (text, type = "success") => {
    setFeedback({ text, type });
    setTimeout(() => setFeedback({ text: "", type: "success" }), 4000);
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const { data } = await api.post("/operators/farmers", regForm);
      showMsg(lang === "hi" ? `किसान ${data.name} सफलतापूर्वक पंजीकृत! MAITTRI ID: ${data.maittri_farmer_id}` : `Farmer ${data.name} registered successfully! MAITTRI ID: ${data.maittri_farmer_id}`);
      setRegForm({
        name: "",
        mobile_number: "",
        alternate_mobile: "",
        state: "Uttar Pradesh",
        district: "Varanasi",
        block: "",
        village: "",
        farm_area: 2.0,
        area_unit: "acre",
        land_ownership: "owner",
        irrigation: "tubewell",
        soil_type: "Alluvial Soil",
        current_crop: "Wheat",
        previous_crop: "Rice",
        planned_crop: "Maize",
        sowing_date: "",
        crop_variety: "",
        preferred_language: "hi",
        sms_consent: true,
        ivr_consent: true
      });
      loadFarmers();
      loadStats();
      setSelectedFarmer(data);
      setActiveTab("farmer_profile");
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "पंजीकरण विफल रहा" : "Registration failed"), "error");
    } finally {
      setLoading(false);
    }
  };

  const handleBookSoilTest = async (e) => {
    e.preventDefault();
    if (!newSoilTest.farmer_id) {
      showMsg(lang === "hi" ? "कृपया किसान का चयन करें" : "Please select a farmer", "error");
      return;
    }
    try {
      const { data } = await api.post("/soil-tests", newSoilTest);
      showMsg(lang === "hi" ? `सॉइल टेस्ट बुकिंग सफल! Request ID: ${data.request_id}` : `Soil test booking successful! Request ID: ${data.request_id}`);
      setNewSoilTest({ farmer_id: "", location: "", crop: "", notes: "" });
      loadSoilTests();
      loadStats();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "बुकिंग विफल रही" : "Booking failed"), "error");
    }
  };

  const handleUpdateSoilStatus = async (reqId, status) => {
    try {
      await api.patch(`/soil-tests/${reqId}/status`, { status });
      showMsg(lang === "hi" ? `स्थिति बदलकर ${status} कर दी गई` : `Status updated to ${status}`);
      loadSoilTests();
      loadStats();
    } catch (err) {
      showMsg(lang === "hi" ? "स्थिति अपडेट विफल" : "Status update failed", "error");
    }
  };

  const handleSubmitLabReport = async (e) => {
    e.preventDefault();
    if (!labReportModal) return;
    try {
      await api.post(`/soil-tests/${labReportModal.request_id}/report`, {
        ...labReportData,
        request_id: labReportModal.request_id,
        farmer_id: labReportModal.farmer_id
      });
      showMsg(lang === "hi" ? "प्रमाणित लैब सॉइल रिपोर्ट सफलतापूर्वक सबमिट की गई!" : "Certified lab soil report submitted successfully!");
      setLabReportModal(null);
      loadSoilTests();
      loadStats();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "रिपोर्ट सबमिशन विफल" : "Report submission failed"), "error");
    }
  };

  const handleCreateServiceRequest = async (e) => {
    e.preventDefault();
    if (!newServiceReq.farmer_id) {
      showMsg(lang === "hi" ? "कृपया किसान का चयन करें" : "Please select a farmer", "error");
      return;
    }
    try {
      const { data } = await api.post("/service-requests", newServiceReq);
      showMsg(lang === "hi" ? `सेवा अनुरोध दर्ज! Request ID: ${data.request_id}` : `Service request created! Request ID: ${data.request_id}`);
      setNewServiceReq({ farmer_id: "", service_type: "SOIL_TEST", description: "" });
      loadServiceRequests();
      loadStats();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "अनुरोध विफल" : "Request creation failed"), "error");
    }
  };

  const handleResolveServiceRequest = async () => {
    if (!resolveReqId) return;
    try {
      await api.post(`/service-requests/${resolveReqId}/resolve`, null, {
        params: { resolution_notes: resolutionNotes }
      });
      showMsg(lang === "hi" ? "सेवा अनुरोध सफलतापूर्वक पूर्ण किया गया!" : "Service request resolved successfully!");
      setResolveReqId(null);
      setResolutionNotes("");
      loadServiceRequests();
      loadStats();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "समाधान विफल" : "Resolution failed"), "error");
    }
  };

  const handleDocumentUpload = async (e) => {
    e.preventDefault();
    if (!uploadDoc.farmer_id || !selectedFile) {
      showMsg(lang === "hi" ? "कृपया किसान व फ़ाइल चुनें" : "Please select farmer and file", "error");
      return;
    }
    try {
      const formPayload = new FormData();
      formPayload.append("farmer_id", uploadDoc.farmer_id);
      formPayload.append("document_name", uploadDoc.document_name);
      formPayload.append("category", uploadDoc.category);
      formPayload.append("file", selectedFile);

      await api.post("/documents/upload", formPayload, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      showMsg(lang === "hi" ? "दस्तावेज़ सफलतापूर्वक अपलोड किया गया!" : "Document uploaded successfully!");
      setUploadDoc({ farmer_id: "", document_name: "", category: "Land Record" });
      setSelectedFile(null);
      loadDocuments();
      loadStats();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "अपलोड विफल" : "Upload failed"), "error");
    }
  };

  const handleSendSms = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/communications/sms/send", {
        mobile_number: smsForm.mobile,
        message: smsForm.message,
        category: smsForm.category
      });
      showMsg(lang === "hi" ? `SMS प्रेषित! स्थिति: ${data.status} (ID: ${data.log_id})` : `SMS dispatched! Status: ${data.status} (ID: ${data.log_id})`);
      setSmsForm({ mobile: "", message: "", category: "weather_warning" });
      loadSmsLogs();
    } catch (err) {
      showMsg(err.response?.data?.detail || (lang === "hi" ? "SMS प्रेषण विफल" : "SMS dispatch failed"), "error");
    }
  };

  const handleIvrStep = async (digit = null) => {
    try {
      const payload = {
        phone: ivrSimInput.phone,
        digits: digit !== null ? digit : undefined,
        menu: ivrSimState?.current_menu || "main"
      };
      const { data } = await api.post("/communications/ivr/simulate", payload);
      setIvrSimState(data);
    } catch (e) {
      showMsg(lang === "hi" ? "IVR सिमुलेशन विफल" : "IVR simulation failed", "error");
    }
  };

  const logout = () => {
    clearAuthSession();
    nav("/login");
  };

  const menuItems = [
    { id: "dashboard", icon: <LayoutDashboard size={18} />, label: t.operator?.navDashboard || (lang === "hi" ? "डैशबोर्ड" : "Dashboard") },
    { id: "register_farmer", icon: <UserPlus size={18} />, label: t.operator?.navRegisterFarmer || (lang === "hi" ? "किसान पंजीकरण" : "Farmer Registration") },
    { id: "farmer_search", icon: <Search size={18} />, label: t.operator?.navFarmerSearch || (lang === "hi" ? "किसान खोज" : "Farmer Search") },
    { id: "farmer_profile", icon: <UserCheck size={18} />, label: t.operator?.navFarmerProfile || (lang === "hi" ? "किसान प्रोफ़ाइल व QR पास" : "Profile & QR Pass") },
    { id: "farm_management", icon: <Tractor size={18} />, label: t.operator?.navFarmManagement || (lang === "hi" ? "खेत प्रबंधन" : "Farm Management") },
    { id: "crop_registration", icon: <Sprout size={18} />, label: t.operator?.navCropRegistration || (lang === "hi" ? "फसल पंजीकरण" : "Crop Registration") },
    { id: "soil_test", icon: <FlaskConical size={18} />, label: t.operator?.navSoilTest || (lang === "hi" ? "सॉइल टेस्ट सेवा" : "Soil Test Service") },
    { id: "documents", icon: <FileText size={18} />, label: t.operator?.navDocuments || (lang === "hi" ? "दस्तावेज़ वॉल्ट" : "Document Vault") },
    { id: "service_requests", icon: <LifeBuoy size={18} />, label: t.operator?.navServiceRequests || (lang === "hi" ? "सेवा अनुरोध" : "Service Requests") },
    { id: "weather_alerts", icon: <CloudRain size={18} />, label: t.operator?.navWeatherAlerts || (lang === "hi" ? "मौसम एवं चेतावनी" : "Weather & Alerts") },
    { id: "market_price", icon: <IndianRupee size={18} />, label: t.operator?.navMarketPrice || (lang === "hi" ? "मंडी भाव SMS" : "Market Price SMS") },
    { id: "fertilizer_pest", icon: <ShieldAlert size={18} />, label: t.operator?.navFertilizerPest || (lang === "hi" ? "उर्वरक एवं कीट मार्गदर्शन" : "Fertilizer & Pest Guidance") },
    { id: "schemes", icon: <Landmark size={18} />, label: t.operator?.navSchemes || (lang === "hi" ? "सरकारी योजनाएं सहायता" : "Schemes Assistance") },
    { id: "insurance", icon: <Shield size={18} />, label: t.operator?.navInsurance || (lang === "hi" ? "फसल बीमा" : "Crop Insurance") },
    { id: "sms_ivr", icon: <PhoneCall size={18} />, label: t.operator?.navSmsIvr || (lang === "hi" ? "SMS एवं IVR केंद्र" : "SMS & IVR Center") },
    { id: "reports", icon: <BarChart3 size={18} />, label: t.operator?.navReports || (lang === "hi" ? "रिपोर्ट्स एवं सारांश" : "Reports & Summary") },
    { id: "activity_log", icon: <History size={18} />, label: t.operator?.navActivityLog || (lang === "hi" ? "ऑडिट गतिविधि लॉग" : "Audit Activity Log") }
  ];

  return (
    <div className="operatorContainer">
      {/* SIDEBAR */}
      <aside className="operatorSidebar">
        <div className="operatorBrand">
          <Logo size="compact" variant="icon" />
          <div className="operatorBrandText">
            <span className="operatorBrandTitle">MAITTRI SEVA</span>
            <span className="operatorBrandSub">{t.operator?.brandSubtitle || (lang === "hi" ? "अधिकृत सेवा ऑपरेटर केंद्र" : "Authorized Seva Operator Center")}</span>
          </div>
        </div>

        <div className="operatorTagline">
          "{t.operator?.tagline || (lang === "hi" ? "बिना स्मार्टफोन वाले किसानों की डिजिटल सेवा" : "Digital Seva for Non-Smartphone Farmers")}"
        </div>

        <nav className="operatorNav">
          {menuItems.map(item => (
            <button
              key={item.id}
              className={`operatorNavItem ${activeTab === item.id ? "active" : ""}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="operatorNavIcon">{item.icon}</span>
              <span className="operatorNavText">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="operatorSidebarFooter">
          <div style={{ display: "flex", gap: "4px", background: "rgba(0,0,0,0.25)", borderRadius: "20px", padding: "3px", marginBottom: "8px" }}>
            <button
              type="button"
              onClick={() => setLang("en")}
              style={{
                flex: 1,
                padding: "5px 8px",
                borderRadius: "16px",
                border: "none",
                fontSize: "11px",
                fontWeight: "700",
                cursor: "pointer",
                background: lang === "en" ? "#16a34a" : "transparent",
                color: lang === "en" ? "#ffffff" : "rgba(255,255,255,0.7)"
              }}
            >
              English
            </button>
            <button
              type="button"
              onClick={() => setLang("hi")}
              style={{
                flex: 1,
                padding: "5px 8px",
                borderRadius: "16px",
                border: "none",
                fontSize: "11px",
                fontWeight: "700",
                cursor: "pointer",
                background: lang === "hi" ? "#16a34a" : "transparent",
                color: lang === "hi" ? "#ffffff" : "rgba(255,255,255,0.7)"
              }}
            >
              हिन्दी
            </button>
          </div>
          <button className="operatorLogoutBtn" onClick={logout}>
            <LogOut size={15} /> {t.operator?.logoutBtn || (lang === "hi" ? "लॉगआउट" : "Logout")}
          </button>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="operatorMain">
        {/* TOPBAR */}
        <header className="operatorTopbar">
          <div className="operatorTopbarLeft">
            <h2>{menuItems.find(m => m.id === activeTab)?.label || (lang === "hi" ? "सेवा केंद्र" : "Seva Center")}</h2>
            <p>{t.operator?.protocolBadge || (lang === "hi" ? "अधिकृत कृषि / सेवा ऑपरेटर कंसोल · प्रोटोकॉल 2026.1" : "Authorized Agriculture Operator Console · Protocol 2026.1")}</p>
          </div>
          <div className="operatorTopbarRight">
            <div style={{ display: "inline-flex", gap: "2px", background: "#f1f5f9", borderRadius: "16px", padding: "2px", border: "1px solid #cbd5e1" }}>
              <button
                type="button"
                onClick={() => setLang("en")}
                style={{
                  padding: "4px 10px",
                  borderRadius: "14px",
                  border: "none",
                  fontSize: "12px",
                  fontWeight: "700",
                  cursor: "pointer",
                  background: lang === "en" ? "#166534" : "transparent",
                  color: lang === "en" ? "#ffffff" : "#64748b"
                }}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang("hi")}
                style={{
                  padding: "4px 10px",
                  borderRadius: "14px",
                  border: "none",
                  fontSize: "12px",
                  fontWeight: "700",
                  cursor: "pointer",
                  background: lang === "hi" ? "#166534" : "transparent",
                  color: lang === "hi" ? "#ffffff" : "#64748b"
                }}
              >
                हिन्दी
              </button>
            </div>
            <div className="operatorBadge">
              <span className="liveDot"></span>
              {t.operator?.authorizedOperatorBadge || (lang === "hi" ? "अधिकृत सेवा ऑपरेटर" : "Authorized Seva Operator")}
            </div>
            <Link to="/dashboard" className="operatorSwitchLink">
              👨‍🌾 {t.operator?.switchFarmerPortal || (lang === "hi" ? "किसान पोर्टल देखें" : "View Farmer Portal")}
            </Link>
          </div>
        </header>

        {feedback.text && (
          <div className={`operatorFeedbackBanner ${feedback.type}`}>
            {feedback.type === "success" ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span>{feedback.text}</span>
          </div>
        )}

        {/* TAB CONTENTS */}
        <div className="operatorTabContent">

          {/* 1. DASHBOARD */}
          {activeTab === "dashboard" && (
            <div className="operatorDashboardView">
              <div className="operatorStatsGrid">
                <div className="operatorStatCard">
                  <div className="statCardIcon green"><UserCheck size={26} /></div>
                  <div className="statCardInfo">
                    <span className="statValue">{stats?.total_registered_farmers || 0}</span>
                    <span className="statLabel">{t.operator?.totalRegisteredFarmers || (lang === "hi" ? "कुल पंजीकृत किसान" : "Registered Farmers")}</span>
                  </div>
                </div>
                <div className="operatorStatCard">
                  <div className="statCardIcon blue"><FlaskConical size={26} /></div>
                  <div className="statCardInfo">
                    <span className="statValue">{stats?.pending_soil_tests || 0}</span>
                    <span className="statLabel">{t.operator?.pendingSoilTests || (lang === "hi" ? "प्रगतिरत सॉइल टेस्ट" : "Pending Soil Tests")}</span>
                  </div>
                </div>
                <div className="operatorStatCard">
                  <div className="statCardIcon amber"><LifeBuoy size={26} /></div>
                  <div className="statCardInfo">
                    <span className="statValue">{stats?.open_service_requests || 0}</span>
                    <span className="statLabel">{t.operator?.openServiceRequests || (lang === "hi" ? "खुले सेवा अनुरोध" : "Open Service Requests")}</span>
                  </div>
                </div>
                <div className="operatorStatCard">
                  <div className="statCardIcon purple"><FileText size={26} /></div>
                  <div className="statCardInfo">
                    <span className="statValue">{stats?.total_documents_archived || 0}</span>
                    <span className="statLabel">{t.operator?.verifiedPasses || (lang === "hi" ? "सत्यापित दस्तावेज़" : "Archived Documents")}</span>
                  </div>
                </div>
              </div>

              {/* Quick Actions & Recent Activities */}
              <div className="operatorDashboardSplit">
                <div className="operatorCard">
                  <h3>⚡ {t.operator?.quickActions || (lang === "hi" ? "त्वरित कार्य" : "Quick Actions")}</h3>
                  <div className="quickActionGrid">
                    <button className="quickActionBtn" onClick={() => setActiveTab("register_farmer")}>
                      <UserPlus size={20} />
                      <span>{t.operator?.navRegisterFarmer || (lang === "hi" ? "नया किसान जोड़ें" : "Register Farmer")}</span>
                    </button>
                    <button className="quickActionBtn" onClick={() => setActiveTab("soil_test")}>
                      <FlaskConical size={20} />
                      <span>{t.operator?.bookSoilTestShort || (lang === "hi" ? "सॉइल टेस्ट बुक करें" : "Book Soil Test")}</span>
                    </button>
                    <button className="quickActionBtn" onClick={() => setActiveTab("sms_ivr")}>
                      <Send size={20} />
                      <span>{t.operator?.sendSmsShort || (lang === "hi" ? "मौसम चेतावनी SMS भेजें" : "Broadcast SMS")}</span>
                    </button>
                    <button className="quickActionBtn" onClick={() => setActiveTab("documents")}>
                      <Upload size={20} />
                      <span>{t.operator?.uploadBtn || (lang === "hi" ? "दस्तावेज़ अपलोड करें" : "Upload Document")}</span>
                    </button>
                  </div>
                </div>

                <div className="operatorCard">
                  <h3>📋 {lang === "hi" ? "हालिया ऑपरेटर गतिविधियां" : "Recent Operator Activities"}</h3>
                  {stats?.recent_activities?.length > 0 ? (
                    <ul className="operatorActivityList">
                      {stats.recent_activities.map(act => (
                        <li key={act.id}>
                          <span className="activityBadge">{act.action_type}</span>
                          <span className="activityDetails">{act.details}</span>
                          <span className="activityTime">{act.created_at}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="emptyText">{lang === "hi" ? "कोई हालिया गतिविधि नहीं।" : "No recent activity."}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 2. REGISTER FARMER */}
          {activeTab === "register_farmer" && (
            <div className="operatorCard">
              <div className="formHeader">
                <h3>📝 {t.operator?.assistedRegTitle || (lang === "hi" ? "किसान सहायता पंजीकरण फॉर्म" : "Assisted Farmer Registration")}</h3>
                <p>{t.operator?.assistedRegDesc || (lang === "hi" ? "यह फॉर्म उन किसानों के लिए है जिनके पास स्मार्टफोन या इंटरनेट नहीं है। सबमिट करने पर एक अद्वितीय MAITTRI FARM ID बनेगी।" : "This form registers farmers without smartphones into the central MAITTRI database.")}</p>
              </div>

              <form onSubmit={handleRegisterSubmit} className="operatorFormGrid">
                <div className="formGroup">
                  <label>{t.operator?.farmerFullName || (lang === "hi" ? "किसान का नाम" : "Farmer Name")} *</label>
                  <input
                    type="text"
                    required
                    placeholder={lang === "hi" ? "उदा. रमेश कुमार" : "e.g. Ramesh Kumar"}
                    value={regForm.name}
                    onChange={e => setRegForm({ ...regForm, name: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.primaryMobile || (lang === "hi" ? "मोबाइल नंबर" : "Mobile Number")} *</label>
                  <input
                    type="tel"
                    required
                    placeholder="9876543210"
                    value={regForm.mobile_number}
                    onChange={e => setRegForm({ ...regForm, mobile_number: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.alternateMobile || (lang === "hi" ? "वैकल्पिक मोबाइल" : "Alternate Mobile")}</label>
                  <input
                    type="tel"
                    placeholder="9123456780"
                    value={regForm.alternate_mobile}
                    onChange={e => setRegForm({ ...regForm, alternate_mobile: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.state || (lang === "hi" ? "राज्य" : "State")}</label>
                  <input
                    type="text"
                    value={regForm.state}
                    onChange={e => setRegForm({ ...regForm, state: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.district || (lang === "hi" ? "जिला" : "District")} *</label>
                  <input
                    type="text"
                    required
                    value={regForm.district}
                    onChange={e => setRegForm({ ...regForm, district: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.blockTehsil || (lang === "hi" ? "ब्लॉक" : "Block")}</label>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "उदा. पिंडरा" : "e.g. Pindra"}
                    value={regForm.block}
                    onChange={e => setRegForm({ ...regForm, block: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.village || (lang === "hi" ? "गाँव" : "Village")} *</label>
                  <input
                    type="text"
                    required
                    placeholder={lang === "hi" ? "उदा. शिवपुर" : "e.g. Shivpur"}
                    value={regForm.village}
                    onChange={e => setRegForm({ ...regForm, village: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.landArea || (lang === "hi" ? "खेत का क्षेत्रफल" : "Farm Area")}</label>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <input
                      type="number"
                      step="0.1"
                      required
                      value={regForm.farm_area}
                      onChange={e => setRegForm({ ...regForm, farm_area: parseFloat(e.target.value) || 1 })}
                    />
                    <select
                      value={regForm.area_unit}
                      onChange={e => setRegForm({ ...regForm, area_unit: e.target.value })}
                    >
                      <option value="acre">{t.operator?.acre || (lang === "hi" ? "एकड़" : "Acre")}</option>
                      <option value="hectare">{t.operator?.hectare || (lang === "hi" ? "हेक्टेयर" : "Hectare")}</option>
                      <option value="bigha">{t.operator?.bigha || (lang === "hi" ? "बीघा" : "Bigha")}</option>
                    </select>
                  </div>
                </div>

                <div className="formGroup">
                  <label>{t.operator?.ownership || (lang === "hi" ? "भूमि स्वामित्व" : "Land Ownership")}</label>
                  <select
                    value={regForm.land_ownership}
                    onChange={e => setRegForm({ ...regForm, land_ownership: e.target.value })}
                  >
                    <option value="owner">{t.operator?.owner || (lang === "hi" ? "स्वयं की भूमि (मालिक)" : "Owner")}</option>
                    <option value="tenant">{t.operator?.tenant || (lang === "hi" ? "पट्टेदार" : "Tenant")}</option>
                    <option value="sharecropper">{t.operator?.sharecropper || (lang === "hi" ? "बटाईदार" : "Sharecropper")}</option>
                  </select>
                </div>

                <div className="formGroup">
                  <label>{t.operator?.irrigationSource || (lang === "hi" ? "सिंचाई सुविधा" : "Irrigation Facility")}</label>
                  <select
                    value={regForm.irrigation}
                    onChange={e => setRegForm({ ...regForm, irrigation: e.target.value })}
                  >
                    <option value="tubewell">{t.operator?.tubewell || (lang === "hi" ? "नलकूप / बोरवेल" : "Tubewell / Borewell")}</option>
                    <option value="canal">{t.operator?.canal || (lang === "hi" ? "नहर" : "Canal")}</option>
                    <option value="drip">{t.operator?.drip || (lang === "hi" ? "ड्रिप / स्प्रिंकलर" : "Drip / Sprinkler")}</option>
                    <option value="rainfed">{t.operator?.rainfed || (lang === "hi" ? "वर्षा आधारित" : "Rainfed")}</option>
                    <option value="none">{lang === "hi" ? "कोई साधन नहीं" : "None"}</option>
                  </select>
                </div>

                <div className="formGroup">
                  <label>{t.operator?.soilType || (lang === "hi" ? "मिट्टी का प्रकार" : "Soil Type")}</label>
                  <select
                    value={regForm.soil_type}
                    onChange={e => setRegForm({ ...regForm, soil_type: e.target.value })}
                  >
                    <option value="Alluvial Soil">{lang === "hi" ? "जलोढ़ मिट्टी" : "Alluvial Soil"}</option>
                    <option value="Black Soil">{lang === "hi" ? "काली मिट्टी" : "Black Soil"}</option>
                    <option value="Red Soil">{lang === "hi" ? "लाल मिट्टी" : "Red Soil"}</option>
                    <option value="Loamy Soil">{lang === "hi" ? "दोमट मिट्टी" : "Loamy Soil"}</option>
                    <option value="Sandy Loam">{lang === "hi" ? "बलुई दोमट" : "Sandy Loam"}</option>
                    <option value="Clayey Soil">{lang === "hi" ? "चिकनी मिट्टी" : "Clayey Soil"}</option>
                  </select>
                </div>

                <div className="formGroup">
                  <label>{t.operator?.currentCrop || (lang === "hi" ? "वर्तमान फसल" : "Current Crop")}</label>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "उदा. गेहूँ" : "e.g. Wheat"}
                    value={regForm.current_crop}
                    onChange={e => setRegForm({ ...regForm, current_crop: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.previousCrop || (lang === "hi" ? "पिछली फसल" : "Previous Crop")}</label>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "उदा. धान" : "e.g. Rice"}
                    value={regForm.previous_crop}
                    onChange={e => setRegForm({ ...regForm, previous_crop: e.target.value })}
                  />
                </div>

                <div className="formGroup">
                  <label>{t.operator?.sowingDate || (lang === "hi" ? "बुवाई की तिथि" : "Sowing Date")}</label>
                  <input
                    type="date"
                    value={regForm.sowing_date}
                    onChange={e => setRegForm({ ...regForm, sowing_date: e.target.value })}
                  />
                </div>

                <div className="formGroup fullWidth">
                  <div className="consentChecks">
                    <label>
                      <input
                        type="checkbox"
                        checked={regForm.sms_consent}
                        onChange={e => setRegForm({ ...regForm, sms_consent: e.target.checked })}
                      />
                      {t.operator?.smsConsent || (lang === "hi" ? "किसान ने SMS मौसम व फसल चेतावनी प्राप्त करने की स्पष्ट सहमति दी है" : "Farmer agrees to receive weather, mandi and stage alerts via SMS")}
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={regForm.ivr_consent}
                        onChange={e => setRegForm({ ...regForm, ivr_consent: e.target.checked })}
                      />
                      {t.operator?.ivrConsent || (lang === "hi" ? "किसान ने IVR वॉइस कॉल मार्गदर्शन की सहमति दी है" : "Farmer agrees to receive automated phone calls (IVR voice advisory)")}
                    </label>
                  </div>
                </div>

                <div className="formGroup fullWidth">
                  <button type="submit" className="operatorPrimaryBtn" disabled={loading}>
                    {loading ? (t.operator?.registering || (lang === "hi" ? "पंजीकरण जारी..." : "Registering...")) : ("✅ " + (t.operator?.registerFarmerBtn || (lang === "hi" ? "किसान पंजीकृत करें व ID उत्पन्न करें" : "Complete Farmer Registration")))}
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* 3. FARMER SEARCH */}
          {activeTab === "farmer_search" && (
            <div className="operatorCard">
              <h3>🔍 {t.operator?.searchFarmerTitle || (lang === "hi" ? "पंजीकृत किसान खोज" : "Search Registered Farmers")}</h3>
              <div className="searchBarRow">
                <input
                  type="text"
                  placeholder={t.operator?.searchPlaceholder || (lang === "hi" ? "किसान का नाम, मोबाइल नंबर, गाँव या ID दर्ज करें..." : "Search by Name, Mobile Number, or Farmer ID...")}
                  value={searchQuery}
                  onChange={e => {
                    setSearchQuery(e.target.value);
                    loadFarmers(e.target.value);
                  }}
                />
                <button className="operatorSecondaryBtn" onClick={() => loadFarmers(searchQuery)}>
                  {t.common?.search || (lang === "hi" ? "खोजें" : "Search")}
                </button>
              </div>

              <div className="operatorTableWrap">
                <table className="operatorTable">
                  <thead>
                    <tr>
                      <th>MAITTRI ID</th>
                      <th>{t.operator?.name || (lang === "hi" ? "किसान का नाम" : "Farmer Name")}</th>
                      <th>{t.operator?.mobile || (lang === "hi" ? "मोबाइल नंबर" : "Mobile Number")}</th>
                      <th>{t.operator?.villageDistrict || (lang === "hi" ? "स्थान / गाँव" : "Location / Village")}</th>
                      <th>{t.operator?.landArea || (lang === "hi" ? "रकबा (क्षेत्रफल)" : "Area")}</th>
                      <th>{t.operator?.currentCrop || (lang === "hi" ? "वर्तमान फसल" : "Current Crop")}</th>
                      <th>{t.operator?.actions || (lang === "hi" ? "कार्य" : "Actions")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {farmers.length > 0 ? (
                      farmers.map(f => (
                        <tr key={f.id}>
                          <td><span className="idBadge">{f.maittri_farmer_id}</span></td>
                          <td><strong>{f.name}</strong></td>
                          <td>{f.mobile_number}</td>
                          <td>{f.village ? `${f.village}, ` : ""}{f.district}</td>
                          <td>{f.farm_area} {f.area_unit}</td>
                          <td><span className="cropBadge">{f.current_crop || (lang === "hi" ? "कोई नहीं" : "None")}</span></td>
                          <td>
                            <button
                              className="actionTableBtn"
                              onClick={() => {
                                setSelectedFarmer(f);
                                setActiveTab("farmer_profile");
                              }}
                            >
                              <Eye size={14} /> {t.operator?.viewProfileBtn || (lang === "hi" ? "प्रोफ़ाइल" : "Profile")}
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="7" style={{ textAlign: "center", padding: "20px" }}>
                          {t.operator?.noFarmersFound || (lang === "hi" ? "कोई किसान नहीं मिला।" : "No farmers found.")}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 4. FARMER PROFILE & QR */}
          {activeTab === "farmer_profile" && (
            <div className="operatorProfileView">
              {selectedFarmer ? (
                <div className="profileLayout">
                  {/* Digital Farmer Card */}
                  <div className="farmerDigitalCard">
                    <div className="cardHeader">
                      <Logo size="compact" variant="icon" />
                      <div>
                        <h4>MAITTRI FARMER PASS</h4>
                        <span>{lang === "hi" ? "मैत्री किसान डिजिटल पहचान" : "MAITTRI Digital Identification"}</span>
                      </div>
                    </div>
                    <div className="cardBody">
                      <div className="cardPhotoPlaceholder">
                        👨‍🌾
                      </div>
                      <div className="cardDetails">
                        <h3>{selectedFarmer.name}</h3>
                        <p className="cardIdText">{selectedFarmer.maittri_farmer_id}</p>
                        <p><strong>{lang === "hi" ? "मोबाइल:" : "Mobile:"}</strong> {selectedFarmer.mobile_number}</p>
                        <p><strong>{lang === "hi" ? "स्थान:" : "Location:"}</strong> {selectedFarmer.village ? `${selectedFarmer.village}, ` : ""}{selectedFarmer.district}</p>
                        <p><strong>{lang === "hi" ? "रकबा:" : "Area:"}</strong> {selectedFarmer.farm_area} {selectedFarmer.area_unit}</p>
                        <p><strong>{lang === "hi" ? "मुख्य फसल:" : "Main Crop:"}</strong> {selectedFarmer.current_crop || "Wheat"}</p>
                      </div>
                    </div>
                    <div className="cardFooter">
                      <div className="qrMockBox">
                        <QrCode size={48} />
                        <span>{lang === "hi" ? "सुरक्षित QR सत्यापन" : "Secure QR Verification"}</span>
                      </div>
                      <div className="cardFooterText">
                        "{t.tagline || (lang === "hi" ? "किसान का साथी, समृद्धि की शुरुआत" : "Farmer's Companion, Beginning of Prosperity")}"<br />
                        <small>{lang === "hi" ? "टोल-फ्री IVR व सेवा केंद्र मान्य" : "Toll-Free IVR & Seva Center Validated"}</small>
                      </div>
                    </div>
                  </div>

                  {/* Comprehensive Profile Info */}
                  <div className="profileInfoBox">
                    <div className="profileHeaderRow">
                      <h3>{lang === "hi" ? "विस्तृत किसान विवरणी" : "Detailed Farmer Profile"}</h3>
                      <div className="profileActionBtns">
                        <button
                          className="operatorSecondaryBtn"
                          onClick={() => {
                            setNewSoilTest(prev => ({ ...prev, farmer_id: selectedFarmer.id, crop: selectedFarmer.current_crop }));
                            setActiveTab("soil_test");
                          }}
                        >
                          🧪 {t.operator?.bookSoilTestShort || (lang === "hi" ? "सॉइल टेस्ट बुक करें" : "Book Soil Test")}
                        </button>
                        <button
                          className="operatorSecondaryBtn"
                          onClick={() => {
                            setSmsForm(prev => ({ ...prev, mobile: selectedFarmer.mobile_number }));
                            setActiveTab("sms_ivr");
                          }}
                        >
                          📩 {t.operator?.sendSmsShort || (lang === "hi" ? "SMS भेजें" : "Send SMS")}
                        </button>
                      </div>
                    </div>

                    <div className="detailsGrid">
                      <div><strong>{lang === "hi" ? "पिता/पति का नाम:" : "Father/Husband Name:"}</strong> {lang === "hi" ? "उपलब्ध नहीं" : "Not available"}</div>
                      <div><strong>{lang === "hi" ? "भूमि का प्रकार:" : "Soil Type:"}</strong> {selectedFarmer.soil_type}</div>
                      <div><strong>{lang === "hi" ? "सिंचाई साधन:" : "Irrigation:"}</strong> {selectedFarmer.irrigation}</div>
                      <div><strong>{lang === "hi" ? "स्वामित्व स्थिति:" : "Ownership:"}</strong> {selectedFarmer.land_ownership}</div>
                      <div><strong>{lang === "hi" ? "पिछली फसल:" : "Previous Crop:"}</strong> {selectedFarmer.previous_crop || "N/A"}</div>
                      <div><strong>{lang === "hi" ? "बुवाई तिथि:" : "Sowing Date:"}</strong> {selectedFarmer.sowing_date || "N/A"}</div>
                      <div><strong>{lang === "hi" ? "पसंदीदा भाषा:" : "Preferred Language:"}</strong> {selectedFarmer.preferred_language === "hi" ? "हिन्दी" : "English"}</div>
                      <div><strong>{lang === "hi" ? "SMS अलर्ट सहमति:" : "SMS Alert Consent:"}</strong> {selectedFarmer.sms_consent ? (lang === "hi" ? "हाँ (सक्रिय)" : "Yes (Active)") : (lang === "hi" ? "नहीं" : "No")}</div>
                      <div><strong>{lang === "hi" ? "IVR वॉइस सहमति:" : "IVR Voice Consent:"}</strong> {selectedFarmer.ivr_consent ? (lang === "hi" ? "हाँ (सक्रिय)" : "Yes (Active)") : (lang === "hi" ? "नहीं" : "No")}</div>
                      <div><strong>{lang === "hi" ? "पंजीकरण तिथि:" : "Registration Date:"}</strong> {selectedFarmer.created_at ? selectedFarmer.created_at.split("T")[0] : (lang === "hi" ? "आज" : "Today")}</div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="operatorCard emptyCard">
                  <UserCheck size={48} />
                  <p>{lang === "hi" ? "कृपया पहले किसान खोजें या नया किसान पंजीकृत करें।" : "Please search for a farmer or register a new farmer first."}</p>
                  <button className="operatorPrimaryBtn" onClick={() => setActiveTab("farmer_search")}>
                    {t.operator?.searchFarmerTitle || (lang === "hi" ? "किसान खोजें" : "Search Farmers")}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* 5. FARM MANAGEMENT */}
          {activeTab === "farm_management" && (
            <div className="operatorCard">
              <h3>🚜 {t.operator?.navFarmManagement || (lang === "hi" ? "खेत एवं भू-अभिलेख प्रबंधन" : "Farm & Land Record Management")}</h3>
              <p>{lang === "hi" ? "किसान के खेतों का रकबा, सिंचाई स्थिति एवं सीमांकन विवरण।" : "Farmer field parcel area, irrigation status and demarcation details."}</p>
              {selectedFarmer ? (
                <div className="farmSpecs">
                  <div className="specItem">
                    <span>खेत का नाम:</span>
                    <strong>{selectedFarmer.name}'s Farm</strong>
                  </div>
                  <div className="specItem">
                    <span>रकबा (क्षेत्रफल):</span>
                    <strong>{selectedFarmer.farm_area} {selectedFarmer.area_unit}</strong>
                  </div>
                  <div className="specItem">
                    <span>मिट्टी वर्गीकरण:</span>
                    <strong>{selectedFarmer.soil_type}</strong>
                  </div>
                  <div className="specItem">
                    <span>सिंचाई की स्थिति:</span>
                    <strong>{selectedFarmer.irrigation}</strong>
                  </div>
                  <div className="specItem">
                    <span>स्थान (District):</span>
                    <strong>{selectedFarmer.district}, {selectedFarmer.state}</strong>
                  </div>
                </div>
              ) : (
                <p className="emptyText">कृपया कोई किसान चुनें।</p>
              )}
            </div>
          )}

          {/* 6. CROP REGISTRATION */}
          {activeTab === "crop_registration" && (
            <div className="operatorCard">
              <h3>🌾 {t.operator?.navCropRegistration || (lang === "hi" ? "फसल चक्र एवं बुवाई पंजीकरण" : "Crop Registration")}</h3>
              {selectedFarmer ? (
                <div>
                  <p>{lang === "hi" ? "वर्तमान सक्रिय फसल:" : "Current Active Crop:"} <strong>{selectedFarmer.current_crop}</strong></p>
                  <p>{lang === "hi" ? "पिछली फसल चक्र:" : "Previous Crop Cycle:"} <strong>{selectedFarmer.previous_crop}</strong></p>
                  <p>{lang === "hi" ? "आगामी योजनाबद्ध फसल:" : "Planned Next Crop:"} <strong>{selectedFarmer.planned_crop || (lang === "hi" ? "मक्का / दलहन" : "Maize / Pulses")}</strong></p>
                  <p>{lang === "hi" ? "बुवाई की अनुमानित तिथि:" : "Estimated Sowing Date:"} <strong>{selectedFarmer.sowing_date || (lang === "hi" ? "हाल ही में" : "Recent")}</strong></p>
                </div>
              ) : (
                <p className="emptyText">{lang === "hi" ? "कृपया कोई किसान चुनें।" : "Please select a farmer."}</p>
              )}
            </div>
          )}

          {/* 7. SOIL TEST SERVICE */}
          {activeTab === "soil_test" && (
            <div className="operatorSoilTestView">
              <div className="operatorCard">
                <h3>🧪 {t.operator?.bookNewSoilTest || (lang === "hi" ? "नई प्रयोगशाला सॉइल टेस्ट बुकिंग" : "Book New Soil Sample Collection")}</h3>
                <p>{t.operator?.soilTestServiceDesc || (lang === "hi" ? "प्रमाणित प्रयोगशाला में नमूना जांच के लिए बुकिंग दर्ज करें।" : "Manage soil sample collection and laboratory test bookings.")}</p>
                <form onSubmit={handleBookSoilTest} className="inlineForm">
                  <select
                    value={newSoilTest.farmer_id}
                    onChange={e => setNewSoilTest({ ...newSoilTest, farmer_id: e.target.value })}
                    required
                  >
                    <option value="">{lang === "hi" ? "-- किसान का चयन करें --" : "-- Select Farmer --"}</option>
                    {farmers.map(f => (
                      <option key={f.id} value={f.id}>{f.name} ({f.maittri_farmer_id}) - {f.village || f.district}</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "खेत का हिस्सा / प्लॉट विवरण" : "Field Parcel / Plot Location"}
                    value={newSoilTest.location}
                    onChange={e => setNewSoilTest({ ...newSoilTest, location: e.target.value })}
                  />
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "फसल" : "Crop"}
                    value={newSoilTest.crop}
                    onChange={e => setNewSoilTest({ ...newSoilTest, crop: e.target.value })}
                  />
                  <button type="submit" className="operatorPrimaryBtn">
                    {t.operator?.bookSoilTestShort || (lang === "hi" ? "बुकिंग दर्ज करें" : "Book Soil Test")}
                  </button>
                </form>
              </div>

              <div className="operatorCard">
                <h3>📋 {t.operator?.recentSoilTests || (lang === "hi" ? "सॉइल टेस्ट अनुरोध एवं स्थिति ट्रैकिंग" : "Recent Soil Test Requests")}</h3>
                <div className="operatorTableWrap">
                  <table className="operatorTable">
                    <thead>
                      <tr>
                        <th>Request ID</th>
                        <th>{lang === "hi" ? "किसान ID" : "Farmer ID"}</th>
                        <th>{lang === "hi" ? "प्लॉट / फसल" : "Plot / Crop"}</th>
                        <th>{t.common?.status || (lang === "hi" ? "वर्तमान स्थिति" : "Status")}</th>
                        <th>{t.operator?.labName || (lang === "hi" ? "प्रयोगशाला" : "Laboratory")}</th>
                        <th>{t.operator?.actions || (lang === "hi" ? "कार्यवाही" : "Actions")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {soilTests.length > 0 ? (
                        soilTests.map(st => (
                          <tr key={st.id}>
                            <td><strong>{st.request_id}</strong></td>
                            <td>Farmer #{st.farmer_id}</td>
                            <td>{st.crop || "General"} ({st.location || "Main"})</td>
                            <td>
                              <span className={`statusPill ${st.status.toLowerCase()}`}>
                                {st.status}
                              </span>
                            </td>
                            <td>{st.lab_name || "Regional KVK Lab"}</td>
                            <td>
                              <div className="tableActionGroup">
                                {st.status === "REQUESTED" && (
                                  <button
                                    className="stepBtn"
                                    onClick={() => handleUpdateSoilStatus(st.request_id, "SCHEDULED")}
                                  >
                                    {lang === "hi" ? "शेड्यूल करें" : "Schedule"}
                                  </button>
                                )}
                                {st.status === "SCHEDULED" && (
                                  <button
                                    className="stepBtn"
                                    onClick={() => handleUpdateSoilStatus(st.request_id, "SAMPLE_COLLECTED")}
                                  >
                                    {lang === "hi" ? "सैंपल कलेक्ट" : "Collect Sample"}
                                  </button>
                                )}
                                {st.status === "SAMPLE_COLLECTED" && (
                                  <button
                                    className="stepBtn"
                                    onClick={() => handleUpdateSoilStatus(st.request_id, "LAB_PROCESSING")}
                                  >
                                    {lang === "hi" ? "लैब प्रोसेसिंग" : "Process in Lab"}
                                  </button>
                                )}
                                {st.status === "LAB_PROCESSING" && (
                                  <button
                                    className="stepBtn primary"
                                    onClick={() => setLabReportModal(st)}
                                  >
                                    {t.operator?.enterLabReport || (lang === "hi" ? "लैब रिपोर्ट दर्ज करें" : "Enter Lab Report")}
                                  </button>
                                )}
                                {st.status === "REPORT_AVAILABLE" && (
                                  <span className="verifiedLabel">✅ {lang === "hi" ? "रिपोर्ट उपलब्ध" : "Report Ready"}</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="6" style={{ textAlign: "center" }}>{lang === "hi" ? "कोई सॉइल टेस्ट बुकिंग नहीं।" : "No soil test requests found."}</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Certified Lab Report Modal */}
              {labReportModal && (
                <div className="operatorModalBackdrop">
                  <div className="operatorModalContent">
                    <div className="modalHeader">
                      <h4>🔬 {t.operator?.soilReportModalTitle || (lang === "hi" ? "प्रमाणित लैब जांच रिपोर्ट दर्ज करें" : "Enter Certified Lab Soil Test Report")} ({labReportModal.request_id})</h4>
                      <button onClick={() => setLabReportModal(null)}><X size={18} /></button>
                    </div>
                    <form onSubmit={handleSubmitLabReport}>
                      <div className="modalFormGrid">
                        <div className="formGroup">
                          <label>{t.operator?.labName || (lang === "hi" ? "प्रयोगशाला का नाम" : "Testing Laboratory")}</label>
                          <input
                            type="text"
                            required
                            value={labReportData.lab_name}
                            onChange={e => setLabReportData({ ...labReportData, lab_name: e.target.value })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.sampleDate || (lang === "hi" ? "परीक्षण तिथि" : "Test Date")}</label>
                          <input
                            type="date"
                            value={labReportData.test_date}
                            onChange={e => setLabReportData({ ...labReportData, test_date: e.target.value })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.nitrogenN || (lang === "hi" ? "नाइट्रोजन (किग्रा/हेक्टेयर)" : "Nitrogen (N) kg/ha")}</label>
                          <input
                            type="number"
                            step="0.1"
                            value={labReportData.nitrogen}
                            onChange={e => setLabReportData({ ...labReportData, nitrogen: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.phosphorusP || (lang === "hi" ? "फास्फोरस (किग्रा/हेक्टेयर)" : "Phosphorus (P) kg/ha")}</label>
                          <input
                            type="number"
                            step="0.1"
                            value={labReportData.phosphorus}
                            onChange={e => setLabReportData({ ...labReportData, phosphorus: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.potassiumK || (lang === "hi" ? "पोटैशियम (किग्रा/हेक्टेयर)" : "Potassium (K) kg/ha")}</label>
                          <input
                            type="number"
                            step="0.1"
                            value={labReportData.potassium}
                            onChange={e => setLabReportData({ ...labReportData, potassium: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.soilPh || (lang === "hi" ? "मृदा pH" : "Soil pH")}</label>
                          <input
                            type="number"
                            step="0.1"
                            value={labReportData.ph}
                            onChange={e => setLabReportData({ ...labReportData, ph: parseFloat(e.target.value) || 7 })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.electricalConductivity || (lang === "hi" ? "विद्युत चालकता" : "EC (dS/m)")}</label>
                          <input
                            type="number"
                            step="0.01"
                            value={labReportData.ec}
                            onChange={e => setLabReportData({ ...labReportData, ec: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                        <div className="formGroup">
                          <label>{t.operator?.organicCarbon || (lang === "hi" ? "जैविक कार्बन (%)" : "Organic Carbon (%)")}</label>
                          <input
                            type="number"
                            step="0.01"
                            value={labReportData.organic_carbon}
                            onChange={e => setLabReportData({ ...labReportData, organic_carbon: parseFloat(e.target.value) || 0 })}
                          />
                        </div>
                      </div>
                      <div className="modalFooter">
                        <button type="button" className="operatorSecondaryBtn" onClick={() => setLabReportModal(null)}>
                          {t.common?.cancel || (lang === "hi" ? "रद्द करें" : "Cancel")}
                        </button>
                        <button type="submit" className="operatorPrimaryBtn">
                          {t.operator?.saveLabReportBtn || (lang === "hi" ? "प्रमाणित रिपोर्ट सबमिट करें" : "Submit Certified Report")}
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 8. DOCUMENT VAULT */}
          {activeTab === "documents" && (
            <div className="operatorDocumentsView">
              <div className="operatorCard">
                <h3>📁 {t.operator?.uploadDocument || (lang === "hi" ? "सुरक्षित किसान दस्तावेज़ अपलोड" : "Upload Farmer Document")}</h3>
                <p>{t.operator?.documentVaultDesc || (lang === "hi" ? "भूमि खसरा/खतौनी, सॉइल टेस्ट कार्ड, बीमा रसीद व पहचान पत्र सुरक्षित रूप से अपलोड करें।" : "Secure storage for Land Records, Soil Health Cards, and Insurance documents.")}</p>
                <form onSubmit={handleDocumentUpload} className="uploadFormRow">
                  <select
                    value={uploadDoc.farmer_id}
                    onChange={e => setUploadDoc({ ...uploadDoc, farmer_id: e.target.value })}
                    required
                  >
                    <option value="">{lang === "hi" ? "-- किसान चुनें --" : "-- Select Farmer --"}</option>
                    {farmers.map(f => (
                      <option key={f.id} value={f.id}>{f.name} ({f.maittri_farmer_id})</option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "दस्तावेज़ का शीर्षक (उदा. खतौनी 1431 फसली)" : "Document Title (e.g. Land Record 2026)"}
                    value={uploadDoc.document_name}
                    onChange={e => setUploadDoc({ ...uploadDoc, document_name: e.target.value })}
                    required
                  />
                  <select
                    value={uploadDoc.category}
                    onChange={e => setUploadDoc({ ...uploadDoc, category: e.target.value })}
                  >
                    <option value="Land Record">{t.operator?.landRecord || (lang === "hi" ? "भू-अभिलेख / खतौनी" : "Land Record")}</option>
                    <option value="Soil Test Report">{t.operator?.soilHealthCard || (lang === "hi" ? "सॉइल टेस्ट रिपोर्ट" : "Soil Test Report")}</option>
                    <option value="Crop Record">{lang === "hi" ? "फसल गिरदावरी / रिकॉर्ड" : "Crop Record"}</option>
                    <option value="Insurance">{t.operator?.insuranceCertificate || (lang === "hi" ? "बीमा पॉलिसी / रसीद" : "Insurance Policy / Receipt")}</option>
                    <option value="Scheme Application">{lang === "hi" ? "योजना आवेदन पत्र" : "Scheme Application"}</option>
                    <option value="Other">{lang === "hi" ? "अन्य सहायक दस्तावेज़" : "Other Document"}</option>
                  </select>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    onChange={e => setSelectedFile(e.target.files[0])}
                    required
                  />
                  <button type="submit" className="operatorPrimaryBtn">
                    {t.operator?.uploadBtn || (lang === "hi" ? "वॉल्ट में अपलोड करें" : "Upload to Vault")}
                  </button>
                </form>
              </div>

              <div className="operatorCard">
                <h3>📜 {t.operator?.uploadedDocuments || (lang === "hi" ? "वॉल्ट में सुरक्षित दस्तावेज़ सूची" : "Stored Documents")}</h3>
                <div className="operatorTableWrap">
                  <table className="operatorTable">
                    <thead>
                      <tr>
                        <th>{t.operator?.docName || (lang === "hi" ? "दस्तावेज़ नाम" : "Document Name")}</th>
                        <th>{lang === "hi" ? "किसान ID" : "Farmer ID"}</th>
                        <th>{t.operator?.docCategory || (lang === "hi" ? "श्रेणी" : "Category")}</th>
                        <th>{lang === "hi" ? "प्रकार" : "Type"}</th>
                        <th>{lang === "hi" ? "साइज़" : "Size"}</th>
                        <th>{t.common?.status || (lang === "hi" ? "स्थिति" : "Status")}</th>
                        <th>{lang === "hi" ? "अपलोड तिथि" : "Upload Date"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {documents.length > 0 ? (
                        documents.map(d => (
                          <tr key={d.id}>
                            <td><strong>{d.document_name}</strong></td>
                            <td>Farmer #{d.farmer_id}</td>
                            <td><span className="categoryPill">{d.category}</span></td>
                            <td>{d.file_type}</td>
                            <td>{d.file_size_kb} KB</td>
                            <td><span className="verifiedLabel">✅ {d.status}</span></td>
                            <td>{d.uploaded_at}</td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="7" style={{ textAlign: "center" }}>{lang === "hi" ? "कोई दस्तावेज़ उपलब्ध नहीं।" : "No documents available."}</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 9. SERVICE REQUESTS */}
          {activeTab === "service_requests" && (
            <div className="operatorServiceRequestsView">
              <div className="operatorCard">
                <h3>🛎️ {t.operator?.createServiceRequest || (lang === "hi" ? "नया सेवा अनुरोध दर्ज करें" : "Create New Service Request")}</h3>
                <form onSubmit={handleCreateServiceRequest} className="inlineForm">
                  <select
                    value={newServiceReq.farmer_id}
                    onChange={e => setNewServiceReq({ ...newServiceReq, farmer_id: e.target.value })}
                    required
                  >
                    <option value="">{lang === "hi" ? "-- किसान चुनें --" : "-- Select Farmer --"}</option>
                    {farmers.map(f => (
                      <option key={f.id} value={f.id}>{f.name} ({f.maittri_farmer_id})</option>
                    ))}
                  </select>
                  <select
                    value={newServiceReq.service_type}
                    onChange={e => setNewServiceReq({ ...newServiceReq, service_type: e.target.value })}
                  >
                    <option value="SOIL_TEST">{t.operator?.soilTestCategory || (lang === "hi" ? "सॉइल टेस्ट सहायता" : "Soil Test Assistance")}</option>
                    <option value="CROP_ADVISORY">{lang === "hi" ? "फसल परामर्श" : "Crop Advisory"}</option>
                    <option value="PEST_ADVISORY">{t.operator?.pestAdvisoryCategory || (lang === "hi" ? "कीट/रोग उपचार" : "Pest & Disease Advisory")}</option>
                    <option value="FERTILIZER_ADVISORY">{lang === "hi" ? "उर्वरक मार्गदर्शन" : "Fertilizer Guidance"}</option>
                    <option value="DOCUMENT_ASSISTANCE">{lang === "hi" ? "दस्तावेज़ सहायता" : "Document Assistance"}</option>
                    <option value="SCHEME_ASSISTANCE">{t.operator?.schemeAssistanceCategory || (lang === "hi" ? "योजना आवेदन सहायता" : "Scheme Application Assistance")}</option>
                    <option value="INSURANCE_ASSISTANCE">{t.operator?.insuranceClaimCategory || (lang === "hi" ? "बीमा क्लेम सहायता" : "Insurance Claim Assistance")}</option>
                  </select>
                  <input
                    type="text"
                    placeholder={lang === "hi" ? "अनुरोध का संक्षिप्त विवरण..." : "Brief description of request / grievance..."}
                    required
                    value={newServiceReq.description}
                    onChange={e => setNewServiceReq({ ...newServiceReq, description: e.target.value })}
                  />
                  <button type="submit" className="operatorPrimaryBtn">
                    {lang === "hi" ? "अनुरोध दर्ज करें" : "Submit Request"}
                  </button>
                </form>
              </div>

              <div className="operatorCard">
                <h3>📋 {t.operator?.openRequestsTable || (lang === "hi" ? "सक्रिय सेवा अनुरोध सूची एवं समाधान" : "Active Service Requests & Tracking")}</h3>
                <div className="operatorTableWrap">
                  <table className="operatorTable">
                    <thead>
                      <tr>
                        <th>Request ID</th>
                        <th>{lang === "hi" ? "किसान ID" : "Farmer ID"}</th>
                        <th>{t.operator?.requestCategory || (lang === "hi" ? "सेवा प्रकार" : "Service Type")}</th>
                        <th>{t.common?.details || (lang === "hi" ? "विवरण" : "Description")}</th>
                        <th>{t.common?.status || (lang === "hi" ? "स्थिति" : "Status")}</th>
                        <th>{lang === "hi" ? "समाधान" : "Resolution"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {serviceRequests.length > 0 ? (
                        serviceRequests.map(sr => (
                          <tr key={sr.id}>
                            <td><strong>{sr.request_id}</strong></td>
                            <td>Farmer #{sr.farmer_id}</td>
                            <td><span className="categoryPill">{sr.service_type}</span></td>
                            <td>{sr.description}</td>
                            <td><span className={`statusPill ${sr.status.toLowerCase()}`}>{sr.status}</span></td>
                            <td>
                              {sr.status !== "COMPLETED" ? (
                                <button
                                  className="stepBtn primary"
                                  onClick={() => setResolveReqId(sr.request_id)}
                                >
                                  {t.operator?.resolveBtn || (lang === "hi" ? "हल करें" : "Resolve")}
                                </button>
                              ) : (
                                <small>{sr.resolution_notes || (lang === "hi" ? "संतुष्टिपूर्वक पूर्ण" : "Resolved successfully")}</small>
                              )}
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="6" style={{ textAlign: "center" }}>{lang === "hi" ? "कोई सेवा अनुरोध नहीं।" : "No service requests found."}</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {resolveReqId && (
                <div className="operatorModalBackdrop">
                  <div className="operatorModalContent">
                    <h4>{lang === "hi" ? "सेवा अनुरोध पूर्ण करें" : "Resolve Service Request"} ({resolveReqId})</h4>
                    <textarea
                      placeholder={lang === "hi" ? "किसान को दी गई सलाह अथवा समाधान विवरण लिखें..." : "Enter resolution notes or advice given to farmer..."}
                      rows="3"
                      value={resolutionNotes}
                      onChange={e => setResolutionNotes(e.target.value)}
                    ></textarea>
                    <div className="modalFooter">
                      <button className="operatorSecondaryBtn" onClick={() => setResolveReqId(null)}>{t.common?.cancel || (lang === "hi" ? "रद्द करें" : "Cancel")}</button>
                      <button className="operatorPrimaryBtn" onClick={handleResolveServiceRequest}>{t.operator?.confirmResolveBtn || (lang === "hi" ? "पूर्ण चिन्हित करें" : "Mark as Resolved")}</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 10. WEATHER ALERTS */}
          {activeTab === "weather_alerts" && (
            <div className="operatorCard">
              <h3>🌦️ {lang === "hi" ? "मौसम पूर्वानुमान एवं क्षेत्रीय चेतावनी प्रसारण" : "Weather Forecast & Regional Alert Broadcast"}</h3>
              <p>{lang === "hi" ? "स्थानीय किसानों को भारी वर्षा, ओलावृष्टि या कीट-अनुकूल आर्द्रता की अग्रिम SMS सूचना दें।" : "Broadcast advance SMS alerts to local farmers for heavy rain, hail, or humidity."}</p>
              <div className="broadcastBox">
                <div className="broadcastAlertInfo">
                  <h4>⚠️ {lang === "hi" ? "वर्तमान मौसमी स्थिति (वाराणसी एवं पूर्वांचल क्षेत्र)" : "Current Weather Alert (Varanasi & Regional Zone)"}</h4>
                  <p>{lang === "hi" ? "अगले 48 घंटों में तापमान 24-28°C और वर्षा की संभावना 15% है। मौसम सामान्यतः अनुकूल है।" : "Temperature 24-28°C with 15% rain probability in next 48 hours. Weather is generally favorable."}</p>
                </div>
                <button
                  className="operatorPrimaryBtn"
                  onClick={() => {
                    setSmsForm({
                      mobile: selectedFarmer?.mobile_number || "9876543210",
                      message: lang === "hi" ? "मैत्री अलर्ट: अगले 24 घंटे मौसम साफ रहेगा। गेहूं/सरसों में सामान्य कृषि कार्य जारी रखें। MAITTRI" : "MAITTRI Alert: Weather expected clear for next 24h. Continue normal agronomy operations. MAITTRI",
                      category: "weather"
                    });
                    setActiveTab("sms_ivr");
                  }}
                >
                  📢 {lang === "hi" ? "मौसम अलर्ट SMS तैयार करें" : "Prepare Weather Alert SMS"}
                </button>
              </div>
            </div>
          )}

          {/* 11. MARKET PRICE */}
          {activeTab === "market_price" && (
            <div className="operatorCard">
              <h3>💰 {lang === "hi" ? "नवीनतम मंडी भाव एवं किसान SMS डिस्पैच" : "Latest Mandi Prices & Farmer SMS Dispatch"}</h3>
              <p>{lang === "hi" ? "कीपैड फोन वाले किसानों को नजदीकी मंडियों के न्यूनतम एवं अधिकतम भाव SMS द्वारा भेजें।" : "Dispatch SMS rates of nearby mandis to button-phone farmers."}</p>
              <div className="mandiRatesGrid">
                <div className="mandiRateCard">
                  <h4>{lang === "hi" ? "गेहूं" : "Wheat"}</h4>
                  <div className="price">₹2,350 / {lang === "hi" ? "क्विंटल" : "quintal"}</div>
                  <span>{lang === "hi" ? "मंडी: राजा तालाब (वाराणसी)" : "Mandi: Raja Talab (Varanasi)"}</span>
                  <small>{lang === "hi" ? "स्रोत: एगमार्कनेट" : "Source: Agmarknet"}</small>
                </div>
                <div className="mandiRateCard">
                  <h4>{lang === "hi" ? "सरसों" : "Mustard"}</h4>
                  <div className="price">₹5,420 / {lang === "hi" ? "क्विंटल" : "quintal"}</div>
                  <span>{lang === "hi" ? "मंडी: चंदौली" : "Mandi: Chandauli"}</span>
                  <small>{lang === "hi" ? "स्रोत: एगमार्कनेट" : "Source: Agmarknet"}</small>
                </div>
                <div className="mandiRateCard">
                  <h4>{lang === "hi" ? "धान (बासमती)" : "Paddy (Basmati)"}</h4>
                  <div className="price">₹3,850 / {lang === "hi" ? "क्विंटल" : "quintal"}</div>
                  <span>{lang === "hi" ? "मंडी: मिर्जापुर" : "Mandi: Mirzapur"}</span>
                  <small>{lang === "hi" ? "स्रोत: एगमार्कनेट" : "Source: Agmarknet"}</small>
                </div>
              </div>
              <div style={{ marginTop: "16px" }}>
                <button
                  className="operatorPrimaryBtn"
                  onClick={() => {
                    setSmsForm({
                      mobile: selectedFarmer?.mobile_number || "9876543210",
                      message: lang === "hi" ? "मैत्री मंडी भाव: गेहूं ₹2350/क्विंटल, सरसों ₹5420/क्विंटल (राजा तालाब मंडी)। स्रोत: Agmarknet. MAITTRI" : "MAITTRI Mandi Rates: Wheat ₹2350/q, Mustard ₹5420/q (Raja Talab Mandi). Source: Agmarknet. MAITTRI",
                      category: "market"
                    });
                    setActiveTab("sms_ivr");
                  }}
                >
                  📲 {lang === "hi" ? "मंडी भाव किसान को SMS भेजें" : "Dispatch Mandi Rates SMS"}
                </button>
              </div>
            </div>
          )}

          {/* 12. FERTILIZER / PEST GUIDANCE */}
          {activeTab === "fertilizer_pest" && (
            <div className="operatorCard">
              <h3>🌱 {t.operator?.navFertilizerPest || (lang === "hi" ? "उर्वरक एवं कीट नियंत्रण ऑपरेटर सहायता" : "Guided Agronomy Advisory")}</h3>
              <p>{lang === "hi" ? "किसान के प्रश्नों पर वैज्ञानिक रूप से सत्यापित सलाह दें:" : "Scientifically verified advisory for farmer queries:"}</p>
              <div className="advisoryChecklist">
                <div className="advisoryItem">
                  <strong>1. {lang === "hi" ? "गेहूं में पीली पत्तियां" : "Wheat Yellow Leaves"}:</strong>
                  <p>{lang === "hi" ? "उंगली से पोंछकर देखें। यदि पीला पाउडर छूटे तो पीला रतुआ है, तुरंत प्रोपिकोनाजोल 1ml/L का छिड़काव अनुशंसित है। बिना पाउडर का पीलापन हो तो यूरिया की टॉप-ड्रेसिंग करें।" : "Wipe leaf with finger. If yellow dust rubs off, it is Yellow Rust (apply Propiconazole 1ml/L). If uniform yellowing without dust, top-dress Urea."}</p>
                </div>
                <div className="advisoryItem">
                  <strong>2. {lang === "hi" ? "सरसों में माहू" : "Mustard Aphids"}:</strong>
                  <p>{lang === "hi" ? "प्रारंभिक अवस्था में 5ml नीम का तेल (1500 ppm) प्रति लीटर पानी में मिलाकर छिड़कें। रासायनिक उपचार से पूर्व केवीके विशेषज्ञ से संपर्क करें।" : "Spray 5ml Neem Oil (1500 ppm) per liter of water at early stage. Consult KVK specialists before chemical intervention."}</p>
                </div>
                <div className="advisoryItem">
                  <strong>3. {lang === "hi" ? "संतुलित NPK प्रयोग" : "Balanced NPK Application"}:</strong>
                  <p>{lang === "hi" ? "डीएपी का अत्यधिक प्रयोग न करें। सॉइल टेस्ट के आधार पर ही जिंक और सल्फर का मिश्रण उपयोग करें।" : "Avoid excessive DAP. Apply Zinc and Sulphur based strictly on certified soil test health cards."}</p>
                </div>
              </div>
            </div>
          )}

          {/* 13. GOVERNMENT SCHEMES */}
          {activeTab === "schemes" && (
            <div className="operatorCard">
              <h3>🏛️ {lang === "hi" ? "सरकारी योजना पात्रता जांच" : "Government Schemes Screening"}</h3>
              <p>{lang === "hi" ? "किसान के रकबे और श्रेणी के अनुसार योजनाओं की पात्रता का सत्यापन करें।" : "Screen farmer eligibility based on land size, crop, and socio-economic category."}</p>
              <div className="schemesList">
                <div className="schemeCard">
                  <h4>{lang === "hi" ? "प्रधानमंत्री किसान सम्मान निधि" : "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)"}</h4>
                  <p>{lang === "hi" ? "पात्रता: सभी भू-स्वामी कृषक परिवार। लाभ: ₹6,000 प्रति वर्ष (3 किस्तों में)।" : "Eligibility: All landholding farmer families. Benefit: ₹6,000 per year in 3 installments."}</p>
                  <span className="eligibleBadge">{lang === "hi" ? "संभावित रूप से पात्र" : "Potentially Eligible"}</span>
                </div>
                <div className="schemeCard">
                  <h4>{lang === "hi" ? "प्रधानमंत्री कृषि सिंचाई योजना" : "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)"}</h4>
                  <p>{lang === "hi" ? "पात्रता: ड्रिप अथवा स्प्रिंकलर सिंचाई अपनाने वाले किसान। लाभ: 45% से 55% तक का सरकारी अनुदान।" : "Eligibility: Farmers adopting micro-irrigation. Benefit: 45% to 55% government subsidy."}</p>
                  <span className="eligibleBadge">{lang === "hi" ? "आवेदन योग्य" : "Eligible for Application"}</span>
                </div>
              </div>
            </div>
          )}

          {/* 14. INSURANCE */}
          {activeTab === "insurance" && (
            <div className="operatorCard">
              <h3>🛡️ {lang === "hi" ? "प्रधानमंत्री फसल बीमा योजना सहायता" : "PMFBY Crop Insurance Assistance"}</h3>
              <p>{lang === "hi" ? "फसल नुकसान, प्राकृतिक आपदा और क्लेम की प्रक्रिया में किसान का सहयोग करें।" : "Assist farmers in crop loss reporting, natural calamity documentation, and claims."}</p>
              <div className="insuranceInfoBox">
                <h4>{lang === "hi" ? "बीमा प्रीमियम दरें:" : "Farmer Premium Rates:"}</h4>
                <ul>
                  <li>{lang === "hi" ? "रबी फसलें (गेहूं, जौ, सरसों): किसान हिस्सा" : "Rabi Crops (Wheat, Barley, Mustard): Farmer Share"} <strong>1.5%</strong></li>
                  <li>{lang === "hi" ? "खरीफ फसलें (धान, मक्का): किसान हिस्सा" : "Kharif Crops (Paddy, Maize): Farmer Share"} <strong>2.0%</strong></li>
                  <li>{lang === "hi" ? "वाणिज्यिक / बागवानी फसलें: किसान हिस्सा" : "Commercial / Horticultural Crops: Farmer Share"} <strong>5.0%</strong></li>
                </ul>
                <div className="alertNotice">
                  ⚠️ <strong>{lang === "hi" ? "क्लेम सूचना अवधि:" : "Claim Intimation Deadline:"}</strong> {lang === "hi" ? "ओलावृष्टि अथवा जलभराव से नुकसान होने पर घटना के 72 घंटे के भीतर टोल-फ्री 14447 पर कॉल दर्ज कराएं।" : "In case of localized calamity (hailstorm/inundation), report within 72 hours via toll-free 14447."}
                </div>
              </div>
            </div>
          )}

          {/* 15. SMS & IVR SERVICES */}
          {activeTab === "sms_ivr" && (
            <div className="operatorCommunicationsView">
              {/* Send SMS Box */}
              <div className="operatorCard">
                <h3>📩 {t.operator?.sendDirectSms || (lang === "hi" ? "किसान SMS प्रेषक" : "Provider-Agnostic SMS Dispatcher")}</h3>
                <div className="demoNoticeBadge">
                  ℹ️ <strong>{lang === "hi" ? "डेमो मोड सक्रिय:" : "DEMO MODE ACTIVE:"}</strong> {lang === "hi" ? "जब तक बाहरी SMS गेटवे क्रेडेंशियल्स कॉन्फ़िगर नहीं होते, तब तक सिम्युलेटेड SMS भेजा और लॉग किया जाता है।" : "Simulated SMS dispatched and logged when external gateway credentials are not configured."}
                </div>
                <form onSubmit={handleSendSms} className="smsSendForm">
                  <div className="formGroup">
                    <label>{t.operator?.recipientMobile || (lang === "hi" ? "मोबाइल नंबर" : "Mobile Number")}</label>
                    <input
                      type="tel"
                      required
                      placeholder="9876543210"
                      value={smsForm.mobile}
                      onChange={e => setSmsForm({ ...smsForm, mobile: e.target.value })}
                    />
                  </div>
                  <div className="formGroup">
                    <label>{t.operator?.alertCategory || (lang === "hi" ? "संदेश श्रेणी" : "Message Category")}</label>
                    <select
                      value={smsForm.category}
                      onChange={e => setSmsForm({ ...smsForm, category: e.target.value })}
                    >
                      <option value="weather_warning">{t.operator?.weatherWarningCategory || (lang === "hi" ? "मौसम चेतावनी" : "Weather Alert")}</option>
                      <option value="crop_advisory">{lang === "hi" ? "फसल कार्य अनुस्मारक" : "Crop Task Reminder"}</option>
                      <option value="market_price">{t.operator?.marketRateCategory || (lang === "hi" ? "मंडी भाव" : "Mandi Price Alert")}</option>
                      <option value="soil_test">{lang === "hi" ? "सॉइल टेस्ट स्थिति" : "Soil Test Status"}</option>
                    </select>
                  </div>
                  <div className="formGroup fullWidth">
                    <label>{t.operator?.smsMessageText || (lang === "hi" ? "संदेश पाठ (160 अक्षरों से कम)" : "SMS Message Text (Max 160 chars)")}</label>
                    <textarea
                      rows="3"
                      required
                      value={smsForm.message}
                      onChange={e => setSmsForm({ ...smsForm, message: e.target.value })}
                      placeholder={lang === "hi" ? "उदा. MAITTRI Alert: कल वर्षा की संभावना है। सिंचाई स्थगित करें।" : "e.g. MAITTRI Alert: Rain expected tomorrow. Postpone irrigation."}
                    ></textarea>
                  </div>
                  <button type="submit" className="operatorPrimaryBtn">
                    <Send size={16} /> {t.operator?.sendSmsBtn || (lang === "hi" ? "SMS डिस्पैच करें" : "Dispatch SMS")}
                  </button>
                </form>
              </div>

              {/* Interactive IVR Simulator Box */}
              <div className="operatorCard">
                <h3>📞 {t.operator?.ivrSimulation || (lang === "hi" ? "इंटरैक्टिव IVR कीपैड सिम्युलेटर" : "Interactive IVR Keypad Simulator")}</h3>
                <p>{t.operator?.ivrDesc || (lang === "hi" ? "बिना टेलीकॉम हार्डवेयर के किसान के कीपैड डायल ट्री का लाइव परीक्षण करें।" : "Live keypad dial tree simulation without telecom hardware.")}</p>
                
                <div className="ivrSimulatorContainer">
                  <div className="ivrPhoneMockup">
                    <div className="ivrScreen">
                      <div className="ivrScreenHeader">
                        <Phone size={14} /> MAITTRI IVR (Toll-Free 1800-XXX-XXXX)
                      </div>
                      <div className="ivrAudioText">
                        {ivrSimState ? (
                          <>
                            <p><strong>🔊 {lang === "hi" ? "ऑडियो (हिन्दी):" : "Audio (Hindi):"}</strong> {ivrSimState.audio_text_hi}</p>
                            <p className="engAudio"><small><strong>🔊 {lang === "hi" ? "ऑडियो (अंग्रेजी):" : "Audio (English):"}</strong> {ivrSimState.audio_text_en}</small></p>
                          </>
                        ) : (
                          <p>{lang === "hi" ? "कॉल प्रारंभ करने के लिए 'कॉल शुरू करें' बटन दबाएं।" : "Press 'Start Session' to initiate IVR call."}</p>
                        )}
                      </div>
                      {ivrSimState?.options && (
                        <div className="ivrOptionsList">
                          {ivrSimState.options.map(opt => (
                            <button
                              key={opt.digit}
                              className="ivrOptionBtn"
                              onClick={() => handleIvrStep(opt.digit)}
                            >
                              [{opt.digit}] {lang === "hi" ? opt.label_hi : (opt.label_en || opt.label_hi)}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="ivrKeypad">
                      {["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"].map(d => (
                        <button
                          key={d}
                          className="keypadBtn"
                          onClick={() => handleIvrStep(d)}
                        >
                          {d}
                        </button>
                      ))}
                    </div>

                    <div className="ivrActionsRow">
                      <button
                        className="operatorPrimaryBtn"
                        onClick={() => handleIvrStep(null)}
                      >
                        📞 {lang === "hi" ? "कॉल शुरू करें" : "Start Session"}
                      </button>
                      <button
                        className="operatorSecondaryBtn"
                        onClick={() => {
                          setIvrSimState(null);
                          setIvrSimInput({ phone: "9876543210", menu: "main", digits: "" });
                        }}
                      >
                        {lang === "hi" ? "कॉल समाप्त" : "Reset Call"}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* SMS Logs Table */}
              <div className="operatorCard">
                <h3>📜 {lang === "hi" ? "हालिया SMS प्रेषण ऑडिट लॉग" : "Recent SMS Audit Logs"}</h3>
                <div className="operatorTableWrap">
                  <table className="operatorTable">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>{t.operator?.mobile || (lang === "hi" ? "मोबाइल नंबर" : "Mobile Number")}</th>
                        <th>{lang === "hi" ? "संदेश सामग्री" : "Message Content"}</th>
                        <th>{lang === "hi" ? "गेटवे" : "Gateway"}</th>
                        <th>{t.common?.status || (lang === "hi" ? "स्थिति" : "Status")}</th>
                        <th>{t.common?.time || (lang === "hi" ? "समय" : "Time")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {smsLogs.length > 0 ? (
                        smsLogs.map(l => (
                          <tr key={l.id}>
                            <td>#{l.id}</td>
                            <td>{l.mobile_number}</td>
                            <td>{l.message_content}</td>
                            <td><span className="providerBadge">{l.provider}</span></td>
                            <td>
                              <span className={`statusPill ${l.status.toLowerCase()}`}>
                                {l.status} {l.is_demo_mode ? "(DEMO)" : ""}
                              </span>
                            </td>
                            <td>{l.created_at ? l.created_at.split("T")[0] : ""}</td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="6" style={{ textAlign: "center" }}>{lang === "hi" ? "कोई SMS लॉग नहीं।" : "No SMS logs found."}</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* 16. REPORTS */}
          {activeTab === "reports" && (
            <div className="operatorCard">
              <h3>📊 {t.operator?.navReports || (lang === "hi" ? "सेवा केंद्र सारांश रिपोर्ट" : "Seva Centre Performance")}</h3>
              <p>{lang === "hi" ? "ऑपरेटर केंद्र द्वारा प्रदान की गई सेवाओं का सांख्यिकीय विश्लेषण:" : "Statistical analytics of services rendered by the Seva center:"}</p>
              <div className="operatorStatsGrid">
                <div className="operatorStatCard">
                  <span className="statValue">{stats?.total_registered_farmers || 0}</span>
                  <span className="statLabel">{t.operator?.totalRegisteredFarmers || (lang === "hi" ? "पंजीकृत किसान" : "Registered Farmers")}</span>
                </div>
                <div className="operatorStatCard">
                  <span className="statValue">{stats?.pending_soil_tests || 0}</span>
                  <span className="statLabel">{t.operator?.pendingSoilTests || (lang === "hi" ? "सॉइल टेस्ट प्रक्रियाधीन" : "Pending Soil Tests")}</span>
                </div>
                <div className="operatorStatCard">
                  <span className="statValue">{smsLogs.length}</span>
                  <span className="statLabel">{lang === "hi" ? "प्रेषित SMS अलर्ट" : "Dispatched SMS Alerts"}</span>
                </div>
                <div className="operatorStatCard">
                  <span className="statValue">{stats?.total_documents_archived || 0}</span>
                  <span className="statLabel">{lang === "hi" ? "सुरक्षित भू-अभिलेख" : "Archived Land Records"}</span>
                </div>
              </div>
            </div>
          )}

          {/* 17. ACTIVITY LOG */}
          {activeTab === "activity_log" && (
            <div className="operatorCard">
              <h3>🕒 {t.operator?.navActivityLog || (lang === "hi" ? "ऑपरेटर ऑडिट गतिविधि लॉग" : "Operator Audit Trail")}</h3>
              <p>{lang === "hi" ? "सुरक्षा व अनुपालन के लिए ऑपरेटर द्वारा किए गए सभी कार्यों का समयबद्ध रिकॉर्ड:" : "Time-stamped audit records of operator actions for safety and compliance:"}</p>
              <div className="operatorTableWrap">
                <table className="operatorTable">
                  <thead>
                    <tr>
                      <th>{lang === "hi" ? "लॉग ID" : "Log ID"}</th>
                      <th>{lang === "hi" ? "कार्य प्रकार" : "Action Type"}</th>
                      <th>{lang === "hi" ? "किसान ID" : "Farmer ID"}</th>
                      <th>{t.common?.details || (lang === "hi" ? "विवरण" : "Details")}</th>
                      <th>{t.common?.time || (lang === "hi" ? "समय" : "Time")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activityLogs.length > 0 ? (
                      activityLogs.map(a => (
                        <tr key={a.id}>
                          <td>#{a.id}</td>
                          <td><span className="activityBadge">{a.action_type}</span></td>
                          <td>{a.farmer_id ? `Farmer #${a.farmer_id}` : "System"}</td>
                          <td>{a.details}</td>
                          <td>{a.timestamp}</td>
                        </tr>
                      ))
                    ) : (
                      <tr><td colSpan="5" style={{ textAlign: "center" }}>{lang === "hi" ? "कोई ऑडिट लॉग नहीं।" : "No audit logs found."}</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
