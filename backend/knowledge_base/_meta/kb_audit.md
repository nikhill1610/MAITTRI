# MAITTRI Knowledge Base Comprehensive Audit Report

**Date**: September 2026  
**Auditor**: Antigravity Technical & Agronomic Audit Engine  
**Target Directory**: `backend/knowledge_base/`  
**Total Existing Files**: 31 Markdown (`.md`), 6 Category Databases (`.json`)

---

## 1. Executive Summary & Audit Baseline

The existing MAITTRI knowledge base provides foundational coverage of North Indian agriculture across 11 directory categories. However, the audit revealed key structural and agronomic limitations:
1. **Shallow Depth**: Existing crop guides average 30–45 lines, lacking variety matrices, agro-climatic distinctions (e.g. NEPZ vs NWPZ for UP), seed treatment recipes, weed control, and post-harvest handling.
2. **Coupled Topics**: Combined files (e.g. `rice_blast_sheath_blight.md`, `potato_tomato_blight.md`) combine two distinct biological pathogens with different epidemiology and management protocols into a single document, impeding precise vector chunk retrieval.
3. **Missing Metadata**: Files lack standard YAML schema attributes including `doc_id`, `crop_stage`, `season`, `soil_type`, `evidence_tier`, `valid_from`, and `farmer_query_aliases`.
4. **Registry Discrepancies**: `crops/crops.json` only contains 5 crops (omits Tomato, despite `crops/tomato_guide.md` existing).

---

## 2. Complete File Audit Matrix

