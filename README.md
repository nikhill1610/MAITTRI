# Maitri – Smart Agriculture AI Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.1+-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-7.1+-646CFF.svg?style=flat&logo=vite)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?style=flat&logo=python)](https://www.python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Maitri** (मैत्री) is an open-source, full-stack precision agriculture and decision-support platform engineered for farmers, agronomists, and agricultural researchers. It combines multi-criteria agronomic intelligence, localized meteorological data, market economics, and physical IoT edge sensing (ESP32 & ESP8266) to empower data-driven farming decisions.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Project Directory Structure](#project-directory-structure)
- [Quick Start (Windows PowerShell)](#quick-start-windows-powershell)
- [Environment Variables](#environment-variables)
- [IoT Edge Hardware (ESP32 / ESP8266)](#iot-edge-hardware-esp32--esp8266)
  - [Hardware BOM & Pinout](#hardware-bom--pinout)
  - [Firmware Configuration](#firmware-configuration)
  - [Simulation Mode (No Hardware Required)](#simulation-mode-no-hardware-required)
- [API Documentation](#api-documentation)
- [Security & Best Practices](#security--best-practices)
- [Troubleshooting Guide](#troubleshooting-guide)
- [License](#license)

---

## Overview

Smallholder and commercial farmers face complex, interconnected challenges: unpredictable weather fluctuations, soil nutrient degradation, fluctuating mandi prices, crop residue management (stubble burning/parali), and pest infestations.

**Maitri** addresses these challenges by offering a unified decision-support platform that operates both on desktop/mobile browsers and with low-cost field hardware:
1. **Actionable Crop Intelligence**: Recommends high-yielding, climate-resilient crops matched to soil profiles and seasonal rainfall.
2. **Economic Forecasting**: Computes expected input costs, projected yields, and net profits across alternative crop choices.
3. **IoT Field Telemetry & Radar**: Streams real-time ambient temperature, humidity, soil moisture, and an automated $20^\circ \longleftrightarrow 160^\circ$ ultrasonic obstacle radar sweep.
4. **Residue (Parali) Solutions**: Provides economically viable in-situ and ex-situ alternatives to stubble burning.
5. **Government & Insurance Integration**: Evaluates farmer eligibility for central/state welfare schemes and calculates PMFBY insurance premiums.

---

## Key Features

- **Multilingual User Interface**: Full bilingual support for **English** and **Hindi (हिन्दी)** with instant runtime switching.
- **Secure Authentication**: User registration and login utilizing **Argon2id** password hashing with fallback to Bcrypt and stateless **JWT (JSON Web Tokens)**.
- **Farm & Soil Profiling**:
  - Interactive location picker powered by OpenStreetMap/Leaflet (optional Google Maps JavaScript API support).
  - Geocoding and reverse-geocoding via Open-Meteo.
  - Farmer-friendly soil selection (Clay, Loam, Sandy, Black, Red, Alluvial) with optional laboratory N-P-K-pH input.
- **Crop Recommendation & Comparison Engine**:
  - Multi-parameter agronomic matching based on soil type, seasonal suitability, and water requirements.
  - Side-by-side comparison of multiple crops with projected revenue and input expense breakdown.
- **Dynamic Farmer Planning & Crop Calendar**:
  - Customized growth stage timelines from sowing to harvest.
  - Daily operations calendar with prioritized field tasks and weather hazard alerts.
- **Fertilizer Guidance & Integrated Pest Management (IPM)**:
  - Scientific NPK dose calculator with organic manure adjustments and basal/split application schedules.
  - Crop-specific insect, fungal, and weed diagnosis with registered treatment methods.
- **Parali (Stubble Burning) Sustainable Management**:
  - Custom hiring center (CHC) machinery cost calculator (Happy Seeder, Super Seeder, Straw Baler).
  - Economic return calculator for selling biomass to bio-ethanol, power plants, and mushroom cultivation.
- **Live Mandi Market Prices**:
  - Daily commodity prices, modal prices, Minimum Support Price (MSP) comparisons, and price volatility indicators.
- **Government Schemes & Crop Insurance**:
  - Central (PM-KISAN, PMKSY, Soil Health Card) and state-specific scheme eligibility matching.
  - Pradhan Mantri Fasal Bima Yojana (PMFBY) actuarial premium and sum insured calculators.
- **IoT Environmental Telemetry & Radar**:
  - Live sensor dashboards for soil moisture, air temperature, and relative humidity.
  - Dynamic polar radar visualization displaying 180-degree sweep obstacle distance and collision hazard levels (`CLEAR`, `OBJECT DETECTED`, `WARNING`, `VERY CLOSE`).
  - Automatic background LAN bridge allowing microcontrollers on local Wi-Fi to reach the backend seamlessly.

---

## Architecture & Tech Stack

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
| `HOST` | `0.0.0.0` | Host interface for uvicorn to bind to (allows LAN access). |
| `PORT` | `8000` | Port for the backend API server. |

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

### IoT Edge Sensor Ingestion
- `POST /api/iot/sensor-data`: Ingest JSON telemetry payload from ESP32/ESP8266 node.
- `GET /api/iot/latest`: Retrieve most recent sensor readings, radar sweep array, and online/offline status.
- `GET /api/iot/devices`: List all registered IoT hardware controllers.
- `GET /api/iot/history`: Fetch chronological telemetry history for analytical charts.
- `GET /api/iot/lan-info`: Fetch detected host machine LAN IPv4 endpoints for easy Arduino configuration.
- `POST /api/iot/simulate`: Generate an on-demand simulated radar sweep.

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

## License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.
