import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Sprout,
  Calendar,
  FlaskConical,
  Wheat,
  TrendingUp,
  Landmark,
  Flame,
  Bot,
  ArrowRight,
  CheckCircle2,
  Shield,
  Radio,
  Sparkles,
  Layers,
  HelpCircle,
  Menu,
  X,
  Languages,
  UserCheck,
  Cpu,
  Droplets,
  Activity,
  CloudSun,
  ChevronRight,
  ShieldCheck,
  Compass,
  FileText
} from "lucide-react";
import Logo from "./Logo";
import { useLang } from "./LanguageContext";
import { isOfficialRole } from "./App";

export default function LandingPage() {
  const [lang, setLang, t] = useLang();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const token = localStorage.getItem("token");
  const storedRole = localStorage.getItem("role");
  const isAuthenticated = Boolean(token);
  const isOfficial = isOfficialRole(storedRole);

  const toggleLanguage = () => {
    setLang(lang === "hi" ? "en" : "hi");
  };

  const handleNavClick = (anchorId) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(anchorId);
    if (element) {
      element.scrollIntoView({ behavior: "smooth" });
    }
  };

  const portalDestination = isOfficial ? "/operator" : "/dashboard";
  const portalLabel = isOfficial
    ? (t("landing.nav.goToOperator") || (lang === "hi" ? "ऑपरेटर पोर्टल" : "Official Portal"))
    : (t("landing.nav.goToDashboard") || (lang === "hi" ? "किसान डैशबोर्ड" : "Farmer Dashboard"));

  const features = [
    {
      icon: <Sprout size={24} />,
      title: t("landing.features.f1Title") || "AI Crop Recommendation",
      desc: t("landing.features.f1Desc") || "Identify suitable, climate-resilient crops based on farm conditions, historical yield, and seasonal forecasts.",
      link: "/crop-farming/recommendation"
    },
    {
      icon: <Calendar size={24} />,
      title: t("landing.features.f2Title") || "Personal Farm Planner & Calendar",
      desc: t("landing.features.f2Desc") || "Stage-by-stage crop timelines tracking vegetative growth, flowering, irrigation alerts, and digital farm notes.",
      link: "/crop-farming/calendar"
    },
    {
      icon: <FlaskConical size={24} />,
      title: t("landing.features.f3Title") || "Soil & Nutrient Intelligence",
      desc: t("landing.features.f3Desc") || "Assess Nitrogen, Phosphorus, Potassium, and pH levels with automated soil health cards and corrective advice.",
      link: "/crop-farming/soil-nutrients"
    },
    {
      icon: <Wheat size={24} />,
      title: t("landing.features.f4Title") || "Fertilizer Intelligence",
      desc: t("landing.features.f4Desc") || "Calculate optimal basal and top-dressing dosages of Urea, DAP, MOP, and bio-fertilizers without wastage.",
      link: "/crop-farming/fertilizer"
    },
    {
      icon: <TrendingUp size={24} />,
      title: t("landing.features.f5Title") || "Mandi Market Price Trends",
      desc: t("landing.features.f5Desc") || "Live prices, modal rates, 30-day historical trends, and revenue projections across Indian mandis.",
      link: "/crop-farming/market-price"
    },
    {
      icon: <Landmark size={24} />,
      title: t("landing.features.f6Title") || "Government Schemes & Subsidies",
      desc: t("landing.features.f6Desc") || "Discover central and state schemes (PM-Kisan, PMFBY, Soil Health Card) with direct eligibility checks.",
      link: "/government-schemes"
    },
    {
      icon: <Flame size={24} />,
      title: t("landing.features.f7Title") || "Parali & Residue Management",
      desc: t("landing.features.f7Desc") || "Eco-friendly, profitable stubble solutions: bio-decomposers, happy seeders, straw baling, and market linkages.",
      link: "/crop-farming/parali-management"
    },
    {
      icon: <Bot size={24} />,
      title: t("landing.features.f8Title") || "Krishi Assistant AI",
      desc: t("landing.features.f8Desc") || "Ask questions in Hindi or English about pests, diseases, irrigation stages, and get ICAR-grounded advice.",
      link: "/krishi-assistant"
    }
  ];

  return (
    <div className="lpPage">
      {/* 1. STICKY POLISHED NAVBAR */}
      <header className="lpNavbar">
        <div className="lpNavInner">
          <Link to="/" className="lpBrand">
            <Logo size="compact" variant="icon" />
            <div className="lpBrandText">
              <div className="lpBrandTitleRow">
                <span className="lpBrandName">MAITTRI</span>
                <span className="lpBrandHindi">मैत्री</span>
              </div>
              <span className="lpBrandTagline">
                {lang === "hi" ? "किसान का साथी, समृद्धि की शुरुआत" : "Smart Agriculture Decision Platform"}
              </span>
            </div>
          </Link>

          <nav className="lpNavLinks" aria-label="Main Navigation">
            <button type="button" className="lpNavLink" onClick={() => handleNavClick("how-it-works")}>
              {t("landing.nav.howItWorks") || "How It Works"}
            </button>
            <button type="button" className="lpNavLink" onClick={() => handleNavClick("features")}>
              {t("landing.nav.features") || "Features"}
            </button>
            <button type="button" className="lpNavLink" onClick={() => handleNavClick("krishi-assistant")}>
              {t("landing.features.f8Title") || "Krishi Assistant"}
            </button>
            <button type="button" className="lpNavLink" onClick={() => handleNavClick("iot-telemetry")}>
              {t("landing.nav.technology") || "Technology"}
            </button>
            <button type="button" className="lpNavLink" onClick={() => handleNavClick("accessibility")}>
              {t("landing.nav.forFarmers") || "For Farmers"}
            </button>
          </nav>

          <div className="lpNavActions">
            <button
              type="button"
              className="lpLangBtn"
              onClick={toggleLanguage}
              title={lang === "hi" ? "Switch to English" : "हिन्दी में बदलें"}
              aria-label="Switch Language"
            >
              <Languages size={15} />
              <span>{lang === "hi" ? "English" : "हिन्दी"}</span>
            </button>

            {isAuthenticated ? (
              <Link to={portalDestination} className="lpPrimaryCtaBtn">
                <UserCheck size={16} />
                <span>{portalLabel}</span>
              </Link>
            ) : (
              <>
                <Link to="/login" className="lpLoginBtn">
                  {t("landing.nav.login") || "Login"}
                </Link>
                <Link to="/register" className="lpPrimaryCtaBtn">
                  <span>{t("landing.nav.getStarted") || "Get Started"}</span>
                  <ArrowRight size={15} />
                </Link>
              </>
            )}

            <button
              type="button"
              className="lpMobileMenuBtn"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div className="lpMobileDrawer open">
            <div className="lpMobileNavLinks">
              <button type="button" className="lpNavLink" onClick={() => handleNavClick("how-it-works")}>
                {t("landing.nav.howItWorks") || "How It Works"}
              </button>
              <button type="button" className="lpNavLink" onClick={() => handleNavClick("features")}>
                {t("landing.nav.features") || "Features"}
              </button>
              <button type="button" className="lpNavLink" onClick={() => handleNavClick("krishi-assistant")}>
                {t("landing.features.f8Title") || "Krishi Assistant"}
              </button>
              <button type="button" className="lpNavLink" onClick={() => handleNavClick("iot-telemetry")}>
                {t("landing.nav.technology") || "Technology"}
              </button>
              <button type="button" className="lpNavLink" onClick={() => handleNavClick("accessibility")}>
                {t("landing.nav.forFarmers") || "For Farmers"}
              </button>
            </div>
            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
              {isAuthenticated ? (
                <Link to={portalDestination} className="lpPrimaryCtaBtn" style={{ width: "100%" }}>
                  <UserCheck size={16} />
                  <span>{portalLabel}</span>
                </Link>
              ) : (
                <>
                  <Link to="/login" className="lpSecondaryCtaBtn" style={{ flex: 1, textAlign: "center" }}>
                    {t("landing.nav.login") || "Login"}
                  </Link>
                  <Link to="/register" className="lpPrimaryCtaBtn" style={{ flex: 1, textAlign: "center" }}>
                    {t("landing.nav.getStarted") || "Get Started"}
                  </Link>
                </>
              )}
            </div>
          </div>
        )}
      </header>

      {/* 2. HERO SECTION */}
      <section className="lpHeroSection" id="home">
        <div className="lpHeroGrid">
          <div className="lpHeroContent">
            <div className="lpBadge">
              <span className="lpBadgePulse"></span>
              <span>{t("landing.hero.badge") || "AI-POWERED AGRITECH FOR INDIA"}</span>
            </div>

            <h1 className="lpHeroTitle">
              {t("landing.hero.title") || "Helping Farmers Make Smarter Decisions."}
            </h1>

            <p className="lpHeroSubtitle">
              {t("landing.hero.subtitle") ||
                "MAITTRI brings agricultural knowledge, AI-powered guidance, market intelligence, government schemes and smart IoT insights together in one simple, farmer-friendly platform."}
            </p>

            <div className="lpHeroActions">
              <Link to="/register" className="lpPrimaryCtaBtn" style={{ fontSize: 16, padding: "12px 28px" }}>
                <span>{t("landing.hero.primaryCta") || "Get Started Free"}</span>
                <ArrowRight size={18} />
              </Link>
              <button
                type="button"
                className="lpSecondaryCtaBtn"
                style={{ fontSize: 16, padding: "12px 28px" }}
                onClick={() => handleNavClick("features")}
              >
                <span>{t("landing.hero.secondaryCta") || "Explore Features"}</span>
              </button>
            </div>

            <div className="lpTrustBadgeRow">
              <ShieldCheck size={18} color="#15803d" />
              <span>
                {t("landing.hero.trustBadge") ||
                  "ICAR & Krishi Vigyan Grounded • 14 Agro-Climatic Zones • Dual Language EN/HI"}
              </span>
            </div>
          </div>

          {/* Interactive Studio Preview Card (Stitch Synthesis) */}
          <div className="lpStudioCard">
            <div className="lpStudioHeader">
              <div className="lpStudioTitle">
                <Logo size={32} variant="icon" />
                <span style={{ fontWeight: 800, fontSize: 15, color: "#141e19" }}>
                  {t("landing.hero.liveStudio") || "MAITTRI Intelligence Studio"}
                </span>
              </div>
              <span className="lpStudioStatusPill">
                <span className="lpBadgePulse" style={{ width: 6, height: 6 }}></span>
                {t("landing.hero.fieldActive") || "Field Active"}
              </span>
            </div>

            <div className="lpStudioFieldInfo">
              <div className="lpStudioCropName">
                {t("landing.hero.currentCrop") || "🌾 Wheat (HD-2967)"}
              </div>
              <div className="lpStudioSoilType">
                {t("landing.hero.soilType") || "Alluvial Soil • pH 6.8 • Plot A-2"}
              </div>
            </div>

            <div className="lpStudioMetrics">
              <div className="lpMetricChip">
                <span className="lpMetricLabel">
                  <Droplets size={13} color="#0284c7" />
                  {t("landing.hero.soilMoisture") || "Soil Moisture"}
                </span>
                <span className="lpMetricValue" style={{ color: "#0284c7" }}>22% Optimal</span>
              </div>

              <div className="lpMetricChip">
                <span className="lpMetricLabel">
                  <FlaskConical size={13} color="#15803d" />
                  {t("landing.hero.npkStatus") || "NPK Nutrient Status"}
                </span>
                <span className="lpMetricValue" style={{ color: "#15803d" }}>
                  {t("landing.hero.balanced") || "Balanced"}
                </span>
              </div>

              <div className="lpMetricChip">
                <span className="lpMetricLabel">
                  <CloudSun size={13} color="#b45300" />
                  {lang === "hi" ? "मौसम पूर्वानुमान" : "Micro-Forecast"}
                </span>
                <span className="lpMetricValue" style={{ color: "#b45300" }}>24°C Sunny</span>
              </div>

              <div className="lpMetricChip">
                <span className="lpMetricLabel">
                  <Radio size={13} color="#15803d" />
                  {lang === "hi" ? "आईओटी टेलीमेट्री" : "IoT Sensor Nodes"}
                </span>
                <span className="lpMetricValue" style={{ color: "#15803d" }}>ESP32 Online</span>
              </div>
            </div>

            <div className="lpStudioAdvisory">
              <Sparkles size={18} color="#b45300" style={{ flexShrink: 0, marginTop: 2 }} />
              <p className="lpStudioAdvisoryText">
                {t("landing.hero.nextAdvisory") || "Next Action: Crown Root Irrigation (CRI) recommended in 3 days."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3. RIBBON / VALUE PROP BAR */}
      <section className="lpRibbon">
        <div className="lpRibbonGrid">
          <div className="lpRibbonItem">
            <div className="lpRibbonIcon"><Bot size={22} /></div>
            <div>
              <div className="lpRibbonTitle">{t("landing.ribbon.aiGuidance") || "AI-Powered Guidance"}</div>
              <div className="lpRibbonDesc">{t("landing.ribbon.aiGuidanceDesc") || "Contextual agronomy reasoning"}</div>
            </div>
          </div>

          <div className="lpRibbonItem">
            <div className="lpRibbonIcon"><TrendingUp size={22} /></div>
            <div>
              <div className="lpRibbonTitle">{t("landing.ribbon.realtime") || "Real-Time Intelligence"}</div>
              <div className="lpRibbonDesc">{t("landing.ribbon.realtimeDesc") || "Mandi prices & hyper-local weather"}</div>
            </div>
          </div>

          <div className="lpRibbonItem">
            <div className="lpRibbonIcon"><Landmark size={22} /></div>
            <div>
              <div className="lpRibbonTitle">{t("landing.ribbon.schemes") || "Scheme Discovery"}</div>
              <div className="lpRibbonDesc">{t("landing.ribbon.schemesDesc") || "Eligibility & direct benefit sync"}</div>
            </div>
          </div>

          <div className="lpRibbonItem">
            <div className="lpRibbonIcon"><Radio size={22} /></div>
            <div>
              <div className="lpRibbonTitle">{t("landing.ribbon.iot") || "Smart IoT Monitoring"}</div>
              <div className="lpRibbonDesc">{t("landing.ribbon.iotDesc") || "Real-time soil & ambient telemetry"}</div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. THE CHALLENGE (PROBLEM STATEMENT) */}
      <section className="lpSection" id="about">
        <div className="lpSectionHeader">
          <span className="lpSectionEyebrow">{t("landing.problem.eyebrow") || "The Challenge"}</span>
          <h2 className="lpSectionTitle">
            {t("landing.problem.title") || "Farming Decisions Shouldn't Depend on Guesswork."}
          </h2>
          <p className="lpSectionSubtitle">
            {t("landing.problem.subtitle") ||
              "Farmers often need information from multiple places — crop guidance, soil knowledge, weather, market prices, government schemes and production practices. MAITTRI brings these decision-support tools into one connected platform."}
          </p>
        </div>

        <div className="lpProblemGrid">
          <div className="lpProblemCard">
            <div className="lpProblemNum">01</div>
            <h3 className="lpProblemTitle">{t("landing.problem.card1Title") || "Information is Scattered"}</h3>
            <p className="lpProblemDesc">
              {t("landing.problem.card1Desc") ||
                "Weather alerts come from one source, mandi prices from another, and fertilizer advice from local retail counters with conflicting suggestions."}
            </p>
          </div>

          <div className="lpProblemCard">
            <div className="lpProblemNum">02</div>
            <h3 className="lpProblemTitle">{t("landing.problem.card2Title") || "Technology is Hard to Access"}</h3>
            <p className="lpProblemDesc">
              {t("landing.problem.card2Desc") ||
                "Complex dashboards and English-only tools leave millions of smallholder farmers without actionable digital guidance in their native language."}
            </p>
          </div>

          <div className="lpProblemCard">
            <div className="lpProblemNum">03</div>
            <h3 className="lpProblemTitle">{t("landing.problem.card3Title") || "Decisions Need Context"}</h3>
            <p className="lpProblemDesc">
              {t("landing.problem.card3Desc") ||
                "Generic advice fails. Real farming guidance must factor in specific plot location, soil texture, water availability, and local sowing calendar."}
            </p>
          </div>
        </div>
      </section>

      {/* 5. SYSTEM WORKFLOW (HOW IT WORKS) */}
      <section className="lpSection" id="how-it-works" style={{ background: "#ffffff", maxWidth: "100%" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto" }}>
          <div className="lpSectionHeader">
            <span className="lpSectionEyebrow">{t("landing.workflow.eyebrow") || "System Workflow"}</span>
            <h2 className="lpSectionTitle">
              {t("landing.workflow.title") || "From Farm Data to Practical Guidance"}
            </h2>
            <p className="lpSectionSubtitle">
              {t("landing.workflow.subtitle") ||
                "A simple three-step process to transform field conditions into clear, profitable agricultural decisions."}
            </p>
          </div>

          <div className="lpWorkflowGrid">
            <div className="lpWorkflowCard">
              <span className="lpWorkflowStepBadge">Step 01</span>
              <h3 className="lpWorkflowTitle">{t("landing.workflow.step1Title") || "Tell Us About Your Farm"}</h3>
              <p className="lpWorkflowDesc">
                {t("landing.workflow.step1Desc") ||
                  "Input plot location, land size, soil type, crop history, irrigation setup, and current season plans via form or voice."}
              </p>
            </div>

            <div className="lpWorkflowCard">
              <span className="lpWorkflowStepBadge">Step 02</span>
              <h3 className="lpWorkflowTitle">{t("landing.workflow.step2Title") || "MAITTRI Evaluates & Reasons"}</h3>
              <p className="lpWorkflowDesc">
                {t("landing.workflow.step2Desc") ||
                  "AI models paired with verified agronomic rules evaluate soil health, weather forecasts, market trends, and eligible schemes."}
              </p>
            </div>

            <div className="lpWorkflowCard">
              <span className="lpWorkflowStepBadge">Step 03</span>
              <h3 className="lpWorkflowTitle">{t("landing.workflow.step3Title") || "Act with Confidence"}</h3>
              <p className="lpWorkflowDesc">
                {t("landing.workflow.step3Desc") ||
                  "Receive an actionable crop calendar, daily farm priorities, precise fertilizer doses, and harvest selling advisories."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. PLATFORM CAPABILITIES (8 REAL MODULES) */}
      <section className="lpSection" id="features">
        <div className="lpSectionHeader">
          <span className="lpSectionEyebrow">{t("landing.features.eyebrow") || "Platform Capabilities"}</span>
          <h2 className="lpSectionTitle">
            {t("landing.features.title") || "One Platform. Multiple Farming Decisions."}
          </h2>
          <p className="lpSectionSubtitle">
            {t("landing.features.subtitle") ||
              "Explore MAITTRI's comprehensive suite of decision-support engines built specifically for Indian agriculture."}
          </p>
        </div>

        <div className="lpFeaturesGrid">
          {features.map((f, i) => (
            <div key={i} className="lpFeatureCard">
              <div className="lpFeatureIcon">{f.icon}</div>
              <h3 className="lpFeatureTitle">{f.title}</h3>
              <p className="lpFeatureDesc">{f.desc}</p>
              <Link to={f.link} className="lpFeatureLink">
                <span>{lang === "hi" ? "सुविधा देखें" : "Explore Module"}</span>
                <ChevronRight size={16} />
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* 7. KRISHI ASSISTANT AI SPOTLIGHT */}
      <section className="lpSection" id="krishi-assistant">
        <div className="lpAssistantCard">
          <div className="lpAssistantGrid">
            <div>
              <span className="lpSectionEyebrow" style={{ color: "#15803d" }}>
                {t("landing.assistant.eyebrow") || "Cognitive Agronomy"}
              </span>
              <h2 className="lpSectionTitle" style={{ fontSize: 30 }}>
                {t("landing.assistant.title") || "An Agricultural Intelligence Layer Built for Real Questions."}
              </h2>
              <p className="lpSectionSubtitle" style={{ marginBottom: 20 }}>
                {t("landing.assistant.subtitle") ||
                  "MAITTRI combines agronomic knowledge retrieval with conversational AI to provide grounded, reliable answers instead of hallucinations."}
              </p>

              <div className="lpAssistantFeatureList">
                <div className="lpAssistantFeatureItem">
                  <CheckCircle2 size={20} className="lpAssistantFeatureIcon" />
                  <div>
                    <strong style={{ display: "block", color: "#141e19", fontSize: 15 }}>
                      {t("landing.assistant.point1Title") || "Verified Agronomic Knowledge"}
                    </strong>
                    <span style={{ fontSize: 13.5, color: "#536359" }}>
                      {t("landing.assistant.point1Desc") ||
                        "Responses are strictly grounded in ICAR research and agricultural university extension manuals."}
                    </span>
                  </div>
                </div>

                <div className="lpAssistantFeatureItem">
                  <CheckCircle2 size={20} className="lpAssistantFeatureIcon" />
                  <div>
                    <strong style={{ display: "block", color: "#141e19", fontSize: 15 }}>
                      {t("landing.assistant.point2Title") || "Dual-Language Native Understanding"}
                    </strong>
                    <span style={{ fontSize: 13.5, color: "#536359" }}>
                      {t("landing.assistant.point2Desc") ||
                        "Communicate naturally in Hindi or English with full agricultural context and terminology."}
                    </span>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: 28 }}>
                <Link to="/krishi-assistant" className="lpPrimaryCtaBtn">
                  <Bot size={16} />
                  <span>{lang === "hi" ? "कृषि सहायक से बात करें" : "Talk to Krishi Assistant"}</span>
                  <ArrowRight size={15} />
                </Link>
              </div>
            </div>

            {/* Grounded Chat Bubble Demonstration */}
            <div className="lpChatBubblePreview">
              <div className="lpChatBubbleUser">
                {t("landing.assistant.sampleQ") ||
                  "What is the critical irrigation stage for wheat, especially CRI stage?"}
              </div>

              <div className="lpChatBubbleAi">
                <div className="lpChatAiBadge">
                  <Sparkles size={13} />
                  <span>{lang === "hi" ? "मैत्री कृषि एआई" : "MAITTRI Krishi AI"}</span>
                </div>
                <div>
                  {t("landing.assistant.sampleA") ||
                    "Crown Root Initiation (CRI) occurs 20-25 days after sowing. It is the most critical stage for wheat; delay causes significant tiller reduction."}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 8. HARDWARE & IOT TELEMETRY */}
      <section className="lpSection" id="iot-telemetry">
        <div className="lpSectionHeader">
          <span className="lpSectionEyebrow">{t("landing.telemetry.eyebrow") || "Hardware & Telemetry"}</span>
          <h2 className="lpSectionTitle">
            {t("landing.telemetry.title") || "Connect the Physical Farm to Digital Intelligence."}
          </h2>
          <p className="lpSectionSubtitle">
            {t("landing.telemetry.subtitle") ||
              "Low-power IoT field nodes collect live soil moisture, ambient temperature, and ultrasonic field radar scans to safeguard crops."}
          </p>
        </div>

        <div className="lpTelemetryGrid">
          <div className="lpTelemetryCard">
            <div className="lpTelemetryHeader">
              <h3 className="lpTelemetryTitle">
                <Cpu size={22} color="#15803d" />
                {t("landing.telemetry.nodeTitle") || "ESP32 Low-Power Field Nodes"}
              </h3>
              <span className="lpStudioStatusPill">Connected</span>
            </div>
            <p className="lpProblemDesc" style={{ marginBottom: 20 }}>
              {t("landing.telemetry.nodeDesc") ||
                "Solar-supported microcontrollers transmitting volumetric soil moisture and temperature updates."}
            </p>
            <div className="lpStudioMetrics" style={{ marginBottom: 0 }}>
              <div className="lpMetricChip">
                <span className="lpMetricLabel">Battery Status</span>
                <span className="lpMetricValue" style={{ color: "#15803d" }}>98% (Solar)</span>
              </div>
              <div className="lpMetricChip">
                <span className="lpMetricLabel">Transmission Interval</span>
                <span className="lpMetricValue" style={{ color: "#141e19" }}>Every 15 min</span>
              </div>
            </div>
          </div>

          <div className="lpTelemetryCard">
            <div className="lpTelemetryHeader">
              <h3 className="lpTelemetryTitle">
                <Radio size={22} color="#0284c7" />
                {t("landing.telemetry.radarTitle") || "Ultrasonic Obstacle & Animal Radar"}
              </h3>
              <span className="lpStudioStatusPill" style={{ background: "#e0f2fe", color: "#0369a1" }}>Scanning</span>
            </div>
            <p className="lpProblemDesc" style={{ marginBottom: 20 }}>
              {t("landing.telemetry.radarDesc") ||
                "Detect field intrusion and obstacles with real-time sweep visualization and distance telemetry."}
            </p>
            <div className="lpStudioMetrics" style={{ marginBottom: 0 }}>
              <div className="lpMetricChip">
                <span className="lpMetricLabel">Sweep Angle</span>
                <span className="lpMetricValue" style={{ color: "#0284c7" }}>15° - 165°</span>
              </div>
              <div className="lpMetricChip">
                <span className="lpMetricLabel">Perimeter Safety</span>
                <span className="lpMetricValue" style={{ color: "#15803d" }}>Clear</span>
              </div>
            </div>
          </div>
        </div>

        <div style={{ textAlign: "center", marginTop: 32 }}>
          <Link to="/iot-monitor" className="lpSecondaryCtaBtn">
            <Activity size={16} />
            <span>{lang === "hi" ? "लाइव आईओटी मॉनिटर खोलें" : "Open Live IoT Field Monitor"}</span>
            <ChevronRight size={16} />
          </Link>
        </div>
      </section>

      {/* 9. INCLUSIVE ACCESS & SEVA NIRMATA PORTAL */}
      <section className="lpSection" id="accessibility" style={{ background: "#ffffff", maxWidth: "100%" }}>
        <div style={{ maxWidth: 1240, margin: "0 auto" }}>
          <div className="lpSectionHeader">
            <span className="lpSectionEyebrow">{t("landing.accessibility.eyebrow") || "Inclusive Design"}</span>
            <h2 className="lpSectionTitle">
              {t("landing.accessibility.title") || "Technology That Meets Farmers Where They Are."}
            </h2>
            <p className="lpSectionSubtitle">
              {t("landing.accessibility.subtitle") ||
                "No smartphone? Low digital literacy? MAITTRI is engineered with an Authorized Seva Nirmata portal so village operators can assist any farmer."}
            </p>
          </div>

          <div className="lpAccessibilityGrid">
            <div className="lpAccessibilityCard">
              <div className="lpAccessIcon"><Languages size={22} /></div>
              <h3 className="lpProblemTitle">{t("landing.accessibility.a1Title") || "Bilingual Voice & Text"}</h3>
              <p className="lpProblemDesc">
                {t("landing.accessibility.a1Desc") ||
                  "Voice search and Hindi text designed with high-contrast typography for readability in direct sunlight."}
              </p>
            </div>

            <div className="lpAccessibilityCard">
              <div className="lpAccessIcon"><Landmark size={22} /></div>
              <h3 className="lpProblemTitle">{t("landing.accessibility.a2Title") || "Authorized Seva Nirmata Portal"}</h3>
              <p className="lpProblemDesc">
                {t("landing.accessibility.a2Desc") ||
                  "Village-level entrepreneurs can create farm profiles, register offline farmers, and print official guidance sheets."}
              </p>
              <div style={{ marginTop: 14 }}>
                <Link to="/operator" style={{ fontSize: 13, fontWeight: 700, color: "#00652c", textDecoration: "underline" }}>
                  {lang === "hi" ? "ऑपरेटर पोर्टल पर जाएं →" : "Visit Operator Portal →"}
                </Link>
              </div>
            </div>

            <div className="lpAccessibilityCard">
              <div className="lpAccessIcon"><Cpu size={22} /></div>
              <h3 className="lpProblemTitle">{t("landing.accessibility.a3Title") || "Low-Bandwidth Optimization"}</h3>
              <p className="lpProblemDesc">
                {t("landing.accessibility.a3Desc") ||
                  "Optimized payload sizes ensure fast loading even on 2G/3G rural networks with offline caching."}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 10. CORE PRINCIPLES */}
      <section className="lpSection">
        <div className="lpSectionHeader">
          <span className="lpSectionEyebrow">{t("landing.principles.eyebrow") || "Core Principles"}</span>
          <h2 className="lpSectionTitle">
            {t("landing.principles.title") || "Designed Around the Farmer."}
          </h2>
        </div>

        <div className="lpPrinciplesGrid">
          <div className="lpPrincipleCard">
            <h3 className="lpPrincipleTitle">
              <CheckCircle2 size={20} color="#15803d" />
              {t("landing.principles.simple") || "Simple & Actionable"}
            </h3>
            <p className="lpPrincipleDesc">
              {t("landing.principles.simpleDesc") ||
                "Complex agronomy presented in plain language without convoluted technical jargon."}
            </p>
          </div>

          <div className="lpPrincipleCard">
            <h3 className="lpPrincipleTitle">
              <Compass size={20} color="#15803d" />
              {t("landing.principles.contextual") || "Context-Aware"}
            </h3>
            <p className="lpPrincipleDesc">
              {t("landing.principles.contextualDesc") ||
                "Every recommendation factors in specific soil type, location, weather, and farm size."}
            </p>
          </div>

          <div className="lpPrincipleCard">
            <h3 className="lpPrincipleTitle">
              <Shield size={20} color="#15803d" />
              {t("landing.principles.trustworthy") || "Trustworthy & Independent"}
            </h3>
            <p className="lpPrincipleDesc">
              {t("landing.principles.trustworthyDesc") ||
                "Unbiased guidance with no vendor lock-in or forced commercial product promotions."}
            </p>
          </div>
        </div>
      </section>

      {/* 11. FINAL CTA BANNER */}
      <section style={{ maxWidth: 1240, margin: "0 auto", padding: "0 24px" }}>
        <div className="lpCtaCard">
          <h2 className="lpCtaTitle">
            {t("landing.cta.title") || "Let's Build a Smarter Future for Farming."}
          </h2>
          <p className="lpCtaSubtitle">
            {t("landing.cta.subtitle") ||
              "Join thousands of farmers making informed decisions with MAITTRI today."}
          </p>
          <div className="lpCtaActions">
            <Link to="/register" className="lpCtaPrimaryBtn">
              <span>{t("landing.cta.button") || "Get Started Free"}</span>
              <ArrowRight size={17} />
            </Link>
            <Link to="/login" className="lpCtaLoginLink">
              {t("landing.cta.loginLink") || "Already registered? Login here"}
            </Link>
          </div>
        </div>
      </section>

      {/* 12. COMPREHENSIVE FOOTER */}
      <footer className="lpFooter">
        <div className="lpFooterInner">
          <div className="lpFooterGrid">
            <div className="lpFooterBrandCol">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <Logo size={42} variant="icon" />
                <span className="lpFooterBrandTitle">MAITTRI • मैत्री</span>
              </div>
              <p className="lpFooterBrandDesc">
                {t("landing.footer.desc") ||
                  "MAITTRI is an AI-powered agricultural decision support platform built for Indian farmers, field operators, and agronomists."}
              </p>
            </div>

            <div>
              <h4 className="lpFooterHeading">{t("landing.footer.product") || "Platform Modules"}</h4>
              <ul className="lpFooterList">
                <li><Link to="/crop-farming/recommendation" className="lpFooterLink">{t("landing.features.f1Title") || "Crop Recommendation"}</Link></li>
                <li><Link to="/crop-farming/calendar" className="lpFooterLink">{t("landing.features.f2Title") || "Farm Planner"}</Link></li>
                <li><Link to="/crop-farming/soil-nutrients" className="lpFooterLink">{t("landing.features.f3Title") || "Soil Nutrients"}</Link></li>
                <li><Link to="/crop-farming/fertilizer" className="lpFooterLink">{t("landing.features.f4Title") || "Fertilizer Intelligence"}</Link></li>
                <li><Link to="/crop-farming/market-price" className="lpFooterLink">{t("landing.features.f5Title") || "Market Prices"}</Link></li>
                <li><Link to="/government-schemes" className="lpFooterLink">{t("landing.features.f6Title") || "Government Schemes"}</Link></li>
                <li><Link to="/krishi-assistant" className="lpFooterLink">{t("landing.features.f8Title") || "Krishi Assistant"}</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="lpFooterHeading">{t("landing.footer.portals") || "Portals"}</h4>
              <ul className="lpFooterList">
                <li><Link to="/dashboard" className="lpFooterLink">{t("landing.footer.farmerPortal") || "Farmer Portal"}</Link></li>
                <li><Link to="/operator" className="lpFooterLink">{t("landing.footer.operatorPortal") || "Official / Seva Operator"}</Link></li>
                <li><Link to="/login" className="lpFooterLink">{t("landing.nav.login") || "Login"}</Link></li>
                <li><Link to="/register" className="lpFooterLink">{t("landing.nav.getStarted") || "Register"}</Link></li>
              </ul>
            </div>

            <div>
              <h4 className="lpFooterHeading">{lang === "hi" ? "संस्थान एवं तकनीक" : "Technology & Trust"}</h4>
              <p style={{ fontSize: 13, color: "#a0b4a8", lineHeight: 1.6, margin: 0 }}>
                {t("landing.footer.developedFor") || "Built for Indian Agriculture • Grounded in Science"}
              </p>
              <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 8 }}>
                <span className="lpBadgePulse" style={{ width: 6, height: 6 }}></span>
                <span style={{ fontSize: 12, color: "#95f8a7", fontWeight: 700 }}>
                  {lang === "hi" ? "14 कृषि-जलवायु क्षेत्र सक्रिय" : "14 Agro-Climatic Zones Active"}
                </span>
              </div>
            </div>
          </div>

          <div className="lpFooterBottom">
            <div>{t("landing.footer.copyright") || "© 2026 MAITTRI. Smart Agriculture Platform. All rights reserved."}</div>
            <div style={{ display: "flex", gap: 18 }}>
              <span>{lang === "hi" ? "किसानों की समृद्धि, देश की प्रगति" : "Farmers' Prosperity, Nation's Progress"}</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