| # | Current File Path | Category | Focus Crop / Topic | Quality Assessment | Action Assigned | Target State / Split Strategy |
|---|---|---|---|---|---|---|
| 1 | `crops/wheat_guide.md` | Crops | Wheat (*Triticum aestivum*) | Basic overview, lacks NEPZ/NWPZ varieties, seed rate details, weed control | **REWRITE & EXPAND** | Deepen into full crop decision pathway (sowing, varieties, CRI, nutrients, storage) |
| 2 | `crops/rice_guide.md` | Crops | Rice (*Oryza sativa*) | Brief text, misses DSR vs transplanted, AWD timing, nursery management | **REWRITE & EXPAND** | Complete pathway covering nursery, puddling, AWD, split urea, zinc, blast prevention |
| 3 | `crops/maize_guide.md` | Crops | Maize (*Zea mays*) | Brief, missing Kharif vs Rabi season distinctions, drainage sensitivity | **REWRITE & EXPAND** | Full pathway covering hybrid selection, FAW whorl monitoring, moisture management |
| 4 | `crops/mustard_guide.md` | Crops | Mustard (*Brassica juncea*) | Short guide, misses sulphur requirement and aphid ETL timing | **REWRITE & EXPAND** | Full pathway covering oilseed varieties, sulphur dosage, late afternoon spray safety |
| 5 | `crops/potato_guide.md` | Crops | Potato (*Solanum tuberosum*) | Lacks seed tuber treatment, late blight forecast criteria, dehaulming | **REWRITE & EXPAND** | Full pathway covering tuber cutting/curing, high potassium need, dehaulming |
| 6 | `crops/tomato_guide.md` | Crops | Tomato (*Solanum lycopersicum*) | Very brief, lacks staking, blossom end rot calcium care, ToLCV vectors | **REWRITE & EXPAND** | Full pathway covering nursery protection, staking, pruning, virus vector management |
| 7 | `diseases/wheat_yellow_rust.md` | Diseases | Stripe Rust (*Puccinia striiformis*) | Reasonable symptoms, needs resistant varieties list and strict label gate | **REWRITE** | Update with full epidemiology, lookalikes, resistant varieties, and CIBRC safety gate |
| 8 | `diseases/rice_blast_sheath_blight.md` | Diseases | Blast & Sheath Blight in Rice | Merged two distinct pathogens (fungi *Pyricularia* vs *Rhizoctonia*) | **SPLIT & KEEP PARENT** | Keep as parent overview; create dedicated `rice_blast.md` and `rice_sheath_blight.md` |
| 9 | `diseases/mustard_white_rust.md` | Diseases | White Rust (*Albugo candida*) | Short, misses staghead floral malformation symptoms | **REWRITE** | Deepen with leaf pustule vs staghead phases, prophylactic vs curative sprays |
| 10 | `diseases/potato_tomato_blight.md` | Diseases | Early & Late Blight | Merges two distinct organisms (*Phytophthora* vs *Alternaria*) across two crops | **SPLIT & KEEP PARENT** | Keep as parent overview; create dedicated `potato_late_blight.md` and `tomato_early_blight.md` |
| 11 | `pests/wheat_stem_borer.md` / `rice_stem_borer.md` | Pests | Yellow Stem Borer (*Scirpophaga incertulas*) | Brief summary, needs pheromone trap numbers and clipping tips | **REWRITE** | Deepen with dead heart vs white earhead, egg mass clipping, biocontrol (*Trichogramma*) |
| 12 | `pests/maize_fall_armyworm.md` | Pests | Fall Armyworm (*Spodoptera frugiperda*) | Lacks early whorl identification, pheromone density, safe whorl application | **REWRITE** | Deepen with early window scouting, sand/ash/neem application, pheromone traps |
| 13 | `pests/mustard_aphids.md` | Pests | Mustard Aphid (*Lipaphis erysimi*) | Lacks ETL quantification, honeybee pollinator safety hours | **REWRITE** | Deepen with ETL (1.5-2 cm colony on 20% plants), late afternoon spray protocol |
| 14 | `pests/tomato_whitefly_curl.md` | Pests | Whitefly (*Bemisia tabaci*) | Needs vector transmission mechanics, yellow sticky traps, barrier cropping | **REWRITE** | Deepen with sticky trap density (10-12/acre), border maize crops, ToLCV management |
| 15 | `pests/gram_pod_borer.md` | Pests | Gram Pod Borer (*Helicoverpa armigera*) | Lacks bird perches, HaNPV application guidelines | **REWRITE** | Deepen with T-perches (20/acre), intercropping with mustard/coriander, pheromone traps |
| 16 | `fertilizers/nitrogen_deficiency_urea.md` | Fertilizers | Nitrogen (N) & Urea | Short, lacks Neem-coated urea, Nano urea foliar rates, V-shape lookalikes | **REWRITE** | Complete guide: V-shaped chlorosis, 3-split schedule, conversion arithmetic |
| 17 | `fertilizers/phosphorus_deficiency_dap.md` | Fertilizers | Phosphorus (P) & DAP / SSP | Short, lacks basal placement depth and SSP sulphur advantage for pulses | **REWRITE** | Complete guide: purpling/bronzing symptoms, 4-5 cm placement, DAP vs SSP guide |
| 18 | `fertilizers/potassium_deficiency_mop.md` | Fertilizers | Potassium (K) & MOP / SOP | Lacks chloride sensitivity warnings for potato seed and tuber quality | **REWRITE** | Complete guide: marginal scorch, lodging resistance, MOP vs SOP distinctions |
| 19 | `fertilizers/micronutrients_zinc_iron.md` | Fertilizers | Zinc (Zn), Iron (Fe), Sulphur (S) | Covers symptoms, lacks lime buffer calculation for foliar zinc spray | **REWRITE** | Complete guide: Khaira disease in paddy, white bud in maize, iron chlorosis, zinc-DAP tank mix prohibition |
| 20 | `irrigation/wheat_irrigation_cri.md` | Irrigation | Crown Root Initiation (CRI) | Good concept, needs remaining 5 physiological stages and waterlogging warnings | **REWRITE** | Complete 6-stage wheat irrigation calendar, palewa moisture adjustments |
| 21 | `irrigation/rice_water_management.md` | Irrigation | Rice Water Management & AWD | Needs perforated pipe specifications and water table depth markers | **REWRITE** | Complete AWD protocol, field water tube installation, critical reproductive ponding |
| 22 | `irrigation/micro_irrigation_drip.md` | Irrigation | Drip & Sprinkler Systems | Brief overview, lacks fertigation scheduling and PMKSY subsidy norms | **REWRITE** | Complete guide: emitter spacing, fertigation advantages, maintenance, subsidy criteria |
| 23 | `crop_residue/parali_stubble_management.md` | Crop Residue | In-situ & Ex-situ Stubble Management | Good summary, needs machinery operational requirements (Super Seeder, Happy Seeder) | **REWRITE** | Complete residue guide: machinery horsepower, soil organic carbon gains, CRM scheme |
| 24 | `schemes/pm_kisan_scheme.md` | Schemes | PM-KISAN Samman Nidhi | Good structure, needs e-KYC steps, land record seeding, DBT grievance workflow | **REWRITE** | Complete eligibility, exclusion criteria, mandatory documentation, helpline 155261 |
| 25 | `schemes/pmfby_crop_insurance.md` | Schemes | PMFBY Crop Insurance | Needs 72-hour localized event cut-off, premium rates by season, sum insured | **REWRITE** | Complete guide: premium rates (2% Kharif, 1.5% Rabi), Crop Insurance App claim steps |
| 26 | `schemes/kcc_kisan_credit_card.md` | Schemes | Kisan Credit Card | Needs scale of finance formula, 7% standard rate with 3% prompt repayment subvention | **REWRITE** | Complete credit guide: limit calculation, collateral exemption up to ₹1.6 lakh, 4% net interest |
| 27 | `soil/soil_health_card.md` | Soil | Soil Health Card (SHC) | Lacks 12-parameter standard range table and soil sampling 'V' notch method | **REWRITE** | Complete guide: 12 parameters, sampling procedure, test interpretation guide |
| 28 | `soil/soil_ph_salinity.md` | Soil | Soil pH, Acidity & Sodic Soils | Needs gypsum requirement calculation and lime application for acid soils | **REWRITE** | Complete reclamation guide: acid soil liming, sodic soil gypsum, drainage leaching |
| 29 | `soil/soil_types_management.md` | Soil | Major Soil Types of India | Lacks UP-specific zone mapping (Alluvial plains, Bundelkhand black/red) | **REWRITE** | Complete guide: Alluvial, Black, Red, Sandy Loam properties, tillage & organic matter |
| 30 | `weather/weather_frost_heatwave_precautions.md` | Weather | Cold Wave, Frost & Terminal Heat | Needs critical temperature thresholds (frost <4°C, heat >35°C at anthesis) | **REWRITE** | Actionable guide: light evening irrigation, smoking boundaries, terminal heat foliar potassium |
| 31 | `Mountain_Farming/mountain_farming.md` | Mountain Farming | Hill Agriculture & High Altitude | Comprehensive but unstructured text, lacking YAML frontmatter and standard sections | **NORMALIZE** | Add YAML frontmatter, standardized headings, keep regional hill crop practices |

