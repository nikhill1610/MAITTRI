import React, { useState, useEffect, useRef } from "react";
import {
  Bot, Send, Sparkles, RefreshCw, Trash2, Sprout, Bug, Droplets,
  FlaskConical, CloudSun, Landmark, Copy, Check, AlertCircle,
  Wheat, Radio, ArrowUpRight, HelpCircle
} from "lucide-react";
import api from "./api";
import { useLang } from "./LanguageContext";

const QUICK_QUESTIONS = [
  {
    id: "crop_yellow",
    icon: <Sprout size={16} color="#16a34a" />,
    labelHi: "गेहूं के पत्ते पीले",
    labelEn: "Wheat leaves turning yellow",
    queryHi: "गेहूं के पत्ते पीले हो रहे हैं, इसका क्या कारण और समाधान है?",
    queryEn: "My wheat leaves are turning yellow, what could be the cause and remedy?",
    category: "Crop Problem"
  },
  {
    id: "pest_rice",
    icon: <Bug size={16} color="#dc2626" />,
    labelHi: "धान में कीट नियंत्रण",
    labelEn: "Pest control in Rice",
    queryHi: "धान की फसल में कीट लग गए हैं, जैविक और रासायनिक उपचार क्या है?",
    queryEn: "meri rice crop me insects aa gaye hain, kya safe control measures hain?",
    category: "Pests & Diseases"
  },
  {
    id: "irrig_stages",
    icon: <Droplets size={16} color="#0284c7" />,
    labelHi: "गेहूं में सिंचाई की अवस्थाएं",
    labelEn: "Wheat irrigation stages",
    queryHi: "गेहूं की फसल में सबसे जरूरी सिंचाई कब करनी चाहिए?",
    queryEn: "What are the critical irrigation stages for wheat, especially CRI stage?",
    category: "Irrigation"
  },
  {
    id: "fert_mustard",
    icon: <FlaskConical size={16} color="#854d0e" />,
    labelHi: "सरसों में खाद व सल्फर",
    labelEn: "Mustard fertilizer & sulphur",
    queryHi: "सरसों की फसल में यूरिया, डीएपी और सल्फर की सही मात्रा क्या है?",
    queryEn: "What is the recommended fertilizer dose and sulphur for mustard?",
    category: "Fertilizer"
  },
  {
    id: "pm_kisan",
    icon: <Landmark size={16} color="#7c3aed" />,
    labelHi: "पीएम-किसान योजना",
    labelEn: "PM-KISAN Scheme",
    queryHi: "पीएम-किसान योजना के तहत सालाना ₹6,000 की पात्रता और नियम क्या हैं?",
    queryEn: "PM-KISAN yojana ke benefits aur eligibility criteria kya hain?",
    category: "Schemes"
  },
  {
    id: "soil_moisture",
    icon: <CloudSun size={16} color="#ea580c" />,
    labelHi: "मौसम और मृदा नमी",
    labelEn: "Weather & Soil Moisture",
    queryHi: "कम नमी की स्थिति में फसल को सूखने से कैसे बचाएं?",
    queryEn: "How to protect crops during sudden temperature rise and low moisture?",
    category: "Weather & Soil"
  }
];

