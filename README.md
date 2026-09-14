# MAITTRI – Smart Agriculture & Seva Operator Decision Support Platform

> *"किसान का साथी, समृद्धि की शुरुआत"*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.1+-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-7.1+-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?style=flat&logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**MAITTRI** (मैत्री) is an enterprise-grade, multi-channel precision agriculture and agronomy decision-support platform designed for farmers, agronomists, and **Authorized Agriculture / Seva Operators**. It combines multi-criteria agronomic intelligence, localized meteorological data, market economics, physical IoT edge sensing (ESP32 / ESP8266), laboratory soil test tracking, and provider-agnostic SMS/IVR access.

---

## 🏛️ Core Architectural Principle: ONE INTELLIGENCE → MULTIPLE ACCESS CHANNELS

MAITTRI is architected on the premise that **digital agriculture must not assume that every farmer has a smartphone or high-speed mobile internet**. A farmer using a basic keypad phone via SMS or IVR, visiting an authorized Seva center, or using the web app receives identical, consistent agronomic intelligence driven by the central **MAITTRI Farm Brain**.

```
                           MAITTRI
                              |
                    MAITTRI FARM BRAIN
                              |
          -----------------------------------------
          |              |             |           |
       FARMER        OPERATOR        WEB       IoT/API
       PORTAL         PORTAL
          |              |
          -----------------------------------------
                         |
                  COMMON FARM DATA
                         |
      ------------------------------------------------
      |       |       |       |       |       |       |
    Soil   Crop   Weather  Market  Schemes Insurance IoT
      |       |       |       |       |       |       |
      ------------------------------------------------
                         |
                   DECISION ENGINE
                         |
               -----------------------
               |          |          |
              WEB        SMS        IVR
```

---

## Table of Contents

