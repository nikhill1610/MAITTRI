import React, { useState, useEffect, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import {
  IndianRupee, TrendingUp, TrendingDown, Minus, MapPin, Building2,
  Store, Sprout, ArrowUpDown, RefreshCw, AlertTriangle, Info,
  CheckCircle2, Sparkles, SlidersHorizontal, ChevronRight, Calendar,
  Layers, BarChart2, ShieldCheck, Scale, ArrowRight, HelpCircle
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";
import { translateCrop } from "./i18n";

export default function MarketPricePage() {
  const [lang, , t] = useLang();

  // Data states
  const [states, setStates] = useState([]);
  const [districts, setDistricts] = useState([]);
  const [mandis, setMandis] = useState([]);
  const [crops, setCrops] = useState([]);
  const [farms, setFarms] = useState([]);

  // Selection states
  const [selectedState, setSelectedState] = useState("Uttar Pradesh");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [selectedMandi, setSelectedMandi] = useState("");
  const [selectedCrop, setSelectedCrop] = useState("Wheat");
  const [selectedFarmId, setSelectedFarmId] = useState("");

  // Price & Market details
  const [priceData, setPriceData] = useState(null);
  const [otherCrops, setOtherCrops] = useState([]);
  const [historyData, setHistoryData] = useState(null);
  const [trendDays, setTrendDays] = useState(30);
  const [unitMode, setUnitMode] = useState("quintal"); // "quintal" | "kg" | "tonne"
  const [stateComparison, setStateComparison] = useState([]);

  // Multi-crop comparison
  const [compareCropsList, setCompareCropsList] = useState(["Wheat", "Mustard", "Rice"]);
  const [comparedData, setComparedData] = useState([]);

  // Sorting & Filtering for other crops
  const [cropSearch, setCropSearch] = useState("");
  const [sortBy, setSortBy] = useState("modal_desc"); // "modal_desc" | "modal_asc" | "alpha" | "trend"

  // Status states
  const [loadingPrice, setLoadingPrice] = useState(false);
  const [loadingOther, setLoadingOther] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [apiError, setApiError] = useState("");

  // Check if a crop was previously planned in localStorage
  const plannedCrop = useMemo(() => {
    try {
      const p = JSON.parse(localStorage.getItem("plan"));
      return p?.crop || null;
    } catch {
      return null;
    }
  }, []);

  // 1. Initial Data Fetch: States, Crops, Farms
  useEffect(() => {
    // Fetch states
    api.get("/market-prices/states")
      .then(res => {
        if (res.data?.states) setStates(res.data.states);
      })
      .catch(() => {});

    // Fetch crops
    api.get("/market-prices/crops")
      .then(res => {
        if (res.data?.crops) setCrops(res.data.crops);
      })
      .catch(() => {});

    // Fetch user farms to auto-detect location and current crop
    api.get("/farms")
      .then(res => {
        const farmList = res.data || [];
        setFarms(farmList);
        if (farmList.length > 0) {
          const firstFarm = farmList[0];
          setSelectedFarmId(String(firstFarm.id));

          // Auto-detect state from farm location
          if (firstFarm.location_name) {
            const locLower = firstFarm.location_name.toLowerCase();
            api.get("/market-prices/states").then(stRes => {
              const allSt = stRes.data?.states || [];
              const matched = allSt.find(s => locLower.includes(s.toLowerCase()));
              if (matched) {
                setSelectedState(matched);
              }
            }).catch(() => {});
          }

          // Auto-select crop from farm's current crop or recommendation plan
          if (plannedCrop) {
            setSelectedCrop(plannedCrop);
          } else if (firstFarm.current_crop) {
            setSelectedCrop(firstFarm.current_crop);
          }
        } else if (plannedCrop) {
          setSelectedCrop(plannedCrop);
        }
      })
      .catch(() => {});
  }, [plannedCrop]);

  // 2. Fetch districts when state changes
  useEffect(() => {
    if (!selectedState) return;
    api.get(`/market-prices/districts?state=${encodeURIComponent(selectedState)}`)
      .then(res => {
        const dists = res.data?.districts || [];
        setDistricts(dists);
        setSelectedDistrict(""); // Reset district on state change
        setSelectedMandi("");
      })
      .catch(() => setDistricts([]));
  }, [selectedState]);

  // 3. Fetch mandis when district changes
  useEffect(() => {
    if (!selectedState || !selectedDistrict) {
      setMandis([]);
      setSelectedMandi("");
      return;
    }
    api.get(`/market-prices/mandis?state=${encodeURIComponent(selectedState)}&district=${encodeURIComponent(selectedDistrict)}`)
      .then(res => {
        const mList = res.data?.mandis || [];
        setMandis(mList);
        setSelectedMandi("");
      })
      .catch(() => setMandis([]));
  }, [selectedState, selectedDistrict]);

  // 4. Fetch latest market price for selected crop & location
  const fetchPrice = useCallback(() => {
    if (!selectedCrop || !selectedState) return;
    setLoadingPrice(true);
    setApiError("");

    let url = `/market-prices/latest?crop=${encodeURIComponent(selectedCrop)}&state=${encodeURIComponent(selectedState)}`;
    if (selectedDistrict) url += `&district=${encodeURIComponent(selectedDistrict)}`;
    if (selectedMandi) url += `&mandi=${encodeURIComponent(selectedMandi)}`;

    api.get(url)
      .then(res => {
        setPriceData(res.data);
      })
      .catch(err => {
        setPriceData(null);
        if (err.response?.status === 404) {
          setApiError(t.priceUnavailable || (lang === "hi" ? "इस फसल/स्थान के लिए मंडी भाव डेटा वर्तमान में उपलब्ध नहीं है।" : "Market price data is currently unavailable for this crop/location."));
        } else {
          setApiError(t.apiFailed || (lang === "hi" ? "मंडी डेटा इस समय लोड नहीं हो सका।" : "Market data could not be loaded right now."));
        }
      })
      .finally(() => setLoadingPrice(false));
  }, [selectedCrop, selectedState, selectedDistrict, selectedMandi, lang, t]);

  useEffect(() => {
    fetchPrice();
  }, [fetchPrice]);

  // 5. Fetch price history trend
  useEffect(() => {
    if (!selectedCrop || !selectedState) return;
    setLoadingHistory(true);
    let url = `/market-prices/history?crop=${encodeURIComponent(selectedCrop)}&state=${encodeURIComponent(selectedState)}&days=${trendDays}`;
    if (selectedDistrict) url += `&district=${encodeURIComponent(selectedDistrict)}`;
    if (selectedMandi) url += `&mandi=${encodeURIComponent(selectedMandi)}`;

    api.get(url)
      .then(res => setHistoryData(res.data))
      .catch(() => setHistoryData(null))
      .finally(() => setLoadingHistory(false));
  }, [selectedCrop, selectedState, selectedDistrict, selectedMandi, trendDays]);

  // 6. Fetch other crops in state
  useEffect(() => {
    if (!selectedState) return;
    setLoadingOther(true);
    api.get(`/market-prices/state-crops?state=${encodeURIComponent(selectedState)}&selected_crop=${encodeURIComponent(selectedCrop)}`)
      .then(res => setOtherCrops(res.data?.crops || []))
      .catch(() => setOtherCrops([]))
      .finally(() => setLoadingOther(false));
  }, [selectedState, selectedCrop]);

  // 7. Fetch multi-crop comparison
  useEffect(() => {
    if (!selectedState || compareCropsList.length === 0) return;
    setLoadingCompare(true);
    const cropsParam = compareCropsList.join(",");
    api.get(`/market-prices/compare?state=${encodeURIComponent(selectedState)}&crops=${encodeURIComponent(cropsParam)}`)
      .then(res => setComparedData(res.data?.compared_crops || []))
      .catch(() => setComparedData([]))
      .finally(() => setLoadingCompare(false));
  }, [selectedState, compareCropsList]);

  // 8. Fetch state-wise comparison for selected crop
  useEffect(() => {
    if (!selectedCrop) return;
    api.get(`/market-prices/state-comparison?crop=${encodeURIComponent(selectedCrop)}`)
      .then(res => setStateComparison(res.data?.states || []))
      .catch(() => setStateComparison([]));
  }, [selectedCrop]);

  // Active farm data for profit calculation
  const activeFarm = useMemo(() => {
    if (!selectedFarmId) return farms[0] || null;
    return farms.find(f => String(f.id) === String(selectedFarmId)) || null;
  }, [farms, selectedFarmId]);

  // Unit conversion helper
  const convertPrice = useCallback((pricePerQuintal, targetUnit) => {
    if (pricePerQuintal === undefined || pricePerQuintal === null) return null;
    if (targetUnit === "kg") {
      return (pricePerQuintal / 100).toFixed(2);
    }
    if (targetUnit === "tonne") {
      return (pricePerQuintal * 10).toLocaleString("en-IN");
    }
    return pricePerQuintal.toLocaleString("en-IN");
  }, []);

  const getUnitLabel = useCallback((targetUnit) => {
    if (targetUnit === "kg") return lang === "hi" ? "₹ / किग्रा" : "₹ / kg";
    if (targetUnit === "tonne") return lang === "hi" ? "₹ / टन" : "₹ / tonne";
    return lang === "hi" ? "₹ / क्विंटल" : "₹ / quintal";
  }, [lang]);

  // Filter and sort other crops
  const filteredOtherCrops = useMemo(() => {
    let list = [...otherCrops];
    if (cropSearch.trim()) {
      const q = cropSearch.toLowerCase().trim();
      list = list.filter(c => c.crop.toLowerCase().includes(q));
    }
    if (sortBy === "modal_desc") {
      list.sort((a, b) => b.modal_price - a.modal_price);
    } else if (sortBy === "modal_asc") {
      list.sort((a, b) => a.modal_price - b.modal_price);
    } else if (sortBy === "alpha") {
      list.sort((a, b) => a.crop.localeCompare(b.crop));
    } else if (sortBy === "trend") {
      const rank = { up: 3, stable: 2, down: 1 };
      list.sort((a, b) => (rank[b.trend] || 0) - (rank[a.trend] || 0));
    }
    return list;
  }, [otherCrops, cropSearch, sortBy]);

  // Toggle crop in compare list
  const toggleCompareCrop = (cropName) => {
    if (compareCropsList.includes(cropName)) {
      if (compareCropsList.length > 2) {
        setCompareCropsList(compareCropsList.filter(c => c !== cropName));
      }
    } else {
      if (compareCropsList.length < 5) {
        setCompareCropsList([...compareCropsList, cropName]);
      }
    }
  };

  // SVG Chart rendering helper
  const renderTrendChart = () => {
    if (!historyData || !historyData.available || !historyData.series || historyData.series.length < 2) {
      return (
        <div className="marketEmptyChart">
          <Info size={32} />
          <p>{t.historicalUnavailable || (lang === "hi" ? "ऐतिहासिक भाव डेटा वर्तमान में उपलब्ध नहीं है।" : "Historical price data is currently unavailable.")}</p>
        </div>
      );
    }

    const series = historyData.series;
    const prices = series.map(s => s.modal_price);
    const minP = Math.min(...prices) * 0.96;
    const maxP = Math.max(...prices) * 1.04;
    const rangeP = maxP - minP || 1;

    const width = 680;
    const height = 240;
    const padX = 50;
    const padY = 30;
    const chartW = width - padX * 2;
    const chartH = height - padY * 2;

    const points = series.map((s, idx) => {
      const x = padX + (idx / (series.length - 1)) * chartW;
      const y = padY + chartH - ((s.modal_price - minP) / rangeP) * chartH;
      return { x, y, price: s.modal_price, date: s.date };
    });

    const pathD = points.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`, "");
    const areaD = `${pathD} L ${points[points.length - 1].x.toFixed(1)} ${height - padY} L ${points[0].x.toFixed(1)} ${height - padY} Z`;

    const avgPrice = Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
    const avgY = padY + chartH - ((avgPrice - minP) / rangeP) * chartH;

    return (
      <div className="marketChartWrapper">
        <svg viewBox={`0 0 ${width} ${height}`} className="marketTrendSvg" preserveAspectRatio="none">
          <defs>
            <linearGradient id="marketAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22c55e" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#22c55e" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={padX} y1={padY} x2={width - padX} y2={padY} stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
          <line x1={padX} y1={padY + chartH / 2} x2={width - padX} y2={padY + chartH / 2} stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
          <line x1={padX} y1={height - padY} x2={width - padX} y2={height - padY} stroke="rgba(255,255,255,0.15)" />

          {/* Average reference line */}
          <line x1={padX} y1={avgY} x2={width - padX} y2={avgY} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth="1.2" opacity="0.6" />

          {/* Area fill */}
          <path d={areaD} fill="url(#marketAreaGradient)" />

          {/* Line stroke */}
          <path d={pathD} fill="none" stroke="#22c55e" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data Points */}
          {points.map((pt, i) => (
            <g key={i} className="chartNodeGroup">
              <circle cx={pt.x} cy={pt.y} r="4" fill="#22c55e" stroke="#0f291e" strokeWidth="2" />
            </g>
          ))}
        </svg>

        {/* Axis Labels */}
        <div className="marketChartLabels">
          <span>{series[0].date}</span>
          <span className="avgLabel">
            <span className="avgDot"></span> {lang === "hi" ? "औसत" : "Avg"}: ₹{avgPrice.toLocaleString("en-IN")}/q
          </span>
          <span>{series[series.length - 1].date}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="content marketPricePage">
      {/* 1. Page Header */}
      <div className="marketHeader">
        <div className="marketHeaderContent">
          <div className="marketBadge">
            <BarChart2 size={16} />
            <span>{lang === "hi" ? "आधिकारिक मंडी भाव" : "Official Mandi Intelligence"}</span>
          </div>
          <h1>{t.marketPriceTitle || (lang === "hi" ? "कृषि मंडी भाव एवं बाज़ार विश्लेषण" : "Agricultural Market Prices")}</h1>
          <p className="marketSubtitle">
            {t.marketPriceSubtitle || (lang === "hi" ? "बुवाई से पहले बाज़ार का भाव जानें — प्रामाणिक मंडी भाव एवं रुझान" : "Know the market before you sow — authentic mandi prices & trend intelligence")}
          </p>
        </div>

        {/* Quick Location & Farm info pill */}
        {activeFarm && (
          <div className="marketFarmPill">
            <MapPin size={16} />
            <div>
              <small>{lang === "hi" ? "सक्रिय खेत" : "Active Farm"}</small>
              <strong>{activeFarm.name} ({activeFarm.area} {activeFarm.area_unit})</strong>
            </div>
          </div>
        )}
      </div>

      {/* 2. State, District & Mandi Selection Toolbar */}
      <div className="card marketToolbarCard">
        <div className="marketToolbarGrid">
          {/* State Selection */}
          <div className="marketSelectGroup">
            <label>
              <MapPin size={15} />
              <span>{t.selectState || (lang === "hi" ? "अपना राज्य चुनें" : "Select Your State")}</span>
              <strong className="requiredStar">*</strong>
            </label>
            <select
              value={selectedState}
              onChange={e => setSelectedState(e.target.value)}
              className="marketSelect"
            >
              {states.map(st => (
                <option key={st} value={st}>{st}</option>
              ))}
            </select>
          </div>

          {/* District Selection (Optional) */}
          <div className="marketSelectGroup">
            <label>
              <Building2 size={15} />
              <span>{t.selectDistrict || (lang === "hi" ? "ज़िला चुनें (वैकल्पिक)" : "Select District (Optional)")}</span>
            </label>
            <select
              value={selectedDistrict}
              onChange={e => setSelectedDistrict(e.target.value)}
              className="marketSelect"
              disabled={districts.length === 0}
            >
              <option value="">{lang === "hi" ? "— सभी ज़िले / राज्य औसत —" : "— All Districts / State Average —"}</option>
              {districts.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          {/* Mandi Selection (Optional) */}
          <div className="marketSelectGroup">
            <label>
              <Store size={15} />
              <span>{t.selectMandi || (lang === "hi" ? "मंडी / बाज़ार चुनें (वैकल्पिक)" : "Select Mandi / Market (Optional)")}</span>
            </label>
            <select
              value={selectedMandi}
              onChange={e => setSelectedMandi(e.target.value)}
              className="marketSelect"
              disabled={mandis.length === 0}
            >
              <option value="">{lang === "hi" ? "— प्रमुख मंडी / बेंचमार्क —" : "— Major Mandi / Benchmark —"}</option>
              {mandis.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Mandi-level data notice when applicable */}
        {selectedDistrict && mandis.length === 0 && (
          <div className="marketNoticePill">
            <Info size={15} />
            <span>{t.mandiDataUnavailable || (lang === "hi" ? "मंडी-स्तरीय डेटा वर्तमान में उपलब्ध नहीं है। उपलब्ध राज्य/बाज़ार डेटा दिखाया जा रहा है।" : "Mandi-level data is currently unavailable. Showing available state/market data.")}</span>
          </div>
        )}
      </div>

      {/* 3. Crop Planning Selection */}
      <div className="card marketCropSelectCard">
        <div className="marketCropHeader">
          <div className="marketCropTitleGroup">
            <Sprout size={20} className="greenIcon" />
            <div>
              <h3>{t.cropPlanningToGrow || (lang === "hi" ? "आप कौन सी फसल उगाने की योजना बना रहे हैं?" : "Which crop are you planning to grow?")}</h3>
              <p>{lang === "hi" ? "नीचे दी गई फसलों में से चुनें या अपनी फसल बदलें" : "Select from tracked crops or switch to compare pricing"}</p>
            </div>
          </div>

          {plannedCrop && plannedCrop.toLowerCase() === selectedCrop.toLowerCase() && (
            <span className="recommendedBadge">
              <Sparkles size={13} /> {lang === "hi" ? "सिफारिश की गई फसल" : "Recommended Crop"}
            </span>
          )}
        </div>

        <div className="marketCropChips">
          {crops.map(c => {
            const isSelected = selectedCrop.toLowerCase() === c.toLowerCase();
            return (
              <button
                key={c}
                type="button"
                onClick={() => setSelectedCrop(c)}
                className={`marketCropChip ${isSelected ? "active" : ""}`}
              >
                <span>{translateCrop(c, lang)}</span>
                {plannedCrop && plannedCrop.toLowerCase() === c.toLowerCase() && (
                  <span className="chipRecDot" title="Recommended Crop">★</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* API Error / No Data State with Retry */}
      {apiError && (
        <div className="card marketErrorCard">
          <AlertTriangle size={24} className="warnIcon" />
          <div>
            <h4>{apiError}</h4>
            <p>{lang === "hi" ? "कृपया राज्य या ज़िला बदलकर देखें, या पुनः प्रयास करें।" : "Please try changing the state or district, or click retry."}</p>
          </div>
          <button onClick={fetchPrice} className="button secondary retryBtn">
            <RefreshCw size={15} /> {lang === "hi" ? "पुनः प्रयास करें" : "Retry"}
          </button>
        </div>
      )}

      {/* 4. PROMINENT HERO PRICE CARD */}
      {loadingPrice ? (
        <div className="card marketHeroCard loading">
          <div className="marketSkeletonTitle"></div>
          <div className="marketSkeletonPrice"></div>
          <div className="marketSkeletonGrid"></div>
        </div>
      ) : priceData ? (
        <div className="card marketHeroCard">
          {/* Top Card Bar */}
          <div className="marketHeroTop">
            <div className="marketCropName">
              <span className="cropIconBadge">🌾</span>
              <div>
                <h2>{translateCrop(priceData.crop, lang)}</h2>
                <div className="marketLocBadges">
                  <span className="locBadge"><MapPin size={13} /> {priceData.state}</span>
                  {priceData.district && <span className="locBadge"><Building2 size={13} /> {priceData.district}</span>}
                  {priceData.market && <span className="locBadge mandi"><Store size={13} /> {priceData.market}</span>}
                </div>
              </div>
            </div>

            {/* Unit Switcher */}
            <div className="marketUnitSwitcher">
              <span className="unitLabel">{t.unit || (lang === "hi" ? "इकाई" : "Unit")}:</span>
              <div className="unitPillGroup">
                <button
                  className={`unitPill ${unitMode === "quintal" ? "active" : ""}`}
                  onClick={() => setUnitMode("quintal")}
                >
                  ₹/q
                </button>
                <button
                  className={`unitPill ${unitMode === "kg" ? "active" : ""}`}
                  onClick={() => setUnitMode("kg")}
                >
                  ₹/kg
                </button>
                <button
                  className={`unitPill ${unitMode === "tonne" ? "active" : ""}`}
                  onClick={() => setUnitMode("tonne")}
                >
                  ₹/t
                </button>
              </div>
            </div>
          </div>

          {/* Main Price Highlight */}
          <div className="marketPriceCenter">
            <div className="marketPriceBig">
              <span className="priceCurrency">₹</span>
              <span className="priceNumber">
                {convertPrice(priceData.price.modal, unitMode)}
              </span>
              <span className="pricePerUnit">
                / {unitMode === "quintal" ? (lang === "hi" ? "क्विंटल" : "quintal") : unitMode === "kg" ? (lang === "hi" ? "किग्रा" : "kg") : (lang === "hi" ? "टन" : "tonne")}
              </span>
            </div>

            {/* Price Change Pill */}
            {priceData.price_change && (
              <div className={`marketChangePill ${priceData.price_change.trend}`}>
                {priceData.price_change.trend === "increasing" && <TrendingUp size={16} />}
                {priceData.price_change.trend === "decreasing" && <TrendingDown size={16} />}
                {priceData.price_change.trend === "stable" && <Minus size={16} />}
                <span>
                  {priceData.price_change.amount > 0 ? `+₹${priceData.price_change.amount}` : `₹${priceData.price_change.amount}`} / q
                  ({priceData.price_change.percentage > 0 ? `+${priceData.price_change.percentage}%` : `${priceData.price_change.percentage}%`})
                </span>
                <small>• {priceData.price_change.trend === "increasing" ? (lang === "hi" ? "बढ़ता हुआ" : "Increasing") : priceData.price_change.trend === "decreasing" ? (lang === "hi" ? "घटता हुआ" : "Decreasing") : (lang === "hi" ? "स्थिर" : "Stable")}</small>
              </div>
            )}
          </div>

          {/* 3 Price Metrics: Min, Modal, Max clearly labeled */}
          <div className="marketTripleMetrics">
            <div className="metricBox min">
              <span className="boxLabel">{t.minPrice || (lang === "hi" ? "न्यूनतम भाव" : "Minimum Price")}</span>
              <strong className="boxVal">₹{convertPrice(priceData.price.min, unitMode)}</strong>
              <small>{getUnitLabel(unitMode)}</small>
            </div>
            <div className="metricBox modal">
              <span className="boxLabel">{t.modalPrice || (lang === "hi" ? "मॉडल भाव (औसत)" : "Modal Price")}</span>
              <strong className="boxVal highlight">₹{convertPrice(priceData.price.modal, unitMode)}</strong>
              <small>{getUnitLabel(unitMode)}</small>
            </div>
            <div className="metricBox max">
              <span className="boxLabel">{t.maxPrice || (lang === "hi" ? "अधिकतम भाव" : "Maximum Price")}</span>
              <strong className="boxVal">₹{convertPrice(priceData.price.max, unitMode)}</strong>
              <small>{getUnitLabel(unitMode)}</small>
            </div>
          </div>

          {/* Metadata Footer */}
          <div className="marketHeroMeta">
            <div className="metaItem">
              <Calendar size={14} />
              <span>{t.latestAvailablePrice || (lang === "hi" ? "नवीनतम उपलब्ध" : "Latest Available")}: <b>{priceData.date}</b></span>
            </div>
            <div className="metaItem">
              <Store size={14} />
              <span>{lang === "hi" ? "मंडी" : "Market"}: <b>{priceData.market}</b></span>
            </div>
            <div className="metaItem">
              <ShieldCheck size={14} />
              <span>{lang === "hi" ? "स्रोत" : "Source"}: <b>{priceData.source}</b></span>
            </div>
            <div className="metaItem freshnessBadge">
              <CheckCircle2 size={13} />
              <span>{lang === "hi" ? "सत्यापित डेटा" : "Verified Data"}</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* 5. PRICE TREND SECTION (Responsive SVG Chart) */}
      <div className="card marketTrendCard">
        <div className="marketCardHeaderWithTabs">
          <div className="titleWithIcon">
            <TrendingUp size={20} className="greenIcon" />
            <div>
              <h3>{t.priceTrend || (lang === "hi" ? "भाव का ऐतिहासिक रुझान" : "Price Trend")}</h3>
              <p>{lang === "hi" ? "विगत दिनों में मॉडल भाव के उतार-चढ़ाव का विश्लेषण" : "Historical modal price fluctuations and volatility"}</p>
            </div>
          </div>

          <div className="marketTrendTabs">
            {[7, 30, 90, 180].map(d => (
              <button
                key={d}
                className={`trendTab ${trendDays === d ? "active" : ""}`}
                onClick={() => setTrendDays(d)}
              >
                {d <= 30 ? `${d} ${lang === "hi" ? "दिन" : "Days"}` : `${d / 30} ${lang === "hi" ? "माह" : "Months"}`}
              </button>
            ))}
          </div>
        </div>

        {loadingHistory ? (
          <div className="marketSkeletonChart"></div>
        ) : (
          renderTrendChart()
        )}
      </div>

      {/* 6. OTHER CROP MARKET PRICES IN SELECTED STATE */}
      <div className="card marketOtherCropsCard">
        <div className="otherCropsHeader">
          <div>
            <h3>{t.otherCropsInState || (lang === "hi" ? "राज्य में अन्य फसलों के मंडी भाव" : "Other Crop Market Prices")}</h3>
            <p>{lang === "hi" ? `राज्य: ${selectedState} — अन्य उपलब्ध फसलों से तुलना करें` : `State: ${selectedState} — Compare with other available crops in this region`}</p>
          </div>

          <div className="otherCropsControls">
            <input
              type="text"
              placeholder={lang === "hi" ? "फसल खोजें..." : "Search crops..."}
              value={cropSearch}
              onChange={e => setCropSearch(e.target.value)}
              className="marketSearchInput"
            />
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value)}
              className="marketSortSelect"
            >
              <option value="modal_desc">{lang === "hi" ? "उच्चतम भाव पहले" : "Highest Price First"}</option>
              <option value="modal_asc">{lang === "hi" ? "न्यूनतम भाव पहले" : "Lowest Price First"}</option>
              <option value="alpha">{lang === "hi" ? "वर्णानुक्रम" : "Alphabetical"}</option>
              <option value="trend">{lang === "hi" ? "रुझान के अनुसार" : "By Price Trend"}</option>
            </select>
          </div>
        </div>

        {loadingOther ? (
          <div className="marketSkeletonList"></div>
        ) : filteredOtherCrops.length === 0 ? (
          <p className="emptyNotice">{lang === "hi" ? "कोई अन्य फसल नहीं मिली।" : "No other crop prices found."}</p>
        ) : (
          <div className="marketOtherTableResponsive">
            <table className="marketTable">
              <thead>
                <tr>
                  <th>{lang === "hi" ? "फसल" : "Crop"}</th>
                  <th>{t.modalPrice || (lang === "hi" ? "मॉडल भाव" : "Modal Price")}</th>
                  <th>{lang === "hi" ? "न्यूनतम — अधिकतम" : "Min — Max"}</th>
                  <th>{lang === "hi" ? "मंडी" : "Market"}</th>
                  <th>{lang === "hi" ? "दिनांक" : "Date"}</th>
                  <th>{lang === "hi" ? "रुझान" : "Trend"}</th>
                  <th>{lang === "hi" ? "कार्रवाई" : "Action"}</th>
                </tr>
              </thead>
              <tbody>
                {filteredOtherCrops.map(item => {
                  const isSelected = selectedCrop.toLowerCase() === item.crop.toLowerCase();
                  return (
                    <tr key={item.crop} className={isSelected ? "selectedCropRow" : ""}>
                      <td>
                        <div className="cropCell">
                          <strong>{translateCrop(item.crop, lang)}</strong>
                          {isSelected && (
                            <span className="selectedCropPill">
                              {t.selectedCropBadge || (lang === "hi" ? "आपकी चयनित फसल" : "SELECTED CROP")}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className="priceCellBig">₹{item.modal_price.toLocaleString("en-IN")}</span>
                        <small className="unitSmall">/q</small>
                      </td>
                      <td>
                        <span className="rangeText">₹{item.min_price} — ₹{item.max_price}</span>
                      </td>
                      <td>{item.market || selectedState}</td>
                      <td>{item.date}</td>
                      <td>
                        <span className={`trendTag ${item.trend}`}>
                          {item.trend === "up" ? "↑ " : item.trend === "down" ? "↓ " : "→ "}
                          {item.trend === "up" ? (lang === "hi" ? "बढ़त" : "Up") : item.trend === "down" ? (lang === "hi" ? "घटत" : "Down") : (lang === "hi" ? "स्थिर" : "Stable")}
                          {item.pct_change ? ` (${item.pct_change > 0 ? `+${item.pct_change}%` : `${item.pct_change}%`})` : ""}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="tableSelectBtn"
                          onClick={() => {
                            setSelectedCrop(item.crop);
                            window.scrollTo({ top: 120, behavior: "smooth" });
                          }}
                        >
                          {isSelected ? (lang === "hi" ? "सक्रिय" : "Active") : (lang === "hi" ? "भाव देखें" : "View Price")}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 7. COMPARE CROPS TOOL (2 to 5 Crops) */}
      <div className="card marketCompareCard">
        <div className="compareHeader">
          <div className="titleWithIcon">
            <Scale size={20} className="greenIcon" />
            <div>
              <h3>{t.compareCropsTitle || (lang === "hi" ? "फसलों की तुलना करें" : "Compare Crops")}</h3>
              <p>{t.compareCropsSubtitle || (lang === "hi" ? "वर्तमान मॉडल भाव, मूल्य सीमा और रुझान की तुलना के लिए 2 से 5 फसलें चुनें" : "Select 2 to 5 crops to compare current modal prices, ranges, and trends")}</p>
            </div>
          </div>

          <div className="compareSelectedCount">
            <span>{compareCropsList.length} / 5 {lang === "hi" ? "चयनित" : "Selected"}</span>
          </div>
        </div>

        {/* Multi-Select Chips */}
        <div className="compareChipsSelector">
          {crops.map(c => {
            const isChecked = compareCropsList.includes(c);
            return (
              <button
                key={c}
                type="button"
                onClick={() => toggleCompareCrop(c)}
                className={`compareChip ${isChecked ? "checked" : ""}`}
              >
                <span>{isChecked ? "✓ " : "+ "}{translateCrop(c, lang)}</span>
              </button>
            );
          })}
        </div>

        {/* Comparison Matrix Table */}
        {loadingCompare ? (
          <div className="marketSkeletonList"></div>
        ) : comparedData.length > 0 ? (
          <div className="marketOtherTableResponsive">
            <table className="marketTable compareTable">
              <thead>
                <tr>
                  <th>{lang === "hi" ? "फसल" : "Crop"}</th>
                  <th>{t.modalPrice || (lang === "hi" ? "मॉडल भाव" : "Modal Price")}</th>
                  <th>{t.minPrice || (lang === "hi" ? "न्यूनतम" : "Minimum")}</th>
                  <th>{t.maxPrice || (lang === "hi" ? "अधिकतम" : "Maximum")}</th>
                  <th>{lang === "hi" ? "मंडी / बाज़ार" : "Market"}</th>
                  <th>{lang === "hi" ? "दिनांक" : "Date"}</th>
                  <th>{lang === "hi" ? "30-दिन रुझान" : "30-Day Trend"}</th>
                </tr>
              </thead>
              <tbody>
                {comparedData.map(c => (
                  <tr key={c.crop} className={selectedCrop.toLowerCase() === c.crop.toLowerCase() ? "selectedCropRow" : ""}>
                    <td>
                      <strong>{translateCrop(c.crop, lang)}</strong>
                    </td>
                    <td>
                      <b className="priceCellBig">₹{c.modal_price.toLocaleString("en-IN")}</b> /q
                    </td>
                    <td>₹{c.min_price}</td>
                    <td>₹{c.max_price}</td>
                    <td>{c.market}</td>
                    <td>{c.date}</td>
                    <td>
                      <span className={`trendTag ${c.trend}`}>
                        {c.trend === "up" ? "↑ " : c.trend === "down" ? "↓ " : "→ "}
                        {c.trend === "up" ? (lang === "hi" ? "बढ़त" : "Increasing") : c.trend === "down" ? (lang === "hi" ? "घटत" : "Decreasing") : (lang === "hi" ? "स्थिर" : "Stable")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      {/* 8. STATE-WISE PRICE COMPARISON */}
      <div className="card marketStateCompCard">
        <div className="titleWithIcon">
          <MapPin size={20} className="greenIcon" />
          <div>
            <h3>{t.stateWiseTitle || (lang === "hi" ? "राज्यवार भाव तुलना" : "State-Wise Price Comparison")}: {translateCrop(selectedCrop, lang)}</h3>
            <p>{t.stateWiseSubtitle || (lang === "hi" ? "उपलब्ध आधिकारिक आंकड़ों के आधार पर विभिन्न राज्यों में इस फसल के भाव देखें" : "Compare prices for this crop across different Indian states with available data")}</p>
          </div>
        </div>

        {stateComparison.length === 0 ? (
          <p className="emptyNotice">{lang === "hi" ? "इस फसल के लिए अंतर्राज्यीय डेटा लोड हो रहा है..." : "Loading state-wise data..."}</p>
        ) : (
          <div className="marketOtherTableResponsive">
            <table className="marketTable">
              <thead>
                <tr>
                  <th>{lang === "hi" ? "राज्य" : "State"}</th>
                  <th>{t.modalPrice || (lang === "hi" ? "मॉडल भाव" : "Modal Price")}</th>
                  <th>{lang === "hi" ? "न्यूनतम — अधिकतम" : "Min — Max"}</th>
                  <th>{lang === "hi" ? "प्रतिनिधि मंडी" : "Representative Mandi"}</th>
                  <th>{lang === "hi" ? "दिनांक" : "Date"}</th>
                </tr>
              </thead>
              <tbody>
                {stateComparison.map(sItem => {
                  const isCurrentState = selectedState.toLowerCase() === sItem.state.toLowerCase();
                  return (
                    <tr key={sItem.state} className={isCurrentState ? "selectedCropRow" : ""}>
                      <td>
                        <strong>{sItem.state}</strong>
                        {isCurrentState && <span className="selectedCropPill">{lang === "hi" ? "आपका राज्य" : "Selected State"}</span>}
                      </td>
                      <td>
                        <b className="priceCellBig">₹{sItem.modal_price.toLocaleString("en-IN")}</b> /q
                      </td>
                      <td>₹{sItem.min_price} — ₹{sItem.max_price}</td>
                      <td>{sItem.market}</td>
                      <td>{sItem.date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="marketExplanationNote">
          <Info size={15} />
          <span>{lang === "hi" ? "नोट: कीमतें मंडी, गुणवत्ता, ग्रेड, परिवहन लागत, स्थानीय मांग और तारीख के अनुसार भिन्न हो सकती हैं। उच्चतम राज्य भाव का अर्थ यह नहीं है कि सभी किसान उसी भाव पर बेच सकते हैं।" : "Note: Prices vary by mandi, quality, grade, transportation, demand and date. A higher price in another state does not imply a farmer can realize that exact net price."}</span>
        </div>
      </div>

      {/* 9. ESTIMATED REVENUE & FARM PROFIT INTEGRATION */}
      {activeFarm && priceData && (
        <div className="card marketProfitCard">
          <div className="titleWithIcon">
            <IndianRupee size={20} className="greenIcon" />
            <div>
              <h3>{t.revenueProfitTitle || (lang === "hi" ? "अनुमानित उत्पादन एवं आय प्रक्षेपण" : "Estimated Production & Revenue Projection")}</h3>
              <p>{t.revenueProfitSubtitle || (lang === "hi" ? "आपके पंजीकृत खेत के क्षेत्रफल, अनुमानित उपज और सांकेतिक मंडी भाव पर आधारित" : "Based on your registered farm area, typical yield, and indicative market price")}</p>
            </div>
          </div>

          <div className="profitMetricsGrid">
            <div className="profitBox">
              <span className="profitLabel">{lang === "hi" ? "खेत का क्षेत्रफल" : "Farm Area"}</span>
              <strong className="profitVal">{activeFarm.area} {activeFarm.area_unit}</strong>
            </div>

            <div className="profitBox">
              <span className="profitLabel">{t.expectedProduction || (lang === "hi" ? "अनुमानित उत्पादन" : "Expected Production")}</span>
              <strong className="profitVal">
                {Math.round(activeFarm.area * (selectedCrop.toLowerCase() === "potato" ? 90 : selectedCrop.toLowerCase() === "tomato" ? 120 : 18))} {lang === "hi" ? "क्विंटल" : "quintals"}
              </strong>
              <small>({lang === "hi" ? "अनुमानित उपज दर पर" : "at standard yield"})</small>
            </div>

            <div className="profitBox">
              <span className="profitLabel">{t.grossRevenue || (lang === "hi" ? "अनुमानित सकल आय" : "Estimated Gross Revenue")}</span>
              <strong className="profitVal green">
                ₹{Math.round(
                  activeFarm.area *
                  (selectedCrop.toLowerCase() === "potato" ? 90 : selectedCrop.toLowerCase() === "tomato" ? 120 : 18) *
                  priceData.price.modal
                ).toLocaleString("en-IN")}
              </strong>
              <small>{lang === "hi" ? "उत्पादन × मॉडल भाव" : "Production × Modal Price"}</small>
            </div>

            <div className="profitBox">
              <span className="profitLabel">{t.netProfit || (lang === "hi" ? "अनुमानित शुद्ध लाभ" : "Estimated Net Profit")}</span>
              <strong className="profitVal highlight">
                ₹{Math.max(0, Math.round(
                  activeFarm.area *
                  (selectedCrop.toLowerCase() === "potato" ? 90 : selectedCrop.toLowerCase() === "tomato" ? 120 : 18) *
                  priceData.price.modal -
                  (activeFarm.area * 22000)
                )).toLocaleString("en-IN")}
              </strong>
              <small>{lang === "hi" ? "सकल आय - अनुमानित लागत" : "Gross Revenue - Estimated Cost"}</small>
            </div>
          </div>

          <div className="profitDisclaimer">
            <AlertTriangle size={14} className="warnIcon" />
            <span>
              {lang === "hi"
                ? "महत्वपूर्ण: यह केवल एक सांकेतिक आर्थिक अनुमान है। वास्तविक शुद्ध आय मौसम, कीट-रोग, फसल की गुणवत्ता, मंडी कमीशन एवं परिवहन पर निर्भर करती है।"
                : "Important: This is strictly an indicative planning estimate and not guaranteed earnings. Actual realization depends on seasonal weather, inputs, grading, and mandi market conditions."}
            </span>
          </div>
        </div>
      )}

      {/* 10. REALIZED PRICE VS MARKET PRICE ADVISORY */}
      <div className="card marketAdvisoryCard">
        <div className="titleWithIcon">
          <HelpCircle size={20} className="greenIcon" />
          <div>
            <h3>{t.realizedPriceAdvisory || (lang === "hi" ? "मंडी भाव बनाम किसान को मिलने वाला वास्तविक मूल्य" : "Market Price vs Farmer's Realized Price")}</h3>
            <p>{t.actualPriceDiffers || (lang === "hi" ? "फसल की गुणवत्ता, ग्रेड, नमी, परिवहन, आढ़त और स्थानीय आवक के आधार पर वास्तविक बिक्री मूल्य प्रदर्शित मंडी भाव से भिन्न हो सकता है।" : "Actual selling price may differ from the displayed market price depending on crop quality, grade, moisture, transport, commission and local arrivals.")}</p>
          </div>
        </div>

        <div className="factorsGrid">
          <div className="factorCard">
            <span className="factorNumber">1</span>
            <strong>{lang === "hi" ? "नमी की मात्रा" : "Moisture Content"}</strong>
            <p>{lang === "hi" ? "मानक से अधिक नमी होने पर मंडी व्यापारी मूल्य में कटौती करते हैं।" : "Grain with moisture above specified standards receives price deductions."}</p>
          </div>

          <div className="factorCard">
            <span className="factorNumber">2</span>
            <strong>{lang === "hi" ? "ग्रेड व दाने का आकार" : "Grade & Grain Quality"}</strong>
            <p>{lang === "hi" ? "बोल्ड व एकसमान दाने को मॉडल भाव से अधिक, जबकि मिश्रित को कम मूल्य मिलता है।" : "Bold, uniform grains fetch premium prices; shriveled grains sell lower."}</p>
          </div>

          <div className="factorCard">
            <span className="factorNumber">3</span>
            <strong>{lang === "hi" ? "परिवहन व आढ़त" : "Transport & Mandi Fee"}</strong>
            <p>{lang === "hi" ? "खेत से मंडी तक ढुलाई, तुलाई और आढ़त किसान के शुद्ध लाभ को प्रभावित करते हैं।" : "Freight, weighing, loading, and market cess deduct from net realization."}</p>
          </div>

          <div className="factorCard">
            <span className="factorNumber">4</span>
            <strong>{lang === "hi" ? "सीजन व दैनिक आवक" : "Peak Seasonal Arrivals"}</strong>
            <p>{lang === "hi" ? "कटाई के तुरंत बाद अत्यधिक आवक होने पर हाजिर भाव गिर सकते हैं।" : "Heavy arrivals immediately post-harvest can temporarily depress spot prices."}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