export default function KrishiAssistantPage() {
  const [lang] = useLang();
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem("maitri_chat_history");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [farmContext, setFarmContext] = useState(null);
  const [iotContext, setIotContext] = useState(null);
  const [statusInfo, setStatusInfo] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  // Persist messages in local storage
  useEffect(() => {
    try {
      localStorage.setItem("maitri_chat_history", JSON.stringify(messages));
    } catch {
      // Ignore quota errors
    }
  }, [messages]);

  // Fetch farmer's primary farm & IoT reading to display active context
  useEffect(() => {
    async function loadContext() {
      try {
        const [farmRes, iotRes, statusRes] = await Promise.allSettled([
          api.get("/farms"),
          api.get("/iot/latest"),
          api.get("/chat/status")
        ]);

        if (farmRes.status === "fulfilled" && Array.isArray(farmRes.value.data) && farmRes.value.data.length > 0) {
          setFarmContext(farmRes.value.data[0]);
        }
        if (iotRes.status === "fulfilled" && iotRes.value.data) {
          setIotContext(iotRes.value.data);
        }
        if (statusRes.status === "fulfilled" && statusRes.value.data) {
          setStatusInfo(statusRes.value.data);
        }
      } catch (e) {
        // Safe silent fail
      }
    }
    loadContext();
  }, []);

  const handleSend = async (textToSend) => {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    setError(null);
    setInput("");

    const userMsg = { role: "user", content: text, timestamp: new Date().toISOString() };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setLoading(true);

    try {
      // Build context payload
      const contextPayload = {};
      if (farmContext) {
        if (farmContext.current_crop) contextPayload.crop = farmContext.current_crop;
        if (farmContext.soil_type) contextPayload.soil_type = farmContext.soil_type;
        if (farmContext.area) contextPayload.land_area = farmContext.area;
        if (farmContext.location_name) contextPayload.location = farmContext.location_name;
        if (farmContext.sowing_date) contextPayload.sowing_date = farmContext.sowing_date;
      }
      if (iotContext) {
        if (iotContext.soil_moisture !== undefined) contextPayload.soil_moisture = iotContext.soil_moisture;
        if (iotContext.temperature !== undefined) contextPayload.temperature = iotContext.temperature;
      }

      // Recent history turns (max last 4)
      const historyTurns = updatedMessages.slice(-5, -1).map(m => ({
        role: m.role,
        content: m.content
      }));

      const res = await api.post("/chat", {
        message: text,
        context: contextPayload,
        history: historyTurns
      });

      const assistantMsg = {
        role: "assistant",
        content: res.data.reply,
        language: res.data.language,
        sources: res.data.sources || [],
        provider: res.data.provider,
        timestamp: new Date().toISOString()
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Chat API error:", err);
      const fallbackText = lang === "hi"
        ? "क्षमा करें, मैत्री सहायक अभी अस्थायी रूप से अनुपलब्ध है। कृपया कुछ क्षणों बाद पुनः प्रयास करें।"
        : "Sorry, Maitri Krishi Assistant is temporarily unavailable. Please try again in a moment.";
      setError(fallbackText);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: fallbackText,
          isError: true,
          timestamp: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearChat = () => {
    if (window.confirm(lang === "hi" ? "क्या आप चैट इतिहास मिटाना चाहते हैं?" : "Clear chat history?")) {
      setMessages([]);
      localStorage.removeItem("maitri_chat_history");
      setError(null);
    }
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="content krishiChatContainer">
      {/* Header Bar */}
      <div className="krishiChatHeader card">
        <div className="krishiHeaderLeft">
          <div className="krishiAvatar">
            <Bot size={28} color="#15803d" />
            <span className="onlineDot" title="AI Assistant Online"></span>
          </div>
          <div>
            <div className="krishiTitleWrap">
              <h1 className="krishiTitle">{lang === "hi" ? "मैत्री कृषि सहायक" : "MAITTRI Krishi Assistant"}</h1>
              <span className="krishiSubBadge">{lang === "hi" ? "किसान का साथी, समृद्धि की शुरुआत" : "Farmer's Companion, Beginning of Prosperity"}</span>
              {statusInfo?.openrouter_configured ? (
                <span className="krishiAiBadge" title={`Powered by ${statusInfo.active_model}`}>
                  <Sparkles size={12} /> OpenRouter AI
                </span>
              ) : (
                <span className="krishiAiBadge offline" title="Knowledge Base Active">
                  📚 ICAR Knowledge Base
                </span>
              )}
            </div>
            <p className="krishiSubtitle">
              {lang === "hi"
                ? "फसल सुरक्षा, कीट-रोग, खाद-पानी, मौसम एवं सरकारी योजनाओं का आपका डिजिटल साथी"
                : "Your AI companion for crops, disease diagnosis, fertilizers, irrigation & schemes"}
            </p>
          </div>
        </div>

        <div className="krishiHeaderActions">
          {messages.length > 0 && (
            <button
              className="button secondary sm clearChatBtn"
              onClick={handleClearChat}
              title={lang === "hi" ? "चैट मिटाएं" : "Clear conversation"}
            >
              <Trash2 size={15} />
              <span>{lang === "hi" ? "चैट साफ करें" : "Clear Chat"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Farm & IoT Context Pill Bar */}
      {(farmContext || (iotContext && iotContext.soil_moisture !== undefined)) && (
        <div className="krishiContextBar">
          <span className="contextLabel">
            🌾 {lang === "hi" ? "सक्रिय खेत संदर्भ:" : "Active Field Context:"}
          </span>
          {farmContext?.current_crop && (
            <span className="contextChip">
              <Wheat size={13} /> {farmContext.current_crop}
            </span>
          )}
          {farmContext?.soil_type && (
            <span className="contextChip">
              🌱 {farmContext.soil_type}
            </span>
          )}
          {iotContext?.soil_moisture !== undefined && (
            <span className="contextChip iotChip">
              <Radio size={13} color="#0284c7" />
              {lang === "hi" ? "नमी" : "Soil Moisture"}: {iotContext.soil_moisture}%
            </span>
          )}
          {farmContext?.location_name && (
            <span className="contextChip locationChip">
              📍 {farmContext.location_name.split(",")[0]}
            </span>
          )}
        </div>
      )}

      {/* Chat Messages Body */}
      <div className="krishiChatMessages">
        {messages.length === 0 ? (
          <div className="krishiWelcomeCard card">
            <div className="welcomeIconCircle">
              <Bot size={44} color="#15803d" />
            </div>
            <h2>Namaste! 🙏 मैत्री कृषि सहायक में आपका स्वागत है</h2>
            <p className="welcomeDesc">
              {lang === "hi"
                ? "मैं भारतीय कृषि, फसलों के रोग-कीट, पोषक तत्व, सिंचाई, मौसम और सरकारी योजनाओं पर आपकी सहायता के लिए तैयार हूँ। मुझसे हिन्दी, हिंग्लिश या इंग्लिश में पूछें।"
                : "Ask me any farming question in Hindi, Hinglish or English. I can help you with crop diseases, fertilizer dosing, irrigation scheduling, and government schemes."}
            </p>

            <div className="quickPromptSection">
              <div className="quickPromptHeader">
                <HelpCircle size={15} />
                <span>{lang === "hi" ? "अक्सर पूछे जाने वाले प्रश्न (टैप करें):" : "Suggested farming questions (Click to ask):"}</span>
              </div>
              <div className="quickChipsGrid">
                {QUICK_QUESTIONS.map((q) => (
                  <button
                    key={q.id}
                    className="quickChipBtn"
                    onClick={() => handleSend(lang === "hi" ? q.queryHi : q.queryEn)}
                  >
                    <span className="quickChipIcon">{q.icon}</span>
                    <span className="quickChipText">
                      {lang === "hi" ? q.labelHi : q.labelEn}
                    </span>
                    <ArrowUpRight size={14} className="quickChipArrow" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={idx} className={`chatBubbleWrap ${m.role}`}>
              {m.role === "assistant" && (
                <div className="botAvatarBubble">
                  <Bot size={18} color="#ffffff" />
                </div>
              )}
              <div className={`chatBubble ${m.role} ${m.isError ? "errorBubble" : ""}`}>
                <div className="bubbleContent">
                  {m.content.split("\n").map((line, lIdx) => (
                    <React.Fragment key={lIdx}>
                      {line}
                      {lIdx < m.content.split("\n").length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>

                {m.sources && m.sources.length > 0 && (
                  <div className="compactSourcesWrap">
                    <button
                      type="button"
                      className="compactSourcesToggle"
                      onClick={() => setExpandedSources(prev => ({ ...prev, [idx]: !prev[idx] }))}
                      title={lang === "hi" ? "स्रोत विवरण देखें" : "Toggle sources"}
                    >
                      <span className="sourceTagLabel">
                        📚 {m.sources.length === 1 ? (lang === "hi" ? "स्रोत" : "Source") : (lang === "hi" ? "स्रोत" : "Sources")} ({Math.min(m.sources.length, 3)})
                      </span>
                      <span className="sourceToggleArrow">
                        {expandedSources[idx] ? "▲" : "▼"}
                      </span>
                    </button>

                    {expandedSources[idx] && (
                      <div className="compactSourcesContent">
                        {m.sources.slice(0, 3).map((s, sIdx) => {
                          const title = typeof s === "object" ? s.title : s;
                          const srcOrg = typeof s === "object" ? (s.organization || s.source || s.domain) : null;
                          const url = typeof s === "object" ? s.url : null;
                          const tier = typeof s === "object" ? (s.source_tier || "") : "";
                          const srcType = typeof s === "object" ? (s.source_type || "") : "";
                          const pubDate = typeof s === "object" ? s.published_date : null;
                          const isOfficial = srcType === "official_verified" || tier === "AUTHORITATIVE" || srcType === "LIVE_WEB_OFFICIAL";
                          const isInstitutional = tier === "INSTITUTIONAL" || srcType === "LIVE_WEB_INSTITUTIONAL";
                          const isGeneralWeb = tier === "GENERAL_WEB" || srcType === "LIVE_WEB_GENERAL";

                          return (
                            <div key={sIdx} className="compactSourceItem">
                              <span className="compactSourceDot">•</span>
                              <span className="compactSourceText">
                                {srcOrg ? <strong>{srcOrg} — </strong> : null}
                                {url ? (
                                  <a
                                    href={url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: "#1d4ed8", textDecoration: "underline" }}
                                    title={url}
                                  >
                                    {title}
                                  </a>
                                ) : (
                                  title
                                )}
                                {isOfficial && (
                                  <span style={{ marginLeft: "6px", fontSize: "0.72rem", color: "#15803d", fontWeight: 600 }}>
                                    ✓ Official
                                  </span>
                                )}
                                {isInstitutional && (
                                  <span style={{ marginLeft: "6px", fontSize: "0.72rem", color: "#2563eb", fontWeight: 600 }}>
                                    🏛️ Institutional
                                  </span>
                                )}
                                {isGeneralWeb && (
                                  <span style={{ marginLeft: "6px", fontSize: "0.72rem", color: "#4b5563", fontWeight: 600 }}>
                                    🌐 Web
                                  </span>
                                )}
                                {pubDate && (
                                  <span style={{ marginLeft: "6px", fontSize: "0.70rem", color: "#6b7280" }}>
                                    ({pubDate})
                                  </span>
                                )}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                <div className="bubbleFooter">
                  <span className="bubbleTime">
                    {new Date(m.timestamp || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                  {m.role === "assistant" && (
                    <button
                      className="copyBtn"
                      onClick={() => handleCopy(m.content, idx)}
                      title="Copy response"
                    >
                      {copiedIndex === idx ? <Check size={13} color="#16a34a" /> : <Copy size={13} />}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="chatBubbleWrap assistant">
            <div className="botAvatarBubble">
              <Bot size={18} color="#ffffff" />
            </div>
            <div className="chatBubble assistant loadingBubble">
              <div className="typingIndicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className="loadingText">
                {lang === "hi" ? "मैत्री कृषि सहायक सोच रहा है..." : "Maitri is thinking..."}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Sticky Bottom Input Box */}
      <div className="krishiInputArea card">
        {error && (
          <div className="chatErrorNotice">
            <AlertCircle size={15} color="#dc2626" />
            <span>{error}</span>
          </div>
        )}

        <div className="inputRow">
          <textarea
            ref={inputRef}
            className="chatTextInput"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              lang === "hi"
                ? "अपनी फसल, बीमारी या खाद से जुड़ा सवाल यहाँ पूछें... (Enter दबाएं)"
                : "Ask about crop diseases, fertilizers, irrigation... (Press Enter)"
            }
            rows={1}
            disabled={loading}
          />
          <button
            className="button sendBtn"
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            aria-label="Send message"
          >
            {loading ? <RefreshCw size={18} className="spin" /> : <Send size={18} />}
          </button>
        </div>

        <div className="inputFooterHelp">
          <span>
            💡 {lang === "hi" ? "हिन्दी, English या Hinglish में टाइप करें" : "Type in Hindi, English, or Hinglish"}
          </span>
          <span className="disclaimerText">
            ⚠️ {lang === "hi" ? "सटीक दवा छिड़काव से पहले कृषि वैज्ञानिक (केवीके) से सलाह लें।" : "Consult local KVK before chemical spraying."}
          </span>
        </div>
      </div>
    </div>
  );
}
