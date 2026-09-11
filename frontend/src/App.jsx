import React, { useEffect, useMemo, useState, useRef } from "react";
import { Routes, Route, Navigate, Link, useNavigate, useParams, useLocation } from "react-router-dom";
import {
  Sprout, LayoutDashboard, MapPinned, CloudSun, Tractor, TreePine,
  Beef, Bird, LogOut, Plus, Languages, Menu, X, Leaf, IndianRupee,
  AlertTriangle, CheckCircle2, Droplets, ThermometerSun, Wind,
  Compass, Sun, CloudRain, Search, Navigation, Calendar, ShieldAlert, Shield, Landmark,
  Check, RefreshCw, Eye, Pencil, Trash2, FlaskConical, HelpCircle, ArrowRight,
  ChevronDown, Wheat, Radio
} from "lucide-react";
import api from "./api";
import Logo from "./Logo";
import { LanguageProvider, useLang } from "./LanguageContext";
import {
  T,
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
} from "./i18n";
import InteractiveLocationMap from "./InteractiveLocationMap";
import NutrientAnalysisPage from "./NutrientAnalysisPage";
import ParaliManagementPage from "./ParaliManagementPage";
import MarketPricePage from "./MarketPricePage";
import FertilizerRecommendationPage from "./FertilizerRecommendationPage";
import InsurancePlanningPage from "./InsurancePlanningPage";
import GovernmentSchemesPage from "./GovernmentSchemesPage";
import IoTMonitorPage from "./IoTMonitorPage";
import FarmerPlanningPage from "./FarmerPlanningPage";


const soilTypes = [
  "Alluvial Soil",
  "Black Soil",
  "Red Soil",
  "Laterite Soil",
  "Desert/Arid Soil",
  "Mountain/Forest Soil",
  "Saline/Alkaline Soil",
  "Loamy Soil",
  "Sandy Soil",
  "Clayey Soil",
  "Sandy Loam",
  "Clay Loam",
  "Silty Soil",
  "Other"
];
const crops = ["Wheat", "Mustard", "Rice", "Maize", "Potato", "Tomato", "Gram/Chickpea", "Cotton", "Sugarcane"];
const seasons = ["rabi", "kharif"];

/**
 * Automatically keeps the browser tab title synchronized with the current route
 */
function PageTitleManager() {
  const location = useLocation();

  useEffect(() => {
    const path = location.pathname;
    let title = "MAITTRI | Smart Agriculture Platform";
    if (path.startsWith("/dashboard")) {
      title = "MAITTRI | Dashboard";
    } else if (path.startsWith("/crop-farming/soil-nutrients") || path.startsWith("/nutrient-analysis")) {
      title = "MAITTRI | Soil & Nutrient Intelligence";
    } else if (path.startsWith("/crop-farming/fertilizer")) {
      title = "MAITTRI | Fertilizer Recommendation";
    } else if (path.startsWith("/crop-farming/recommendation") || path.startsWith("/recommend")) {
      title = "MAITTRI | Crop Recommendations";
    } else if (path.startsWith("/crop-farming/calendar") || path.startsWith("/plan")) {
      title = "MAITTRI | Personal Farm Planner & Crop Calendar";
    } else if (path.startsWith("/crop-farming/parali-management") || path.startsWith("/parali")) {
      title = "MAITTRI | Parali Management";
    } else if (path.startsWith("/crop-farming/market-price")) {

      title = "MAITTRI | Market Price";
    } else if (path.startsWith("/crop-farming/weather") || path.startsWith("/weather")) {
      title = "MAITTRI | Weather";
    } else if (path.startsWith("/farm/edit")) {
      title = "MAITTRI | Edit Farm";
    } else if (path.startsWith("/farm") || path.startsWith("/crop-farming")) {
      title = "MAITTRI | Crop Farming";

    } else if (path.startsWith("/insurance-planning") || path.startsWith("/insurance")) {
      title = "MAITTRI | Insurance Planning";
    } else if (path.startsWith("/government-schemes") || path.startsWith("/schemes")) {
      title = "MAITTRI | Government Schemes";
    } else if (path.startsWith("/horticulture")) {
      title = "MAITTRI | Horticulture";
    } else if (path.startsWith("/iot-monitor") || path.startsWith("/iot")) {
      title = "MAITTRI | IoT Field Monitor";

    } else if (path.startsWith("/login")) {
      title = "MAITTRI | Login";
    } else if (path.startsWith("/register")) {
      title = "MAITTRI | Register";
    }
    document.title = title;
  }, [location.pathname]);

  return null;
}

function WeatherConditionIcon({ icon, size = 24 }) {
  if (icon === "sun") return <Sun size={size} color="#eab308"/>;
  if (icon === "cloud-rain" || icon === "cloud-drizzle") return <CloudRain size={size} color="#0284c7"/>;
  return <CloudSun size={size} color="#16a34a"/>;
}

