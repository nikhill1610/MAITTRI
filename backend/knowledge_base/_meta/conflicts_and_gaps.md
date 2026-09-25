# Agronomic Evidence Conflicts, Boundary Limitations & Research Gaps

This document establishes the authoritative evidence boundary principles, agronomic conflict resolutions, and research gap register for the MAITTRI Agricultural Knowledge Base in accordance with `docs/DATA_AND_EVIDENCE.md` and `Deep_Research_Review.pdf`.

---

## 1. Core Evidentiary Principles

1. **No Uncalibrated Cross-State Generalization**: Agronomic practices, sowing dates, variety suitability, and fertilizer recommendations valid for Punjab or Haryana cannot be unthinkingly applied to Eastern Uttar Pradesh, Bundelkhand, or Bihar. Zone-specific distinctions (e.g., North Western Plains Zone [NWPZ] vs. North Eastern Plains Zone [NEPZ]) must be made explicit.
2. **Missing Evidence vs. Guessing**: If a numerical dosage, local variety name, or exact threshold is missing from verified ICAR or SAU packages of practices, it is flagged with `SOURCE_RESEARCH_REQUIRED` rather than approximated.
3. **Pesticide / Fungicide / Herbicide Statutory Gate**: Chemical recommendations must never be generated freely. No pesticide dose is recommended without current CIBRC/PPQS label registration for that exact `Crop x Pest/Disease` combination. Every chemical section must carry the mandatory regulatory caveat:
   > **Regulatory Safety Notice**: *Chemical recommendation requires current label verification with the Central Insecticides Board & Registration Committee (CIBRC) and local Krishi Vigyan Kendra (KVK) / State Agriculture Department officer before purchase or application.*

---

## 2. Identified Agronomic Disagreements & Clarifications

### A. Fertilizer Nutrient vs. Commercial Fertilizer Product
* **Common Error**: Confusing elemental nutrient doses (e.g. $120\text{ kg N/ha}$) with commercial fertilizer weight (e.g. $120\text{ kg Urea/ha}$).
* **Official Formula**:
  $$\text{Fertilizer Product Amount} = \frac{\text{Elemental Nutrient Required}}{\text{Active Nutrient Fraction in Product}}$$
  * For Nitrogen ($N$) from Urea ($46\% N$): $120\text{ kg } N \div 0.46 = 260.8\text{ kg Urea/ha}$ ($104.3\text{ kg Urea/acre}$).
  * For Phosphorus ($P_2O_5$) from DAP ($46\% P_2O_5, 18\% N$): $60\text{ kg } P_2O_5 \div 0.46 = 130.4\text{ kg DAP/ha}$ (which also supplies $130.4 \times 0.18 = 23.5\text{ kg } N$).
  * For Potassium ($K_2O$) from MOP ($60\% K_2O$): $40\text{ kg } K_2O \div 0.60 = 66.7\text{ kg MOP/ha}$ ($26.7\text{ kg MOP/acre}$).

### B. Wheat Irrigation Timing: Days After Sowing (DAS) vs. Physiological Stage
* **Conflict**: Some literature quotes CRI at 21 DAS, while others state 20–25 DAS.
* **Agronomic Truth**: Crown Root Initiation (CRI) is a physiological stage occurring when the crown roots emerge. In cool soils or deep sowing, CRI may delay to 25 DAS; in warm, sandy soils, it may occur at 20 DAS. If soil has adequate residual moisture from pre-sowing irrigation (*palewa*), irrigating too early in heavy soils causes yellowing from root hypoxia. The guide must explain *both* the 21-day guideline and the soil-moisture criterion.

### C. Rice Water Management: Continuous Submergence vs. Alternate Wetting & Drying (AWD)
* **Conflict**: Traditional practice demands 5 cm continuous standing water throughout the season.
* **Modern ICAR/NRRI Recommendation**: Continuous ponding is only necessary during the first 1–2 weeks after transplanting (for seedling establishment) and during the reproductive stage (panicle initiation to flowering). During vegetative tillering, AWD (allowing water to recede until 15 cm below soil surface in a perforated field pipe) saves 25–30% water and reduces methane emissions without yield penalty.