---

## 3. JSON Registries Audit

1. `crops/crops.json`:
   - Contains: Wheat, Rice, Mustard, Maize, Potato.
   - Finding: Missing Tomato. Needs Tomato added with complete schema parity (`crop`, `hindi_name`, `season`, `soil`, `water_requirement`, `fertilizer_general`, `common_issues`).
2. `diseases/diseases.json`:
   - Contains: Yellow Rust, Leaf Blast, Aphids, Late Blight, Fall Armyworm.
   - Finding: Mixes insect pests with fungal diseases. Needs synchronized entries for individual diseases (Rice Blast, Sheath Blight, Potato Late Blight, Tomato Early Blight, Mustard White Rust) and distinct pest records.
3. `fertilizers/fertilizers.json`:
   - Contains: 5 records on N, P, K, Micronutrients, Soil pH.
   - Status: High quality; will enrich with precise elemental vs product conversion formulas and nano-fertilizer guidance.
4. `irrigation/irrigation.json`:
   - Contains: 3 records on soil moisture, critical stages, micro-irrigation.
   - Status: Valid; enrich with AWD criteria and PMKSY guidelines.
5. `parali/parali.json`:
   - Contains: 2 records on in-situ and ex-situ management.
   - Status: Valid; enrich with CRM subsidy details.
6. `schemes/schemes.json`:
   - Contains: 4 records (PM-KISAN, PMFBY, Soil Health Card, PMKSY).
   - Finding: Missing Kisan Credit Card (KCC). Needs KCC added with complete schema parity.

---

## 4. Priority Expansions Planned (P0 & P1)

1. `weeds/wheat_phalaris_minor.md`: Management of resistant canary grass (*Phalaris minor*) in wheat.
2. `weeds/rice_echinochloa_weeds.md`: Management of barnyard grass (*Echinochloa colona/crus-galli*) in puddle and direct seeded rice.
3. `safety/pesticide_handling_ppe.md`: Farm safety, spray drift prevention, PPE requirements, container washing/disposal.
4. `storage/grain_storage_pests.md`: Post-harvest drying to <12% moisture, hermetic storage bags, khapra beetle prevention.
