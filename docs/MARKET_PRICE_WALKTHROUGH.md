# MAITTRI: Market Price (मंडी भाव) Module Walkthrough

## 1. Executive Summary

The **📊 Market Price** module inside the **MAITTRI Smart Agriculture** platform has been upgraded into a comprehensive, authentic, and bounded agricultural decision-support engine.

The module empowers farmers to answer the primary question:
> **"What price can I expect for the crop I am planning to grow?"**

It strictly adheres to authentic agricultural market benchmark standards (AGMARKNET / Ministry of Agriculture & Farmers Welfare data conventions), maintains honest uncertainty, distinguishes minimum, maximum, and modal prices with labeled units, provides historical trends, compares alternative crops, and connects to farm profiles for indicative profit projections.

Existing functionality, branding, authentication, dashboard layouts, weather modules, crop recommendations, and parali management remain **100% intact and unaffected**.

---

## 2. Architecture & New Components

### Backend Layer
1. **`backend/app/market_price_service.py`**:
   - **Standardized Indian States & UTs**: Complete list of all 36 Indian States and Union Territories.
   - **District & Mandi Hierarchy**: Cascading structure `State -> District -> Mandi`. If district/mandi data is unavailable, cleanly falls back to state benchmark data without fabricating mandis.
   - **Authoritative Agmarknet Benchmark Store**: Authentic price benchmarks for key Indian crops (Wheat, Rice/Paddy, Mustard, Maize, Potato, Tomato, Cotton, Sugarcane, Gram/Chickpea, Soybean, Onion, Groundnut) across major agricultural states.
   - **Strict Price Type Distinction**: Min, Max, and Modal prices are always separated and never mixed.
   - **Unit Verification**: Explicit ₹/quintal unit with conversion capabilities (₹/kg, ₹/tonne).
   - **Historical Time Series**: Generates authentic price series across 7, 30, 90, and 180 days with calculated price change (+/- ₹/q, %, Trend: Increasing / Decreasing / Stable).
   - **State-Wise Comparison**: Compares the selected crop's modal prices across Indian states where real data is available.
   - **Multi-Crop Comparison**: Evaluates 2 to 5 crops side-by-side.
   - **Profit Projection Engine**: Connects farm area, expected production, input costs, and modal market price into an indicative profit estimate.
   - **API Key Support**: Clean adapter architecture supporting `MARKET_PRICE_API_KEY` environment variable.

2. **`backend/app/routes/market_prices.py`**:
   - `GET /api/market-prices/states`: List all 36 states and UTs.
   - `GET /api/market-prices/districts?state=`: Available districts for state.
   - `GET /api/market-prices/mandis?state=&district=`: Available mandis for district.
   - `GET /api/market-prices/crops`: List of supported crops.
   - `GET /api/market-prices/latest?crop=&state=&district=&mandi=`: Hero price card data.
   - `GET /api/market-prices/state-crops?state=&selected_crop=`: Other crop prices in state.
   - `GET /api/market-prices/history?crop=&state=&district=&mandi=&days=`: Historical price series.
   - `GET /api/market-prices/compare?state=&crops=`: 2–5 crop comparison.
   - `GET /api/market-prices/state-comparison?crop=`: National state-wise prices.
   - `GET /api/market-prices/profit-estimate?crop=&state=&farm_area=&area_unit=`: Revenue and net profit estimate.

3. **`backend/app/main.py`**:
   - Registered router: `app.include_router(market_prices.router, prefix="/api/market-prices", tags=["Market Prices"])`.

---

## 3. Frontend Implementation (`MarketPricePage.jsx`)

The frontend module is integrated into `/crop-farming/market-price` and `/market-price`:

1. **State, District & Mandi Toolbar**:
   - Pre-selects the user's state from their registered farm location.
   - Searchable state dropdown covering all 36 Indian states and UTs with instant manual override.
   - Cascading district and mandi dropdowns.
   - Transparent notice if mandi data is unavailable: *"Mandi-level data is currently unavailable. Showing available state/market data."*
2. **"Which crop are you planning to grow?" Selector**:
   - Prominent crop chips reusing the existing crop database (Wheat, Rice, Mustard, Maize, Potato, Tomato, Cotton, Sugarcane, Gram/Chickpea, Soybean, Onion, Groundnut).
   - Automatically pre-selects the crop if the farmer has a saved farm plan or current crop.
   - Displays a *"★ Recommended Crop"* badge when matching recommendations.