### D. Mustard Aphid Spraying Time & Pollinator Protection
* **Conflict**: Spraying at the first sight of aphids vs. waiting for Economic Threshold Level (ETL).
* **Agronomic & Safety Truth**: Spraying before ETL (1.5–2.0 cm aphid colony on 20% central twigs, or 50 aphids/plant) is economically wasteful and destroys natural predators like ladybird beetles (*Coccinella septempunctata*). Chemical sprays must strictly be applied in late afternoon (after 3:30 PM) when honeybee foraging activity ceases.

### E. Leaf Yellowing Lookalikes (Diagnostic Discrimination)
* **Nitrogen Deficiency**: Generalized uniform yellowing starting strictly from older bottom leaves, progressing upwards in a 'V' shape along the midrib.
* **Zinc Deficiency (Khaira in Rice)**: Midrib remains green initially; reddish-brown or rusty spots appear on 3rd/4th leaf from top, leaves become brittle.
* **Iron Deficiency**: Interveinal chlorosis appearing strictly on the youngest top leaves; leaf veins remain sharp green while blade bleaches ivory-white. Common in high pH, calcareous soils.
* **Yellow Rust (Stripe Rust in Wheat)**: Bright yellow fungal urediniospores arranged in parallel linear stripes along leaf veins; rubs off as bright yellow powder on fingers. Thrives in cool, humid weather (10–15°C).
* **Sulphur Deficiency**: Yellowing appears on younger leaves first (unlike Nitrogen where it appears on older leaves first).

---

## 3. Dynamic Data Gaps (Live Routing Required)

The following parameters must never be hard-coded as static knowledge in RAG documents:
1. **Mandi Prices**: Wholesale rates fluctuate daily on AGMARKNET. The RAG document explains how modal prices are determined, how grades affect prices, and directs the farmer to live market feeds.
2. **Real-time Weather & Agromet Bulletins**: IMD updates bi-weekly block and district advisories. The RAG documents provide actionable conditional rules (e.g. "Do not spray if wind speed exceeds 15 km/h or rain is forecasted within 6 hours").
3. **Subsidy Amounts & Scheme Status**: Central and state allocations change annually. Documents specify eligibility rules, documentation needs, and portal verification steps.

---

## 4. Numerical Recommendations Provenance Audit

Every actionable numerical claim in MAITTRI must satisfy the 7-element traceability criteria:
$$\text{Traceability} = \text{Value} + \text{Unit} + \text{Crop} + \text{Stage/Condition} + \text{Geography} + \text{Exact Source} + \text{Version/Date}$$

| Parameter Category | Standard Unit | Governing Institutional Source | Traceability Status |
|---|---|---|---|
| **Basal NPK Fertilizer Rates** | kg/ha or kg/acre | ICAR-IISS / SAU Package of Practices | Verified (Tier A/B) |
| **Split Nitrogen Timing** | Days After Sowing (DAS) | ICAR-IIWBR / NRRI / IIMR | Verified (Tier A) |
| **CRI Irrigation Window** | 20–25 DAS | ICAR-IIWBR Karnal | Verified (Tier A) |
| **Aphid ETL Threshold** | 1.5–2.0 cm colony / terminal shoot | ICAR-DRMR Bharatpur | Verified (Tier A) |
| **Safe Grain Storage Moisture** | $\le 10\% - 12\%$ | IGGMRI Hapur & ICAR-CIPHET | Verified (Tier A) |
| **Ground Frost Temperature Trigger** | $< 4.0^\circ\text{C}$ nocturnal | IMD Agromet Advisory Services | Verified (Tier A) |
| **Terminal Heat Threshold in Wheat** | $> 30.0^\circ - 32.0^\circ\text{C}$ diurnal | ICAR-IIWBR / IMD | Verified (Tier A) |
| **PM-KISAN Installment Tranches** | ₹2,000 $\times$ 3 = ₹6,000/yr | DA&FW Operational Guidelines | Verified (Tier A) |
| **PMFBY Farmer Premium Share** | 2% Kharif, 1.5% Rabi, 5% Commercial | PMFBY Revised Guidelines | Verified (Tier A) |
| **KCC Net Effective Interest** | 4.0% p.a. (7% base - 3% PRI) | NABARD / RBI Master Circular | Verified (Tier A) |
| **KCC Collateral-Free Limit** | ₹1.60 Lakh (₹3 Lakh tie-up) | RBI Agricultural Credit Circular | Verified (Tier A) |
| **PMFBY Localized Reporting Window**| Strictly within 72 hours | PMFBY Operational Guidelines | Verified (Tier A) |