function LocationSearchInput({ onSelect, placeholder, defaultValue = "" }) {
  const [query, setQuery] = useState(defaultValue);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef(null);
  const skipSearchRef = useRef(false);

  useEffect(() => {
    if (defaultValue !== query) {
      skipSearchRef.current = true;
      setQuery(defaultValue || "");
    }
  }, [defaultValue]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (skipSearchRef.current) {
      skipSearchRef.current = false;
      return;
    }
    if (!query || query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await api.get("/location/search", { params: { query: query.trim(), count: 6 } });
        setResults(data.results || []);
        setOpen(true);
      } catch (err) {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item) => {
    skipSearchRef.current = true;
    setQuery(item.display_name);
    setOpen(false);
    setResults([]);
    onSelect(item);
  };

  const handleClear = () => {
    skipSearchRef.current = true;
    setQuery("");
    setResults([]);
    setOpen(false);
  };

  return (
    <div className="searchWrapper" ref={wrapperRef}>
      <Search className="searchIcon" size={18}/>
      <input
        type="text"
        placeholder={placeholder || "Search city, district or village..."}
        value={query}
        onChange={(e) => {
          skipSearchRef.current = false;
          setQuery(e.target.value);
        }}
        onFocus={() => { if (results.length > 0) setOpen(true); }}
      />
      {loading && <span className="searchLoading"><RefreshCw size={14} className="spin"/></span>}
      {!loading && query && (
        <button type="button" className="searchClearBtn" onClick={handleClear} title="Clear">
          <X size={14}/>
        </button>
      )}
      {open && results.length > 0 && (
        <ul className="suggestionsDropdown">
          {results.map((item) => (
            <li key={item.id || item.display_name} className="suggestionItem" onClick={() => handleSelect(item)}>
              <strong>{item.name}</strong>
              <span>{[item.district, item.state, item.country].filter(Boolean).join(", ")}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * 3. SPLASH / STARTUP SCREEN (MAITTRI Brand)
 */
function Splash({ onDone }) {
  const [lang] = useLang();
  
  useEffect(() => {
    const timer = setTimeout(onDone, 1800);
    return () => clearTimeout(timer);
  }, [onDone]);

  return (
    <div className="splash">
      <div className="splashBrandContainer">
        <div className="splashLogoGlow">
          <Logo size="splash" variant="icon" />
        </div>
        <h1 className="splashBrandTitle">MAITTRI</h1>
        <div className="splashBrandHindi">मैत्री</div>
        <p className="splashTagline">"किसान का साथी, समृद्धि की शुरुआत"</p>
        <p className="splashSubtext">Intelligent Agriculture • Better Decisions • Better Farming</p>
        
        <div className="splashLoadingContainer">
          <div className="splashLoadingBar">
            <div className="splashLoadingProgress"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Language({ onDone }) {
  const [, setLang, t] = useLang();
  return (
    <div className="centerPage">
      <div className="card languageCard">
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
          <Logo size={80} variant="icon" />
        </div>
        <h1 style={{ margin: "6px 0 2px", color: "#14532d" }}>MAITTRI</h1>
        <div style={{ fontSize: 18, color: "#16a34a", fontWeight: 700, marginBottom: 6 }}>मैत्री</div>
        <p style={{ margin: "4px 0 16px", color: "#64748b", fontSize: 13, fontWeight: 600 }}>
          "किसान का साथी, समृद्धि की शुरुआत"
        </p>
        <p style={{ fontWeight: 600, color: "#334155", margin: "12px 0 8px" }}>{t.language}</p>
        <button className="button" onClick={() => { setLang("en"); onDone(); }}>English</button>
        <button className="button secondary" onClick={() => { setLang("hi"); onDone(); }}>हिन्दी</button>
      </div>
    </div>
  );
}

/**
 * 4. LOGIN & REGISTRATION PAGE (MAITTRI Brand)
 */
function Auth({ mode = "login", onAuth }) {
  const [lang, setLang, t] = useLang();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const nav = useNavigate();

  const getErrorMessage = (err) => {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map(item => item.msg || JSON.stringify(item)).join(", ");
    if (detail && typeof detail === "object") return detail.msg || JSON.stringify(detail);
    if (err.response?.status >= 500) return lang === "hi" ? "सर्वर त्रुटि। कृपया थोड़ी देर बाद पुनः प्रयास करें।" : "Server error. Please try again later.";
    if (!err.response && err.message) return lang === "hi" ? "नेटवर्क त्रुटि। कृपया इंटरनेट कनेक्शन जांचें।" : "Network error. Please check your connection.";
    return lang === "hi" ? "कुछ त्रुटि हुई। कृपया पुनः प्रयास करें।" : "Something went wrong";
  };

  const submit = async e => {
    e.preventDefault(); setError("");
    try {
      const url = mode === "login" ? "/auth/login" : "/auth/register";
      const { data } = await api.post(url, { email: email.trim(), password, language: lang });
      localStorage.setItem("token", data.access_token);
      if (onAuth) onAuth();
      nav("/dashboard");
    } catch(err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <div className="centerPage authPage">
      <div className="authBackgroundWatermark">
        <Logo size={440} variant="icon" />
      </div>

      <form className="card authCard" onSubmit={submit}>
        <div className="authBrandHeader">
          <div className="authLogoCircle">
            <Logo size="login" variant="icon" />
          </div>
          <h1 className="authTitle">MAITTRI</h1>
          <div className="authHindiTitle">मैत्री</div>
          <div className="authPlatformSub">{t.platformDesc || "Smart Agriculture Platform"}</div>
          <div className="authTagline">"किसान का साथी, समृद्धि की शुरुआत"</div>
        </div>

        <div className="authLangToggle">
          <button
            type="button"
            className={`authLangBtn ${lang === "en" ? "active" : ""}`}
            onClick={() => setLang("en")}
          >
            English
          </button>
          <button
            type="button"
            className={`authLangBtn ${lang === "hi" ? "active" : ""}`}
            onClick={() => setLang("hi")}
          >
            हिन्दी
          </button>
        </div>

        <h2 className="authFormHeader">{mode === "login" ? t.login : t.register}</h2>
        {error && <div className="error">{error}</div>}
        
        <label className="authLabel">{t.email}</label>
        <input
          className="authInput"
          type="email"
          required
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder={lang === "hi" ? "अपना ईमेल दर्ज करें" : "Enter your email"}
        />
        
        <label className="authLabel">{t.password}</label>
        <input
          className="authInput"
          type="password"
          minLength="6"
          maxLength="128"
          required
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder={lang === "hi" ? "पासवर्ड दर्ज करें" : "Enter password"}
        />
        
        <button type="submit" className="button authSubmitBtn">
          {mode === "login" ? t.login : t.register}
        </button>
        
        <div className="authSwitchRow">
          <Link to={mode === "login" ? "/register" : "/login"}>
            {mode === "login"
              ? (lang === "hi" ? "नया खाता बनाएं / रजिस्टर करें" : "Create account / Register")
              : (lang === "hi" ? "पहले से खाता है? लॉगिन करें" : "Already have an account? Login")}
          </Link>
        </div>
      </form>
    </div>
  );
}

function Protected({ children }) { return localStorage.getItem("token") ? children : <Navigate to="/login" replace/>; }

/**
 * 5 & 6. SIDEBAR & TOPBAR BRANDING (MAITTRI Layout)
 */
function Layout({ children }) {
  const [lang, setLang, t] = useLang();
  const [open, setOpen] = useState(false);
  const [sidebarWeather, setSidebarWeather] = useState(null);
  const location = useLocation();
  const nav = useNavigate();
  const logout = () => { localStorage.removeItem("token"); nav("/login"); };

  // Current route tracking for parent and child active states
  const currentPath = location.pathname;
  const isCropPath = (
    currentPath.startsWith("/crop-farming") ||
    currentPath.startsWith("/farm") ||
    currentPath.startsWith("/nutrient-analysis") ||
    currentPath.startsWith("/recommend") ||
    currentPath.startsWith("/plan") ||
    currentPath.startsWith("/parali")
  );


  const [cropExpanded, setCropExpanded] = useState(() => isCropPath);

  // Automatically keep Crop Farming open if navigated to any crop route
  useEffect(() => {
    if (isCropPath) {
      setCropExpanded(true);
    }
  }, [currentPath, isCropPath]);

  useEffect(() => {
    api.get("/farms").then(r => {
      if (r.data && r.data.length > 0 && r.data[0].latitude && r.data[0].longitude) {
        api.post("/weather", {
          latitude: r.data[0].latitude,
          longitude: r.data[0].longitude,
          location_name: r.data[0].location_name || r.data[0].name
        }).then(res => setSidebarWeather(res.data)).catch(() => {});
      }
    }).catch(() => {});
  }, []);

  const item = (to, icon, label) => {
    const isActive = currentPath === to;
    return (
      <Link onClick={() => setOpen(false)} to={to} className={`navItem ${isActive ? "active" : ""}`}>
        {icon}
        <span>{label}</span>
      </Link>
    );
  };

  const subItem = (to, icon, label, aliases = []) => {
    const isSubActive = currentPath === to || aliases.some(alias => currentPath === alias || currentPath.startsWith(alias + "/"));
    return (
      <Link
        to={to}
        onClick={() => {
          setCropExpanded(true);
          setOpen(false);
        }}
        className={`navSubItem ${isSubActive ? "active" : ""}`}
      >
        <span className="navSubItemIcon">{icon}</span>
        <span>{label}</span>
      </Link>
    );
  };

  return (
    <div className="appShell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="sidebarBrandHeader">
          <div className="sidebarLogoWrap">
            <Logo size="sidebar" variant="icon" />
            <button className="mobileClose" onClick={() => setOpen(false)} aria-label="Close menu">
              <X size={20}/>
            </button>
          </div>
          <div className="sidebarBrandNames">
            <span className="sidebarTitle">MAITTRI</span>
            <span className="sidebarSubtitle">मैत्री</span>
          </div>
          <div className="sidebarTagline">किसान का साथी, समृद्धि की शुरुआत</div>
        </div>

        <nav className="sidebarNav">
          {item("/dashboard", <LayoutDashboard size={20}/>, t.dashboard)}

          {/* CROP FARMING EXPANDABLE PARENT (APPEARS ONLY ONCE) */}
          <div className="navParentGroup">
            <button
              type="button"
              className={`navParentItem ${cropExpanded ? "expanded" : ""} ${isCropPath ? "active" : ""}`}
              onClick={() => setCropExpanded(prev => !prev)}
              aria-expanded={cropExpanded}
            >
              <div className="navParentLeft">
                <Tractor size={20}/>
                <span>{t.cropFarming || t.crop || (lang === "hi" ? "फसल खेती" : "Crop Farming")}</span>
              </div>
              <span className={`navParentArrow ${cropExpanded ? "rotated" : ""}`}>
                <ChevronDown size={18}/>
              </span>
            </button>

            <div className={`navSubmenu ${cropExpanded ? "open" : ""}`}>
              <div className="navSubmenuTree">
                {subItem(
                  "/crop-farming/soil-nutrients",
                  <FlaskConical size={15}/>,
                  t.soilNutrientDepletion || (lang === "hi" ? "मृदा एवं पोषक तत्व ह्रास विश्लेषण" : "Soil & Nutrient Depletion Intelligence"),
                  ["/nutrient-analysis"]
                )}
                {subItem(
                  "/crop-farming/recommendation",
                  <Leaf size={15}/>,
                  t.cropRecommendation || (lang === "hi" ? "फसल सिफारिश" : "Crop Recommendation"),
                  ["/recommend"]
                )}
                {subItem(
                  "/crop-farming/fertilizer",
                  <Sprout size={15}/>,
                  t.fertilizerRecommendation || (lang === "hi" ? "उर्वरक सिफारिश" : "Fertilizer Recommendation"),
                  ["/fertilizer"]
                )}
                {subItem(
                  "/crop-farming/calendar",
                  <Calendar size={15}/>,
                  t.cropCalendar || (lang === "hi" ? "फसल कैलेंडर एवं योजना" : "Crop Calendar"),
                  ["/plan"]
                )}
                {subItem(
                  "/crop-farming/parali-management",
                  <span style={{ fontSize: "14px", lineHeight: 1 }}>🌾</span>,
                  lang === "hi" ? "पराली प्रबंधन" : "Parali Management",
                  ["/parali", "/parali-management"]
                )}

                {subItem(
                  "/crop-farming/market-price",
                  <IndianRupee size={15}/>,
                  t.marketPrice || (lang === "hi" ? "मंडी भाव एवं बाज़ार विश्लेषण" : "Market Price"),
                  ["/market-price"]
                )}
                {subItem(
                  "/crop-farming/weather",
                  <CloudSun size={15}/>,
                  t.weatherImpact || (lang === "hi" ? "मौसम प्रभाव एवं चेतावनी" : "Weather Impact / Alerts"),
                  ["/weather"]
                )}
              </div>

            </div>
          </div>

          {item(
            "/insurance-planning",
            <Shield size={20}/>,
            <span>🛡️ {lang === "hi" ? "कृषि बीमा योजना" : "Insurance Planning"}</span>,
            ["/insurance"]
          )}
          {item(
            "/government-schemes",
            <Landmark size={20}/>,
            <span>🏛️ {lang === "hi" ? "सरकारी योजनाएं" : "Government Schemes"}</span>,
            ["/schemes"]
          )}
          {item(
            "/iot-monitor",
            <Radio size={20}/>,
            <span>📡 {lang === "hi" ? "आईओटी फील्ड मॉनिटर" : "IoT Field Monitor"}</span>,
            ["/iot", "/crop-farming/iot-monitor"]
          )}

          {item("/horticulture", <TreePine size={20}/>, t.horticulture)}
          <div className="navItem disabled"><Bird size={20}/><span>🐔 {lang === "hi" ? "मुर्गी पालन" : "Poultry"}</span><small>{t.coming}</small></div>
          <div className="navItem disabled"><Beef size={20}/><span>🐄 {lang === "hi" ? "पशुपालन" : "Cattle"}</span><small>{t.coming}</small></div>
        </nav>

        <div className="sidebarBottom">
          {/* ONLY ONE SEPARATE WEATHER LOGO IN LOWER LEFT CORNER */}
          <Link
            to="/weather"
            className="lowerLeftWeatherLogo"
            onClick={() => setOpen(false)}
            title={lang === "hi" ? "मौसम सेवा (Weather)" : "Weather Service"}
            aria-label="Weather"
          >
            <div className="lowerLeftWeatherIconWrap">
              <CloudSun size={22}/>
              <span className="lowerLeftWeatherPulseDot"></span>
            </div>
            <div className="lowerLeftWeatherContent">
              <span className="lowerLeftWeatherTitle">{t.weather}</span>
              {sidebarWeather ? (
                <span className="lowerLeftWeatherTemp">
                  {sidebarWeather.current.temperature_2m}°C · {translateWeatherCondition(sidebarWeather.current.condition, lang)}
                </span>
              ) : (
                <span className="lowerLeftWeatherTemp">{lang === "hi" ? "लाइव मौसम" : "Live Forecast"}</span>
              )}
            </div>
          </Link>

          <select value={lang} onChange={e => setLang(e.target.value)}>
            <option value="en">English</option>
            <option value="hi">हिन्दी</option>
          </select>
          <button className="logout" onClick={logout}><LogOut size={16}/> {t.logout}</button>
        </div>
      </aside>

      {/* Floating lower-left weather logo on mobile when sidebar is closed */}
      <Link
        to="/weather"
        className="mobileLowerLeftWeatherBtn"
        title={lang === "hi" ? "मौसम सेवा" : "Weather"}
        aria-label="Weather"
      >
        <CloudSun size={20} />
        {sidebarWeather ? (
          <span className="mobileWeatherBadge">{sidebarWeather.current.temperature_2m}°C</span>
        ) : (
          <span>{t.weather}</span>
        )}
      </Link>

      <main className="main">
        <header className="topbar">
          <div className="topbarLeft">
            <button className="mobileMenu" onClick={() => setOpen(true)} aria-label="Open menu"><Menu size={22}/></button>
            <div className="topbarMobileLogo">
              <Logo size="compact" variant="icon" />
            </div>
            <div>
              <h2 className="topbarTitle">
                <span>MAITTRI</span>
                <span className="topbarHindiBadge">मैत्री</span>
              </h2>
              <p className="topbarSubtitle">{t.platformDesc || "Smart Agriculture Platform"} · {t.welcome}</p>
            </div>
          </div>
          <div className="topbarRight">
            <span className="topbarTagline">"किसान का साथी, समृद्धि की शुरुआत"</span>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}

function Dashboard() {
  const [lang,,t] = useLang();
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [weather, setWeather] = useState(null);
  const [feedback, setFeedback] = useState("");
  const [iotData, setIotData] = useState(null);

  useEffect(() => {
    api.get("/iot/latest").then(r => setIotData(r.data)).catch(() => {});
    const timer = setInterval(() => {
      api.get("/iot/latest").then(r => setIotData(r.data)).catch(() => {});
    }, 4000);
    return () => clearInterval(timer);
  }, []);

  const loadFarms = () => {
    api.get("/farms").then(r => {
      setFarms(r.data);
      if (r.data.length > 0 && !selectedFarmId) {
        setSelectedFarmId(String(r.data[0].id));
      }
    }).catch(() => {});
  };

  useEffect(() => {
    loadFarms();
  }, []);

  const f = farms.find(farm => String(farm.id) === String(selectedFarmId)) || farms[0];

  useEffect(() => {
    if (f?.latitude && f?.longitude) {
      api.post("/weather", {
        latitude: f.latitude,
        longitude: f.longitude,
        location_name: f.location_name || f.name
      }).then(r => setWeather(r.data)).catch(() => {});
    } else {
      setWeather(null);
    }
  }, [f]);

  const handleDeleteFarm = async (farmId, farmName) => {
    if (window.confirm(`${t.confirmDelete}\n\n${farmName}`)) {
      try {
        await api.delete(`/farms/${farmId}`);
        setFeedback(t.farmDeleted);
        setTimeout(() => setFeedback(""), 3500);
        const updated = farms.filter(item => item.id !== farmId);
        setFarms(updated);
        if (updated.length > 0) {
          setSelectedFarmId(String(updated[0].id));
        } else {
          setSelectedFarmId("");
        }
      } catch {
        alert(lang === "hi" ? "खेत हटाने में विफल।" : "Failed to delete farm.");
      }
    }
  };

  return (
    <div className="content">
      <div className="hero">
        <div>
          <span className="eyebrow">{lang === "hi" ? "मैत्री कृषि डैशबोर्ड" : "MAITTRI AGRONOMY PLATFORM"}</span>
          <h1>{t.dashboard}</h1>
          <p>{lang === "hi" ? "अपने खेत का विश्लेषण करें, फसलों की तुलना करें, पोषक तत्वों का प्रबंधन करें और मौसम पर नज़र रखें।" : "Analyze your farm, compare crops, manage nutrients and monitor weather."}</p>
        </div>
        <Link className="button" to="/farm"><Plus size={16}/> {t.addFarm}</Link>
      </div>

      {feedback && <div className="feedbackBanner success"><Check size={16}/> {feedback}</div>}

      {!f ? (
        <div className="card empty">
          <Sprout size={52}/>
          <h2>{t.noData}</h2>
          <Link className="button" to="/farm"><Plus size={16}/> {t.addFarm}</Link>
        </div>
      ) : (
        <>
          {/* UPPER SECTION: Left side separate Weather Box + Right side Farm Overview */}
          <div className="dashboardUpperGrid">
            {/* LEFT SIDE UPPER SEPARATE WEATHER BOX */}
            <div className="weatherBoxUpperSeparate">
              <div>
                <div className="weatherUpperHeader">
                  <div className="weatherUpperTitleGroup">
                    <CloudSun size={22}/>
                    <h3>{t.weather}</h3>
                  </div>
                  <span className="weatherLivePulseBadge">
                    <span className="liveDot"></span>
                    {lang === "hi" ? "लाइव मौसम" : "Live Weather"}
                  </span>
                </div>

                <div className="weatherLocationTag">
                  <MapPinned size={14}/>
                  <span>{f.location_name || f.name}</span>
                </div>

                {weather ? (
                  <>
                    <div className="weatherMainDisplay">
                      <WeatherConditionIcon icon={weather.current.icon} size={48}/>
                      <div>
                        <strong>{weather.current.temperature_2m}°C</strong>
                        <div className="weatherConditionDesc">
                          {translateWeatherCondition(weather.current.condition, lang)}
                        </div>
                        <div className="weatherFeelsLike">
                          {t.feelsLike} {weather.current.apparent_temperature}°C
                        </div>
                      </div>
                    </div>

                    <div className="weatherMetricsRow">
                      <div className="weatherMiniMetric">
                        <span>{t.humidity}</span>
                        <strong>{weather.current.relative_humidity_2m}%</strong>
                      </div>
                      <div className="weatherMiniMetric">
                        <span>{t.rain || (lang === "hi" ? "बारिश" : "Rain")}</span>
                        <strong>{weather.current.precipitation} mm</strong>
                      </div>
                      <div className="weatherMiniMetric">
                        <span>{t.windSpeed}</span>
                        <strong>{weather.current.wind_speed_10m} km/h</strong>
                      </div>
                    </div>

                    {weather.advisories?.spraying && (
                      <div className="weatherSprayingAdvisory">
                        <span>🌱 {t.sprayingWindow}:</span>
                        <span className={`statusBadge ${weather.advisories.spraying.status}`}>
                          {translateAdvisoryText(weather.advisories.spraying.badge, lang)}
                        </span>
                      </div>
                    )}

                    {weather.alerts?.map((a, i) => (
                      <div className="alert" key={i}><AlertTriangle size={16}/>{a.message}</div>
                    ))}
                  </>
                ) : (
                  <div style={{padding: "20px 0", color: "#64748b", fontSize: 13.5}}>
                    <p>{lang === "hi" ? "मौसम लोड करने के लिए खेत के निर्देशांक जोड़ें।" : "Add farm coordinates to load weather."}</p>
                  </div>
                )}
              </div>

              <div className="weatherBoxActions">
                <Link className="button secondary" style={{width: "100%", justifyContent: "center", fontSize: 13, padding: "10px 14px"}} to="/weather">
                  <CloudSun size={16}/> {t.viewFullForecast}
                </Link>
              </div>
            </div>

            {/* RIGHT SIDE UPPER: Farm Header & Profile Stats */}
            <div className="dashboardOverviewCol">
              {/* Farm Header Bar: Switcher + Edit + Delete */}
              <div className="farmHeaderBar" style={{margin: 0}}>
                <div className="farmSwitcherGroup">
                  <label>🌾 {t.farm}:</label>
                  {farms.length > 1 ? (
                    <select value={selectedFarmId || f.id} onChange={e => setSelectedFarmId(e.target.value)}>
                      {farms.map(farm => (
                        <option key={farm.id} value={farm.id}>
                          {farm.name} — {farm.area} {farm.area_unit} ({farm.location_name || (lang === "hi" ? "केवल निर्देशांक" : "Coordinates only")})
                        </option>
                      ))}
                    </select>
                  ) : (
                    <strong style={{fontSize: 16, color: "#194022"}}>{f.name}</strong>
                  )}
                </div>

                <div className="farmActionGroup">
                  <Link to={`/farm/edit/${f.id}`} className="button secondary" style={{padding: "8px 14px", fontSize: 13}}>
                    <Pencil size={15}/> {t.editFarm}
                  </Link>
                  <button
                    className="button danger"
                    style={{padding: "8px 14px", fontSize: 13}}
                    onClick={() => handleDeleteFarm(f.id, f.name)}
                    title={t.deleteFarm}
                  >
                    <Trash2 size={15}/> {t.deleteFarm}
                  </button>
                </div>
              </div>

              {/* 2x2 Key Stats Grid */}
              <div className="statsGrid2x2">
                <div className="stat">
                  <MapPinned/>
                  <span>{t.location}</span>
                  <b>{f.location_name || (f.latitude ? `${f.latitude.toFixed(2)}, ${f.longitude.toFixed(2)}` : (lang === "hi" ? "दर्ज नहीं" : "Not set"))}</b>
                </div>
                <div className="stat">
                  <Tractor/>
                  <span>{t.area}</span>
                  <b>{f.area} {f.area_unit}</b>
                </div>
                <div className="stat">
                  <Leaf/>
                  <span>{t.soil}</span>
                  <b>{translateSoil(f.soil_type, lang)}</b>
                </div>
                <div className="stat">
                  <Droplets/>
                  <span>{t.irrigation}</span>
                  <b>{translateIrrigation(f.irrigation, lang)}</b>
                </div>
              </div>

              {/* Next Step / Recommendations Shortcut Card */}
              <div className="nextStepActionCard">
                <div>
                  <div style={{display: "flex", alignItems: "center", gap: 8, color: "#15803d", fontWeight: 700, marginBottom: 4}}>
                    <Sprout size={18}/>
                    <span>{t.nextStep || (lang === "hi" ? "अगला कदम" : "Next step")}</span>
                  </div>
                  <p style={{margin: 0, fontSize: 13.5, color: "#475569"}}>
                    {t.nextStepDesc || (lang === "hi" ? "अपने खेत के विवरण के आधार पर उपयुक्त फसलों की सिफारिश देखें।" : "Run the crop recommendation engine using your farm profile.")}
                  </p>
                </div>
                <Link className="button" style={{whiteSpace: "nowrap", flexShrink: 0}} to="/recommend">
                  {t.recommend} <ArrowRight size={16}/>
                </Link>
              </div>
            </div>
          </div>

          {/* LIVE IOT FIELD TELEMETRY & RADAR PREVIEW WIDGET */}
          <div className="card iotDashboardPreviewCard">
            <div className="iotDashboardPreviewHeader">
              <div className="iotDashboardPreviewTitleGroup">
                <div className="iotPreviewPulseWrap">
                  <Radio size={20} color="#16a34a" />
                  <span className={`liveDot ${iotData?.is_online ? "green" : "red"}`}></span>
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
                    <span>{lang === "hi" ? "लाइव आईओटी फील्ड टेलीमेट्री एवं रडार" : "Live IoT Field Telemetry & Radar"}</span>
                    <span className="chipTag small">{iotData?.controller_type || "ESP32"}</span>
                  </h3>
                  <p style={{ margin: "2px 0 0", fontSize: 12.5, color: "#64748b" }}>
                    {iotData?.is_online ? "🟢 Telemetry active" : "🔴 Device offline"} · {t.nearestObject || "Nearest"}: {iotData?.nearest_object?.distance != null ? `${iotData.nearest_object.distance} cm @ ${iotData.nearest_object.angle}°` : "Clear"}
                  </p>
                </div>
              </div>
              <Link to="/iot-monitor" className="button" style={{ padding: "7px 14px", fontSize: 13 }}>
                <span>{lang === "hi" ? "लाइव रडार खोलें" : "Open Live Radar"}</span>
                <ArrowRight size={14} />
              </Link>
            </div>

            <div className="iotDashboardPreviewGrid">
              <div className="iotPreviewStat">
                <span>🌡️ {t.temperature || "Temperature"}</span>
                <strong>{iotData?.temperature != null ? `${iotData.temperature} °C` : "--"}</strong>
              </div>
              <div className="iotPreviewStat">
                <span>💧 {t.humidity || "Humidity"}</span>
                <strong>{iotData?.humidity != null ? `${iotData.humidity} %` : "--"}</strong>
              </div>
              <div className="iotPreviewStat">
                <span>🌱 {t.soilMoisture || "Soil Moisture"}</span>
                <strong>{iotData?.soil_moisture != null ? `${iotData.soil_moisture} %` : "--"}</strong>
              </div>
              <div className="iotPreviewStat">
                <span>🎯 {t.nearestObject || "Nearest Obstacle"}</span>
                <strong>{iotData?.nearest_object?.distance != null ? `${iotData.nearest_object.distance} cm` : "Clear"}</strong>
              </div>
              <div className="iotPreviewStat">
                <span>🛡️ {t.objectStatus || "Status"}</span>
                <strong className={iotData?.object_status === "VERY CLOSE" ? "textCritical" : (iotData?.object_status === "WARNING" ? "textWarning" : "textSafe")}>
                  {iotData?.object_status || "CLEAR"}
                </strong>
              </div>
            </div>
          </div>

          {/* All Farms Summary Card */}
          {farms.length > 1 && (
            <div className="card" style={{marginTop: 24}}>
              <div className="cardTitle"><Tractor/><h3>{t.allFarms} ({farms.length})</h3></div>
              <div className="farmsListGrid">
                {farms.map(farm => (
                  <div key={farm.id} className={`farmMiniCard ${farm.id === f.id ? "active" : ""}`}>
                    <div className="farmMiniCardTop">
                      <strong>{farm.name}</strong>
                      {farm.id === f.id && <span className="statusBadge favorable">{t.active || (lang === "hi" ? "सक्रिय" : "Active")}</span>}
                    </div>
                    <div className="farmMiniCardDetails">
                      <span>📍 {farm.location_name || (farm.latitude ? `${farm.latitude.toFixed(2)}, ${farm.longitude.toFixed(2)}` : (lang === "hi" ? "स्थान दर्ज नहीं" : "Location not set"))}</span>
                      <span>📐 {farm.area} {farm.area_unit} · {translateSoil(farm.soil_type, lang)}</span>
                      <span>💧 {translateIrrigation(farm.irrigation, lang)}</span>
                    </div>
                    <div className="farmMiniCardActions">
                      <button
                        className="smallBtn"
                        style={{margin: 0, flex: 1}}
                        onClick={() => setSelectedFarmId(String(farm.id))}
                      >
                        {farm.id === f.id ? (t.selectedFarm || (lang === "hi" ? "चयनित" : "Selected")) : t.select}
                      </button>
                      <Link
                        to={`/farm/edit/${farm.id}`}
                        className="smallBtn"
                        style={{margin: 0, textDecoration: "none"}}
                        title={t.editFarm}
                      >
                        <Pencil size={14}/>
                      </Link>
                      <button
                        className="smallBtn"
                        style={{margin: 0, color: "#dc2626", borderColor: "#fca5a5"}}
                        onClick={() => handleDeleteFarm(farm.id, farm.name)}
                        title={t.deleteFarm}
                      >
                        <Trash2 size={14}/>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function WeatherPage() {
  const [lang,,t] = useLang();
  const [farms, setFarms] = useState([]);
  const [selectedFarmId, setSelectedFarmId] = useState("");
  const [activeLoc, setActiveLoc] = useState({ latitude: 18.52, longitude: 73.85, name: "Pune, Maharashtra" });
  const [weather, setWeather] = useState(null);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);

  useEffect(() => {
    api.get("/farms").then(r => {
      setFarms(r.data);
      if (r.data.length > 0 && r.data[0].latitude && r.data[0].longitude) {
        setSelectedFarmId(String(r.data[0].id));
        setActiveLoc({
          latitude: r.data[0].latitude,
          longitude: r.data[0].longitude,
          name: r.data[0].location_name || r.data[0].name
        });
      } else {
        setActiveLoc({ latitude: 18.52, longitude: 73.85, name: "Pune, Maharashtra, India" });
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!activeLoc?.latitude || !activeLoc?.longitude) return;
    setLoading(true);
    api.post("/weather", {
      latitude: activeLoc.latitude,
      longitude: activeLoc.longitude,
      location_name: activeLoc.name,
      forecast_days: 7
    }).then(r => {
      setWeather(r.data);
    }).catch(() => {}).finally(() => {
      setLoading(false);
    });
  }, [activeLoc]);

  const handleFarmSelect = (e) => {
    const val = e.target.value;
    setSelectedFarmId(val);
    const found = farms.find(f => String(f.id) === val);
    if (found && found.latitude && found.longitude) {
      setActiveLoc({
        latitude: found.latitude,
        longitude: found.longitude,
        name: found.location_name || found.name
      });
    }
  };

  const handleGpsDetect = () => {
    if (!navigator.geolocation) {
      alert(lang === "hi" ? "आपके ब्राउज़र द्वारा जियोलोकेशन समर्थित नहीं है।" : "Geolocation is not supported by your browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        try {
          const { data } = await api.get("/location/reverse", { params: { latitude: lat, longitude: lon } });
          setActiveLoc({
            latitude: lat,
            longitude: lon,
            name: data.display_name || `${lat.toFixed(2)}, ${lon.toFixed(2)}`
          });
          setSelectedFarmId("gps");
        } catch {
          setActiveLoc({ latitude: lat, longitude: lon, name: `${lat.toFixed(2)}, ${lon.toFixed(2)}` });
        } finally {
          setLocating(false);
        }
      },
      () => {
        alert(lang === "hi" ? "स्थान की अनुमति अस्वीकृत या उपलब्ध नहीं है।" : "Location permission denied or unavailable.");
        setLocating(false);
      },
      { timeout: 8000, enableHighAccuracy: false, maximumAge: 60000 }
    );
  };

  const handleCitySelect = (item) => {
    setActiveLoc({
      latitude: item.latitude,
      longitude: item.longitude,
      name: item.display_name
    });
    setSelectedFarmId("custom");
  };

  return (
    <div className="content">
      <div className="hero">
        <div>
          <span className="eyebrow">{lang === "hi" ? "लाइव सैटेलाइट एवं मौसम सेवा" : "LIVE SATELLITE & WEATHER API"}</span>
          <h1>{t.weatherTitle}</h1>
          <p>{t.weatherSubtitle}</p>
        </div>
      </div>

      {/* Top Location Selector Bar */}
      <div className="weatherTopBar">
        {farms.length > 0 && (
          <select value={selectedFarmId} onChange={handleFarmSelect}>
            <option value="" disabled>{t.selectFarmLocation}</option>
            {farms.map(f => (
              <option key={f.id} value={f.id}>
                🚜 {f.name} ({f.location_name || `${f.latitude?.toFixed(2)}, ${f.longitude?.toFixed(2)}`})
              </option>
            ))}
            {selectedFarmId === "gps" && <option value="gps">📍 {t.myLocation}</option>}
            {selectedFarmId === "custom" && <option value="custom">🔍 {activeLoc.name}</option>}
          </select>
        )}

        <button className="button secondary" type="button" onClick={handleGpsDetect} disabled={locating}>
          <Navigation size={16} className={locating ? "spin" : ""}/>
          {locating ? t.locating : t.detectLocation}
        </button>

        <div style={{flex: 1, minWidth: 260}}>
          <LocationSearchInput onSelect={handleCitySelect} placeholder={t.searchCity}/>
        </div>
      </div>

      {loading && !weather && (
        <div className="card empty">
          <RefreshCw size={44} className="spin" style={{color: "#2f7d32"}}/>
          <h2>{lang === "hi" ? "मौसम पूर्वानुमान लोड हो रहा है..." : "Loading weather forecast..."}</h2>
        </div>
      )}

      {weather && (
        <>
          {/* Main Weather Hero Card */}
          <div className="weatherHeroCard">
            <div className="weatherHeroLeft">
              <div className="weatherPlace">
                <MapPinned size={20}/>
                <span>{weather.location?.name || activeLoc.name}</span>
              </div>
              <div className="weatherMainTemp">
                {weather.current?.temperature_2m}°C
              </div>
              <div className="weatherConditionBadge">
                <WeatherConditionIcon icon={weather.current?.icon} size={20}/>
                <span>{translateWeatherCondition(weather.current?.condition, lang)}</span>
                <span style={{opacity: .7}}>· {t.feelsLike} {weather.current?.apparent_temperature}°C</span>
              </div>
            </div>

            {/* Quick Metrics */}
            <div className="weatherMetricsGrid">
              <div className="weatherMetricPill">
                <Droplets size={24}/>
                <div>
                  <span>{t.humidity}</span>
                  <strong>{weather.current?.relative_humidity_2m}%</strong>
                </div>
              </div>
              <div className="weatherMetricPill">
                <Wind size={24}/>
                <div>
                  <span>{t.windSpeed}</span>
                  <strong>{weather.current?.wind_speed_10m} km/h</strong>
                </div>
              </div>
              <div className="weatherMetricPill">
                <CloudRain size={24}/>
                <div>
                  <span>{t.rain || (lang === "hi" ? "बारिश" : "Rain")}</span>
                  <strong>{weather.current?.precipitation} mm</strong>
                </div>
              </div>
              <div className="weatherMetricPill">
                <Sun size={24}/>
                <div>
                  <span>{t.uvIndex}</span>
                  <strong>{weather.daily?.[0]?.uv_index_max ?? "Moderate"}</strong>
                </div>
              </div>
              <div className="weatherMetricPill">
                <Compass size={24}/>
                <div>
                  <span>{t.pressure}</span>
                  <strong>{weather.current?.surface_pressure} hPa</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Agricultural Advisories Grid */}
          <h2 style={{fontSize: 20, margin: "28px 0 14px", color: "#193c20"}}>{t.farmDecisionAdvisories || (lang === "hi" ? "कृषि निर्णय सहयोग एवं सलाह" : "Farm Decision Support & Advisories")}</h2>
          <div className="advisoryGrid">
            {/* Spraying Window */}
            <div className="advisoryCard">
              <div className="advisoryHeader">
                <h3><Droplets size={18}/> {t.sprayingWindow}</h3>
                <span className={`statusBadge ${weather.advisories?.spraying?.status}`}>
                  {translateAdvisoryText(weather.advisories?.spraying?.badge, lang)}
                </span>
              </div>
              <div className="advisoryTitle">{translateAdvisoryText(weather.advisories?.spraying?.title, lang)}</div>
              <p className="advisoryReason">{translateReason(weather.advisories?.spraying?.reason, lang)}</p>
              <div className="advisoryRec">
                <strong>{lang === "hi" ? "अनुशंसा:" : "Recommendation:"}</strong> {translateReason(weather.advisories?.spraying?.recommendation, lang)}
              </div>
            </div>

            {/* Irrigation Guidance */}
            <div className="advisoryCard">
              <div className="advisoryHeader">
                <h3><Tractor size={18}/> {t.irrigationAdvisory}</h3>
                <span className={`statusBadge ${weather.advisories?.irrigation?.status}`}>
                  {translateAdvisoryText(weather.advisories?.irrigation?.badge, lang)}
                </span>
              </div>
              <div className="advisoryTitle">{translateAdvisoryText(weather.advisories?.irrigation?.title, lang)}</div>
              <p className="advisoryReason">{translateReason(weather.advisories?.irrigation?.reason, lang)}</p>
              <div className="advisoryRec">
                <strong>{lang === "hi" ? "अनुशंसा:" : "Recommendation:"}</strong> {translateReason(weather.advisories?.irrigation?.recommendation, lang)}
              </div>
            </div>

            {/* Disease Risk */}
            <div className="advisoryCard">
              <div className="advisoryHeader">
                <h3><ShieldAlert size={18}/> {t.diseaseRisk}</h3>
                <span className={`statusBadge ${weather.advisories?.disease?.status}`}>
                  {translateAdvisoryText(weather.advisories?.disease?.badge, lang)}
                </span>
              </div>
              <div className="advisoryTitle">{translateAdvisoryText(weather.advisories?.disease?.title, lang)}</div>
              <p className="advisoryReason">{translateReason(weather.advisories?.disease?.reason, lang)}</p>
              <div className="advisoryRec">
                <strong>{lang === "hi" ? "अनुशंसा:" : "Recommendation:"}</strong> {translateReason(weather.advisories?.disease?.recommendation, lang)}
              </div>
            </div>
          </div>

          {/* Temperature / Severe Weather Alerts */}
          {weather.alerts?.map((alert, i) => (
            <div className="alert" key={i} style={{marginBottom: 20}}>
              <AlertTriangle size={22}/>
              <div>
                <strong>{alert.title}</strong>
                <p style={{margin: "4px 0 0"}}>{alert.message}</p>
              </div>
            </div>
          ))}

          {/* 7-Day Forecast */}
          <div className="forecastSection">
            <h2 style={{fontSize: 20, margin: "24px 0 10px", color: "#193c20"}}>{t.forecast7Days}</h2>
            <div className="forecastGrid">
              {weather.daily?.map((d, index) => {
                const dateObj = new Date(d.date);
                const dayName = index === 0 ? (t.today || (lang === "hi" ? "आज" : "Today")) : dateObj.toLocaleDateString(lang === "hi" ? "hi-IN" : "en-US", { weekday: "short" });
                const formattedDate = dateObj.toLocaleDateString(lang === "hi" ? "hi-IN" : "en-US", { month: "short", day: "numeric" });
                return (
                  <div key={d.date} className={`forecastCard ${index === 0 ? "today" : ""}`}>
                    <span className="forecastDay">{dayName}</span>
                    <span className="forecastDate">{formattedDate}</span>
                    <div className="forecastIcon">
                      <WeatherConditionIcon icon={d.icon} size={24}/>
                    </div>
                    <span className="forecastCondition">{translateWeatherCondition(d.condition, lang)}</span>
                    <div className="forecastTempRange">
                      <span className="max">{Math.round(d.temp_max)}°</span>
                      <span className="min">/ {Math.round(d.temp_min)}°</span>
                    </div>
                    <span className="forecastRain">
                      <CloudRain size={12}/> {d.precipitation_probability}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 24-Hour Hourly Trend */}
          <div style={{marginTop: 26}}>
            <h2 style={{fontSize: 20, margin: "0 0 8px", color: "#193c20"}}>{t.hourlyForecast}</h2>
            <div className="hourlyStripWrapper">
              <div className="hourlyStrip">
                {weather.hourly?.map((h) => {
                  const hourText = new Date(h.time).toLocaleTimeString(lang === "hi" ? "hi-IN" : [], { hour: "2-digit", minute: "2-digit" });
                  return (
                    <div key={h.time} className="hourlyCard">
                      <span className="hourlyTime">{hourText}</span>
                      <WeatherConditionIcon icon={h.icon} size={20}/>
                      <span className="hourlyTemp">{Math.round(h.temperature)}°</span>
                      <span className="hourlyRain"><CloudRain size={10}/> {h.rain_probability}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function FarmForm() {
  const [lang,,t] = useLang();
  const nav = useNavigate();
  const { farmId } = useParams();
  const isEditing = Boolean(farmId);
  const [loadingFarm, setLoadingFarm] = useState(isEditing);
  const [feedback, setFeedback] = useState({ type: "", message: "" });
  const [locating, setLocating] = useState(false);
  const [geoError, setGeoError] = useState("");

  const [form, setForm] = useState({
    name: "My Farm",
    area: "",
    area_unit: "acre",
    soil_type: "Loamy Soil",
    soil_type_source: "farmer_selected",
    soil_confidence: "Medium",
    irrigation: "available",
    previous_crop: "",
    previous_crop_month: "",
    previous_crop_period: "",
    current_crop: "",
    cultivation_count: 1,
    soil_n: "",
    soil_p: "",
    soil_k: "",
    soil_ph: "",
    organic_carbon: "",
    latitude: "",
    longitude: "",
    location_name: "",
    location_source: "manual"
  });

  const [soilEstimate, setSoilEstimate] = useState(null);
  const [estimatingSoil, setEstimatingSoil] = useState(false);
  const [showSoilDropdown, setShowSoilDropdown] = useState(false);
  const [showDeterminedInfo, setShowDeterminedInfo] = useState(false);

  useEffect(() => {
    if (farmId) {
      setLoadingFarm(true);
      api.get(`/farms/${farmId}`).then(res => {
        const f = res.data;
        setForm({
          name: f.name || "My Farm",
          area: f.area != null ? String(f.area) : "",
          area_unit: f.area_unit || "acre",
          soil_type: f.soil_type || "Loamy Soil",
          soil_type_source: f.soil_type_source || "farmer_selected",
          soil_confidence: f.soil_confidence || "Medium",
          irrigation: f.irrigation || "available",
          previous_crop: f.previous_crop || "",
          previous_crop_month: f.previous_crop_month || "",
          previous_crop_period: f.previous_crop_period || "",
          current_crop: f.current_crop || "",
          cultivation_count: f.cultivation_count || 1,
          soil_n: f.soil_n != null ? String(f.soil_n) : "",
          soil_p: f.soil_p != null ? String(f.soil_p) : "",
          soil_k: f.soil_k != null ? String(f.soil_k) : "",
          soil_ph: f.soil_ph != null ? String(f.soil_ph) : "",
          organic_carbon: f.organic_carbon != null ? String(f.organic_carbon) : "",
          latitude: f.latitude != null ? String(f.latitude) : "",
          longitude: f.longitude != null ? String(f.longitude) : "",
          location_name: f.location_name || "",
          location_source: f.location_source || "manual"
        });
        if (f.latitude && f.longitude) {
          fetchSoilEstimate(f.latitude, f.longitude, false);
        }
      }).catch(() => {
        setFeedback({ type: "error", message: lang === "hi" ? "खेत विवरण लोड करने में विफल।" : "Failed to load farm details." });
      }).finally(() => {
        setLoadingFarm(false);
      });
    }
  }, [farmId]);

  const set = (k, v) => setForm(x => ({ ...x, [k]: v }));

  const fetchSoilEstimate = async (lat, lon, autoApply = true) => {
    if (lat == null || lon == null || isNaN(Number(lat)) || isNaN(Number(lon))) return;
    setEstimatingSoil(true);
    try {
      const { data } = await api.post("/soil/estimate", { latitude: Number(lat), longitude: Number(lon) });
      setSoilEstimate(data);
      if (autoApply) {
        setForm(prev => {
          if (prev.soil_type_source !== "farmer_selected") {
            return {
              ...prev,
              soil_type: data.probable_soil_type,
              soil_type_source: "auto_detected",
              soil_confidence: data.confidence || "Medium"
            };
          }
          return { ...prev, soil_confidence: data.confidence || "Medium" };
        });
      }
    } catch {
      // Gracefully continue if external soil service fails
    } finally {
      setEstimatingSoil(false);
    }
  };

  const handleMapLocationChange = async (lat, lon, source = "map_click") => {
    setGeoError("");
    setForm(x => ({
      ...x,
      latitude: String(lat),
      longitude: String(lon),
      location_source: source
    }));
    try {
      const { data } = await api.get("/location/reverse", { params: { latitude: lat, longitude: lon } });
      set("location_name", data.display_name || `${lat.toFixed(2)}, ${lon.toFixed(2)}`);
    } catch {
      set("location_name", `${lat.toFixed(2)}, ${lon.toFixed(2)}`);
    }
    fetchSoilEstimate(lat, lon, form.soil_type_source !== "farmer_selected");
  };

  const handleCitySelect = (item) => {
    setGeoError("");
    setForm(x => ({
      ...x,
      location_name: item.display_name,
      latitude: String(item.latitude),
      longitude: String(item.longitude),
      location_source: "search"
    }));
    fetchSoilEstimate(item.latitude, item.longitude, form.soil_type_source !== "farmer_selected");
  };

  const useLocation = () => {
    setGeoError("");
    if (!navigator.geolocation) {
      setGeoError(lang === "hi" ? "ब्राउज़र द्वारा स्थान सेवा समर्थित नहीं है।" : "Geolocation is not supported by your browser.");
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async (p) => {
        const lat = p.coords.latitude;
        const lon = p.coords.longitude;
        setForm(x => ({
          ...x,
          latitude: String(lat),
          longitude: String(lon),
          location_source: "gps"
        }));
        try {
          const { data } = await api.get("/location/reverse", { params: { latitude: lat, longitude: lon } });
          set("location_name", data.display_name || `${lat.toFixed(2)}, ${lon.toFixed(2)}` );
        } catch {
          set("location_name", `${lat.toFixed(2)}, ${lon.toFixed(2)}`);
        } finally {
          setLocating(false);
        }
        fetchSoilEstimate(lat, lon, form.soil_type_source !== "farmer_selected");
      },
      (err) => {
        setLocating(false);
        if (err.code === 1) {
          setGeoError(lang === "hi" ? "स्थान की अनुमति अस्वीकृत हुई। आप मानचित्र पर क्लिक करके खेत चुन सकते हैं।" : "Location permission was denied. You can select your field directly on the interactive map.");
        } else if (err.code === 2) {
          setGeoError(lang === "hi" ? "स्थान अनुपलब्ध है। कृपया डिवाइस का जीपीएस जांचें।" : "Location unavailable. Please check device GPS or choose on the map.");
        } else if (err.code === 3) {
          setGeoError(lang === "hi" ? "स्थान अनुरोध समय समाप्त। कृपया मानचित्र पर क्लिक करें।" : "Location request timed out. Please click on the map.");
        } else {
          setGeoError(lang === "hi" ? "स्थान का पता नहीं चल सका। कृपया मानचित्र पर खेत का स्थान पिन करें।" : "Unable to detect location. Please click on the map to pin your field.");
        }
      },
      { timeout: 8000, enableHighAccuracy: false, maximumAge: 60000 }
    );
  };

  const handleSoilSelect = (e) => {
    const selected = e.target.value;
    setForm(x => ({
      ...x,
      soil_type: selected,
      soil_type_source: "farmer_selected"
    }));
  };

  const submit = async (e, nextAction = "save") => {
    if (e && e.preventDefault) e.preventDefault();
    setFeedback({ type: "", message: "" });
    const payload = {
      ...form,
      area: Number(form.area),
      latitude: form.latitude ? Number(form.latitude) : null,
      longitude: form.longitude ? Number(form.longitude) : null,
      location_name: form.location_name || null,
      location_source: form.location_source || "manual",
      soil_type_source: form.soil_type_source || "farmer_selected",
      soil_confidence: form.soil_confidence || "Medium",
      previous_crop_period: form.previous_crop_period || null,
      cultivation_count: form.cultivation_count ? Number(form.cultivation_count) : 1,
      soil_n: form.soil_n ? Number(form.soil_n) : null,
      soil_p: form.soil_p ? Number(form.soil_p) : null,
      soil_k: form.soil_k ? Number(form.soil_k) : null,
      soil_ph: form.soil_ph ? Number(form.soil_ph) : null,
      organic_carbon: form.organic_carbon ? Number(form.organic_carbon) : null
    };

    try {
      let savedId = farmId;
      if (isEditing) {
        const { data } = await api.put(`/farms/${farmId}`, payload);
        savedId = data.id;
        setFeedback({ type: "success", message: t.farmUpdated });
      } else {
        const { data } = await api.post("/farms", payload);
        savedId = data.id;
      }

      if (nextAction === "analyze") {
        nav(`/nutrient-analysis/${savedId}`);
      } else {
        if (isEditing) {
          setTimeout(() => nav("/dashboard"), 1200);
        } else {
          nav("/dashboard");
        }
      }
    } catch {
      setFeedback({ type: "error", message: lang === "hi" ? "खेत सहेजने में त्रुटि। कृपया इनपुट मान जांचें।" : "Error saving farm. Please check input values." });
    }
  };

  if (loadingFarm) {
    return (
      <div className="content">
        <div className="card empty">
          <RefreshCw size={44} className="spin" style={{color: "#2f7d32"}}/>
          <h2>{lang === "hi" ? "खेत विवरण लोड हो रहा है..." : "Loading farm details..."}</h2>
        </div>
      </div>
    );
  }

  const parsedLat = form.latitude ? Number(form.latitude) : null;
  const parsedLon = form.longitude ? Number(form.longitude) : null;

  return (
    <div className="content">
      <div className="pageTitle">
        <h1>{isEditing ? `${t.editFarm}: ${form.name}` : t.addFarm}</h1>
        <p>{isEditing ? (lang === "hi" ? "अपने खेत का रकबा, स्थान, मिट्टी विश्लेषण और फसल विवरण अपडेट करें।" : "Update your farm's acreage, location, soil analysis, and crop details.") : (lang === "hi" ? "अनुकूलित फसल सिफारिशों और मौसम चेतावनियों के लिए अपने खेत का स्थान और मिट्टी का विवरण दर्ज करें।" : "Enter your farm location and soil profile for tailored crop recommendations and weather alerts.")}</p>
      </div>

      {feedback.message && (
        <div className={`feedbackBanner ${feedback.type}`}>
          {feedback.type === "success" ? <Check size={18}/> : <AlertTriangle size={18}/>}
          {feedback.message}
        </div>
      )}

      <form className="card form" onSubmit={(e) => submit(e, "analyze")}>
        <div className="section">
          <h3>{lang === "hi" ? "1. खेत एवं स्थान" : "1. Farm & Location"}</h3>
          <div className="formGrid">
            <Field label={lang === "hi" ? "खेत का नाम" : "Farm name"}>
              <input value={form.name} required onChange={e => set("name", e.target.value)}/>
            </Field>
            <Field label={t.area}>
              <div className="inline">
                <input type="number" min="0.01" step="0.01" required value={form.area} onChange={e => set("area", e.target.value)}/>
                <select value={form.area_unit} onChange={e => set("area_unit", e.target.value)}>
                  <option value="acre">{lang === "hi" ? "एकड़ (acre)" : "acre"}</option>
                  <option value="hectare">{lang === "hi" ? "हेक्टेयर (hectare)" : "hectare"}</option>
                  <option value="bigha">{lang === "hi" ? "बीघा (bigha)" : "bigha"}</option>
                  <option value="sqm">{lang === "hi" ? "वर्ग मीटर (sqm)" : "sqm"}</option>
                </select>
              </div>
            </Field>

            {/* Location Search & Auto-complete */}
            <div style={{gridColumn: "1 / -1"}}>
              <Field label={t.location}>
                <LocationSearchInput
                  onSelect={handleCitySelect}
                  placeholder={t.searchCity}
                  defaultValue={form.location_name}
                />
              </Field>

              {/* Interactive Leaflet Map with Click-to-Pin & GPS */}
              <InteractiveLocationMap
                latitude={parsedLat}
                longitude={parsedLon}
                locationName={form.location_name}
                onChangeLocation={handleMapLocationChange}
                onLocateUser={useLocation}
                isLocating={locating}
                error={geoError}
              />

              <div className="inline" style={{marginTop: 8}}>
                <input placeholder="Latitude" value={form.latitude} onChange={e => {
                  set("latitude", e.target.value);
                  if (e.target.value && form.longitude) fetchSoilEstimate(e.target.value, form.longitude);
                }}/>
                <input placeholder="Longitude" value={form.longitude} onChange={e => {
                  set("longitude", e.target.value);
                  if (form.latitude && e.target.value) fetchSoilEstimate(form.latitude, e.target.value);
                }}/>
                <span style={{ fontSize: 12, color: "#64748b", alignSelf: "center" }}>
                  {lang === "hi" ? "स्रोत: " : "Source: "}
                  <strong>
                    {form.location_source === "gps"
                      ? (lang === "hi" ? "जीपीएस द्वारा पता लगाया गया" : "GPS Detection")
                      : form.location_source === "map_click"
                      ? (lang === "hi" ? "मानचित्र पर पिन" : "Map Pin Click")
                      : form.location_source === "search"
                      ? (lang === "hi" ? "शहर खोज" : "City Search")
                      : (lang === "hi" ? "मैन्युअल निर्देशांक" : "Manual Coordinates")}
                  </strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="section">
          <h3>{lang === "hi" ? "2. मिट्टी एवं सिंचाई" : "2. Soil & Water"}</h3>
          
          {/* Automatic Soil Estimation Box with Farmer Override */}
          <div className="soilEstimateCard">
            <div className="soilProbableTop">
              <div>
                <small style={{ color: "#64748b", textTransform: "uppercase", fontWeight: 700, fontSize: 11, display: "block" }}>
                  {t.probableSoilType || (lang === "hi" ? "संभावित मिट्टी का प्रकार" : "Probable Soil Type")}
                </small>
                <div className="soilTypeDisplay">
                  <span className="soilTypeName">{translateSoil(form.soil_type, lang)}</span>
                  <span className={`sourcePill ${form.soil_type_source === "farmer_selected" ? "manual" : "auto"}`}>
                    {form.soil_type_source === "farmer_selected" ? (t.farmerSelected || (lang === "hi" ? "किसान द्वारा चयनित" : "Farmer selected")) : (t.autoDetected || (lang === "hi" ? "स्वतः पहचाना गया" : "Auto-detected"))}
                  </span>
                  <span className={`confidenceTag ${form.soil_confidence?.toLowerCase() || "medium"}`}>
                    {translateConfidence(form.soil_confidence, lang)} {lang === "hi" ? "विश्वसनीयता" : "Confidence"}
                  </span>
                  {estimatingSoil && <RefreshCw size={14} className="spin" color="#16a34a"/>}
                </div>
              </div>

              <button
                type="button"
                className="toggleSoilBtn"
                onClick={() => setShowSoilDropdown(!showSoilDropdown)}
              >
                {showSoilDropdown ? (lang === "hi" ? "मिट्टी के विकल्प छिपाएं" : "Hide soil options") : (t.changeSoilType || (lang === "hi" ? "सही नहीं है? मिट्टी बदलें" : "Not correct? Change soil type"))}
              </button>
            </div>

            {/* Collapsible Info: How was this determined? */}
            <button
              type="button"
              className="howDeterminedBtn"
              onClick={() => setShowDeterminedInfo(!showDeterminedInfo)}
            >
              <HelpCircle size={14}/> {t.howDetermined || (lang === "hi" ? "यह कैसे निर्धारित हुआ?" : "How was this determined?")}
            </button>

            {showDeterminedInfo && (
              <div className="soilDeterminedBox">
                <p><strong>{lang === "hi" ? "पद्धति (Methodology):" : "Methodology:"}</strong> {soilEstimate?.methodology || (lang === "hi" ? "आपके चयनित अक्षांश और देशांतर से जुड़े क्षेत्रीय कृषि-पारिस्थितिक मिट्टी वर्गीकरण से प्राप्त।" : "Derived from regional agro-ecological soil classification associated with your selected latitude & longitude.")}</p>
                <p><strong>{lang === "hi" ? "भौगोलिक संदर्भ:" : "Geographic Context:"}</strong> {soilEstimate?.explanation || (lang === "hi" ? "इंडो-गंगा और दक्कन कृषि-पारिस्थितिक क्षेत्र आईसीएआर और सॉइल-ग्रिड्स डेटा के आधार पर मिट्टी की बनावट को कैलिब्रेट करते हैं।" : "Indo-Gangetic and Deccan agro-ecological zones calibrate soil texture based on ICAR and SoilGrids data.")}</p>
                <p style={{ margin: 0, fontSize: 11.5, color: "#64748b" }}>
                  <em>{soilEstimate?.disclaimer || (lang === "hi" ? "क्षेत्रीय भू-स्थानिक आंकड़ों पर आधारित; वास्तविक खेत की मिट्टी की स्थिति भिन्न हो सकती है। आप ऊपर अपनी सटीक मिट्टी चुन सकते हैं।" : "Based on regional geospatial data; local field soil conditions may vary. You can select your actual soil type above.")}</em>
                </p>
              </div>
            )}

            {/* Expanded Dropdown for Farmer Override */}
            {showSoilDropdown && (
              <div style={{ marginTop: 12, padding: "12px 14px", background: "#ffffff", borderRadius: 8, border: "1px solid #c8d8c9" }}>
                <label style={{ display: "block", fontWeight: 700, fontSize: 13, marginBottom: 6, color: "#164e20" }}>
                  {lang === "hi" ? "अपने खेत की मिट्टी का प्रकार चुनें:" : "Select Your Field Soil Type:"}
                </label>
                <select value={form.soil_type} onChange={handleSoilSelect} style={{ width: "100%", padding: "8px 12px", borderRadius: 8 }}>
                  {soilTypes.map(x => <option key={x} value={x}>{translateSoil(x, lang)}</option>)}
                </select>
                <small style={{ color: "#64748b", marginTop: 4, display: "block" }}>
                  {lang === "hi"
                    ? "मिट्टी का प्रकार चुनने पर इसे 'किसान द्वारा चयनित' माना जाएगा और सभी पोषक तत्व गणनाओं के लिए यह लागू होगा।"
                    : "Selecting a soil type will mark it as Farmer selected and will override the automatic estimate for all nutrient calculations."}
                </small>
              </div>
            )}
          </div>

          <div className="formGrid">
            <Field label={t.irrigation}>
              <select value={form.irrigation} onChange={e => set("irrigation", e.target.value)}>
                <option value="available">{translateIrrigation("available", lang)}</option>
                <option value="limited">{translateIrrigation("limited", lang)}</option>
                <option value="rainfed">{translateIrrigation("rainfed", lang)}</option>
              </select>
            </Field>

            {/* Optional Soil pH */}
            <Field label={t.soilPhOptional || (lang === "hi" ? "मिट्टी का pH (वैकल्पिक)" : "Soil pH (optional)")}>
              <input
                type="number"
                step="0.1"
                value={form.soil_ph}
                onChange={e => set("soil_ph", e.target.value)}
                placeholder={lang === "hi" ? "उदा. 6.5 (जांच न होने पर खाली छोड़ें)" : "e.g. 6.5 (Leave blank if not tested)"}
              />
            </Field>
          </div>
          <p className="hint">
            {t.soilPhHint || (lang === "hi" ? "pH जानना अनिवार्य नहीं है। यदि आपके पास मिट्टी जांच रिपोर्ट है, तो आप N/P/K और pH मान दर्ज कर सकते हैं। खाली छोड़ने पर यह 'दर्ज नहीं' रहेगा।" : "You do not need to know pH. If you have a soil-test report, you can optionally enter N/P/K and pH values. If left blank, it will be marked 'Not provided'.")}
          </p>
        </div>

        <div className="section">
          <h3>{lang === "hi" ? "3. वैकल्पिक प्रयोगशाला मृदा परीक्षण आंकड़े" : "3. Optional Soil-Test Values"}</h3>
          <p style={{ fontSize: 12.5, color: "#64748b", margin: "-6px 0 12px" }}>
            {lang === "hi"
              ? "केवल तभी दर्ज करें जब आपके पास वास्तविक मृदा स्वास्थ्य कार्ड (Soil Health Card) रिपोर्ट हो। यदि दर्ज किया गया, तो यह AI अनुमानों की जगह उच्च विश्वसनीयता के साथ लागू होगा।"
              : "Only enter if you have a physical Soil Health Card report. If provided, values will override AI estimates with High confidence."}
          </p>
          <div className="formGrid">
            <Field label={lang === "hi" ? "नाइट्रोजन (N) [किग्रा/हेक्टेयर]" : "Nitrogen (N) [kg/ha]"}>
              <input type="number" step="0.1" value={form.soil_n} onChange={e => set("soil_n", e.target.value)} placeholder="e.g. 65"/>
            </Field>
            <Field label={lang === "hi" ? "फास्फोरस (P) [किग्रा/हेक्टेयर]" : "Phosphorus (P) [kg/ha]"}>
              <input type="number" step="0.1" value={form.soil_p} onChange={e => set("soil_p", e.target.value)} placeholder="e.g. 30"/>
            </Field>
            <Field label={lang === "hi" ? "पोटैशियम (K) [किग्रा/हेक्टेयर]" : "Potassium (K) [kg/ha]"}>
              <input type="number" step="0.1" value={form.soil_k} onChange={e => set("soil_k", e.target.value)} placeholder="e.g. 40"/>
            </Field>
            <Field label={lang === "hi" ? "जैविक कार्बन (%)" : "Organic Carbon (%)"}>
              <input type="number" step="0.01" value={form.organic_carbon} onChange={e => set("organic_carbon", e.target.value)} placeholder="e.g. 0.55"/>
            </Field>
          </div>
        </div>

        <div className="section">
          <h3>{lang === "hi" ? "4. फसल इतिहास एवं फसल चक्र" : "4. Crop History & Cropping Sequence"}</h3>
          <div className="formGrid">
            <Field label={t.previous}>
              <select value={form.previous_crop} onChange={e => set("previous_crop", e.target.value)}>
                <option value="">{lang === "hi" ? "ज्ञात नहीं / कोई नहीं" : "Not known / None"}</option>
                {crops.map(x => <option key={x} value={x}>{translateCrop(x, lang)}</option>)}
              </select>
            </Field>
            <Field label={t.growingPeriod || (lang === "hi" ? "पिछली फसल का समय / माह" : "Previous Crop Growing Period")}>
              <input
                placeholder={lang === "hi" ? "उदा. नवंबर - अप्रैल" : "e.g. November – April"}
                value={form.previous_crop_period || form.previous_crop_month}
                onChange={e => {
                  set("previous_crop_period", e.target.value);
                  set("previous_crop_month", e.target.value);
                }}
              />
            </Field>
            <Field label={t.current}>
              <select value={form.current_crop} onChange={e => set("current_crop", e.target.value)}>
                <option value="">{lang === "hi" ? "वर्तमान में कोई फसल नहीं (परती / आगामी बुवाई)" : "No current crop (Fallow / Sowing soon)"}</option>
                {crops.map(x => <option key={x} value={x}>{translateCrop(x, lang)}</option>)}
              </select>
            </Field>
            <Field label={t.cultivationCount || (lang === "hi" ? "हाल में कितनी बार यह फसल उगाई गई" : "Times Grown Recently")}>
              <select value={form.cultivation_count} onChange={e => set("cultivation_count", Number(e.target.value))}>
                <option value={1}>{lang === "hi" ? "1 पहला सीजन / फसल चक्र बदला गया" : "1st season / Rotated"}</option>
                <option value={2}>{lang === "hi" ? "लगातार 2 सीजन" : "2 consecutive seasons"}</option>
                <option value={3}>{lang === "hi" ? "3+ लगातार सीजन (सघन फसल)" : "3+ consecutive seasons (Continuous)"}</option>
              </select>
            </Field>
          </div>
        </div>

        <div style={{display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12}}>
          <div style={{display: "flex", gap: 12}}>
            <button className="button" type="submit" style={{display: "inline-flex", alignItems: "center", gap: 8}}>
              {t.analyzeNutrients || (lang === "hi" ? "मिट्टी एवं पोषक तत्व विश्लेषण करें" : "Analyze Soil & Nutrients")} <ArrowRight size={16}/>
            </button>
            <button
              type="button"
              className="button secondary"
              onClick={(e) => submit(e, "save")}
            >
              {isEditing ? t.saveChanges : t.save}
            </button>
          </div>

          {isEditing && (
            <button type="button" className="button secondary" onClick={() => nav("/dashboard")}>
              {lang === "hi" ? "रद्द करें" : "Cancel"}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

function Field({ label, children }) { return <label className="field"><span>{label}</span>{children}</label>; }

function Recommend() {
  const [lang,,t] = useLang();
  const nav = useNavigate();
  const [farms, setFarms] = useState([]);
  const [farmId, setFarmId] = useState("");
  const [season, setSeason] = useState("rabi");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/farms").then(r => { setFarms(r.data); if (r.data[0]) setFarmId(String(r.data[0].id)); });
  }, []);

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const r = await api.post("/recommendations", { farm_id: Number(farmId), season, budget: 50000, market_preference: "balanced" });
      setData(r.data);
    } catch {
      setError(lang === "hi" ? "सिफारिशें प्राप्त करने में विफल। कृपया खेत विवरण जांचें।" : "Failed to fetch recommendations. Please verify farm data.");
    } finally {
      setLoading(false);
    }
  };

  const plan = async crop => {
    try {
      const r = await api.post("/recommendations/plan", { farm_id: Number(farmId), crop });
      localStorage.setItem("plan", JSON.stringify(r.data));
      nav("/plan");
    } catch {
      alert(lang === "hi" ? "खेती योजना तैयार करने में विफल। कृपया पुनः प्रयास करें।" : "Failed to generate plan. Please try again.");
    }
  };

  return (
    <div className="content">
      <div className="pageTitle">
        <h1>{t.results}</h1>
        <p>{t.recommendDesc || (lang === "hi" ? "सिफारिशें खेत की मिट्टी, सीजन अनुकूलता, सिंचाई सुविधा, फसल चक्र और आर्थिक लाभ को मिलाकर तैयार की जाती हैं।" : "Recommendations combine soil, season, irrigation, crop history and demo economics.")}</p>
      </div>
      {error && <div className="feedbackBanner error"><AlertTriangle size={18}/> {error}</div>}
      <div className="card controls">
        <select value={farmId} onChange={e => setFarmId(e.target.value)}>
          {farms.map(f => <option key={f.id} value={f.id}>{f.name} · {f.area} {f.area_unit}</option>)}
        </select>
        <select value={season} onChange={e => setSeason(e.target.value)}>
          {seasons.map(s => <option key={s} value={s}>{translateSeason(s, lang)}</option>)}
        </select>
        <button className="button" disabled={!farmId || loading} onClick={run}>
          {loading ? (lang === "hi" ? "विश्लेषण किया जा रहा है..." : "Analyzing...") : t.recommend}
        </button>
      </div>

      {data && (
        <>
          <div className="card">
            <h3>{t.nutrients}</h3>
            <div className="nutrients">
              {data.nutrient_analysis.map(n => (
                <div className="nutrient" key={n.nutrient}>
                  <b>{translateNutrient(n.nutrient, lang)}</b>
                  <span className={n.status}>{translateNutrientStatus(n.status, lang)}</span>
                  <small>{n.value == null ? (lang === "hi" ? "प्रयोगशाला मान नहीं" : "No soil-test value") : (lang === "hi" ? `मान: ${n.value}` : `Value: ${n.value}`)}</small>
                  {n.status === "low" && <p>{translateReason(n.suggestion, lang)}</p>}
                </div>
              ))}
            </div>
          </div>

          <div className="recommendGrid">
            {data.recommendations.map((r, i) => (
              <div className={"card cropCard " + (i === 0 ? "best" : "")} key={r.crop}>
                <div className="rank">#{i + 1}</div>
                <h2>{translateCrop(r.crop, lang)}</h2>
                <div className="score">{r.score}%</div>
                <p>{r.duration_days} {lang === "hi" ? "दिन" : "days"} · {translateWater(r.water_requirement, lang)}</p>
                <div className="money">
                  <span>{t.cost || (lang === "hi" ? "लागत" : "Cost")} ₹{r.estimated_cost.toLocaleString()}</span>
                  <span>{t.profit || (lang === "hi" ? "लाभ" : "Profit")} ₹{r.estimated_profit.toLocaleString()}</span>
                </div>
                <ul>{r.reasons.slice(0, 3).map(x => <li key={x}>{translateReason(x, lang)}</li>)}</ul>
                <button className="button" onClick={() => plan(r.crop)}>{t.plan}</button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Plan() {
  const [lang,,t] = useLang();
  const plan = useMemo(() => { try { return JSON.parse(localStorage.getItem("plan")); } catch { return null; } }, []);

  if (!plan) {
    return (
      <div className="content">
        <div className="card empty">
          <h2>{t.noPlanSelected || (lang === "hi" ? "कोई योजना चयनित नहीं है" : "No plan selected")}</h2>
          <Link className="button" to="/recommend">{t.goToRecommendations || (lang === "hi" ? "फसल सिफारिशों पर जाएं" : "Go to recommendations")}</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="content">
      <div className="pageTitle">
        <h1>{translateCrop(plan.crop, lang)} {t.plan}</h1>
        <p>{t.approxDuration || (lang === "hi" ? "अनुमानित फसल अवधि" : "Approximate crop duration")}: {plan.duration_days} {t.days || (lang === "hi" ? "दिन" : "days")}.</p>
      </div>
      <div className="timeline">
        {plan.steps.map((s, i) => (
          <div className="timelineItem" key={s.stage}>
            <div className="dot">{i + 1}</div>
            <div className="card">
              <h3>{translateStage(s.stage, lang)}</h3>
              <ul>{s.actions.map(a => <li key={a}>{translateAction(a, lang)}</li>)}</ul>
            </div>
          </div>
        ))}
      </div>
      <div className="card">
        <h3>{t.nutrients}</h3>
        {plan.nutrient_analysis.map(n => (
          <p key={n.nutrient}>
            <b>{translateNutrient(n.nutrient, lang)}:</b> {translateNutrientStatus(n.status, lang)} — {translateReason(n.suggestion, lang)}
          </p>
        ))}
        <p className="warningText">{translateReason(plan.note, lang)}</p>
      </div>
    </div>
  );
}

function Horticulture() {
  const [lang,,t] = useLang();
  return (
    <div className="content">
      <div className="hero">
        <div>
          <span className="eyebrow">MODULE</span>
          <h1>{t.horticulture}</h1>
          <p>{lang === "hi" ? "फल, सब्जी और फूलों की खेती की योजना इसी फार्म-डेटा इंजन पर उपलब्ध होगी।" : "Fruit, vegetable and flower planning will be added on the same farm-data engine."}</p>
        </div>
      </div>
      <div className="card empty">
        <TreePine size={50}/>
        <h2>{lang === "hi" ? "बागवानी मॉड्यूल की नींव" : "Horticulture module foundation"}</h2>
        <p>{lang === "hi" ? "बागवानी फसलों के लिए खेत की प्रोफाइल, मौसम, पोषक तत्व और अर्थशास्त्र सेवाओं का पुनः उपयोग करें।" : "Reuse the farm profile, weather, nutrient and economics services for horticultural crops."}</p>
      </div>
    </div>
  );
}

function AppContent() {
  return (
    <>
      <PageTitleManager />
      <Routes>
        <Route path="/login" element={<Auth mode="login" onAuth={() => {}}/>}/>
        <Route path="/register" element={<Auth mode="register" onAuth={() => {}}/>}/>
        <Route path="*" element={
          <Protected>
            <Layout>
              <Routes>
                <Route path="/dashboard" element={<Dashboard/>}/>

                {/* Crop Farming Submenu & Detailed Feature Routes */}
                <Route path="/farm" element={<FarmForm/>}/>
                <Route path="/farm/edit/:farmId" element={<FarmForm/>}/>
                <Route path="/crop-farming" element={<FarmForm/>}/>
                <Route path="/crop-farming/soil-nutrients" element={<NutrientAnalysisPage/>}/>
                <Route path="/crop-farming/soil-nutrients/:farmId" element={<NutrientAnalysisPage/>}/>
                <Route path="/crop-farming/fertilizer" element={<FertilizerRecommendationPage/>}/>
                <Route path="/crop-farming/recommendation" element={<Recommend/>}/>
                <Route path="/crop-farming/calendar" element={<FarmerPlanningPage/>}/>
                <Route path="/crop-farming/parali-management" element={<ParaliManagementPage/>}/>
                <Route path="/crop-farming/market-price" element={<MarketPricePage/>}/>
                <Route path="/crop-farming/weather" element={<WeatherPage/>}/>

                {/* Direct & Backward-Compatible Routes */}
                <Route path="/fertilizer" element={<FertilizerRecommendationPage/>}/>
                <Route path="/market-price" element={<MarketPricePage/>}/>
                <Route path="/parali" element={<ParaliManagementPage/>}/>
                <Route path="/parali-management" element={<ParaliManagementPage/>}/>

                <Route path="/nutrient-analysis" element={<NutrientAnalysisPage/>}/>
                <Route path="/nutrient-analysis/:farmId" element={<NutrientAnalysisPage/>}/>
                <Route path="/weather" element={<WeatherPage/>}/>
                <Route path="/recommend" element={<Recommend/>}/>
                <Route path="/plan" element={<FarmerPlanningPage/>}/>
                <Route path="/crop-calendar" element={<FarmerPlanningPage/>}/>
                <Route path="/farmer-plan" element={<FarmerPlanningPage/>}/>

                <Route path="/insurance-planning" element={<InsurancePlanningPage/>}/>
                <Route path="/insurance" element={<InsurancePlanningPage/>}/>
                <Route path="/government-schemes" element={<GovernmentSchemesPage/>}/>
                <Route path="/schemes" element={<GovernmentSchemesPage/>}/>
                <Route path="/horticulture" element={<Horticulture/>}/>
                <Route path="/iot-monitor" element={<IoTMonitorPage/>}/>
                <Route path="/iot" element={<IoTMonitorPage/>}/>
                <Route path="/crop-farming/iot-monitor" element={<IoTMonitorPage/>}/>

                <Route path="*" element={<Navigate to="/dashboard" replace/>}/>
              </Routes>
            </Layout>
          </Protected>
        }/>
      </Routes>
    </>
  );
}

export default function App() {
  const [started, setStarted] = useState(false);

  return (
    <LanguageProvider>
      {!started ? (
        <Splash onDone={() => setStarted(true)} />
      ) : (
        <AppContent />
      )}
    </LanguageProvider>
  );
}
