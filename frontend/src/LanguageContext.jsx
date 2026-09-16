import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from "react";
import { T, t as tHelper } from "./i18n";

export const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const saved = localStorage.getItem("maittri_language") || localStorage.getItem("lang");
    return saved === "hi" ? "hi" : "en";
  });

  const setLang = useCallback((newLang) => {
    const validLang = newLang === "hi" ? "hi" : "en";
    localStorage.setItem("maittri_language", validLang);
    localStorage.setItem("lang", validLang);
    document.documentElement.lang = validLang;
    if (typeof document !== "undefined" && document.body) {
      document.body.setAttribute("data-lang", validLang);
    }
    setLangState(validLang);
  }, []);

  useEffect(() => {
    const validLang = lang === "hi" ? "hi" : "en";
    document.documentElement.lang = validLang;
    if (typeof document !== "undefined" && document.body) {
      document.body.setAttribute("data-lang", validLang);
    }
    localStorage.setItem("maittri_language", validLang);
    localStorage.setItem("lang", validLang);

    // Listen for storage events across tabs
    const handleStorage = (e) => {
      if ((e.key === "maittri_language" || e.key === "lang") && e.newValue) {
        if (e.newValue === "hi" || e.newValue === "en") {
          setLangState(e.newValue);
          document.documentElement.lang = e.newValue;
          if (typeof document !== "undefined" && document.body) {
            document.body.setAttribute("data-lang", e.newValue);
          }
        }
      }
    };
    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, [lang]);

  const dict = useMemo(() => T[lang] || T.en, [lang]);

  const translate = useCallback((key, fallback) => {
    return tHelper(key, fallback, lang);
  }, [lang]);

  // Extend dict with callable function t()
  const extendedT = useMemo(() => {
    const fn = (key, fallback) => translate(key, fallback);
    return new Proxy(fn, {
      get(target, prop) {
        if (typeof prop === "symbol" || prop === "then" || prop === "$$typeof" || prop === "toJSON") {
          return target[prop];
        }
        if (prop === "t") return translate;
        if (prop in dict && dict[prop] !== undefined) return dict[prop];
        const val = translate(prop, undefined);
        return (val !== undefined && val !== "") ? val : undefined;
      },
      apply(target, thisArg, args) {
        return translate(args[0], args[1]);
      }
    });
  }, [dict, translate]);

  const contextValue = useMemo(() => ({
    lang,
    setLang,
    changeLang: setLang,
    t: extendedT,
    translate,
    isHindi: lang === "hi",
    isEnglish: lang === "en"
  }), [lang, setLang, extendedT, translate]);

  return (
    <LanguageContext.Provider value={contextValue}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLang() {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    const fallbackLang = (localStorage.getItem("maittri_language") || localStorage.getItem("lang")) === "hi" ? "hi" : "en";
    const change = (x) => {
      const valid = x === "hi" ? "hi" : "en";
      localStorage.setItem("maittri_language", valid);
      localStorage.setItem("lang", valid);
      document.documentElement.lang = valid;
    };
    const dict = T[fallbackLang] || T.en;
    const translate = (k, f) => tHelper(k, f, fallbackLang);
    const fn = (k, f) => translate(k, f);
    const t = new Proxy(fn, {
      get(target, prop) {
        if (typeof prop === "symbol" || prop === "then" || prop === "$$typeof" || prop === "toJSON") {
          return target[prop];
        }
        if (prop === "t") return translate;
        if (prop in dict && dict[prop] !== undefined) return dict[prop];
        const val = translate(prop, undefined);
        return (val !== undefined && val !== "") ? val : undefined;
      },
      apply(target, thisArg, args) {
        return translate(args[0], args[1]);
      }
    });
    const res = [fallbackLang, change, t, translate];
    res.lang = fallbackLang;
    res.setLang = change;
    res.changeLang = change;
    res.t = t;
    res.translate = translate;
    res.isHindi = fallbackLang === "hi";
    res.isEnglish = fallbackLang === "en";
    return res;
  }

  const res = [ctx.lang, ctx.setLang, ctx.t, ctx.translate];
  res.lang = ctx.lang;
  res.setLang = ctx.setLang;
  res.changeLang = ctx.setLang;
  res.t = ctx.t;
  res.translate = ctx.translate;
  res.isHindi = ctx.isHindi;
  res.isEnglish = ctx.isEnglish;
  return res;
}

export default LanguageContext;
