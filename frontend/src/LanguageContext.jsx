import React, { createContext, useContext, useState, useEffect } from "react";
import { T } from "./i18n";

export const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => localStorage.getItem("lang") || "en");

  const setLang = (newLang) => {
    localStorage.setItem("lang", newLang);
    setLangState(newLang);
    document.documentElement.lang = newLang;
  };

  useEffect(() => {
    // Listen for storage changes across windows/tabs
    const handleStorage = (e) => {
      if (e.key === "lang" && e.newValue) {
        setLangState(e.newValue);
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const t = T[lang] || T.en;

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    const fallbackLang = localStorage.getItem("lang") || "en";
    const change = (x) => {
      localStorage.setItem("lang", x);
      document.documentElement.lang = x;
    };
    const t = T[fallbackLang] || T.en;
    const res = [fallbackLang, change, t];
    res.lang = fallbackLang;
    res.setLang = change;
    res.changeLang = change;
    res.t = t;
    return res;
  }
  const res = [ctx.lang, ctx.setLang, ctx.t];
  res.lang = ctx.lang;
  res.setLang = ctx.setLang;
  res.changeLang = ctx.setLang;
  res.t = ctx.t;
  return res;
}

export default LanguageContext;
