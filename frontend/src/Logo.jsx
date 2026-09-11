import React from "react";
import logoImg from "./assets/maittri-logo.png";

/**
 * Reusable MAITTRI Logo Component
 * 
 * Supports variants:
 * - 'icon': circular badge logo only (with custom size or preset sizes)
 * - 'stacked': logo with MAITTRI / मैत्री and tagline below
 * - 'horizontal': logo on left, MAITTRI / tagline on right
 * 
 * Preset sizes:
 * - 'splash': 140px
 * - 'login': 110px
 * - 'sidebar': 64px
 * - 'compact': 40px
 * - 'sm': 32px
 */
export default function Logo({
  size = "sidebar",
  className = "",
  style = {},
  variant = "icon",
  showText = false,
  showTagline = false,
  lang = "en"
}) {
  const sizeMap = {
    splash: 140,
    login: 110,
    sidebar: 64,
    compact: 42,
    sm: 32,
    md: 56,
    lg: 96,
    xl: 140
  };

  const pixelSize = typeof size === "number" ? size : (sizeMap[size] || 64);

  const imgElement = (
    <img
      src={logoImg}
      alt="MAITTRI Logo"
      width={pixelSize}
      height={pixelSize}
      className={`maittriLogoImg ${className}`}
      style={{
        width: pixelSize,
        height: pixelSize,
        objectFit: "contain",
        display: "inline-block",
        verticalAlign: "middle",
        borderRadius: "50%",
        flexShrink: 0,
        ...style
      }}
      loading="eager"
    />
  );

  if (!showText && variant === "icon") {
    return imgElement;
  }

  if (variant === "horizontal") {
    return (
      <div className={`maittriBrandHorizontal ${className}`} style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
        {imgElement}
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6 }}>
            <span style={{ fontWeight: 800, fontSize: pixelSize > 50 ? 20 : 16, color: "#14532d", letterSpacing: "0.5px" }}>
              MAITTRI
            </span>
            <span style={{ fontWeight: 700, fontSize: pixelSize > 50 ? 16 : 14, color: "#16a34a" }}>
              मैत्री
            </span>
          </div>
          {showTagline && (
            <span style={{ fontSize: 11.5, color: "#475569", fontWeight: 500 }}>
              किसान का साथी, समृद्धि की शुरुआत
            </span>
          )}
        </div>
      </div>
    );
  }

  // Stacked variant (used in sidebar, login, splash)
  return (
    <div className={`maittriBrandStacked ${className}`} style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
      {imgElement}
      {(showText || showTagline) && (
        <div style={{ marginTop: 8, lineHeight: 1.25 }}>
          {showText && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
              <span style={{ fontWeight: 800, fontSize: pixelSize > 90 ? 24 : 18, color: "#14532d", letterSpacing: "1px" }}>
                MAITTRI
              </span>
              <span style={{ fontWeight: 700, fontSize: pixelSize > 90 ? 18 : 15, color: "#16a34a" }}>
                मैत्री
              </span>
            </div>
          )}
          {showTagline && (
            <div style={{ fontSize: pixelSize > 90 ? 13 : 11, color: "#15803d", fontWeight: 600, marginTop: 4 }}>
              किसान का साथी, समृद्धि की शुरुआत
            </div>
          )}
        </div>
      )}
    </div>
  );
}
