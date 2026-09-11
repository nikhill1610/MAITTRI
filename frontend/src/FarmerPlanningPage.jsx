import React, { useState, useEffect, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Calendar, CheckCircle2, AlertTriangle, Clock, Droplets, CloudSun,
  Sprout, Bug, IndianRupee, Shield, Landmark, Leaf, ChevronRight,
  ChevronDown, ChevronUp, Sparkles, RefreshCw, Send, Check, AlertCircle,
  HelpCircle, ExternalLink, BookOpen, Layers, Award, Radio, Info, ArrowRight,
  TrendingUp, Wind, Thermometer
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";
import {
  T,
  translateCrop,
  translateSoil,
  translateStage,
  translateAction,
  translateNutrient,
  translateNutrientStatus,
  translateReason
} from "./i18n";

export default function FarmerPlanningPage() {
  const { lang, t } = useLang();
  const navigate = useNavigate();

  // Active View Tab: 'plan' | 'calendar' | 'diary'
  const [activeTab, setActiveTab] = useState("plan");

  // Farm Context
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [loadingFarms, setLoadingFarms] = useState(false);

  // Form Inputs
  const [crop, setCrop] = useState("Wheat");
  const [sowingDate, setSowingDate] = useState("");
  const [variety, setVariety] = useState("");
  const [cropAgeInput, setCropAgeInput] = useState("");
  const [selectedStageInput, setSelectedStageInput] = useState("");
  const [inputMode, setInputMode] = useState("date"); // 'date' | 'age' | 'stage'

  // Plan State
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [planData, setPlanData] = useState(null);
  const [savedPlans, setSavedPlans] = useState([]);
  const [planError, setPlanError] = useState("");

  // Crop Calendar Browser State (Tab 2)
  const [allCalendars, setAllCalendars] = useState([]);
  const [selectedCalCrop, setSelectedCalCrop] = useState("Wheat");
  const [loadingCalendars, setLoadingCalendars] = useState(false);

  // Farm Diary State (Tab 3)
  const [diaryEntries, setDiaryEntries] = useState([]);
  const [loadingDiary, setLoadingDiary] = useState(false);

  // Task Completion & Note Modal
  const [activeNoteModalTask, setActiveNoteModalTask] = useState(null);
  const [farmerNoteText, setFarmerNoteText] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);

  // Expandable sections
  const [showOtherTasks, setShowOtherTasks] = useState(false);
  const [expandedTimelineStage, setExpandedTimelineStage] = useState(null);

  // Available Crops
  const availableCrops = [
    { key: "Wheat", en: "Wheat", hi: "गेहूं (Wheat)" },
    { key: "Rice", en: "Rice / Paddy", hi: "धान / चावल (Rice)" },
    { key: "Mustard", en: "Mustard", hi: "सरसों (Mustard)" },
    { key: "Maize", en: "Maize / Corn", hi: "मक्का (Maize)" },
    { key: "Potato", en: "Potato", hi: "आलू (Potato)" },
    { key: "Tomato", en: "Tomato", hi: "टमाटर (Tomato)" },
    { key: "Gram", en: "Gram / Chickpea", hi: "चना (Gram)" },
    { key: "Cotton", en: "Cotton", hi: "कपास (Cotton)" },
    { key: "Sugarcane", en: "Sugarcane", hi: "गन्ना (Sugarcane)" },
  ];

  // Fetch Farms on mount
  useEffect(() => {
    async function loadFarms() {
      setLoadingFarms(true);
      try {
        const res = await api.get("/farms");
        const list = res.data || [];
        setFarms(list);
        if (list.length > 0) {
          const first = list[0];
          setSelectedFarmId(String(first.id));
          if (first.current_crop) {
            setCrop(first.current_crop);
            setSelectedCalCrop(first.current_crop);
          }
          if (first.sowing_date) {
            setSowingDate(first.sowing_date);
          }
        }
      } catch (e) {
        console.error("Failed to load farms", e);
      } finally {
        setLoadingFarms(false);
      }
    }
    loadFarms();
  }, []);

  // When selected farm changes, pre-fill values
  useEffect(() => {
    if (!selectedFarmId || farms.length === 0) return;
    const f = farms.find(x => String(x.id) === String(selectedFarmId));
    if (f) {
      if (f.current_crop) {
        setCrop(f.current_crop);
        setSelectedCalCrop(f.current_crop);
      }
      if (f.sowing_date) {
        setSowingDate(f.sowing_date);
      }
      loadExistingPlansForFarm(f.id);
    }
  }, [selectedFarmId, farms]);

  // Load authoritative calendars
  useEffect(() => {
    async function loadCalendars() {
      setLoadingCalendars(true);
      try {
        const res = await api.get("/crop-calendar");
        setAllCalendars(res.data || []);
      } catch (e) {
        console.error("Failed to load calendars", e);
      } finally {
        setLoadingCalendars(false);
      }
    }
    loadCalendars();
  }, []);

  // Helper to load existing plans
  async function loadExistingPlansForFarm(farmId) {
    try {
      const res = await api.get(`/farmer-plans?farm_id=${farmId}`);
      const plans = res.data?.plans || [];
      setSavedPlans(plans);
      if (plans.length > 0) {
        // Load the latest plan details
        loadPlanDetails(plans[0].id);
      }
    } catch (e) {
      console.error("Failed to list plans", e);
    }
  }

  // Load detailed plan by plan_id
  async function loadPlanDetails(planId) {
    setLoadingPlan(true);
    setPlanError("");
    try {
      const res = await api.get(`/farmer-plans/${planId}`);
      setPlanData(res.data);
      if (res.data.sowing_date) {
        setSowingDate(res.data.sowing_date);
      }
      if (res.data.crop) {
        setCrop(res.data.crop);
      }
      // Also load diary
      loadDiary(planId);
    } catch (e) {
      console.error("Failed to load plan details", e);
      setPlanError(lang === "hi" ? "योजना विवरण लोड करने में असमर्थ।" : "Failed to load plan details.");
    } finally {
      setLoadingPlan(false);
    }
  }

  // Load Farm Diary
  async function loadDiary(planId) {
    setLoadingDiary(true);
    try {
      const res = await api.get(`/farmer-plans/${planId}/history`);
      setDiaryEntries(res.data?.diary_entries || []);
    } catch (e) {
      console.error("Failed to load diary", e);
    } finally {
      setLoadingDiary(false);
    }
  }

  // Generate or Recalculate Plan
  async function handleGeneratePlan(e) {
    if (e) e.preventDefault();
    if (!selectedFarmId) {
      setPlanError(lang === "hi" ? "कृपया पहले खेत का चयन करें।" : "Please select a farm first.");
      return;
    }

    setLoadingPlan(true);
    setPlanError("");

    const payload = {
      farm_id: Number(selectedFarmId),
      crop: crop,
      variety: variety || undefined,
    };

    if (inputMode === "date") {
      if (!sowingDate) {
        setPlanError(t.enterSowingDatePrompt || "Please enter sowing/planting date to generate a personalized calendar.");
        setLoadingPlan(false);
        return;
      }
      payload.sowing_date = sowingDate;
    } else if (inputMode === "age") {
      if (!cropAgeInput) {
        setPlanError(lang === "hi" ? "कृपया फसल की आयु (दिनों में) दर्ज करें।" : "Please enter crop age in days.");
        setLoadingPlan(false);
        return;
      }
      payload.crop_age_days = Number(cropAgeInput);
    } else if (inputMode === "stage") {
      if (!selectedStageInput) {
        setPlanError(lang === "hi" ? "कृपया वर्तमान फसल अवस्था का चयन करें।" : "Please select current crop growth stage.");
        setLoadingPlan(false);
        return;
      }
      payload.current_stage = selectedStageInput;
    }

    try {
      const res = await api.post("/farmer-plans", payload);
      if (res.data?.success && res.data?.plan) {
        setPlanData(res.data.plan);
        if (res.data.plan.sowing_date) {
          setSowingDate(res.data.plan.sowing_date);
        }
        if (res.data.plan.plan_id) {
          loadDiary(res.data.plan.plan_id);
        }
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      setPlanError(msg);
    } finally {
      setLoadingPlan(false);
    }
  }

  // Toggle Task Completion
  async function handleToggleTask(task) {
    if (!task?.id) return;
    const newStatus = task.status === "completed" ? "pending" : "completed";

    // Optimistic UI update in planData
    setPlanData(prev => {
      if (!prev) return prev;
      const updateList = list => list.map(t => t.id === task.id ? { ...t, status: newStatus } : t);
      return {
        ...prev,
        today_goals: {
          ...prev.today_goals,
          top_3_priorities: updateList(prev.today_goals.top_3_priorities),
          other_tasks: updateList(prev.today_goals.other_tasks || [])
        }
      };
    });

    try {
      if (newStatus === "completed") {
        await api.post(`/farmer-plans/tasks/${task.id}/complete`, { status: "completed" });
      } else {
        await api.patch(`/farmer-plans/tasks/${task.id}`, { status: "pending" });
      }
      if (planData?.plan_id) {
        loadDiary(planData.plan_id);
      }
    } catch (e) {
      console.error("Failed to update task status", e);
    }
  }

  // Save Note to Task & Diary
  async function handleSaveNote() {
    if (!activeNoteModalTask || !farmerNoteText.trim()) return;
    setSubmittingNote(true);
    try {
      await api.post(`/farmer-plans/tasks/${activeNoteModalTask.id}/note`, {
        notes: farmerNoteText.trim()
      });
      if (planData?.plan_id) {
        loadDiary(planData.plan_id);
      }
      setActiveNoteModalTask(null);
      setFarmerNoteText("");
    } catch (e) {
      console.error("Failed to save note", e);
    } finally {
      setSubmittingNote(false);
    }
  }

  // Quick Sowing Date Helpers
  function setQuickDate(daysAgo) {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    const iso = d.toISOString().split("T")[0];
    setSowingDate(iso);
    setInputMode("date");
  }

  // Active Authoritative Calendar
  const activeCalendar = useMemo(() => {
    return allCalendars.find(c => c.name.toLowerCase() === selectedCalCrop.toLowerCase() || c.crop_key === selectedCalCrop.toLowerCase()) || allCalendars[0];
  }, [allCalendars, selectedCalCrop]);

  const selectedFarm = useMemo(() => {
    return farms.find(f => String(f.id) === String(selectedFarmId));
  }, [farms, selectedFarmId]);

  return (
    <div className="content" style={{ maxWidth: "1240px", margin: "0 auto", paddingBottom: "60px" }}>
      {/* 1. Header Banner */}
      <div className="hero" style={{
        background: "linear-gradient(135deg, #0f2e17 0%, #166534 60%, #14532d 100%)",
        borderRadius: "16px",
        padding: "32px 28px",
        color: "#ffffff",
        marginBottom: "24px",
        position: "relative",
        overflow: "hidden",
        boxShadow: "0 10px 25px -5px rgba(22, 101, 52, 0.25)"
      }}>
        <div style={{ position: "relative", zIndex: 2 }}>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(255,255,255,0.15)", padding: "4px 12px", borderRadius: "20px", fontSize: "13px", fontWeight: "600", marginBottom: "12px", backdropFilter: "blur(4px)" }}>
            <Sparkles size={14} color="#facc15" />
            <span>{lang === "hi" ? "स्मार्ट कृषि योजना इंजन" : "Smart Farm Planning Engine"}</span>
          </div>
          <h1 style={{ fontSize: "32px", fontWeight: "800", margin: "0 0 8px 0", letterSpacing: "-0.5px" }}>
            {lang === "hi" ? "🌾 मैत्री व्यक्तिगत कृषि योजना" : "🌾 MAITTRI Personal Farm Planner"}
          </h1>
          <p style={{ margin: "0 0 16px 0", fontSize: "16px", opacity: 0.9, maxWidth: "700px", lineHeight: 1.5 }}>
            {t.farmerPlanningTagline || (lang === "hi" ? "आपकी बुवाई की तारीख और फसल अवस्था पर आधारित सटीक दैनिक एवं साप्ताहिक योजना" : "Stage-based agronomic guidance tailored to your sowing date")}
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "4px 10px", borderRadius: "8px", fontSize: "13px" }}>
              🌱 {lang === "hi" ? "दैनिक लक्ष्य" : "Today's Goals"}
            </span>
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "4px 10px", borderRadius: "8px", fontSize: "13px" }}>
              📅 {lang === "hi" ? "7-दिवसीय योजना" : "7-Day Plan"}
            </span>
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "4px 10px", borderRadius: "8px", fontSize: "13px" }}>
              ⏳ {lang === "hi" ? "जीवन-चक्र समयरेखा" : "Lifecycle Timeline"}
            </span>
            <span style={{ background: "rgba(255,255,255,0.2)", padding: "4px 10px", borderRadius: "8px", fontSize: "13px" }}>
              🌦️ {lang === "hi" ? "मौसम एवं सेंसर अनुकूलित" : "Weather & IoT Sensor Synced"}
            </span>
          </div>
        </div>
      </div>

      {/* 2. Mode Navigation Tabs */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "24px", borderBottom: "2px solid #e2e8f0", paddingBottom: "8px" }}>
        <button
          onClick={() => setActiveTab("plan")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "10px",
            border: "none",
            fontWeight: "700",
            fontSize: "15px",
            cursor: "pointer",
            transition: "all 0.2s ease",
            background: activeTab === "plan" ? "#166534" : "transparent",
            color: activeTab === "plan" ? "#ffffff" : "#475569"
          }}
        >
          <Sprout size={18} />
          {lang === "hi" ? "व्यक्तिगत कृषि योजना" : "Personal Farm Plan"}
        </button>

        <button
          onClick={() => setActiveTab("calendar")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "10px",
            border: "none",
            fontWeight: "700",
            fontSize: "15px",
            cursor: "pointer",
            transition: "all 0.2s ease",
            background: activeTab === "calendar" ? "#166534" : "transparent",
            color: activeTab === "calendar" ? "#ffffff" : "#475569"
          }}
        >
          <Calendar size={18} />
          {lang === "hi" ? "प्रमाणित फसल कैलेंडर" : "Authoritative Crop Calendar"}
        </button>

        <button
          onClick={() => setActiveTab("diary")}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 20px",
            borderRadius: "10px",
            border: "none",
            fontWeight: "700",
            fontSize: "15px",
            cursor: "pointer",
            transition: "all 0.2s ease",
            background: activeTab === "diary" ? "#166534" : "transparent",
            color: activeTab === "diary" ? "#ffffff" : "#475569"
          }}
        >
          <BookOpen size={18} />
          {lang === "hi" ? "डिजिटल फार्म डायरी" : "Digital Farm Diary"}
          {diaryEntries.length > 0 && (
            <span style={{ background: activeTab === "diary" ? "#ffffff" : "#166534", color: activeTab === "diary" ? "#166534" : "#ffffff", padding: "1px 7px", borderRadius: "10px", fontSize: "12px" }}>
              {diaryEntries.length}
            </span>
          )}
        </button>
      </div>

      {/* TAB 1: PERSONAL FARM PLAN */}
      {activeTab === "plan" && (
        <>
          {/* Farm & Sowing Date Input Card */}
          <div className="card" style={{ marginBottom: "24px", padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0", boxShadow: "0 2px 8px rgba(0,0,0,0.04)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "18px", fontWeight: "700", color: "#14532d", display: "flex", alignItems: "center", gap: "8px" }}>
                  <Leaf size={20} color="#166534" />
                  {lang === "hi" ? "खेत एवं फसल चयन" : "Farm & Crop Selection"}
                </h3>
                <p style={{ margin: "4px 0 0 0", fontSize: "14px", color: "#64748b" }}>
                  {t.whenDidYouSowHi || (lang === "hi" ? "आपने फसल कब बोई / लगाई है?" : "When did you sow / plant the crop?")}
                </p>
              </div>

              {/* Input Mode Selector */}
              <div style={{ display: "flex", background: "#f1f5f9", borderRadius: "8px", padding: "3px" }}>
                <button
                  type="button"
                  onClick={() => setInputMode("date")}
                  style={{
                    border: "none",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: "600",
                    background: inputMode === "date" ? "#ffffff" : "transparent",
                    color: inputMode === "date" ? "#14532d" : "#64748b",
                    boxShadow: inputMode === "date" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                    cursor: "pointer"
                  }}
                >
                  {lang === "hi" ? "📅 बुवाई की तारीख" : "📅 Sowing Date"}
                </button>
                <button
                  type="button"
                  onClick={() => setInputMode("age")}
                  style={{
                    border: "none",
                    padding: "6px 12px",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: "600",
                    background: inputMode === "age" ? "#ffffff" : "transparent",
                    color: inputMode === "age" ? "#14532d" : "#64748b",
                    boxShadow: inputMode === "age" ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
                    cursor: "pointer"
                  }}
                >
                  {lang === "hi" ? "🔢 फसल आयु (दिन)" : "🔢 Crop Age"}
                </button>
              </div>
            </div>

            <form onSubmit={handleGeneratePlan}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "16px" }}>
                {/* 1. Farm Select */}
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                    {lang === "hi" ? "खेत चुनें (Farm)" : "Select Farm"}
                  </label>
                  <select
                    value={selectedFarmId}
                    onChange={e => setSelectedFarmId(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px", background: "#f8fafc" }}
                  >
                    {farms.map(f => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.area} {f.area_unit || "acre"} · {f.soil_type || "Soil"})
                      </option>
                    ))}
                  </select>
                </div>

                {/* 2. Crop Select */}
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                    {lang === "hi" ? "फसल (Crop)" : "Select Crop"}
                  </label>
                  <select
                    value={crop}
                    onChange={e => setCrop(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px", background: "#f8fafc" }}
                  >
                    {availableCrops.map(c => (
                      <option key={c.key} value={c.key}>
                        {lang === "hi" ? c.hi : c.en}
                      </option>
                    ))}
                  </select>
                </div>

                {/* 3. Sowing Date / Crop Age */}
                {inputMode === "date" ? (
                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                      {t.sowingDate || (lang === "hi" ? "बुवाई / रोपाई की तारीख" : "Sowing Date")} <span style={{ color: "#dc2626" }}>*</span>
                    </label>
                    <input
                      type="date"
                      value={sowingDate}
                      onChange={e => setSowingDate(e.target.value)}
                      style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px" }}
                    />
                  </div>
                ) : (
                  <div>
                    <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                      {t.cropAgeInDays || (lang === "hi" ? "फसल की आयु (दिन)" : "Crop Age in Days")} <span style={{ color: "#dc2626" }}>*</span>
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="365"
                      placeholder="e.g. 25"
                      value={cropAgeInput}
                      onChange={e => setCropAgeInput(e.target.value)}
                      style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px" }}
                    />
                  </div>
                )}

                {/* 4. Variety (Optional) */}
                <div>
                  <label style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "#334155", marginBottom: "6px" }}>
                    {t.variety || (lang === "hi" ? "फसल की किस्म (वैकल्पिक)" : "Variety (Optional)")}
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. HD-3086, PBW-502..."
                    value={variety}
                    onChange={e => setVariety(e.target.value)}
                    style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px" }}
                  />
                </div>
              </div>

              {/* Quick Date Presets */}
              {inputMode === "date" && (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
                  <span style={{ fontSize: "12px", color: "#64748b", fontWeight: "600" }}>
                    {lang === "hi" ? "त्वरित चयन:" : "Quick select:"}
                  </span>
                  <button type="button" onClick={() => setQuickDate(0)} style={{ border: "1px solid #cbd5e1", background: "#f8fafc", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}>
                    {lang === "hi" ? "आज बोई (0 दिन)" : "Today (0 days)"}
                  </button>
                  <button type="button" onClick={() => setQuickDate(10)} style={{ border: "1px solid #cbd5e1", background: "#f8fafc", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}>
                    {lang === "hi" ? "10 दिन पहले" : "10 days ago"}
                  </button>
                  <button type="button" onClick={() => setQuickDate(22)} style={{ border: "1px solid #cbd5e1", background: "#f8fafc", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}>
                    {lang === "hi" ? "22 दिन पहले (CRI/टिलरिंग)" : "22 days ago (CRI)"}
                  </button>
                  <button type="button" onClick={() => setQuickDate(45)} style={{ border: "1px solid #cbd5e1", background: "#f8fafc", padding: "4px 10px", borderRadius: "6px", fontSize: "12px", cursor: "pointer" }}>
                    {lang === "hi" ? "45 दिन पहले" : "45 days ago"}
                  </button>
                </div>
              )}

              {/* Submit Button */}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", alignItems: "center" }}>
                {planError && (
                  <span style={{ color: "#dc2626", fontSize: "14px", fontWeight: "500", display: "flex", alignItems: "center", gap: "4px" }}>
                    <AlertCircle size={16} /> {planError}
                  </span>
                )}
                <button
                  type="submit"
                  disabled={loadingPlan}
                  className="button"
                  style={{
                    background: "#166534",
                    color: "#ffffff",
                    fontWeight: "700",
                    padding: "12px 24px",
                    borderRadius: "8px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    border: "none",
                    cursor: loadingPlan ? "not-allowed" : "pointer"
                  }}
                >
                  {loadingPlan ? <RefreshCw size={18} className="spin" /> : <Sparkles size={18} />}
                  {planData ? (t.recalculatePlan || (lang === "hi" ? "योजना पुनः परिकलित करें" : "Recalculate Plan")) : (t.generatePlan || (lang === "hi" ? "मेरी कृषि योजना तैयार करें" : "Generate My Farm Plan"))}
                </button>
              </div>
            </form>
          </div>

          {/* If Plan is Loaded, Show Main Sections */}
          {planData ? (
            <>
              {/* SECTION A: 🎯 TODAY'S FARM GOAL */}
              <div className="card" style={{
                marginBottom: "24px",
                padding: "24px",
                background: "linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%)",
                borderRadius: "16px",
                border: "2px solid #bbf7d0",
                boxShadow: "0 4px 12px rgba(22, 101, 52, 0.08)"
              }}>
                {/* Header Info Banner */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px", marginBottom: "20px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
                      <span style={{ background: "#dc2626", color: "#ffffff", fontSize: "12px", fontWeight: "800", padding: "3px 8px", borderRadius: "4px", textTransform: "uppercase" }}>
                        TODAY · {planData.reference_date_display}
                      </span>
                      <span style={{ background: "#166534", color: "#ffffff", fontSize: "12px", fontWeight: "700", padding: "3px 8px", borderRadius: "4px" }}>
                        {translateCrop(planData.crop, lang)}
                      </span>
                      <span style={{ background: "#fef08a", color: "#854d0e", fontSize: "12px", fontWeight: "700", padding: "3px 8px", borderRadius: "4px" }}>
                        {planData.crop_age_days} {lang === "hi" ? "दिन पुरानी" : "Days After Sowing"}
                      </span>
                    </div>

                    <h2 style={{ margin: "0 0 6px 0", fontSize: "24px", fontWeight: "800", color: "#0f2e17" }}>
                      🎯 {t.whatShouldIDoToday || (lang === "hi" ? "आज क्या करना है?" : "What should I do today?")}
                    </h2>
                    <p style={{ margin: 0, fontSize: "15px", color: "#334155" }}>
                      {lang === "hi" ? "वर्तमान वृद्धि अवस्था:" : "Current Growth Stage:"}{" "}
                      <strong style={{ color: "#166534" }}>
                        {lang === "hi" ? planData.current_stage.hindi_name : planData.current_stage.name}
                      </strong>
                      {" · "}
                      <span>{lang === "hi" ? `कटाई में लगभग ${planData.days_to_harvest} दिन शेष` : `~${planData.days_to_harvest} days to harvest`}</span>
                    </p>
                  </div>

                  {/* Priority & Weather Pill */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontSize: "13px", fontWeight: "600", color: "#64748b" }}>
                        {lang === "hi" ? "आज की प्राथमिकता:" : "Today's Priority:"}
                      </span>
                      <span style={{
                        background: planData.today_goals.priority === "HIGH" ? "#fee2e2" : "#fef9c3",
                        color: planData.today_goals.priority === "HIGH" ? "#b91c1c" : "#854d0e",
                        padding: "4px 10px",
                        borderRadius: "12px",
                        fontWeight: "800",
                        fontSize: "12px"
                      }}>
                        {planData.today_goals.priority}
                      </span>
                    </div>
                    {planData.weather_context?.available && (
                      <span style={{ fontSize: "13px", color: "#475569", display: "flex", alignItems: "center", gap: "4px" }}>
                        <CloudSun size={15} color="#0284c7" />
                        {planData.weather_context.current_condition}, {planData.weather_context.current_temp}°C
                      </span>
                    )}
                  </div>
                </div>

                {/* "Why MAITTRI Recommends This" Callout Card */}
                <div style={{
                  background: "#ffffff",
                  borderLeft: "4px solid #166534",
                  padding: "14px 18px",
                  borderRadius: "8px",
                  marginBottom: "20px",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                    <Sparkles size={16} color="#eab308" />
                    <span style={{ fontWeight: "700", fontSize: "14px", color: "#14532d" }}>
                      {t.whyMaittriRecommends || (lang === "hi" ? "मैत्री यह सिफारिश क्यों करता है" : "Why MAITTRI Recommends This")}
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: "14px", color: "#334155", lineHeight: 1.5 }}>
                    {lang === "hi" ? planData.today_goals.why_maittri_recommends_hi : planData.today_goals.why_maittri_recommends_en}
                  </p>
                </div>

                {/* Top 3 Important Tasks Today */}
                <div style={{ marginBottom: "16px" }}>
                  <h4 style={{ margin: "0 0 12px 0", fontSize: "16px", fontWeight: "800", color: "#0f2e17", display: "flex", alignItems: "center", gap: "6px" }}>
                    <span>🔥</span> {t.top3Priorities || (lang === "hi" ? "आज के 3 सबसे महत्वपूर्ण कार्य" : "Top 3 Important Tasks Today")}
                  </h4>

                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "16px" }}>
                    {planData.today_goals.top_3_priorities.map((task, idx) => (
                      <div
                        key={task.id || idx}
                        style={{
                          background: task.status === "completed" ? "#f8fafc" : "#ffffff",
                          border: task.status === "completed" ? "1px solid #cbd5e1" : "1px solid #86efac",
                          borderRadius: "12px",
                          padding: "18px",
                          boxShadow: "0 2px 6px rgba(0,0,0,0.04)",
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                          position: "relative",
                          opacity: task.status === "completed" ? 0.75 : 1
                        }}
                      >
                        <div>
                          {/* Category & Plan Updated Reason */}
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                            <span style={{ background: "#dcfce7", color: "#166534", padding: "3px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "700" }}>
                              {task.category}
                            </span>
                            <span style={{ fontSize: "12px", color: "#64748b", display: "flex", alignItems: "center", gap: "4px" }}>
                              <Clock size={13} /> {task.estimated_duration}
                            </span>
                          </div>

                          {task.plan_updated_reason && (
                            <div style={{ background: "#fef3c7", color: "#92400e", padding: "4px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "600", marginBottom: "8px", display: "flex", alignItems: "center", gap: "4px" }}>
                              <AlertTriangle size={13} /> {task.plan_updated_reason}
                            </div>
                          )}

                          {/* Title */}
                          <h4 style={{ margin: "0 0 6px 0", fontSize: "16px", fontWeight: "700", color: "#1e293b", textDecoration: task.status === "completed" ? "line-through" : "none" }}>
                            {task.title}
                          </h4>

                          {/* Description */}
                          <p style={{ margin: "0 0 10px 0", fontSize: "13px", color: "#475569", lineHeight: 1.4 }}>
                            {task.description}
                          </p>

                          {/* Action steps */}
                          {task.action_steps && (
                            <div style={{ background: "#f8fafc", padding: "8px 10px", borderRadius: "6px", fontSize: "12px", color: "#334155", marginBottom: "12px" }}>
                              <strong>{lang === "hi" ? "क्या करें:" : "Action:"}</strong> {task.action_steps}
                            </div>
                          )}
                        </div>

                        {/* Bottom Bar: Completion Checkbox & Note Button */}
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid #f1f5f9", paddingTop: "10px", marginTop: "10px" }}>
                          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "13px", fontWeight: "600", color: task.status === "completed" ? "#166534" : "#334155" }}>
                            <input
                              type="checkbox"
                              checked={task.status === "completed"}
                              onChange={() => handleToggleTask(task)}
                              style={{ width: "18px", height: "18px", cursor: "pointer", accentColor: "#166534" }}
                            />
                            {task.status === "completed" ? (lang === "hi" ? "पूर्ण किया गया" : "Completed") : (lang === "hi" ? "कार्य पूर्ण करें" : "Mark Done")}
                          </label>

                          <button
                            type="button"
                            onClick={() => {
                              setActiveNoteModalTask(task);
                              setFarmerNoteText("");
                            }}
                            style={{
                              background: "transparent",
                              border: "1px solid #cbd5e1",
                              borderRadius: "6px",
                              padding: "4px 8px",
                              fontSize: "12px",
                              cursor: "pointer",
                              color: "#475569"
                            }}
                          >
                            📝 {t.addNote || (lang === "hi" ? "टिप्पणी" : "Note")}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Other Tasks Accordion */}
                {planData.today_goals.other_tasks?.length > 0 && (
                  <div style={{ marginTop: "12px" }}>
                    <button
                      type="button"
                      onClick={() => setShowOtherTasks(!showOtherTasks)}
                      style={{
                        background: "#f1f5f9",
                        border: "none",
                        width: "100%",
                        padding: "10px 16px",
                        borderRadius: "8px",
                        fontSize: "14px",
                        fontWeight: "600",
                        color: "#334155",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        cursor: "pointer"
                      }}
                    >
                      <span>
                        📋 {t.otherTasksToday || (lang === "hi" ? "आज के अन्य कार्य" : "Other Tasks Today")} ({planData.today_goals.other_tasks.length})
                      </span>
                      {showOtherTasks ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>

                    {showOtherTasks && (
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px", marginTop: "12px" }}>
                        {planData.today_goals.other_tasks.map((task, idx) => (
                          <div
                            key={task.id || idx}
                            style={{
                              background: "#ffffff",
                              border: "1px solid #e2e8f0",
                              borderRadius: "8px",
                              padding: "12px",
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center"
                            }}
                          >
                            <div>
                              <div style={{ fontSize: "11px", fontWeight: "700", color: "#166534" }}>{task.category}</div>
                              <div style={{ fontSize: "14px", fontWeight: "600", color: "#1e293b" }}>{task.title}</div>
                              <div style={{ fontSize: "12px", color: "#64748b" }}>{task.estimated_duration}</div>
                            </div>
                            <input
                              type="checkbox"
                              checked={task.status === "completed"}
                              onChange={() => handleToggleTask(task)}
                              style={{ width: "18px", height: "18px", cursor: "pointer", accentColor: "#166534" }}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* SECTION B: 📅 THIS WEEK'S FARM PLAN (7-DAY VIEW) */}
              <div className="card" style={{ marginBottom: "24px", padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <h3 style={{ margin: "0 0 4px 0", fontSize: "18px", fontWeight: "800", color: "#14532d", display: "flex", alignItems: "center", gap: "8px" }}>
                      <Calendar size={20} color="#166534" />
                      {t.thisWeekPlan || (lang === "hi" ? "📅 इस हफ्ते की कृषि योजना" : "This Week's Farm Plan")}
                    </h3>
                    <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
                      {lang === "hi" ? "आगामी 7 दिनों की तारीख-वार योजना एवं मौसमी सावधानियां" : "Dynamic 7-day schedule tailored to upcoming crop age and weather"}
                    </p>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "14px" }}>
                  {planData.week_plan.map((day, idx) => (
                    <div
                      key={day.date}
                      style={{
                        background: idx === 0 ? "#f0fdf4" : "#f8fafc",
                        border: idx === 0 ? "2px solid #86efac" : "1px solid #e2e8f0",
                        borderRadius: "10px",
                        padding: "14px",
                        position: "relative"
                      }}
                    >
                      {/* Day Header */}
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px", borderBottom: "1px solid rgba(0,0,0,0.06)", paddingBottom: "6px" }}>
                        <div>
                          <div style={{ fontSize: "14px", fontWeight: "800", color: idx === 0 ? "#166534" : "#1e293b" }}>
                            {idx === 0 ? (lang === "hi" ? "आज (Today)" : "Today") : (lang === "hi" ? day.day_name_hi : day.day_name_en)}
                          </div>
                          <div style={{ fontSize: "12px", color: "#64748b" }}>
                            {day.date_display} · {lang === "hi" ? `दिन ${day.crop_age_day}` : `Day ${day.crop_age_day}`}
                          </div>
                        </div>
                        <span style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "4px", padding: "2px 6px", fontSize: "11px", fontWeight: "700", color: "#334155" }}>
                          {lang === "hi" ? day.growth_stage_hi : day.growth_stage_en}
                        </span>
                      </div>

                      {/* Day Main Goal */}
                      <div style={{ marginBottom: "10px" }}>
                        <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                          {lang === "hi" ? "मुख्य लक्ष्य" : "Main Goal"}
                        </div>
                        <div style={{ fontSize: "13px", fontWeight: "600", color: "#0f2e17" }}>
                          {day.main_goal}
                        </div>
                      </div>

                      {/* Day Tasks List */}
                      <div style={{ marginBottom: "10px" }}>
                        {day.tasks.slice(0, 2).map(t => (
                          <div key={t.title} style={{ fontSize: "12px", color: "#334155", display: "flex", alignItems: "flex-start", gap: "6px", marginBottom: "4px" }}>
                            <span style={{ color: "#166534" }}>•</span>
                            <span>{t.title}</span>
                          </div>
                        ))}
                      </div>

                      {/* Weather pill */}
                      <div style={{ fontSize: "11px", color: "#475569", background: "#ffffff", padding: "3px 8px", borderRadius: "4px", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <CloudSun size={12} color="#0284c7" />
                        <span>{day.weather_consideration}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* SECTION C: 🌱 COMPLETE CROP LIFECYCLE TIMELINE */}
              <div className="card" style={{ marginBottom: "24px", padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ margin: "0 0 4px 0", fontSize: "18px", fontWeight: "800", color: "#14532d", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Layers size={20} color="#166534" />
                    {t.cropLifecycleTimeline || (lang === "hi" ? "🌱 फसल जीवन-चक्र समयरेखा" : "Crop Lifecycle Timeline")}
                  </h3>
                  <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
                    {lang === "hi" ? "आपकी बुवाई की तारीख से परिकलित वास्तविक कैलेंडर तिथियां" : "Actual calculated calendar dates from your sowing date"}
                  </p>
                </div>

                {/* Horizontal Progress Timeline */}
                <div style={{ display: "flex", gap: "8px", overflowX: "auto", paddingBottom: "12px" }}>
                  {planData.timeline.map((st, idx) => (
                    <div
                      key={st.stage_id}
                      onClick={() => setExpandedTimelineStage(expandedTimelineStage === st.stage_id ? null : st.stage_id)}
                      style={{
                        minWidth: "160px",
                        flex: "1 0 160px",
                        background: st.is_current ? "#dcfce7" : "#f8fafc",
                        border: st.is_current ? "2px solid #166534" : "1px solid #cbd5e1",
                        borderRadius: "10px",
                        padding: "12px",
                        cursor: "pointer",
                        position: "relative",
                        transition: "all 0.2s ease"
                      }}
                    >
                      {st.is_current && (
                        <span style={{ position: "absolute", top: "-10px", right: "8px", background: "#166534", color: "#ffffff", padding: "1px 6px", borderRadius: "10px", fontSize: "10px", fontWeight: "800" }}>
                          CURRENT
                        </span>
                      )}
                      <div style={{ fontSize: "11px", fontWeight: "700", color: "#64748b", marginBottom: "4px" }}>
                        {lang === "hi" ? `दिन ${st.start_day}–${st.end_day}` : `Day ${st.start_day}–${st.end_day}`}
                      </div>
                      <div style={{ fontSize: "13px", fontWeight: "700", color: "#14532d", marginBottom: "6px" }}>
                        {lang === "hi" ? st.hindi_name : st.name}
                      </div>
                      <div style={{ fontSize: "11px", color: "#475569", fontWeight: "600" }}>
                        {st.start_date_display} – {st.end_date_display}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Expanded Stage Detail */}
                {expandedTimelineStage && (() => {
                  const s = planData.timeline.find(x => x.stage_id === expandedTimelineStage);
                  if (!s) return null;
                  return (
                    <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: "8px", padding: "16px", marginTop: "12px" }}>
                      <h4 style={{ margin: "0 0 6px 0", fontSize: "15px", color: "#14532d" }}>
                        {lang === "hi" ? s.hindi_name : s.name} ({s.start_date_display} – {s.end_date_display})
                      </h4>
                      <p style={{ margin: "0 0 10px 0", fontSize: "13px", color: "#334155" }}>
                        {lang === "hi" ? s.hindi_description : s.description}
                      </p>
                      {s.fertilizer_guidance && (
                        <div style={{ fontSize: "12px", marginBottom: "4px" }}>
                          <strong>🧪 {lang === "hi" ? "उर्वरक:" : "Fertilizer:"}</strong> {s.fertilizer_guidance}
                        </div>
                      )}
                      {s.irrigation_note && (
                        <div style={{ fontSize: "12px", marginBottom: "4px" }}>
                          <strong>💧 {lang === "hi" ? "सिंचाई:" : "Irrigation:"}</strong> {s.irrigation_note}
                        </div>
                      )}
                      {s.pest_disease_scouting && (
                        <div style={{ fontSize: "12px" }}>
                          <strong>🐛 {lang === "hi" ? "कीट निगरानी:" : "Pest Scouting:"}</strong> {s.pest_disease_scouting}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* SECTION D: SPECIALIZED FARM BRAIN INTEGRATION CARDS */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "24px" }}>
                {/* 1. Weather Impact */}
                <div className="card" style={{ padding: "18px", borderRadius: "12px", border: "1px solid #e2e8f0", background: "#ffffff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <h4 style={{ margin: 0, fontSize: "15px", fontWeight: "700", color: "#0369a1", display: "flex", alignItems: "center", gap: "6px" }}>
                      <CloudSun size={18} color="#0284c7" />
                      {lang === "hi" ? "मौसम प्रभाव" : "Weather Impact"}
                    </h4>
                    <Link to="/weather" style={{ fontSize: "12px", color: "#0284c7", textDecoration: "none", fontWeight: "600" }}>
                      {lang === "hi" ? "विस्तार" : "View"} →
                    </Link>
                  </div>
                  {planData.weather_context?.available ? (
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: "600", color: "#1e293b", marginBottom: "4px" }}>
                        {planData.weather_context.current_condition} · {planData.weather_context.current_temp}°C
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                        {planData.weather_context.rain_forecast_next_48h
                          ? (lang === "hi" ? `अगले 48 घंटों में वर्षा का अनुमान (${planData.weather_context.precipitation_sum_48h}mm)` : `Rain expected in next 48h (${planData.weather_context.precipitation_sum_48h}mm)`)
                          : (lang === "hi" ? "आगामी 48 घंटों में भारी वर्षा की संभावना नहीं।" : "No significant rainfall forecast in next 48 hours.")}
                      </p>
                    </div>
                  ) : (
                    <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                      {t.weatherUnavailable || "Weather data unavailable."}
                    </p>
                  )}
                </div>

                {/* 2. Smart Irrigation & IoT Sensor */}
                <div className="card" style={{ padding: "18px", borderRadius: "12px", border: "1px solid #e2e8f0", background: "#ffffff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <h4 style={{ margin: 0, fontSize: "15px", fontWeight: "700", color: "#15803d", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Droplets size={18} color="#16a34a" />
                      {lang === "hi" ? "स्मार्ट सिंचाई" : "Smart Irrigation"}
                    </h4>
                    <Link to="/iot-monitor" style={{ fontSize: "12px", color: "#15803d", textDecoration: "none", fontWeight: "600" }}>
                      {lang === "hi" ? "सेंसर" : "Sensor"} →
                    </Link>
                  </div>
                  {planData.iot_context?.available ? (
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: "600", color: "#1e293b", marginBottom: "4px" }}>
                        {lang === "hi" ? "मृदा नमी:" : "Soil Moisture:"} {planData.iot_context.soil_moisture}% ({planData.iot_context.moisture_status})
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                        {planData.iot_context.is_dry
                          ? (lang === "hi" ? "मृदा सूखी है। सिंचाई की जांच अनुशंसित।" : "Soil is dry. Irrigation check recommended.")
                          : (lang === "hi" ? "मृदा में नमी पर्याप्त है।" : "Soil moisture is adequate.")}
                      </p>
                    </div>
                  ) : (
                    <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                      {t.sensorUnavailable || "Sensor data unavailable. Please use manual soil observation."}
                    </p>
                  )}
                </div>

                {/* 3. Fertilizer Timing */}
                <div className="card" style={{ padding: "18px", borderRadius: "12px", border: "1px solid #e2e8f0", background: "#ffffff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <h4 style={{ margin: 0, fontSize: "15px", fontWeight: "700", color: "#7c2d12", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Sprout size={18} color="#c2410c" />
                      {lang === "hi" ? "उर्वरक समय" : "Fertilizer Timing"}
                    </h4>
                    <Link to="/fertilizer" style={{ fontSize: "12px", color: "#c2410c", textDecoration: "none", fontWeight: "600" }}>
                      {lang === "hi" ? "सिफारिश" : "Recommend"} →
                    </Link>
                  </div>
                  <p style={{ margin: 0, fontSize: "12px", color: "#334155" }}>
                    {planData.current_stage.fertilizer_guidance || (lang === "hi" ? "सटीक मात्रा मिट्टी परीक्षण एवं आधिकारिक सिफारिश पर आधारित होनी चाहिए।" : "Dosage should be based on soil test and official guidelines.")}
                  </p>
                </div>

                {/* 4. Mandi Market Price */}
                <div className="card" style={{ padding: "18px", borderRadius: "12px", border: "1px solid #e2e8f0", background: "#ffffff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <h4 style={{ margin: 0, fontSize: "15px", fontWeight: "700", color: "#065f46", display: "flex", alignItems: "center", gap: "6px" }}>
                      <IndianRupee size={18} color="#059669" />
                      {lang === "hi" ? "मंडी भाव विश्लेषण" : "Market Price"}
                    </h4>
                    <Link to="/market-price" style={{ fontSize: "12px", color: "#059669", textDecoration: "none", fontWeight: "600" }}>
                      {lang === "hi" ? "मंडी भाव" : "Mandi"} →
                    </Link>
                  </div>
                  {planData.mandi_snapshot ? (
                    <div>
                      <div style={{ fontSize: "14px", fontWeight: "600", color: "#1e293b" }}>
                        ₹{planData.mandi_snapshot.modal_price || planData.mandi_snapshot.price} / {planData.mandi_snapshot.unit || "Quintal"}
                      </div>
                      <p style={{ margin: "2px 0 0 0", fontSize: "12px", color: "#64748b" }}>
                        {planData.mandi_snapshot.state} · {planData.mandi_snapshot.price_trend || "Stable"}
                      </p>
                    </div>
                  ) : (
                    <p style={{ margin: 0, fontSize: "12px", color: "#64748b" }}>
                      {lang === "hi" ? "कटाई के करीब आते ही मंडी भाव ट्रैक करें।" : "Track mandi rates as harvest approaches."}
                    </p>
                  )}
                </div>
              </div>

              {/* SECTION E: UPCOMING WEEKLY MILESTONES */}
              <div className="card" style={{ marginBottom: "24px", padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
                <div style={{ marginBottom: "16px" }}>
                  <h3 style={{ margin: "0 0 4px 0", fontSize: "18px", fontWeight: "800", color: "#14532d", display: "flex", alignItems: "center", gap: "8px" }}>
                    <Award size={20} color="#166534" />
                    {t.upcomingWeeks || (lang === "hi" ? "📋 आगामी साप्ताहिक लक्ष्य" : "Upcoming Weekly Milestones")}
                  </h3>
                  <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
                    {lang === "hi" ? "फसल के सम्पूर्ण जीवन-चक्र का साप्ताहिक विभाजन" : "Week-by-week roadmap through harvest and storage"}
                  </p>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "12px" }}>
                  {planData.weekly_milestones.slice(0, 8).map(w => (
                    <div
                      key={w.week_number}
                      style={{
                        background: w.is_current ? "#f0fdf4" : (w.is_past ? "#f8fafc" : "#ffffff"),
                        border: w.is_current ? "2px solid #86efac" : "1px solid #e2e8f0",
                        borderRadius: "8px",
                        padding: "12px",
                        opacity: w.is_past ? 0.7 : 1
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                        <span style={{ fontSize: "13px", fontWeight: "700", color: w.is_current ? "#166534" : "#1e293b" }}>
                          {lang === "hi" ? w.title_hi : w.title}
                        </span>
                        <span style={{ fontSize: "11px", color: "#64748b" }}>{w.days_range}</span>
                      </div>
                      <div style={{ fontSize: "11px", color: "#059669", fontWeight: "600", marginBottom: "4px" }}>
                        {w.date_range}
                      </div>
                      <p style={{ margin: 0, fontSize: "12px", color: "#475569" }}>
                        {w.key_focus}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            /* Empty State: Enter Sowing Date */
            <div className="card" style={{ padding: "40px 20px", textAlign: "center", background: "#ffffff", borderRadius: "14px", border: "1px dashed #cbd5e1" }}>
              <Calendar size={48} color="#166534" style={{ margin: "0 auto 16px auto" }} />
              <h3 style={{ margin: "0 0 8px 0", fontSize: "18px", color: "#1e293b" }}>
                {t.enterSowingDatePrompt || (lang === "hi" ? "व्यक्तिगत कैलेंडर तैयार करने के लिए कृपया बुवाई/रोपाई की तारीख दर्ज करें।" : "Please enter sowing/planting date to generate a personalized calendar.")}
              </h3>
              <p style={{ margin: "0 0 20px 0", fontSize: "14px", color: "#64748b", maxWidth: "500px", marginLeft: "auto", marginRight: "auto" }}>
                {lang === "hi"
                  ? "मैत्री आपकी चुनी गई तारीख और खेत के स्थान के आधार पर आज के लक्ष्य, सिंचाई समय, उर्वरक अनुसूची और 7-दिवसीय कार्य योजना तैयार करेगा।"
                  : "MAITTRI will calculate today's goals, irrigation windows, fertilizer timings, and a 7-day schedule tailored to your farm."}
              </p>
            </div>
          )}
        </>
      )}

      {/* TAB 2: AUTHORITATIVE CROP CALENDAR */}
      {activeTab === "calendar" && (
        <div className="card" style={{ padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h3 style={{ margin: "0 0 4px 0", fontSize: "20px", fontWeight: "800", color: "#14532d" }}>
                📅 {t.authoritativeCalendar || (lang === "hi" ? "प्रमाणित फसल कैलेंडर" : "Authoritative Crop Calendar")}
              </h3>
              <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
                {lang === "hi" ? "ICAR, कृषि विज्ञान केंद्र एवं राज्य कृषि विश्वविद्यालयों द्वारा अनुमोदित उत्पादन तकनीकें" : "Scientific package of practices from ICAR, KVKs, and State Agricultural Universities"}
              </p>
            </div>

            {/* Crop Selector */}
            <div style={{ minWidth: "200px" }}>
              <select
                value={selectedCalCrop}
                onChange={e => setSelectedCalCrop(e.target.value)}
                style={{ width: "100%", padding: "10px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "14px", fontWeight: "600" }}
              >
                {availableCrops.map(c => (
                  <option key={c.key} value={c.key}>
                    {lang === "hi" ? c.hi : c.en}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {activeCalendar ? (
            <div>
              {/* Crop Meta Banner */}
              <div style={{ background: "#f0fdf4", border: "1px solid #86efac", borderRadius: "10px", padding: "16px", marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                  <div>
                    <h2 style={{ margin: 0, fontSize: "20px", fontWeight: "800", color: "#0f2e17" }}>
                      {lang === "hi" ? activeCalendar.hindi_name : activeCalendar.name} ({activeCalendar.scientific_name})
                    </h2>
                    <div style={{ fontSize: "13px", color: "#166534", marginTop: "4px" }}>
                      {lang === "hi" ? "अनुमानित अवधि:" : "Duration:"} {activeCalendar.typical_duration_days} {lang === "hi" ? "दिन" : "days"} · {activeCalendar.family}
                    </div>
                  </div>
                  <div style={{ fontSize: "12px", color: "#475569" }}>
                    <strong>{lang === "hi" ? "अनुकूल बुवाई खिड़की:" : "Sowing Window:"}</strong> {activeCalendar.recommended_sowing_window}
                  </div>
                </div>
              </div>

              {/* Stages Accordion / List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {activeCalendar.stages?.map((stage, i) => (
                  <div key={stage.stage_id} style={{ border: "1px solid #e2e8f0", borderRadius: "10px", padding: "16px", background: "#ffffff" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "15px", fontWeight: "700", color: "#14532d" }}>
                        {i + 1}. {lang === "hi" ? stage.hindi_name : stage.name}
                      </span>
                      <span style={{ background: "#f1f5f9", padding: "3px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "600", color: "#475569" }}>
                        {lang === "hi" ? `दिन ${stage.start_day}–${stage.end_day}` : `Days ${stage.start_day}–${stage.end_day}`}
                      </span>
                    </div>

                    <p style={{ margin: "0 0 10px 0", fontSize: "13px", color: "#334155" }}>
                      {lang === "hi" ? stage.hindi_description : stage.description}
                    </p>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "10px", background: "#f8fafc", padding: "10px", borderRadius: "6px", fontSize: "12px" }}>
                      {stage.fertilizer_guidance && (
                        <div>
                          <strong style={{ color: "#c2410c" }}>🧪 {lang === "hi" ? "उर्वरक:" : "Fertilizer:"}</strong>
                          <div>{stage.fertilizer_guidance}</div>
                        </div>
                      )}
                      {stage.irrigation_note && (
                        <div>
                          <strong style={{ color: "#16a34a" }}>💧 {lang === "hi" ? "सिंचाई:" : "Irrigation:"}</strong>
                          <div>{stage.irrigation_note}</div>
                        </div>
                      )}
                      {stage.pest_disease_scouting && (
                        <div>
                          <strong style={{ color: "#dc2626" }}>🐛 {lang === "hi" ? "कीट निगरानी:" : "Pest Scouting:"}</strong>
                          <div>{stage.pest_disease_scouting}</div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Official Sources Citation */}
              <div style={{ marginTop: "24px", paddingTop: "16px", borderTop: "1px solid #e2e8f0", fontSize: "12px", color: "#64748b" }}>
                <strong>{lang === "hi" ? "प्रमाणित स्रोत:" : "Authoritative Sources:"}</strong>
                <ul style={{ margin: "4px 0 0 0", paddingLeft: "20px" }}>
                  {activeCalendar.official_sources?.map(src => (
                    <li key={src}>{src}</li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <p>{t.cropCalendarUnavailable || "Crop calendar unavailable."}</p>
          )}
        </div>
      )}

      {/* TAB 3: DIGITAL FARM DIARY */}
      {activeTab === "diary" && (
        <div className="card" style={{ padding: "24px", background: "#ffffff", borderRadius: "14px", border: "1px solid #e2e8f0" }}>
          <div style={{ marginBottom: "20px" }}>
            <h3 style={{ margin: "0 0 4px 0", fontSize: "20px", fontWeight: "800", color: "#14532d" }}>
              📔 {t.farmDiary || (lang === "hi" ? "डिजिटल फार्म डायरी" : "Digital Farm Diary")}
            </h3>
            <p style={{ margin: 0, fontSize: "14px", color: "#64748b" }}>
              {lang === "hi" ? "आपके खेत के पूर्ण किए गए कार्यों, टिप्पणियों और पर्यावरणीय रीडिंग्स का ऐतिहासिक रिकॉर्ड" : "Historical record of completed farm activities, farmer observations, and sensor readings"}
            </p>
          </div>

          {loadingDiary ? (
            <div style={{ textAlign: "center", padding: "30px" }}>
              <RefreshCw size={24} className="spin" color="#166534" />
            </div>
          ) : diaryEntries.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {diaryEntries.map(entry => (
                <div
                  key={entry.id}
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "10px",
                    padding: "16px",
                    background: "#f8fafc"
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                    <span style={{ fontSize: "15px", fontWeight: "700", color: "#1e293b" }}>
                      {entry.task_title}
                    </span>
                    <span style={{ background: "#dcfce7", color: "#166534", padding: "2px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "700" }}>
                      ✓ {entry.completed_at_display}
                    </span>
                  </div>

                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "8px" }}>
                    {entry.category} · {entry.growth_stage} · Day {entry.crop_age_day}
                  </div>

                  {entry.farmer_notes && (
                    <div style={{ background: "#ffffff", border: "1px solid #cbd5e1", borderRadius: "6px", padding: "8px 12px", fontSize: "13px", color: "#334155", marginBottom: "8px" }}>
                      <strong>📝 {lang === "hi" ? "किसान की टिप्पणी:" : "Farmer Note:"}</strong> {entry.farmer_notes}
                    </div>
                  )}

                  {/* Environmental Snapshot */}
                  <div style={{ display: "flex", gap: "12px", fontSize: "11px", color: "#64748b", flexWrap: "wrap" }}>
                    {entry.sensor_snapshot && (
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <Radio size={12} color="#16a34a" />
                        Soil Moisture: {entry.sensor_snapshot.soil_moisture}%
                      </span>
                    )}
                    {entry.weather_snapshot && (
                      <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                        <CloudSun size={12} color="#0284c7" />
                        {entry.weather_snapshot.temp}°C · {entry.weather_snapshot.condition}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "40px 20px", color: "#64748b" }}>
              <BookOpen size={40} color="#94a3b8" style={{ margin: "0 auto 12px auto" }} />
              <p style={{ margin: 0, fontSize: "15px" }}>
                {lang === "hi" ? "अभी तक कोई कार्य पूर्ण नहीं किया गया है। आज के लक्ष्यों को पूरा करने पर वे यहां दर्ज होंगे।" : "No completed tasks yet. When you mark today's tasks done, they will appear in your diary."}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Note Modal */}
      {activeNoteModalTask && (
        <div style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: "rgba(0,0,0,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000,
          padding: "20px"
        }}>
          <div style={{
            background: "#ffffff",
            borderRadius: "14px",
            padding: "24px",
            maxWidth: "480px",
            width: "100%",
            boxShadow: "0 10px 30px rgba(0,0,0,0.2)"
          }}>
            <h3 style={{ margin: "0 0 6px 0", fontSize: "18px", color: "#14532d" }}>
              📝 {t.addNote || (lang === "hi" ? "खेत निरीक्षण टिप्पणी जोड़ें" : "Add Field Observation Note")}
            </h3>
            <p style={{ margin: "0 0 14px 0", fontSize: "13px", color: "#64748b" }}>
              {activeNoteModalTask.title}
            </p>

            <textarea
              rows="4"
              value={farmerNoteText}
              onChange={e => setFarmerNoteText(e.target.value)}
              placeholder={t.farmerNotePlaceholder || "Enter your field observation..."}
              style={{
                width: "100%",
                padding: "10px",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                fontSize: "14px",
                fontFamily: "inherit",
                marginBottom: "16px",
                boxSizing: "border-box"
              }}
            />

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button
                type="button"
                onClick={() => setActiveNoteModalTask(null)}
                style={{ background: "#f1f5f9", border: "none", padding: "8px 16px", borderRadius: "6px", fontSize: "13px", cursor: "pointer", color: "#475569" }}
              >
                {lang === "hi" ? "रद्द करें" : "Cancel"}
              </button>
              <button
                type="button"
                disabled={submittingNote || !farmerNoteText.trim()}
                onClick={handleSaveNote}
                style={{
                  background: "#166534",
                  color: "#ffffff",
                  border: "none",
                  padding: "8px 18px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: submittingNote ? "not-allowed" : "pointer"
                }}
              >
                {submittingNote ? "Saving..." : (t.saveNote || (lang === "hi" ? "सहेजें" : "Save"))}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