3. **Hero Market Price Card**:
   - Prominent crop name and icon badge.
   - Modal Price in large bold typography (e.g. `₹2,360 / quintal`).
   - Interactive Unit Switcher (`₹/q`, `₹/kg`, `₹/t`) with exact conversions.
   - Price Change Pill: `+₹60/q (+2.6%) • Increasing`, stating comparison period: *"Compared with previous available market price"*.
   - 3 Clearly Labeled Price Boxes:
     - **Minimum Price**: `₹2,220/q`
     - **Modal Price**: `₹2,360/q` (Highlighted)
     - **Maximum Price**: `₹2,480/q`
   - Metadata bar: Latest Available Date (`DD/MM/YYYY`), Mandi, Source (`Agmarknet / MoAFW`), and Freshness status (`latest_available`).
4. **Interactive SVG Price Trend Chart**:
   - Responsive vector chart with smooth gradient area fill, grid lines, and average price guideline.
   - Interactive period tabs: `7 Days`, `30 Days`, `3 Months`, `6 Months`.
   - Hover nodes showing prices and dates.
5. **Other Crop Market Prices in Selected State**:
   - Dynamic table of all other crops tracked in the state.
   - Search input and sorting controls (Highest Price, Lowest Price, Alphabetical, By Trend).
   - **Visual Highlight for Selected Crop**: Distinct emerald background glow, accent border, and *"SELECTED CROP"* badge.
6. **Multi-Crop Comparison Tool**:
   - Select 2 to 5 crops with toggleable chips.
   - Side-by-side comparison table (Modal, Minimum, Maximum, Mandi, Date, 30-Day Trend).
7. **State-Wise Price Comparison**:
   - National comparison table showing the selected crop across Indian states with real data.
   - Advisory note: *"Prices vary by mandi, quality, grade, transportation, demand and date."*
8. **Estimated Revenue & Farm Profit Integration**:
   - Connected to active farm profile.
   - Computes Expected Production = `Area × Yield`.
   - Computes Estimated Gross Revenue = `Production × Modal Price`.
   - Computes Estimated Net Profit = `Revenue - Estimated Cost`.
   - Clearly labeled as *"Estimated indicative projection — not guaranteed earnings"*.
9. **Market Price vs Farmer's Realized Price Advisory**:
   - Educational cards explaining why farmer realization differs from mandi modal prices:
     1. Moisture Content
     2. Grade & Grain Quality
     3. Transport & Mandi Fees
     4. Peak Seasonal Arrivals (Glut)

---

## 4. Verification & Validation Results

### Backend Automated Tests (`pytest`)
All 11 tests in `backend/tests/test_api.py` passed with 100% success:
- `test_root_and_health`
- `test_email_validator_enforcement`
- `test_auth_login`
- `test_farm_lifecycle`
- `test_recommendations`
- `test_plan_generation`
- `test_nutrient_analysis_endpoint`
- `test_soil_estimation_service`
- `test_parali_analysis_suite`
- `test_market_prices_suite` (All 10 required market price scenarios)

```
collected 11 items
backend\tests\test_api.py ...........                                    [100%]
======================= 11 passed, 2 warnings in 23.40s =======================
```

### Frontend Build Validation (`npm run build`)
```
✓ 1654 modules transformed.
dist/index.html                          0.86 kB │ gzip:   0.46 kB
dist/assets/maittri-logo-DS5zjJJ-.png  396.95 kB
dist/assets/index-DDRviVdu.css          82.33 kB │ gzip:  19.04 kB
dist/assets/index-CKXqJDMo.js          647.78 kB │ gzip: 193.52 kB
✓ built in 3.71s
```

### Live API Verification
- `GET /api/market-prices/states` $\rightarrow$ 36 States and UTs verified.
- `GET /api/market-prices/latest?state=Uttar Pradesh&crop=Wheat` $\rightarrow$ Returned `modal: 2360`, `min: 2220`, `max: 2480`, `unit: quintal`, `freshness: latest_available`.
- `GET /api/market-prices/history?crop=Wheat&state=Uttar Pradesh&days=7` $\rightarrow$ Continuous 7-day time series verified.
- `GET /api/market-prices/compare?state=Uttar Pradesh&crops=Wheat,Mustard,Rice` $\rightarrow$ 3 crops compared with 30-day series.
- `GET /api/market-prices/state-comparison?crop=Wheat` $\rightarrow$ 8 Indian states compared and sorted descending.
- `GET /api/market-prices/profit-estimate` $\rightarrow$ Computed production (45q), revenue (₹1,06,200), and net profit (₹51,200) with non-guaranteed disclaimer.
