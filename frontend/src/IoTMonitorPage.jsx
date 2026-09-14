import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Radio, Wifi, WifiOff, Thermometer, Droplets, Sprout, Target,
  AlertTriangle, ShieldCheck, ShieldAlert, RefreshCw, Play, Settings,
  Cpu, Activity, CheckCircle2, ChevronRight, Info, Eye, ExternalLink,
  Copy, Check
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";

export default function IoTMonitorPage() {
  const [lang,, t] = useLang();

  // State
  const [telemetry, setTelemetry] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState("MAITRI_ESP32_01");
  const [loading, setLoading] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [showPinout, setShowPinout] = useState(false);
  const [thresholds, setThresholds] = useState({
    clear_distance: 100.0,
    warning_distance: 50.0,
    critical_distance: 20.0,
    offline_timeout_seconds: 45
  });
  const [feedback, setFeedback] = useState("");
  const [copiedUrl, setCopiedUrl] = useState("");
  const [showLanHelp, setShowLanHelp] = useState(false);

  const handleCopyUrl = (url) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(url);
    }
    setCopiedUrl(url);
    setTimeout(() => setCopiedUrl(""), 3000);
  };

  // Sweep animation angle for radar display
  const [sweepAngle, setSweepAngle] = useState(90);
  const sweepDirRef = useRef(1);

  // Fetch device list
  const fetchDevices = async () => {
    try {
      const res = await api.get("/iot/devices");
      if (res.data && res.data.length > 0) {
        setDevices(res.data);
        const onlineDevice = res.data.find((d) => d.is_online);
        if (onlineDevice && selectedDevice !== onlineDevice.device_id) {
          setSelectedDevice(onlineDevice.device_id);
        }
      }
    } catch {
      // Fallback
    }
  };

  // Fetch latest telemetry
  const fetchLatestTelemetry = async (devId = selectedDevice) => {
    try {
      const res = await api.get("/iot/latest", {
        params: devId ? { device_id: devId } : {}
      });
      if (res.data) {
        setTelemetry(res.data);
        if (res.data.device_id && selectedDevice !== res.data.device_id) {
          setSelectedDevice(res.data.device_id);
        }
        if (res.data.thresholds) {
          setThresholds(res.data.thresholds);
        }
      }
    } catch (err) {
      console.error("Failed to fetch IoT telemetry:", err);
    }
  };

  // Initial load
  useEffect(() => {
    fetchDevices();
    fetchLatestTelemetry();
  }, [selectedDevice]);

  // Polling loop (every 3 seconds)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchLatestTelemetry();
      fetchDevices();
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, selectedDevice]);

  // Animated sweep beam effect
  useEffect(() => {
    const sweepInterval = setInterval(() => {
      setSweepAngle((prev) => {
        let next = prev + sweepDirRef.current * 4;
        if (next >= 160) {
          next = 160;
          sweepDirRef.current = -1;
        } else if (next <= 20) {
          next = 20;
          sweepDirRef.current = 1;
        }
        return next;
      });
    }, 45);
    return () => clearInterval(sweepInterval);
  }, []);

  // One-click sweep simulation
  const handleSimulateSweep = async () => {
    setSimulating(true);
    try {
      const controller = selectedDevice.includes("32") ? "ESP32" : "ESP8266";
      const res = await api.post(`/iot/simulate?device_id=${selectedDevice}&controller_type=${controller}`);
      if (res.data && res.data.data) {
        setTelemetry(res.data.data);
        setFeedback(lang === "hi" ? "सिमुलेशन डेटा सफलतापूर्वक भेजा गया!" : "Simulated sweep ingested successfully!");
        setTimeout(() => setFeedback(""), 3500);
      }
    } catch {
      setFeedback(lang === "hi" ? "सिमुलेशन विफल।" : "Simulation failed.");
      setTimeout(() => setFeedback(""), 3500);
    } finally {
      setSimulating(false);
    }
  };

  // Save updated thresholds
  const handleSaveThresholds = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post("/iot/config", thresholds);
      if (res.data && res.data.thresholds) {
        setThresholds(res.data.thresholds);
        setFeedback(lang === "hi" ? "सीमाएं सफलतापूर्वक अपडेट हुईं!" : "Safety thresholds updated successfully!");
        setTimeout(() => setFeedback(""), 3500);
        setShowConfig(false);
        fetchLatestTelemetry();
      }
    } catch {
      alert("Failed to update thresholds");
    }
  };

  // Data helpers
  const isOnline = telemetry?.is_online || false;
  const tempVal = telemetry?.temperature != null ? `${telemetry.temperature} °C` : "--";
  const humVal = telemetry?.humidity != null ? `${telemetry.humidity} %` : "--";
  const soilVal = telemetry?.soil_moisture != null ? `${telemetry.soil_moisture} %` : "--";
  const nearestObj = telemetry?.nearest_object;
  const nearestDist = nearestObj?.distance != null ? `${nearestObj.distance} cm` : (lang === "hi" ? "कोई नहीं" : "Clear (None)");
  const nearestAngle = nearestObj?.angle != null ? `@ ${nearestObj.angle}°` : "";
  const overallStatus = telemetry?.object_status || "CLEAR";

  const getStatusBadge = (status) => {
    switch (status) {
      case "VERY CLOSE":
        return <span className="iotBadge critical"><ShieldAlert size={14} /> {lang === "hi" ? "अत्यधिक निकट" : "VERY CLOSE"}</span>;
      case "WARNING":
        return <span className="iotBadge warning"><AlertTriangle size={14} /> {lang === "hi" ? "चेतावनी" : "WARNING"}</span>;
      case "OBJECT DETECTED":
        return <span className="iotBadge detected"><Target size={14} /> {lang === "hi" ? "वस्तु पहचानी गई" : "OBJECT DETECTED"}</span>;
      case "CLEAR":
        return <span className="iotBadge clear"><ShieldCheck size={14} /> {lang === "hi" ? "सुरक्षित" : "CLEAR"}</span>;
      default:
        return <span className="iotBadge none"><Info size={14} /> {lang === "hi" ? "कोई रीडिंग नहीं" : "NO READING"}</span>;
    }
  };

  // Soil moisture comfort label
  const getSoilMoistureStatus = (val) => {
    if (val == null) return "--";
    if (val < 30) return lang === "hi" ? "सूखी मिट्टी (सिंचाई करें)" : "Dry (Needs Irrigation)";
    if (val <= 70) return lang === "hi" ? "उपयुक्त नमी (संतोषजनक)" : "Optimal Moisture";
    return lang === "hi" ? "अत्यधिक गीली मिट्टी" : "Wet / Saturated";
  };

  // Radar parameters
  const radarRadius = 180;
  const maxDistanceCm = 150; // max visible cm on the radar arc
  const radarScan = telemetry?.scan || [];

  // Convert (angle, distance) to SVG coordinates
  // Angle: 20° (right) to 160° (left), 90° is straight up
  const polarToSvg = (angle, distance) => {
    const clampedDist = Math.min(Math.max(distance, 0), maxDistanceCm);
    const r = (clampedDist / maxDistanceCm) * radarRadius;
    const rad = (angle * Math.PI) / 180;
    // x = center + r * cos(rad)  (90° -> cos(90°)=0, 20° -> cos(20°)>0 right, 160° -> cos(160°)<0 left)
    // y = center - r * sin(rad)  (sin(angle) > 0 so points upward)
    const x = 200 + r * Math.cos(rad);
    const y = 200 - r * Math.sin(rad);
    return { x, y };
  };

  // SVG arc path generator
  const getArcPath = (distCm) => {
    const pStart = polarToSvg(20, distCm);
    const pEnd = polarToSvg(160, distCm);
    const r = (distCm / maxDistanceCm) * radarRadius;
    return `M ${pStart.x} ${pStart.y} A ${r} ${r} 0 0 0 ${pEnd.x} ${pEnd.y}`;
  };

  return (
    <div className="content iotDashboardContent">
      {/* HERO & HEADER SECTION */}
      <div className="hero iotHero">
        <div className="iotHeroTitleBlock">
          <div className="iotEyebrow">
            <Radio size={16} className="pulseIcon" />
            <span>MAITTRI IOT HARDWARE SUBSYSTEM</span>
          </div>
          <h1>{t.iotMonitor || "IoT Field Monitor & Radar"}</h1>
          <p>{t.iotMonitorSubtitle || "Live ultrasonic obstacle radar & environmental telemetry from ESP8266 / ESP32"}</p>
        </div>

        {/* CONNECTED DEVICE DISPLAY & ACTION BAR */}
        <div className="iotHeroActions">
          <div className="iotConnectedDeviceBadge">
            <Cpu size={18} className="iotConnectedIcon" />
            <div className="iotConnectedDeviceInfo">
              <span className="iotConnectedDeviceLabel">
                {lang === "hi" ? "कनेक्टेड डिवाइस" : "CONNECTED DEVICE"}
              </span>
              <strong className="iotConnectedDeviceName">
                {telemetry?.device_id || selectedDevice} ({telemetry?.controller_type || "ESP32"})
              </strong>
            </div>
            <span className={`iotStatusIndicatorBadge ${isOnline ? "online" : "offline"}`}>
              <span className={`liveDot ${isOnline ? "green" : "red"}`}></span>
              <span>{isOnline ? (lang === "hi" ? "सक्रिय (ऑनलाइन)" : "Live Online") : (lang === "hi" ? "ऑफ़लाइन" : "Offline")}</span>
            </span>
          </div>

          <button
            type="button"
            className={`iotButton small ${autoRefresh ? "active" : ""}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
            title="Toggle continuous auto-polling every 3s"
          >
            <Activity size={14} />
            <span>{autoRefresh ? (lang === "hi" ? "ऑटो-रीफ्रेश (सक्रिय)" : "Auto: ON") : (lang === "hi" ? "ऑटो: बंद" : "Auto: OFF")}</span>
          </button>

          <button
            type="button"
            className="iotButton small"
            onClick={() => {
              setLoading(true);
              fetchLatestTelemetry().finally(() => setLoading(false));
            }}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? "spin" : ""} />
            <span>{t.refreshNow || "Refresh"}</span>
          </button>

          <button
            type="button"
            className="iotButton highlight small"
            onClick={handleSimulateSweep}
            disabled={simulating}
            title="Simulate a real-time radar sweep and telemetry update"
          >
            <Play size={14} />
            <span>{simulating ? "Scanning..." : (t.simulateSweep || "Simulate Sweep")}</span>
          </button>

          <button
            type="button"
            className={`iotButton small ${showLanHelp ? "active" : ""}`}
            onClick={() => setShowLanHelp(!showLanHelp)}
            title="View target IP for Arduino sketch"
          >
            <Wifi size={14} />
            <span>{lang === "hi" ? "हार्डवेयर IP गाइड" : "Target IP Guide"}</span>
          </button>

          <button
            type="button"
            className="iotButton iconOnly small"
            onClick={() => setShowConfig(!showConfig)}
            title="Configure safety thresholds"
          >
            <Settings size={16} />
          </button>
        </div>
      </div>

      {feedback && (
        <div className="feedbackBanner success">
          <CheckCircle2 size={16} /> {feedback}
        </div>
      )}

      {/* DEVICE LIVE STATUS STRIP */}
      <div className="iotLiveStatusStrip">
        <div className="iotLiveStatusItem">
          <div className="iotLiveStatusLabel">{t.deviceStatus || "DEVICE STATUS"}</div>
          <div className="iotLiveStatusValue">
            {isOnline ? (
              <span className="deviceStatusBadge online">
                <span className="liveDot green"></span>
                <span>🟢 {t.deviceOnline || "Device Online"}</span>
              </span>
            ) : (
              <span className="deviceStatusBadge offline">
                <span className="liveDot red"></span>
                <span>🔴 {t.deviceOffline || "Device Offline"}</span>
              </span>
            )}
          </div>
        </div>

        <div className="iotLiveStatusItem">
          <div className="iotLiveStatusLabel">{t.controllerType || "CONTROLLER"}</div>
          <div className="iotLiveStatusValue">
            <span className="chipTag">
              <Cpu size={14} /> {telemetry?.controller_type || (selectedDevice.includes("32") ? "ESP32" : "ESP8266")}
            </span>
          </div>
        </div>

        <div className="iotLiveStatusItem">
          <div className="iotLiveStatusLabel">{t.lastUpdated || "LAST UPDATED"}</div>
          <div className="iotLiveStatusValue timeValue">
            {telemetry?.last_seen ? (
              <>
                <strong>{telemetry.last_seen}</strong>
                <small>({telemetry.time_diff_seconds || 0}s ago)</small>
              </>
            ) : (
              "Waiting for first transmission"
            )}
          </div>
        </div>

        <div className="iotLiveStatusItem">
          <div className="iotLiveStatusLabel">{t.nearestObject || "NEAREST OBJECT"}</div>
          <div className="iotLiveStatusValue">
            <span className="nearestVal">
              {nearestDist} <small>{nearestAngle}</small>
            </span>
          </div>
        </div>

        <div className="iotLiveStatusItem">
          <div className="iotLiveStatusLabel">{t.objectStatus || "OBJECT STATUS"}</div>
          <div className="iotLiveStatusValue">
            {getStatusBadge(overallStatus)}
          </div>
        </div>
      </div>

      {/* HARDWARE CONNECTION & LAN IP HELPER CARD */}
      {(!isOnline || showLanHelp) && (
        <div className="iotLanHelperCard">
          <div className="iotLanHelperHeader">
            <div className="iotLanHelperTitle">
              <span className="iotLanHelperIcon">⚡</span>
              <div>
                <h4>
                  {lang === "hi"
                    ? "ESP32 हार्डवेयर कनेक्शन गाइड (हॉटस्पॉट / वाई-फ़ाई)"
                    : "ESP32 Hardware Connection Guide & Target IP"}
                </h4>
                <p>
                  {lang === "hi"
                    ? "Arduino IDE में नीचे दिए गए URL को SERVER_URL में सेट करें ताकि डेटा डैशबोर्ड पर तुरंत लाइव दिखे"
                    : "Configure this exact SERVER_URL in your Arduino IDE sketch to stream telemetry directly to this dashboard"}
                </p>
              </div>
            </div>
            {isOnline && (
              <button
                type="button"
                className="button textOnly small"
                onClick={() => setShowLanHelp(false)}
              >
                ✕
              </button>
            )}
          </div>

          <div className="iotLanEndpointsGrid">
            {(telemetry?.lan_ips || [
              { ip: "192.168.137.1", label: "Windows Mobile Hotspot (Recommended)", url: "http://192.168.137.1:8000/api/iot/sensor-data", is_hotspot: true },
              { ip: "10.38.2.70", label: "Local Wi-Fi Network", url: "http://10.38.2.70:8000/api/iot/sensor-data", is_hotspot: false }
            ]).map((endpoint, i) => (
              <div key={i} className={`iotEndpointBox ${endpoint.is_hotspot ? "recommended" : ""}`}>
                <div className="endpointHeader">
                  <span className="endpointLabel">{endpoint.label}</span>
                  {endpoint.is_hotspot && (
                    <span className="recommendedBadge">
                      {lang === "hi" ? "सक्रिय हॉटस्पॉट" : "ACTIVE HOTSPOT"}
                    </span>
                  )}
                </div>
                <div className="endpointUrlRow">
                  <code>{endpoint.url}</code>
                  <button
                    type="button"
                    className="copyButton"
                    onClick={() => handleCopyUrl(endpoint.url)}
                    title="Copy URL"
                  >
                    {copiedUrl === endpoint.url ? (
                      <Check size={14} className="copiedCheck" />
                    ) : (
                      <Copy size={14} />
                    )}
                    <span>{copiedUrl === endpoint.url ? (lang === "hi" ? "कॉपी किया गया!" : "Copied!") : (lang === "hi" ? "कॉपी करें" : "Copy")}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="iotTroubleshootSteps">
            <strong>{lang === "hi" ? "त्वरित सेटअप चरण:" : "3-Step Setup in Arduino IDE:"}</strong>
            <ol>
              <li>
                {lang === "hi" ? (
                  <>
                    Arduino IDE में <code>hardware/esp32/maitri_esp32_node.ino</code> फ़ाइल खोलें।
                  </>
                ) : (
                  <>
                    Open <code>hardware/esp32/maitri_esp32_node.ino</code> in Arduino IDE.
                  </>
                )}
              </li>
              <li>
                {lang === "hi" ? (
                  <>
                    लाइन 50 पर <code>SERVER_URL</code> को ऊपर दिए गए हॉटस्पॉट URL (<code>http://192.168.137.1:8000/api/iot/sensor-data</code>) से बदलें। (<code>127.0.0.1</code> या <code>192.168.1.100</code> न रखें)।
                  </>
                ) : (
                  <>
                    Ensure line 50 <code>SERVER_URL</code> is set to the Hotspot URL above (<code>http://192.168.137.1:8000/api/iot/sensor-data</code>). Do not use 127.0.0.1 or localhost.
                  </>
                )}
              </li>
              <li>
                {lang === "hi" ? (
                  <>
                    ESP32 में कोड <strong>Upload (Ctrl+U)</strong> करें और <strong>Serial Monitor (115200 baud)</strong> में <code>[HTTP] Ingestion successful!</code> देखें। यह डैशबोर्ड तुरंत <strong>Live Online 🟢</strong> हो जाएगा!
                  </>
                ) : (
                  <>
                    Upload sketch to ESP32 and open Serial Monitor (115200 baud). Once it prints <code>[HTTP] Ingestion successful!</code>, the status turns <strong>Live Online 🟢</strong>!
                  </>
                )}
              </li>
            </ol>
          </div>
        </div>
      )}

      {/* CONFIGURATION DRAWER / MODAL */}
      {showConfig && (
        <div className="card iotConfigCard">
          <div className="iotConfigHeader">
            <h3>⚙️ {t.thresholdSettings || "Safety Thresholds & Controller Settings"}</h3>
            <button className="button textOnly" onClick={() => setShowConfig(false)}>✕ Close</button>
          </div>
          <form onSubmit={handleSaveThresholds} className="iotConfigForm">
            <div className="iotConfigGrid">
              <div className="formGroup">
                <label>Clear Threshold (&gt; cm):</label>
                <input
                  type="number"
                  value={thresholds.clear_distance}
                  onChange={(e) => setThresholds({ ...thresholds, clear_distance: parseFloat(e.target.value) || 100 })}
                  min="50"
                  max="300"
                />
                <small>Distances above this value are marked CLEAR.</small>
              </div>

              <div className="formGroup">
                <label>Warning Threshold (cm):</label>
                <input
                  type="number"
                  value={thresholds.warning_distance}
                  onChange={(e) => setThresholds({ ...thresholds, warning_distance: parseFloat(e.target.value) || 50 })}
                  min="20"
                  max="150"
                />
                <small>50cm &lt; dist &le; 100cm = DETECTED, 20cm &lt; dist &le; 50cm = WARNING.</small>
              </div>

              <div className="formGroup">
                <label>Critical / Very Close Threshold (&le; cm):</label>
                <input
                  type="number"
                  value={thresholds.critical_distance}
                  onChange={(e) => setThresholds({ ...thresholds, critical_distance: parseFloat(e.target.value) || 20 })}
                  min="5"
                  max="50"
                />
                <small>Distances at or below this trigger VERY CLOSE alert.</small>
              </div>

              <div className="formGroup">
                <label>Device Offline Timeout (seconds):</label>
                <input
                  type="number"
                  value={thresholds.offline_timeout_seconds}
                  onChange={(e) => setThresholds({ ...thresholds, offline_timeout_seconds: parseInt(e.target.value) || 20 })}
                  min="5"
                  max="120"
                />
                <small>Device marked OFFLINE if no ping within this window.</small>
              </div>
            </div>
            <div className="iotConfigActions">
              <button type="submit" className="button">Save Thresholds</button>
              <button type="button" className="button secondary" onClick={() => setShowConfig(false)}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* 6 KEY METRICS ROW (Exact Required Spec) */}
      <div className="iotMetricsGrid">
        {/* Metric 1: TEMPERATURE */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className="iotMetricIcon temp">
              <Thermometer size={22} />
            </div>
            <span className="iotMetricTag">DHT22 Ambient</span>
          </div>
          <div className="iotMetricLabel">TEMPERATURE</div>
          <div className="iotMetricNumber">{tempVal}</div>
          <div className="iotMetricDesc">
            {telemetry?.temperature != null
              ? (telemetry.temperature > 35 ? "High (Heat Stress)" : (telemetry.temperature < 15 ? "Cool" : "Optimal for Crop Growth"))
              : "Sensor ready"}
          </div>
        </div>

        {/* Metric 2: HUMIDITY */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className="iotMetricIcon hum">
              <Droplets size={22} />
            </div>
            <span className="iotMetricTag">Relative</span>
          </div>
          <div className="iotMetricLabel">HUMIDITY</div>
          <div className="iotMetricNumber">{humVal}</div>
          <div className="iotMetricDesc">
            {telemetry?.humidity != null
              ? (telemetry.humidity > 80 ? "High Humidity (Fungal Risk)" : (telemetry.humidity < 40 ? "Low Humidity" : "Comfortable Window"))
              : "Sensor ready"}
          </div>
        </div>

        {/* Metric 3: SOIL MOISTURE */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className="iotMetricIcon soil">
              <Sprout size={22} />
            </div>
            <span className="iotMetricTag">In-Situ Probe</span>
          </div>
          <div className="iotMetricLabel">SOIL MOISTURE</div>
          <div className="iotMetricNumber">{soilVal}</div>
          <div className="iotMetricDesc">{getSoilMoistureStatus(telemetry?.soil_moisture)}</div>
        </div>

        {/* Metric 4: NEAREST OBJECT */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className="iotMetricIcon target">
              <Target size={22} />
            </div>
            <span className="iotMetricTag">HC-SR04 Ping</span>
          </div>
          <div className="iotMetricLabel">NEAREST OBJECT</div>
          <div className="iotMetricNumber">{nearestDist}</div>
          <div className="iotMetricDesc">
            {nearestObj?.angle != null ? `Detected at servo position ${nearestObj.angle}°` : "Clear line of sight"}
          </div>
        </div>

        {/* Metric 5: OBJECT STATUS */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className="iotMetricIcon status">
              <AlertTriangle size={22} />
            </div>
            <span className="iotMetricTag">Proximity Filter</span>
          </div>
          <div className="iotMetricLabel">OBJECT STATUS</div>
          <div className="iotMetricStatusPill">
            {getStatusBadge(overallStatus)}
          </div>
          <div className="iotMetricDesc">
            {overallStatus === "VERY CLOSE" ? "Imminent obstacle (< 20 cm)" : (overallStatus === "WARNING" ? "Object within perimeter (20-50 cm)" : "Field corridor clear")}
          </div>
        </div>

        {/* Metric 6: DEVICE STATUS */}
        <div className="card iotMetricCard">
          <div className="iotMetricTop">
            <div className={`iotMetricIcon ${isOnline ? "online" : "offline"}`}>
              {isOnline ? <Wifi size={22} /> : <WifiOff size={22} />}
            </div>
            <span className="iotMetricTag">Heartbeat</span>
          </div>
          <div className="iotMetricLabel">DEVICE STATUS</div>
          <div className="iotMetricNumber">
            {isOnline ? (
              <span style={{ color: "#16a34a" }}>ONLINE</span>
            ) : (
              <span style={{ color: "#dc2626" }}>OFFLINE</span>
            )}
          </div>
          <div className="iotMetricDesc">
            {isOnline ? "Active telemetry stream" : `Timed out (> ${thresholds.offline_timeout_seconds}s without ping)`}
          </div>
        </div>
      </div>

      {/* MAIN RADAR & TELEMETRY SECTION */}
      <div className="iotMainGrid">
        {/* LEFT COLUMN: LIVE ULTRASONIC SWEEP RADAR */}
        <div className="card iotRadarCard">
          <div className="iotRadarCardHeader">
            <div>
              <h3>📡 {t.radarSweep || "Ultrasonic Scanning Radar"}</h3>
              <p>Servo-mounted HC-SR04 scanning sweep ($20^\circ \longleftrightarrow 160^\circ$)</p>
            </div>
            <div className="iotRadarLegend">
              <span className="legendDot critical"></span> &le; 20cm
              <span className="legendDot warning"></span> 20-50cm
              <span className="legendDot detected"></span> 50-100cm
              <span className="legendDot clear"></span> &gt; 100cm
            </div>
          </div>

          <div className="radarSvgWrapper">
            <svg
              viewBox="0 0 400 230"
              className="radarSvg"
              role="img"
              aria-label="Ultrasonic sweep radar display"
            >
              <defs>
                {/* Glow filters for high-tech aesthetic */}
                <filter id="radarGlow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="blipGlow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="4" result="glow" />
                  <feMerge>
                    <feMergeNode in="glow" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
                <linearGradient id="sweepBeamGrad" x1="0%" y1="100%" x2="0%" y2="0%">
                  <stop offset="0%" stopColor="rgba(34, 197, 94, 0.05)" />
                  <stop offset="100%" stopColor="rgba(34, 197, 94, 0.45)" />
                </linearGradient>
                <radialGradient id="radarBackdropGrad" cx="50%" cy="100%" r="90%">
                  <stop offset="0%" stopColor="#0b2416" />
                  <stop offset="60%" stopColor="#061a0f" />
                  <stop offset="100%" stopColor="#031009" />
                </radialGradient>
              </defs>

              {/* Radar Background Arc */}
              <path
                d="M 20 200 A 180 180 0 0 1 380 200 Z"
                fill="url(#radarBackdropGrad)"
                stroke="#166534"
                strokeWidth="1.5"
              />

              {/* Concentric Range Rings */}
              {/* 150 cm (Max perimeter) */}
              <path d={getArcPath(150)} fill="none" stroke="rgba(34, 197, 94, 0.3)" strokeWidth="1" strokeDasharray="3 3" />
              {/* 100 cm (Detection threshold) */}
              <path d={getArcPath(100)} fill="none" stroke="rgba(34, 197, 94, 0.5)" strokeWidth="1.2" />
              {/* 50 cm (Warning threshold) */}
              <path d={getArcPath(50)} fill="none" stroke="rgba(234, 179, 8, 0.5)" strokeWidth="1.2" strokeDasharray="4 2" />
              {/* 20 cm (Critical threshold) */}
              <path d={getArcPath(20)} fill="none" stroke="rgba(239, 68, 68, 0.6)" strokeWidth="1.5" />

              {/* Range Distance Labels */}
              <text x="202" y="186" fill="#ef4444" fontSize="9" fontWeight="bold">20cm</text>
              <text x="202" y="148" fill="#eab308" fontSize="9" fontWeight="bold">50cm</text>
              <text x="202" y="88" fill="#22c55e" fontSize="9" fontWeight="bold">100cm</text>
              <text x="202" y="28" fill="#86efac" fontSize="9" fontWeight="bold">150cm</text>

              {/* Radial Angle Spokes (20°, 40°, 60°, 90°, 120°, 140°, 160°) */}
              {[20, 40, 60, 90, 120, 140, 160].map((deg) => {
                const p = polarToSvg(deg, 150);
                const pLabel = polarToSvg(deg, 168);
                return (
                  <g key={deg}>
                    <line
                      x1="200"
                      y1="200"
                      x2={p.x}
                      y2={p.y}
                      stroke={deg === 90 ? "rgba(34, 197, 94, 0.7)" : "rgba(34, 197, 94, 0.25)"}
                      strokeWidth={deg === 90 ? "1.5" : "1"}
                    />
                    <text
                      x={pLabel.x}
                      y={pLabel.y + (deg === 90 ? -4 : 4)}
                      fill="#86efac"
                      fontSize="9"
                      textAnchor="middle"
                      fontWeight="600"
                    >
                      {deg}°
                    </text>
                  </g>
                );
              })}

              {/* Animated Sweep Beam (Shows active scanning vector) */}
              {(() => {
                const beamEnd = polarToSvg(sweepAngle, 150);
                const beamEndBack = polarToSvg(sweepAngle - sweepDirRef.current * 8, 145);
                return (
                  <g className="sweepGroup">
                    <polygon
                      points={`200,200 ${beamEnd.x},${beamEnd.y} ${beamEndBack.x},${beamEndBack.y}`}
                      fill="url(#sweepBeamGrad)"
                    />
                    <line
                      x1="200"
                      y1="200"
                      x2={beamEnd.x}
                      y2={beamEnd.y}
                      stroke="#4ade80"
                      strokeWidth="2"
                      filter="url(#radarGlow)"
                    />
                  </g>
                );
              })()}

              {/* Detected Scan Obstacles (Blips) */}
              {radarScan.map((pt, idx) => {
                if (pt.distance == null || pt.distance <= 0) return null;
                const pos = polarToSvg(pt.angle, pt.distance);

                // Determine blip color based on distance/status
                let blipColor = "#22c55e"; // clear
                let rSize = 3.5;
                if (pt.distance <= 20) {
                  blipColor = "#ef4444"; // red
                  rSize = 6;
                } else if (pt.distance <= 50) {
                  blipColor = "#f97316"; // orange
                  rSize = 5;
                } else if (pt.distance <= 100) {
                  blipColor = "#06b6d4"; // cyan
                  rSize = 4.5;
                }

                const isNearest = nearestObj && nearestObj.angle === pt.angle && Math.abs(nearestObj.distance - pt.distance) < 0.5;

                return (
                  <g key={idx} className="radarBlipGroup">
                    {/* Pulsing ring for critical or nearest object */}
                    {isNearest && (
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r="10"
                        fill="none"
                        stroke={blipColor}
                        strokeWidth="1.5"
                        className="radarTargetPing"
                      />
                    )}
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={rSize}
                      fill={blipColor}
                      filter="url(#blipGlow)"
                    />
                  </g>
                );
              })}

              {/* Center Servo Pivot Point */}
              <circle cx="200" cy="200" r="10" fill="#0f2e17" stroke="#22c55e" strokeWidth="2" />
              <circle cx="200" cy="200" r="4" fill="#4ade80" />
              <text x="200" y="218" fill="#a7f3d0" fontSize="9" textAnchor="middle" fontWeight="bold">
                SENSOR ORIGIN
              </text>
            </svg>
          </div>

          {/* RADAR METADATA READOUT */}
          <div className="radarTelemetryReadout">
            <div className="radarReadoutBox">
              <span className="label">ACTIVE SERVO SWEEP</span>
              <strong>{sweepAngle}°</strong>
            </div>
            <div className="radarReadoutBox">
              <span className="label">NEAREST DISTANCE</span>
              <strong className={nearestObj?.distance <= 20 ? "textCritical" : (nearestObj?.distance <= 50 ? "textWarning" : "")}>
                {nearestDist}
              </strong>
            </div>
            <div className="radarReadoutBox">
              <span className="label">TARGET BEARING</span>
              <strong>{nearestAngle || "None"}</strong>
            </div>
            <div className="radarReadoutBox">
              <span className="label">ACTIVE STATUS</span>
              <strong>{overallStatus}</strong>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: ANGLE-BY-ANGLE SWEEP TABLE & HARDWARE SPECS */}
        <div className="iotRightColumn">
          {/* ANGLE-BY-ANGLE TABLE */}
          <div className="card iotSweepTableCard">
            <div className="iotSweepTableHeader">
              <div>
                <h4>📋 {t.angleBreakdown || "Angle-by-Angle Ultrasonic Scan"}</h4>
                <p>Telemetry recorded across the $20^\circ \to 160^\circ$ sweep path</p>
              </div>
              <span className="iotTotalPointsBadge">{radarScan.length} points</span>
            </div>

            <div className="iotTableWrap">
              <table className="iotTable">
                <thead>
                  <tr>
                    <th>{t.scanAngle || "Angle"}</th>
                    <th>{t.distance || "Distance"}</th>
                    <th>{t.objectStatus || "Status"}</th>
                    <th>Visual Range</th>
                  </tr>
                </thead>
                <tbody>
                  {radarScan.length === 0 ? (
                    <tr>
                      <td colSpan="4" style={{ textAlign: "center", padding: "20px" }}>
                        Waiting for initial scan transmission...
                      </td>
                    </tr>
                  ) : (
                    radarScan.map((p) => {
                      const d = p.distance;
                      const pct = d != null ? Math.min(Math.round((d / 150) * 100), 100) : 0;
                      let barClass = "barClear";
                      if (d != null) {
                        if (d <= 20) barClass = "barCritical";
                        else if (d <= 50) barClass = "barWarning";
                        else if (d <= 100) barClass = "barDetected";
                      }

                      return (
                        <tr key={p.angle} className={nearestObj?.angle === p.angle ? "highlightNearestRow" : ""}>
                          <td><strong>{p.angle}°</strong></td>
                          <td>
                            {d != null ? (
                              <span>{d} cm</span>
                            ) : (
                              <span style={{ color: "#94a3b8" }}>No Echo</span>
                            )}
                          </td>
                          <td>{getStatusBadge(p.status)}</td>
                          <td>
                            <div className="miniRangeBarTrack">
                              <div
                                className={`miniRangeBarFill ${barClass}`}
                                style={{ width: `${pct}%` }}
                              ></div>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* HARDWARE PINOUT & WIRING REFERENCE */}
          <div className="card iotHardwareInfoCard">
            <div className="iotHardwareInfoHeader">
              <div>
                <h4>⚡ {t.hardwareSpecs || "Hardware Pinout & Controller Mapping"}</h4>
                <p>NodeMCU ESP8266 & ESP32 connection matrix</p>
              </div>
              <button
                type="button"
                className="button textOnly small"
                onClick={() => setShowPinout(!showPinout)}
              >
                {showPinout ? "Hide Details" : "Show Pinout"}
              </button>
            </div>

            {showPinout && (
              <div className="iotPinoutBody">
                <div className="pinoutGroup">
                  <h5>ESP8266 NodeMCU Wiring:</h5>
                  <ul>
                    <li><strong>DHT22 (Temp & Hum):</strong> DATA &rarr; <code>D2 / GPIO4</code> (Pull-up 10k&Omega;)</li>
                    <li><strong>Soil Moisture:</strong> AO &rarr; <code>A0 (Analog Input)</code></li>
                    <li><strong>Servo Motor:</strong> Signal &rarr; <code>D5 / GPIO14</code> (PWM)</li>
                    <li><strong>HC-SR04 (Ultrasonic):</strong> TRIG &rarr; <code>D6 / GPIO12</code>, ECHO &rarr; <code>D7 / GPIO13</code></li>
                  </ul>
                </div>

                <div className="pinoutGroup">
                  <h5>ESP32 DevKit Wiring:</h5>
                  <ul>
                    <li><strong>DHT22 (Temp & Hum):</strong> DATA &rarr; <code>GPIO4</code></li>
                    <li><strong>Soil Moisture:</strong> AO &rarr; <code>GPIO34 (ADC1_CH6, WiFi safe)</code></li>
                    <li><strong>Servo Motor:</strong> Signal &rarr; <code>GPIO18</code></li>
                    <li><strong>HC-SR04 (Ultrasonic):</strong> TRIG &rarr; <code>GPIO5</code>, ECHO &rarr; <code>GPIO19</code></li>
                  </ul>
                </div>

                <div className="pinoutNote">
                  <strong>LAN Communication:</strong> Microcontrollers post JSON to{" "}
                  <code>http://&lt;YOUR_PC_LAN_IP&gt;:8000/api/iot/sensor-data</code>. Do not use 127.0.0.1 on the ESP.
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
