
# MAITRI IoT Hardware Prototype Integration Guide

Welcome to the **MAITRI Smart Agriculture IoT Subsystem**. This guide details how to wire, configure, flash, and operate the IoT edge hardware nodes (**ESP8266 NodeMCU** and **ESP32**) to stream live environmental telemetry and servo-mounted ultrasonic radar sweeps into the MAITRI platform.

---

## 1. Hardware Bill of Materials (BOM)

| Component | Function | Notes |
| :--- | :--- | :--- |
| **ESP8266 NodeMCU** | Primary Microcontroller | Built-in 802.11 b/g/n Wi-Fi |
| **ESP32 DevKit** *(Alternative)* | High-Performance Node | Dual-core, hardware PWM |
| **DHT22 (AM2302)** | Temperature & Humidity Sensor | Precision digital sensing |
| **Analog Soil Moisture Sensor** | In-situ Soil Moisture Probe | Resistive or Capacitive |
| **HC-SR04** | Ultrasonic Rangefinder | Measures object distance (2cm - 400cm) |
| **Micro Servo (SG90 / MG90S)** | Steerable Radar Turret | $20^\circ \longleftrightarrow 160^\circ$ sweep |
| **5V Power Supply / Breadboard** | Power Delivery | 5V 2A recommended for servo |

---

## 2. Wiring & Pin Configuration

### A. ESP8266 NodeMCU Pinout

```
+-------------------+--------------------+--------------------------------+
| Sensor / Actuator | NodeMCU Board Pin  | ESP8266 GPIO / Function        |
+-------------------+--------------------+--------------------------------+
| DHT22 DATA        | D2                 | GPIO4 (with 10k pull-up to 3V3)|
| Soil Moisture AO  | A0                 | ADC0 (Analog input 0 - 1.0V)   |
| Servo SIGNAL      | D5                 | GPIO14 (Hardware Timer / PWM)  |
| HC-SR04 TRIG      | D6                 | GPIO12 (Digital Output)        |
| HC-SR04 ECHO      | D7                 | GPIO13 (Digital Input)         |
| All VCC           | 5V / VIN / 3V3     | 5V for Servo & HC-SR04; 3.3V   |
| All GND           | GND                | Common Ground                  |
+-------------------+--------------------+--------------------------------+
```

### B. ESP32 DevKit Pinout

```
+-------------------+--------------------+--------------------------------+
| Sensor / Actuator | ESP32 Board Pin    | Function / Notes               |
+-------------------+--------------------+--------------------------------+
| DHT22 DATA        | GPIO4              | Digital I/O (with pull-up)     |
| Soil Moisture AO  | GPIO34             | ADC1_CH6 (Wi-Fi safe analog)   |
| Servo SIGNAL      | GPIO18             | PWM Channel (LEDC / Timer 0)   |
| HC-SR04 TRIG      | GPIO5              | Digital Output                 |
| HC-SR04 ECHO      | GPIO19             | Digital Input                  |
| All VCC           | VIN (5V) / 3V3     | 5V for Servo & HC-SR04; 3.3V   |
| All GND           | GND                | Common Ground                  |
+-------------------+--------------------+--------------------------------+
```

> [!NOTE]
> **ESP32 ADC Safety Tip**: On the ESP32, **ADC2** pins cannot be read while Wi-Fi is active. The MAITRI firmware uses **GPIO34 (ADC1_CH6)**, guaranteeing uninterrupted soil moisture sampling during Wi-Fi transmissions.

---

## 3. Arduino IDE Setup & Required Libraries

### Step 1: Add Board Manager URLs
In Arduino IDE, go to **File &rarr; Preferences** and add the board package URLs to *Additional Boards Manager URLs*:
- **ESP8266**: `http://arduino.esp8266.com/stable/package_esp8266com_index.json`
- **ESP32**: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`

Go to **Tools &rarr; Board &rarr; Boards Manager**, search and install:
- `esp8266` by **ESP8266 Community**
- `esp32` by **Espressif Systems**

### Step 2: Install Libraries via Library Manager
Open **Sketch &rarr; Include Library &rarr; Manage Libraries...** and install:
1. `DHT sensor library` by **Adafruit** *(version 1.4.x)*
2. `Adafruit Unified Sensor` by **Adafruit**
3. `ArduinoJson` by **Benoit Blanchon** *(version 6.x or 7.x)*
4. `ESP32Servo` by **Kevin Harrington** *(only needed when compiling for ESP32)*

---

## 4. Local Area Network (LAN) Configuration

The ESP8266 and ESP32 are separate networked physical devices and cannot reach your computer at `127.0.0.1` or `localhost`. They must connect to your computer's **LAN IPv4 address**.

### Step 1: Find Your Computer's LAN IP
1. Open PowerShell or Command Prompt on Windows:
   ```cmd
   ipconfig
   ```
2. Look for **IPv4 Address** under your active Wi-Fi adapter (e.g. `192.168.1.100` or `192.168.29.45`).

### Step 2: Configure Arduino Sketch
Open `hardware/esp8266/maitri_esp8266_node.ino` or `hardware/esp32/maitri_esp32_node.ino`:
```cpp
// 1. Wi-Fi Credentials
const char* WIFI_SSID     = "Your_Home_WiFi";
const char* WIFI_PASSWORD = "Your_WiFi_Password";