---

## 5. Pesticide & Regulatory Label Boundaries

All 23 chemical-containing documents in MAITTRI have been audited against the CIBRC Registered Uses compendium:
- **Mandatory Caveat**: 100% of chemical advice blocks explicitly mandate: *"Chemical recommendation requires current label verification with the Central Insecticides Board & Registration Committee (CIBRC) and local agricultural extension authorities before application."*
- **Restricted Use Pesticides (RUP)**: Aluminium Phosphide 56% tablets are explicitly categorized as Restricted Use Pesticides, prohibited in residential dwellings, and strictly restricted to gas-tight silos by certified operators.
- **Honeybee Stewardship**: In flowering crops (Mustard, Pulses, Vegetables), morning spraying is strictly prohibited. Application is restricted to late afternoon (after 3:30 PM) to protect pollinator populations.

---

## 6. Crop Completeness & Research Gaps Resolution Register

| Gap ID | Description | Prior Status | Current Resolution Status | Governing Knowledge Base Document(s) |
|:---:|:---|:---:|:---:|:---|
| **GAP-001** | **Bundelkhand Dryland Pulse Decision Pathway** | PARTIAL | **RESOLVED (Tier A)** | `crops/chickpea_lentil_bundelkhand_guide.md`<br>`diseases/pulse_wilt_root_rot.md` |
| **GAP-002** | **Western UP Sugarcane Decision Pathway & Red Rot Eradication** | MISSING | **RESOLVED (Tier A)** | `crops/sugarcane_guide.md`<br>`diseases/sugarcane_red_rot.md` |
| **GAP-003** | **Commercial Biostimulants, Amino Acids & Humic Acid Products** | UNVALIDATED | **REGULATORY CAUTION / SOURCE_RESEARCH_REQUIRED** | `fertilizers/biofertilizers_organic_manures.md`<br>(Explains FCO 2021 Schedule VI mandates; prohibits unvalidated proprietary commercial dosage claims). |
| **GAP-004** | **P1 Commercial Cash & Vegetable Expansion** (Onion, Soybean, Groundnut, Pigeonpea, Chilli, Banana, Cotton) | PLANNED | **RESOLVED (Tier A)** | `crops/onion_guide.md`<br>`crops/soybean_guide.md`<br>`crops/groundnut_guide.md`<br>`crops/pigeonpea_arhar_guide.md`<br>`crops/chilli_guide.md`<br>`crops/banana_guide.md`<br>`crops/cotton_guide.md` |
| **GAP-005** | **P1 Cross-Cutting Foundations** (Biofertilizers, Nematodes & Rodents, Climate Contingency, Farm Mechanization CHC) | PLANNED | **RESOLVED (Tier A)** | `fertilizers/biofertilizers_organic_manures.md`<br>`pests/nematodes_rodents_management.md`<br>`weather/climate_contingency_plans.md`<br>`machinery/farm_mechanization_chc.md` |
| **GAP-006** | **P2 National & Allied Agro-Ecosystems** (Protected Cultivation, Drones, Agroforestry, Mountain Farming, Dairy, Poultry, Fisheries, Apiculture) | PLANNED | **RESOLVED (Tier A)** | `horticulture/protected_cultivation_polyhouse.md`<br>`horticulture/precision_farming_drones.md`<br>`agroforestry/agroforestry_poplar_eucalyptus.md`<br>`Mountain_Farming/mountain_horticulture_temperate.md`<br>`allied/dairy_cattle_buffalo_management.md`<br>`allied/backyard_poultry_farming.md`<br>`allied/inland_freshwater_aquaculture.md`<br>`allied/apiculture_beekeeping.md` |