- [Overview & Core Value Proposition](#overview--core-value-proposition)
- [Two User Portals (Farmer & Authorized Seva Operator)](#two-user-portals)
- [MAITTRI Farm Brain (Decision Intelligence Engine)](#maittri-farm-brain)
- [SMS & IVR Communication Architecture](#sms--ivr-communication-architecture)
- [Certified Soil Testing & Service Request Tracking](#certified-soil-testing--service-requests)
- [Key Features](#key-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Directory Structure](#project-directory-structure)
- [Quick Start (Windows PowerShell)](#quick-start-windows-powershell)
- [Environment Variables & Credentials](#environment-variables)
- [IoT Edge Hardware (ESP32 / ESP8266)](#iot-edge-hardware-esp32--esp8266)
- [API Documentation](#api-documentation)
- [Production Deployment (Render, Vercel, Supabase)](#production-deployment-render-vercel-supabase)
- [Demo Mode vs Production Requirements](#demo-mode-vs-production-requirements)
- [Agricultural Safety & AI Accuracy Disclaimers](#agricultural-safety--accuracy-disclaimers)
- [Security & Best Practices](#security--best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)
- [License](#license)

---

## Overview & Core Value Proposition

Smallholder and commercial farmers face complex, interconnected challenges: unpredictable weather fluctuations, soil nutrient degradation, fluctuating mandi prices, crop residue management (stubble burning/parali), and pest infestations. Furthermore, millions of smallholders lack smartphones or digital literacy.

**MAITTRI** solves this through a unified multi-access ecosystem:
1. **Single Source of Truth**: Central Farm Profile linked to a unique **MAITTRI Farm ID** (`MT-FARM-XXXXXX`) across all channels.
2. **Central Farm Brain**: Generates prioritized, explainable daily agronomic actions (*"What Should I Do Today?"*, *"Why?"*, *"Risk?"*, *"Data Used?"*, *"What Information is Missing?"*).
3. **Assisted Farmer Seva**: Allows authorized operators to register farmers, book lab tests, upload farm documents, and broadcast emergency weather/crop advisories.
4. **Keypad Phone Access**: Provider-agnostic SMS alerts and IVR interactive voice menus for farmers without smartphones.
5. **Calibrated Telemetry**: Clear separation between *indicative* in-field IoT sensor readings and *certified laboratory* soil tests.

---

## Two User Portals

MAITTRI implements role-based access control with distinct portals:

### 1. Farmer Web/App Portal (`FARMER`)
- **Interactive Dashboard**: Real-time localized weather, live IoT telemetry, and Central Digital Farm Pass.
- **"What Should I Do Today?"**: Prioritized action cards (🔴 High, 🟠 Medium, 🟢 Normal) powered by Farm Brain.
- **Soil & Nutrient Intelligence**: Nutrient depletion diagnostics and scientific NPK dose recommendations.
- **Crop Planning & Calendar**: Growth stage timelines with daily task lists.
- **Weather Impact & Advisories**: Spraying suitability, rainfall forecasts, and frost warnings.
- **Market Mandi Prices**: Modal prices, MSP comparisons, and market trends.
- **Government Schemes & Crop Insurance**: Eligibility analysis for PM-KISAN, PMFBY, and PMKSY.
- **Krishi Assistant AI**: RAG-grounded conversational chatbot supporting Hindi, English, and Hinglish.

### 2. Authorized Agriculture / Seva Operator Portal (`AUTHORIZED_OPERATOR`)
Designed for rural common service centers (CSCs), KVKs, and agricultural extension workers assisting farmers without smartphones:
1. **Operator Dashboard**: Aggregate metrics on registered farmers, pending soil tests, and active service requests.
2. **Assisted Farmer Registration**: Comprehensive onboarding generating unique `MT-FARM-XXXXXX` IDs with SMS/IVR consent.
3. **Farmer Search**: Instant lookup by mobile number, name, state, district, or Farm ID.
4. **Farmer Profile & QR Verification**: Digital pass with opaque tokenized identifiers ensuring privacy.
5. **Farm Management**: Multi-parcel farm management, soil categorization, and irrigation mapping.
6. **Crop Registration**: Sowing date, variety, crop cycle tracking.
7. **Certified Soil Test Management**: Booking, status lifecycle tracking, and certified lab report entry.
8. **Document Vault**: Secure, role-gated file repository for 7/12 land records, soil cards, and insurance policies.
9. **Service Requests**: End-to-end service ticket lifecycle (`MT-REQ-XXXXXX`).
10. **Weather & Alerts Dispatch**: Broadcast localized heavy rainfall, pest, and temperature warnings.
11. **Market Price SMS Engine**: Query official mandi prices and dispatch formatted SMS advisories.
12. **Fertilizer & Pest Assistance**: Prescribe calibrated treatments without blindly recommending chemicals.
13. **Government Schemes Assistance**: Document checklist and eligibility verification.
14. **Crop Insurance Assistance**: PMFBY claim assistance and deadline tracking.
15. **SMS & IVR Service Center**: Live interactive Keypad IVR Simulator and test SMS transmitter.
16. **Reports & Summaries**: Village-level, crop-wise, and seasonal agronomy analytics.
17. **Activity Audit Log**: Immutable tracking of all operator actions and document updates.

---

## MAITTRI Farm Brain

The **MAITTRI Farm Brain** (`backend/app/services/farm_brain_service.py`) is the centralized agronomical intelligence engine. It synthesizes:
- Verified Farmer Profile & Land Details
- In-situ IoT Edge Telemetry (Indicative soil moisture, temp, humidity)
- Certified Laboratory Soil Test Reports (Lab N, P, K, pH, EC, Organic Carbon)
- Localized IMD Meteorological Forecasts (Precipitation probability, heat stress, wind speed)
- Crop Growth Stage Timelines & Sowing Dates
- Pest & Disease Observation Guides (ICAR Grounded)

### Explainable Recommendation Schema:
Every recommendation generated by Farm Brain contains:
- **Action**: Concrete operational step (e.g., *"Postpone irrigation for next 48 hours"*).
- **Reason (Why?)**: Scientific agronomic rationale (e.g., *"High rainfall of 32mm forecast with 85% probability"*).
- **Risk**: Potential damage if neglected (e.g., *"Waterlogging, nitrogen leaching, root rot"*).
- **Data Used**: Transparent evidence list (e.g., `["Open-Meteo precipitation: 32mm", "IoT Soil Moisture: 68%"]`).
- **Missing Info**: Clear disclosure if certain data points are missing (e.g., *"Laboratory organic carbon not tested"*).
- **Confidence Level**: `HIGH`, `MEDIUM`, or `LOW`.
- **Source**: Formal agricultural citation (e.g., *"IMD Forecast + ICAR Crop Advisory"*).

---

## SMS & IVR Communication Architecture

MAITTRI implements a **provider-agnostic adapter architecture** allowing deployment with any SMS or IVR telecom gateway:

### SMS System
- **Provider Interface**: `SMSProvider` base class with pluggable adapters (`DemoSMSAdapter`, `TwilioSMSAdapter`, `Msg91SMSAdapter`).
- **Safe Demo Mode**: When external credentials (`SMS_API_KEY`) are not configured, the system logs attempts transparently in `sms_logs` and marks them as `[DEMO MODE]`, never crashing and never fabricating delivery.
- **Telecom Compliance**: Ready for Indian Telecom **DLT (Distributed Ledger Technology)** registration with Entity IDs and approved template IDs.

### IVR (Interactive Voice Response) Keypad State Machine
Designed for feature/keypad phones where farmers dial into the MAITTRI hotline:
- **Language Selection**: Press `1` for Hindi, `2` for English.
- **Main Menu**:
  - `1` → Today's Farm Action (Today's highest priority task from Farm Brain)
  - `2` → Weather Forecast & Spraying Advisory
  - `3` → Crop Stage & Irrigation Advice
  - `4` → Guided Pest & Disease Diagnostic (Interactive symptom questions)
  - `5` → Mandi Market Prices
  - `6` → Government Schemes Guidance
  - `7` → PMFBY Crop Insurance Information
  - `8` → Soil Test Booking & Status Tracking
  - `9` → Repeat Menu / Replay

```
+-------------------------------------------------------------------------+
|                              MAITRI CLIENT                              |
|          React 19 + Vite + Lucide Icons + Leaflet (EN/HI Bilingual)     |
+------------------------------------+------------------------------------+
                                     |  HTTP REST / JSON
                                     v
+-------------------------------------------------------------------------+
|                           FASTAPI BACKEND                               |
|        - Uvicorn ASGI Server with LAN Bridge Auto-Forwarding            |
|        - Security: Argon2id Hashing + JWT Token Bearer Authentication   |
|        - SQLAlchemy ORM with SQLite (PostgreSQL Ready)                  |
|        - Decision-Support Services & Calculators                        |
+-------------------+--------------------------------+--------------------+
                    |                                |
                    v                                v
+-----------------------------------+  +----------------------------------+
|           EXTERNAL APIS           |  |        IoT EDGE HARDWARE         |
|  - Open-Meteo Weather & Geocoding |  |  - ESP32 / ESP8266 Microcontroller|
|  - OpenStreetMap Tile Server      |  |  - DHT22 (Temp & Humidity)       |
|  - Optional: Google Maps SDK      |  |  - Capacitive/Resistive Soil Probe|
|                                   |  |  - HC-SR04 Ultrasonic on Servo  |
+-----------------------------------+  +----------------------------------+
```

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite, React Router 7 | Responsive, high-performance web interface |
| **Styling & UI** | Pure Modern CSS, Lucide React | Clean, responsive, glassmorphic UI design |
| **Mapping** | Leaflet, OpenStreetMap, Google Maps SDK | Interactive farm boundary and location selection |
| **Backend API** | FastAPI, Uvicorn, Pydantic v2 | High-speed async REST API with automatic OpenAPI docs |
| **Database** | SQLAlchemy, SQLite | Embedded relational storage (zero external DB install needed) |
| **Security** | Argon2-cffi, Python-jose, Bcrypt | Cryptographic password hashing and stateless JWT tokens |
| **IoT Hardware** | ESP32 DevKit, ESP8266 NodeMCU | Edge telemetry sampling and servo radar sweep |
| **Sensors** | DHT22, HC-SR04, Analog Soil Probe | In-situ temperature, humidity, soil moisture, and obstacle range |

---

## Project Directory Structure

```text
smart_agriculture_ai/
├── .gitignore                      # Comprehensive Git exclusion rules
├── .env.example                    # Root environment configuration template
├── README.md                       # Master documentation
├── start_app.bat                   # 1-Click Windows startup script (Backend + Frontend)
│
├── backend/                        # FastAPI REST API
│   ├── .env.example                # Backend environment template
│   ├── requirements.txt            # Python dependencies (fastapi, uvicorn, etc.)
│   ├── pytest.ini                  # Pytest test runner configuration
│   ├── simulate_iot_device.py      # Hardware-free IoT radar & telemetry simulator
│   ├── app/
│   │   ├── main.py                 # FastAPI application entrypoint & middleware
│   │   ├── database.py             # Database engine & session management
│   │   ├── models.py               # SQLAlchemy database models (Users, Farms, IoT, etc.)
│   │   ├── schemas.py              # Pydantic request/response schemas
│   │   ├── security.py             # Argon2id hashing & JWT token helpers
│   │   ├── deps.py                 # FastAPI dependency injection (auth, db)
│   │   ├── routes/                 # Modular API route controllers
│   │   │   ├── auth.py             # User authentication endpoints
│   │   │   ├── farms.py            # Farm entity management
│   │   │   ├── recommendations.py  # Crop recommendation algorithms
│   │   │   ├── weather.py          # Meteorological data & advisories
│   │   │   ├── location.py         # Geocoding & reverse geocoding
│   │   │   ├── nutrients.py        # Nutrient deficiency diagnostic
│   │   │   ├── soil.py             # Soil characteristics estimation
│   │   │   ├── fertilizer.py       # NPK dose & pest management
│   │   │   ├── farmer_planning.py  # Seasonal planning & crop calendar
│   │   │   ├── parali.py           # Crop residue (stubble) management
│   │   │   ├── market_prices.py    # Mandi commodity prices & MSP
│   │   │   ├── government_schemes.py # Central & state scheme matching
│   │   │   ├── insurance.py        # PMFBY insurance calculator
│   │   │   └── iot.py              # IoT sensor & radar telemetry ingestion
│   │   └── services/               # Core business logic & agronomic models
│   │       ├── iot_service.py      # Real-time telemetry processing & buffering
│   │       ├── lan_bridge.py       # Automatic LAN socket bridge for IoT nodes
│   │       └── ...                 # Agronomic, market & scheme engines
│   └── tests/                      # Automated test suite (66 unit & integration tests)
│
├── frontend/                       # React 19 + Vite single-page application
│   ├── .env.example                # Frontend environment template
│   ├── package.json                # NPM package definitions & scripts
│   ├── index.html                  # HTML entrypoint
│   ├── src/
│   │   ├── main.jsx                # Application DOM mounter
│   │   ├── App.jsx                 # Main navigation & core dashboards
│   │   ├── api.js                  # Axios client configured with base URL
│   │   ├── i18n.js                 # English & Hindi translation dictionaries
│   │   ├── LanguageContext.jsx     # Global language context provider
│   │   ├── IoTMonitorPage.jsx      # Real-time IoT & Ultrasonic Radar dashboard
│   │   ├── FarmerPlanningPage.jsx  # Seasonal planner & daily tasks
│   │   ├── FertilizerRecommendationPage.jsx # NPK & pest management
│   │   ├── ParaliManagementPage.jsx # Stubble burning mitigation calculator
│   │   ├── MarketPricePage.jsx     # Mandi prices & market trends
│   │   ├── GovernmentSchemesPage.jsx # Welfare schemes explorer
│   │   ├── InsurancePlanningPage.jsx # PMFBY insurance estimator
│   │   ├── InteractiveLocationMap.jsx # Leaflet & Google Maps component
│   │   └── styles.css              # Custom responsive stylesheet
│
├── hardware/                       # Embedded C++ firmware for IoT Edge Nodes
│   ├── README.md                   # Detailed wiring & flashing guide
│   ├── esp32/
│   │   ├── maitri_esp32_node.ino   # ESP32 Arduino sketch (WiFi + Servo + Radar)
│   │   └── secrets.example.h       # Optional header-based Wi-Fi config template
│   └── esp8266/
│       └── maitri_esp8266_node.ino # ESP8266 NodeMCU Arduino sketch
│
├── datasets/                       # Reference agricultural dataset schemas
└── docs/                           # Architectural, PRD, and technical references
```

---

## Quick Start (Windows PowerShell)

Follow these steps to clone, configure, and launch the platform on Windows:

### 1. Clone the Repository
```powershell
git clone https://github.com/your-username/smart_agriculture_ai.git
cd smart_agriculture_ai
```

### 2. Set Up Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install Backend Dependencies
```powershell
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
```

### 4. Configure Environment Files
```powershell
# Root configuration
Copy-Item .env.example .env

# Backend configuration
Copy-Item backend\.env.example backend\.env

# Frontend configuration
Copy-Item frontend\.env.example frontend\.env
```

### 5. Run Automated Tests
Verify all 66 backend unit and integration tests pass:
```powershell
cd backend
python -m pytest
cd ..
```

### 6. Start the Backend Server
Run the FastAPI backend on port `8000` listening on all LAN interfaces (`0.0.0.0` allows physical ESP32 devices to connect):
```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **API Root**: `http://127.0.0.1:8000`
- **Swagger Interactive API Docs**: `http://127.0.0.1:8000/docs`
- **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`

### 7. Start the Frontend Server (New PowerShell Terminal)
```powershell
cd frontend
npm install
npm run dev
```
- **Web Application**: `http://localhost:5173`

> [!TIP]
> **One-Click Startup**: On Windows, you can simply double-click **`start_app.bat`** in the project root to launch both the backend and frontend simultaneously in separate console windows.

---

## Environment Variables

### Root / Backend (`.env` or `backend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `SECRET_KEY` | `change-this-in-production...` | Secret key used for signing JWT authentication tokens. |
| `DATABASE_URL` | `sqlite:///./agri.db` | SQLAlchemy database URL. Defaults to SQLite. Can be set to PostgreSQL. |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated list of allowed frontend origins for CORS. |
| `HOST` | `0.0.0.0` | Host interface for uvicorn to bind to (`0.0.0.0` allows ESP32/LAN access). |
| `PORT` | `8000` | Port for the backend API server. |
| `OPENROUTER_API_KEY` | *(empty / your_key)* | OpenRouter API Key for the Maitri Krishi Assistant chatbot. Kept strictly server-side. |
| `OPENROUTER_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | LLM model identifier for OpenRouter (supports free and custom models). |
| `SMS_PROVIDER` | `demo` | Provider adapter: `demo`, `twilio`, or `msg91`. |
| `SMS_API_KEY` | *(empty)* | API key for external SMS provider (optional in prototype/demo mode). |
| `SMS_SENDER_ID` | `MAITRI` | Sender ID / DLT Header for transactional SMS. |
| `SMS_TEMPLATE_ID` | *(empty)* | Telecom DLT-approved template registration ID for commercial delivery. |
| `IVR_PROVIDER` | `demo` | Provider adapter: `demo`, `twilio`, or `exotel`. |
| `IVR_API_KEY` | *(empty)* | API key for external voice provider. |
| `IVR_NUMBER` | `+911800XXXXXX` | Inbound toll-free or virtual number for farmer hotline. |

### Frontend (`frontend/.env`)

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `VITE_API_URL` | `http://127.0.0.1:8000/api` | Base URL used by Axios in the React application to reach the backend. |
| `VITE_GOOGLE_MAPS_API_KEY` | *(empty)* | Optional Google Maps API key. If empty, OpenStreetMap/Leaflet is used. |

---

## IoT Edge Hardware (ESP32 / ESP8266)

The platform supports live field telemetry streaming from an **ESP32** or **ESP8266 NodeMCU** microcontroller. The node collects ambient temperature, humidity, soil moisture, and performs a 180-degree sweep using an **HC-SR04** ultrasonic sensor mounted on an **SG90/MG90S** servo motor.

### Hardware BOM & Pinout

| Sensor / Module | ESP32 GPIO | ESP8266 Pin | Notes |
| :--- | :--- | :--- | :--- |
| **DHT22 Data** | `GPIO4` | `D2 (GPIO4)` | 10kΩ pull-up resistor to 3.3V |
| **Soil Moisture AO** | `GPIO34` *(ADC1_CH6)* | `A0 (ADC0)` | Uses ADC1 on ESP32 so Wi-Fi does not interfere |
| **Servo PWM Signal** | `GPIO18` | `D5 (GPIO14)` | Hardware PWM / LEDC timer |
| **HC-SR04 TRIG** | `GPIO5` | `D6 (GPIO12)` | Digital output pulse |
| **HC-SR04 ECHO** | `GPIO19` | `D7 (GPIO13)` | Digital input |
| **Power & Ground** | `VIN (5V) & GND` | `5V / VIN & GND` | Power servo and HC-SR04 from 5V (2A supply recommended) |

### Firmware Configuration

1. Open Arduino IDE and install required libraries:
   - `DHT sensor library` (Adafruit)
   - `Adafruit Unified Sensor` (Adafruit)
   - `ArduinoJson` (v6 or v7 by Benoit Blanchon)
   - `ESP32Servo` (by Kevin Harrington, for ESP32 only)
2. Open [`hardware/esp32/maitri_esp32_node.ino`](file:///c:/Users/nikhi/Desktop/smart_agriculture_ai/hardware/esp32/maitri_esp32_node.ino) (or ESP8266 sketch).
3. Update your Wi-Fi credentials:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_SSID";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   ```
4. Set the `SERVER_URL` to your PC's LAN IP (find it via `ipconfig` in PowerShell):
   ```cpp
   // If using Windows Mobile Hotspot:
   const char* SERVER_URL = "http://192.168.137.1:8000/api/iot/sensor-data";
   // If using Home / Phone Wi-Fi:
   const char* SERVER_URL = "http://192.168.1.100:8000/api/iot/sensor-data";
   ```
5. Select your board and COM port, then click **Upload**.
6. Open Serial Monitor at **115200 baud** to observe sensor readings and HTTP 200/201 ingestion confirmations.

### Simulation Mode (No Hardware Required)

You can test the complete IoT monitoring interface and ultrasonic radar sweeps immediately without physical hardware using the built-in simulator:

```powershell
cd backend
python simulate_iot_device.py --device MAITRI_ESP32_01 --interval 3
```

Navigate to `http://localhost:5173/iot-monitor` to see the live sweep radar, temperature, humidity, and soil moisture updating in real time.

---

## API Documentation

The backend provides complete interactive Swagger documentation at `http://127.0.0.1:8000/docs`. Key endpoints include:

### Authentication
- `POST /api/auth/register`: Create a new farmer account.
- `POST /api/auth/login`: Authenticate with email/password and obtain a JWT bearer token.
- `GET /api/auth/me`: Retrieve profile of currently authenticated user.

### Farms & Crops
- `GET /api/farms`: List farms associated with current user.
- `POST /api/farms`: Register farm location, area, and soil characteristics.
- `POST /api/recommendations/recommend`: Generate ranked crop recommendations based on soil, season, and climate.

### Weather & Location
- `POST /api/weather`: Retrieve current conditions and 7-day agricultural forecast via Open-Meteo.
- `GET /api/weather/advisories`: Generate crop spraying, irrigation, and wind hazard advisories.
- `GET /api/location/search`: Search city/district coordinates.
- `GET /api/location/reverse`: Reverse geocode coordinates into a human-readable address.

### Soil & Agronomics
- `POST /api/soil/estimate`: Estimate soil properties from location coordinates.
- `POST /api/nutrients/deficiency-analysis`: Diagnose visual plant deficiency symptoms (N, P, K, Fe, Zn).
- `POST /api/fertilizer/recommend`: Calculate exact fertilizer quantities (Urea, DAP, MOP) and split applications.
- `GET /api/pest/crops`: List registered pest management strategies.

### Parali & Economics
- `POST /api/parali/calculate`: Calculate stubble burning management options, machinery rental costs, and biomass revenue.
- `GET /api/market-prices/latest`: Fetch modal mandi prices, MSP comparisons, and market trends.
- `POST /api/government-schemes/eligible`: Determine eligibility for PM-KISAN, PMKSY, and state welfare schemes.
- `POST /api/insurance/calculate-premium`: Calculate PMFBY crop insurance premium rates and government subsidies.

### MAITTRI Farm Brain (Central Decision Engine)
- `GET /api/farm-brain/today/{farm_id}`: Synthesizes weather, indicative IoT, soil tests, and crop stage into ranked daily actions with Why, Risk, Data Used, and Missing Info.
- `GET /api/farm-brain/week/{farm_id}`: 7-day outlook of upcoming field operations and risk prevention tasks.
- `POST /api/farm-brain/analyze`: Ad-hoc farm analysis for planned crops and simulated weather anomalies.

### Authorized Agriculture / Seva Operator Endpoints
- `GET /api/operators/stats`: Aggregated summary of registered farmers, pending soil tests, and active tickets.
- `POST /api/operators/farmers/register`: Operator-assisted onboarding generating unique `MT-FARM-XXXXXX` IDs with SMS/IVR consent.
- `GET /api/operators/farmers/search`: Search farmers by mobile number, name, state, district, or Farm ID.
- `GET /api/operators/farmers/{farmer_id}`: Full farmer profile including linked parcels, soil tests, and tickets.
- `PATCH /api/operators/farmers/{farmer_id}`: Update farmer contact, area, or communication preferences.
- `GET /api/operators/activity-logs`: Immutable audit trail of operator registrations and updates.

### Central Farmer Profile & QR Verification
- `GET /api/farmer-profile/me`: Get current logged-in farmer's unified profile and Farm ID.
- `GET /api/farmer-profile/verify/{farmer_id}`: Validate QR verification scan using opaque tokenized identifier.
- `POST /api/farmer-profile/sync-farm/{farm_id}`: Link farm parcel to farmer record.

### Certified Soil Test Management
- `POST /api/soil-tests`: Book certified soil test (`MT-STR-XXXXXX`) for a farm parcel.
- `GET /api/soil-tests`: List soil tests filtered by farm, farmer, or status.
- `GET /api/soil-tests/{request_id}`: Retrieve detailed soil test progress and laboratory report.
- `PATCH /api/soil-tests/{request_id}/status`: Progress lifecycle (`REQUESTED` → `SCHEDULED` → `SAMPLE_COLLECTED` → `LAB_PROCESSING` → `REPORT_AVAILABLE`).
- `POST /api/soil-tests/{request_id}/report`: Enter certified laboratory test values (N, P, K, pH, EC, Organic Carbon).

### Service Request Lifecycle
- `POST /api/service-requests`: Open support ticket (`MT-REQ-XXXXXX`) for advisory, schemes, or documents.
- `GET /api/service-requests`: List service requests filtered by status or farmer.
- `GET /api/service-requests/{request_id}`: View ticket details and resolution history.
- `PATCH /api/service-requests/{request_id}`: Update request status and assign operator notes.

### Secure Document Vault
- `POST /api/documents/upload`: Upload land/crop/insurance documents (PDF, JPG, PNG up to 10MB).
- `GET /api/documents`: List uploaded files for farmer or farm parcel.
- `GET /api/documents/{doc_id}/download`: Secure authenticated file download with MIME type validation.

### SMS & IVR Communication Endpoints
- `GET /api/communications/preferences/{farmer_id}`: Retrieve notification consents (weather, crop, market, schemes).
- `PATCH /api/communications/preferences/{farmer_id}`: Update farmer communication channels and language.
- `POST /api/communications/sms/send`: Send or broadcast SMS advisory (falls back cleanly to demo mode if provider is not configured).
- `POST /api/communications/ivr/simulate`: Interactive keypad simulator executing IVR tree state machine.
- `POST /api/communications/ivr/webhook`: TwiML / voice gateway webhook for live telephony integration.

### AI Agriculture Assistant (Maitri Krishi Assistant - RAG)
- `POST /api/chat`: Send farmer question in English, Hindi, or Hinglish; retrieves vector chunks and grounds response via OpenRouter.
- `POST /api/chat/message`: Alternative alias for chat ingestion.
- `POST /api/chat/debug`: Development debug endpoint to inspect top retrieved chunks, similarity distances, and source metadata.
- `GET /api/chat/status`: Check AI assistant availability, ChromaDB chunk count, and OpenRouter configuration.

---

## Maitri Krishi Assistant (RAG Architecture & Knowledge Base)

**Maitri Krishi Assistant** is a true **Retrieval-Augmented Generation (RAG)** agricultural advisory system grounded in curated research from **ICAR, IMD, CAQM, and the Ministry of Agriculture & Farmers Welfare**. It communicates fluently in **Hindi (हिंदी)**, **Hinglish**, and **English**, dynamically matching the farmer's dialect.

### End-to-End RAG Architecture

```
Farmer / Frontend UI (React + Vite)
       │
       ▼  POST /api/chat (Message, recent conversation history, farm & IoT context)
FastAPI Backend (/api/chat)
       │
       ▼
Multilingual Preprocessing & Query Term Expansion (Hindi / Hinglish / English)
       │
       ▼  Dense Vector Embedding (all-MiniLM-L6-v2 via ONNX runtime)
ChromaDB Persistent Vector Store (backend/vector_store/)
       │
       ▼  Cosine Distance / Similarity Search & Relevance Thresholding
Top 3–5 Ranked Knowledge Chunks
       │
       ├──► [Out-of-Domain Query: e.g. "Capital of France"] ──► Polite Agricultural Scope Refusal
       ├──► [Low Confidence / Gibberish] ────────────────────► Safe Non-Hallucinatory Clarification Request
       │
       ▼
Combine Prompt:
       - User Question
       - Retrieved Knowledge Chunks (ICAR / IMD)
       - Active Farmer Profile & Real-time IoT Sensor Readings (Moisture / Temp)
       - Recent Multi-turn History
       │
       ▼  HTTPS POST https://openrouter.ai/api/v1/chat/completions
OpenRouter LLM (e.g. openrouter/free or meta-llama/llama-3.3-70b-instruct:free)
       │
       ├──► [Fallback if OpenRouter Offline / Timeout] ──► Grounded synthesis directly from vector chunks
       │
       ▼
Grounded Farmer Answer with Verified Sources & Confidence Score:
       - Structured reply
       - sources: [{ title, source, section, category, crop }]
       - retrieved_chunks count & actual calculated confidence
       │
       ▼
Farmer UI (Rendered with "Maitri is thinking..." and 📚 Sources section)
```

### Knowledge Base Organization (`backend/knowledge_base/`)

The knowledge base is modular and extensible across 9 core domains:
```text
backend/knowledge_base/
├── crops/           # Wheat, Rice, Maize, Potato, Tomato, Mustard production guides
├── diseases/        # Yellow Rust, Blast, Sheath Blight, Late/Early Blight, White Rust
├── pests/           # Fall Armyworm, Stem Borer, Mustard Aphids, Whitefly, Pod Borer
├── fertilizers/     # Nitrogen, Phosphorus, Potassium, Zinc, Iron, Urea, DAP, MOP
├── irrigation/      # Wheat CRI stages, Rice AWD water management, Drip & Sprinkler
├── soil/            # Soil types, pH, Saline/Alkali reclamation, Soil Health Card
├── schemes/         # PM-KISAN, PMFBY (Fasal Bima), PMKSY, Kisan Credit Card (KCC)
├── crop_residue/    # Parali management, Happy Seeder, Super Seeder, PUSA Bio-Decomposer
└── weather/         # Frost protection, Cold wave smudging, Heat stress mitigation
```

### Adding New Documents & Ingestion Pipeline

To add new research advisories, simply drop `.md`, `.txt`, or `.json` files into the appropriate folder under `backend/knowledge_base/` with optional frontmatter:
```markdown
---
title: Your Advisory Title
source: ICAR / State Agriculture University / KVK
category: Crops
crop: Wheat
verified: true
keywords_hi: गेहूं, बीज उपचार, बुवाई
---

# Your Document Heading
Content text here...
```

Then run the ingestion script to synchronize the knowledge base into Supabase pgvector:
```powershell
cd backend
# Synchronize curated agricultural knowledge base into Supabase pgvector:
python scripts/ingest_knowledge_supabase.py --rebuild

# Inspect knowledge base chunks and frontmatter:
python scripts/audit_kb.py
```

### Configuring OpenRouter Models

In your `.env` (root or `backend/.env`):
```ini
# OpenRouter API Key (Kept server-side only; never exposed to browser or committed to Git)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# OpenRouter Model (Configurable: free or paid models)
OPENROUTER_MODEL=openrouter/free
```
Popular supported free models:
- `openrouter/free` (auto-routes to currently available top free model)
- `meta-llama/llama-3.3-70b-instruct:free`
- `google/gemini-2.0-flash-exp:free`
- `mistralai/mistral-small-3`

### API Request & Response Example

#### Request (`POST /api/chat`)
```json
{
  "message": "Why are wheat leaves yellow?",
  "context": {
    "crop": "Wheat",
    "soil_type": "Loamy",
    "soil_moisture": 32.0,
    "temperature": 24.5
  }
}
```

#### Response (`200 OK`)
```json
{
  "reply": "Wheat leaves turning yellow can indicate either Yellow Rust or Nitrogen Deficiency...",
  "sources": [
    {
      "title": "Wheat Yellow Rust (Stripe Rust) Diagnosis & Integrated Management",
      "source": "ICAR - Indian Institute of Wheat and Barley Research (IIWBR), Karnal",
      "section": "Symptoms & Identification",
      "category": "Diseases",
      "crop": "Wheat"
    },
    {
      "title": "Nitrogen Deficiency Identification, Causes & Urea Application Guide",
      "source": "ICAR - Indian Institute of Soil Science (IISS), Bhopal",
      "section": "Visual Identification & Deficiency Symptoms",
      "category": "Fertilizers",
      "crop": "General"
    }
  ],
  "retrieved_chunks": 4,
  "confidence": 0.77,
  "language": "en",
  "provider": "openrouter"
}
```

### Developer RAG Debug Endpoint (`POST /api/chat/debug`)
To inspect the exact chunks, scores, and distances retrieved for any query without calling the LLM (requires `AUTHORIZED_OPERATOR` or `ADMIN` authentication in production):
```powershell
curl -X POST http://127.0.0.1:8000/api/chat/debug \
  -H "Authorization: Bearer <OPERATOR_JWT>" \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"गेहूं में पहली सिंचाई कब करनी चाहिए?\", \"top_k\": 3}"
```

---

## Production Deployment (Render, Vercel, Supabase)

MAITTRI is built for cloud-native deployment across **Supabase** (authoritative PostgreSQL + pgvector + Auth + Storage), **Render** (FastAPI backend), and **Vercel** (React 19 + Vite frontend).

### 1. Supabase PostgreSQL & pgvector Setup
The repository includes clean, sequential SQL migrations in `supabase/migrations/`:
* `001_extensions.sql`: Enables `vector`, `uuid-ossp`, and `pgcrypto` extensions.
* `002_profiles_and_auth.sql`: Creates `public.profiles` and triggers on `auth.users`.
* `003_farmers_and_farms.sql`: Core tables (`farmers`, `farms`, `farm_plans`, `tasks`, `soil_tests`, etc.).
* `004_iot_telemetry.sql`: Hardware device registry and time-series telemetry table.
* `005_rag_pgvector.sql`: Knowledge chunk vector table (`all-MiniLM-L6-v2`, 384 dimensions) and cosine search RPC function `private.match_knowledge_chunks`.
* `006_storage_buckets.sql`: Provisions private `farmer-vault` storage bucket with RLS policies.
* `007_row_level_security.sql`: Zero-trust Row Level Security (RLS) policies.

To apply migrations:
```bash
# Using Supabase CLI:
supabase db push

# Or execute migrations 001 through 007 sequentially in the Supabase SQL Editor.
```

Populate the pgvector store with verified agricultural knowledge:
```bash
cd backend
python scripts/ingest_knowledge_supabase.py --rebuild
```

### 2. Render Backend Deployment (FastAPI)
The backend includes turnkey configurations via `render.yaml`, `Procfile`, and `backend/Dockerfile`.

1. Connect your repository to [Render](https://render.com).
2. Choose **Blueprint** deployment (automatically uses `render.yaml`) or create a **Web Service** with:
   * **Runtime**: Python 3.12 (or Docker using `backend/Dockerfile`)
   * **Build Command**: `cd backend && pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend`
   * **Health Check Path**: `/health`
3. Configure the following environment variables in Render:
   * `ENVIRONMENT=production`
   * `DATABASE_URL`: Supabase Transaction Pooler connection string (`postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require`)
   * `SECRET_KEY`: High-entropy 32+ character string
   * `SUPABASE_URL`: `https://<ref>.supabase.co`
   * `SUPABASE_ANON_KEY`: Supabase anon/public key
   * `SUPABASE_SERVICE_ROLE_KEY`: Supabase service_role key (server-side only)
   * `OPENROUTER_API_KEY`: OpenRouter API key for Krishi Assistant
   * `OPENROUTER_MODEL`: `meta-llama/llama-3.3-70b-instruct:free`
   * `CORS_ORIGINS`: Your Vercel domain (e.g. `https://maitri.vercel.app`)

### 3. Vercel Frontend Deployment (React + Vite)
1. Import your repository into [Vercel](https://vercel.app).
2. Configure project settings:
   * **Root Directory**: `frontend`
   * **Framework Preset**: Vite
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
3. Environment variables:
   * `VITE_API_URL`: `https://<your-render-backend>.onrender.com/api`
   * `VITE_GOOGLE_MAPS_API_KEY`: (Optional) Google Maps API key; falls back to Leaflet if unset.
4. The included `frontend/vercel.json` automatically configures SPA rewrite rules for client-side routing.

### 4. Health & Liveness Endpoints
* `GET /health`: Liveness probe for containers and platforms (returns HTTP 200 `{ "status": "healthy" }`).
* `GET /ready`: Readiness probe verifying PostgreSQL connection pool health and pgvector availability (returns HTTP 200 when ready, HTTP 503 if database connection fails).

---

## Security & Best Practices

1. **Never Commit Secrets**: Never commit `.env`, `*.pem`, `*.key`, or Wi-Fi credentials to Git. The repository includes `.gitignore` to safeguard against accidental exposure.
2. **Change Default Secret Keys**: In production, generate a secure random secret key:
   ```powershell
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
   Set this value in `SECRET_KEY` in your `.env` file.
3. **Argon2id Cryptographic Security**: Passwords are saved as Argon2id salted hashes, protecting against GPU/ASIC rainbow table attacks.
4. **CORS Restrictions**: For public deployment, restrict `CORS_ORIGINS` in `.env` to your exact production domain.

---

## Troubleshooting Guide

| Issue | Potential Cause | Solution |
| :--- | :--- | :--- |
| **Backend fails to start (`ModuleNotFoundError`)** | Virtual environment not activated or missing packages | Run `.\venv\Scripts\Activate.ps1` and `pip install -r backend\requirements.txt`. |
| **Backend port 8000 in use** | Another instance of uvicorn is running | Kill existing python processes via Task Manager or run on another port: `--port 8001`. |
| **Frontend cannot fetch from backend** | `VITE_API_URL` misconfigured or backend not running | Ensure `frontend/.env` has `VITE_API_URL=http://127.0.0.1:8000/api` and backend is listening. |
| **ESP32 reports HTTP Connection Error** | Microcontroller attempting to reach `127.0.0.1` or blocked by Firewall | 1. Use your PC's LAN IP (e.g. `192.168.1.100` or `192.168.137.1`), NOT `127.0.0.1`.<br>2. Ensure Windows Firewall permits incoming connections on port 8000.<br>3. Connect both PC and ESP32 to the same Wi-Fi router or Windows Mobile Hotspot. |
| **Soil moisture sensor reads zero on ESP32** | Wi-Fi radio interfering with ADC2 pins | ESP32 ADC2 pins are disabled when Wi-Fi is active. Connect the analog pin to **GPIO34** (ADC1), which is safe during active Wi-Fi. |
| **Google Maps displays an error** | Missing or invalid API key | If you do not have a Google Maps API key, leave `VITE_GOOGLE_MAPS_API_KEY` blank; the app will automatically fall back to OpenStreetMap. |

---

---

## Demo Mode vs Production Requirements

### 1. Prototype & Demo Mode
Because MAITTRI is designed for extensible hackathons, research pilots, and local evaluation:
- If SMS or IVR provider credentials (`SMS_API_KEY`, `IVR_API_KEY`) are omitted from `.env`, the system **never crashes**.
- Outgoing SMS attempts are recorded in the `sms_logs` database table and marked with status `DEMO_SENT` / `[DEMO MODE]`.
- The Seva Operator Portal includes an interactive **Keypad Phone Simulator** to test the entire DTMF audio tree and voice prompts without needing an active telecom trunk line.
- The system **never claims an actual SMS was delivered** unless an external provider returns an HTTP 200/201 delivery receipt.

### 2. Production Deployment & Indian Telecom DLT Compliance
To activate live commercial SMS and IVR in India:
1. **TRAI DLT Registration**: Register your legal entity on an authorized telecom DLT portal (e.g., Jio DLT, Airtel DLT, Vodafone Idea DLT, BSNL DLT).
2. **Sender Header Approval**: Register a 6-character alphanumeric sender header (e.g., `MAITRI`).
3. **Template ID Registration**: Register exact transactional and service implicit templates matching TRAI regulations.
4. **Provider Integration**: Set `SMS_PROVIDER=msg91` (or `twilio`) and supply `SMS_API_KEY`, `SMS_SENDER_ID`, and `SMS_TEMPLATE_ID` in `.env`.
5. **Inbound IVR Trunk**: Provision an Indian virtual toll-free number (via Exotel, Tata Tele, or Twilio) and configure the incoming voice webhook to point to `https://your-domain.com/api/communications/ivr/webhook`.

---

## Agricultural Safety & Accuracy Disclaimers

> [!IMPORTANT]
> **Agronomic Responsibility & Ethical Guidelines**

1. **Hybrid Architecture (Not "Black-Box 100% AI")**:
   MAITTRI utilizes a transparent, hybrid decision-intelligence architecture combining ICAR agricultural guidelines, verified IMD weather models, and domain rule engines. It is ML-ready for validated yield and pest-risk models. We strictly **do not claim 100% or 98.9% accuracy** without verified field trials.
2. **Indicative IoT Telemetry vs Certified Soil Laboratory Assays**:
   In-field IoT probes (capacitive moisture, temperature, ultrasonic radar) provide **indicative real-time operational metrics**. They are **not equivalent to certified laboratory chemical soil tests** (e.g., Kjeldahl nitrogen, Bray phosphorus, atomic absorption spectrophotometry). Farmers and operators can book certified lab tests directly in the portal.
3. **Pest & Disease Diagnosis**:
   Pest and disease advisories offer probable symptom matches and emphasize Integrated Pest Management (IPM). Never apply chemical pesticides or fungicides at unverified concentrations. Always cross-verify with your local Krishi Vigyan Kendra (KVK) or agricultural extension officer.
4. **Official Government Representation**:
   The operator console is strictly designated as an **"Authorized Agriculture / Seva Operator"** portal to support common service center (CSC) assisted digital delivery. It does not falsely claim direct sovereign government authority unless an official institutional memorandum of understanding (MoU) and API gateway are connected.

---

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