// 2. Server URL with your PC's IP
const char* SERVER_URL    = "http://192.168.1.100:8000/api/iot/sensor-data";
```

---

## 5. Starting the Backend on LAN (`0.0.0.0`)

The FastAPI backend must bind to `0.0.0.0` so it accepts connections from external network devices:

### Option A: Using the Automated Startup Script
Double-click:
```cmd
start_app.bat
```
*(This script automatically launches FastAPI on `0.0.0.0:8000` and Vite frontend on `http://localhost:5173`)*

### Option B: Manual Command Line
```powershell
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 6. Testing the Pipeline

### 1. Verification without Hardware (Simulation Mode)
If you do not have physical hardware plugged in right now, you can test the complete frontend radar and backend API immediately using the included simulator:
```powershell
cd backend
..\venv\Scripts\python.exe simulate_iot_device.py --device MAITRI_ESP8266_01 --interval 3
```
- Open your browser at `http://localhost:5173/iot-monitor`.
- Watch the live ultrasonic radar sweep smoothly across $20^\circ \longleftrightarrow 160^\circ$!
- Observe temperature, humidity, and soil moisture updating in real time.

### 2. Verification with Hardware
1. Connect ESP8266/ESP32 via micro-USB.
2. Select your COM port in Arduino IDE.
3. Open the Serial Monitor at **115200 baud**.
4. Click **Upload**.
5. Once booted, the Serial Monitor will print:
   ```text
   [WiFi] Connected successfully!
   [WiFi] ESP8266 IP Address: 192.168.1.142
   [SWEEP] Beginning Ultrasonic Radar Scan (20° -> 160°)...
   [Angle 20°] Distance: 86.4 cm | Status: CLEAR
   [Angle 70°] Distance: 34.2 cm | Status: WARNING
   [HTTP] Sending POST payload to MAITRI backend...
   [HTTP] Response code: 201
   [HTTP] Ingestion successful!
   ```
6. Visit `http://localhost:5173/iot-monitor` on your PC or mobile device connected to the same Wi-Fi.

---

## 7. Example JSON Telemetry Contract

Both ESP8266 and ESP32 transmit the exact same schema to `POST /api/iot/sensor-data`:

```json
{
  "device_id": "MAITRI_ESP8266_01",
  "controller_type": "ESP8266",
  "temperature": 28.6,
  "humidity": 67.2,
  "soil_moisture": 45.0,
  "scan": [
    {
      "angle": 20,
      "distance": 86.4,
      "object_detected": false,
      "status": "CLEAR"
    },
    {
      "angle": 70,
      "distance": 34.2,
      "object_detected": true,
      "status": "WARNING"
    },
    {
      "angle": 90,
      "distance": 18.5,
      "object_detected": true,
      "status": "VERY CLOSE"
    }
  ]
}
```

Backend response from `GET /api/iot/latest`:
```json
{
  "device_id": "MAITRI_ESP8266_01",
  "controller_type": "ESP8266",
  "status": "ONLINE",
  "is_online": true,
  "temperature": 28.6,
  "humidity": 67.2,
  "soil_moisture": 45.0,
  "nearest_object": {
    "angle": 90,
    "distance": 18.5,
    "status": "VERY CLOSE"
  },
  "object_status": "VERY CLOSE",
  "timestamp": "2026-09-08T15:00:00.000Z",
  "last_seen": "15:00:00 UTC",
  "time_diff_seconds": 2.4,
  "thresholds": {
    "clear_distance": 100.0,
    "warning_distance": 50.0,
    "critical_distance": 20.0,
    "offline_timeout_seconds": 20
  }
}
```

---

## 8. Safety Distance Thresholds

- $\mathbf{Distance > 100\text{ cm}}$: `CLEAR` (Field corridor is safe)
- $\mathbf{50\text{ cm} < Distance \le 100\text{ cm}}$: `OBJECT DETECTED` (Noticeable obstacle)
- $\mathbf{20\text{ cm} < Distance \le 50\text{ cm}}$: `WARNING` (Caution: approaching crop obstacle / boundary)
- $\mathbf{Distance \le 20\text{ cm}}$: `VERY CLOSE` (Critical collision hazard)
- $\mathbf{No\ echo / Timeout}$: `NO READING`
