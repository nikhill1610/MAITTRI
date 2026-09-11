/**
 * ============================================================================
 * MAITRI Smart Agriculture - IoT Edge Node
 * Controller: ESP8266 NodeMCU
 * ============================================================================
 * Features:
 *  - Ambient Temperature & Humidity via DHT22
 *  - In-situ Soil Moisture via Analog Capacitive/Resistive Probe (A0)
 *  - Ultrasonic Obstacle Scanning via HC-SR04 mounted on SG90 / MG90S Servo
 *  - Sweep from 20° to 160° in 10° steps
 *  - Real-time safety status classification (CLEAR, OBJECT DETECTED, WARNING, VERY CLOSE)
 *  - Serialized JSON transmission via HTTP POST to FastAPI backend over LAN Wi-Fi
 *  - Automatic non-blocking Wi-Fi reconnection & sensor fault tolerance
 * ============================================================================
 * Required Arduino Libraries:
 *  1. ESP8266WiFi (Built-in with ESP8266 core)
 *  2. ESP8266HTTPClient (Built-in with ESP8266 core)
 *  3. Servo (Built-in)
 *  4. DHT sensor library by Adafruit
 *  5. Adafruit Unified Sensor
 *  6. ArduinoJson (v6 or v7) by Benoit Blanchon
 * ============================================================================
 */

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <Servo.h>
#include <DHT.h>
#include <ArduinoJson.h>

// ============================================================================
// 1. HARDWARE PIN CONFIGURATION (Configurable)
// ============================================================================
#define PIN_DHT22         4    // NodeMCU D2 (GPIO4)
#define PIN_SOIL_ANALOG   A0   // NodeMCU A0 (ADC0)
#define PIN_SERVO         14   // NodeMCU D5 (GPIO14)
#define PIN_HCSR04_TRIG   12   // NodeMCU D6 (GPIO12)
#define PIN_HCSR04_ECHO   13   // NodeMCU D7 (GPIO13)

#define DHT_TYPE          DHT22

// ============================================================================
// 2. NETWORK & SERVER CONFIGURATION
// ============================================================================
// Put your Wi-Fi credentials here (PC Mobile Hotspot or Home/Phone Wi-Fi)
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// OPTION A (Active Windows Mobile Hotspot - Recommended):
// When ESP8266 connects to your Windows Mobile Hotspot, the PC's IP is 192.168.137.1
const char* SERVER_URL    = "http://192.168.137.1:8000/api/iot/sensor-data";

// OPTION B (Home / Phone Wi-Fi 'vivo Y400 Pro 5G'):
// When ESP8266 connects to your Phone/Home Wi-Fi router, use your PC's Wi-Fi IP:
// const char* SERVER_URL = "http://10.38.2.70:8000/api/iot/sensor-data";

// Device Identification
const char* DEVICE_ID       = "MAITRI_ESP8266_01";
const char* CONTROLLER_TYPE = "ESP8266";

// ============================================================================
// 3. RADAR & SENSOR SCAN CONFIGURATION
// ============================================================================
const int SCAN_START_ANGLE = 20;   // Sweep start angle (degrees)
const int SCAN_END_ANGLE   = 160;  // Sweep end angle (degrees)
const int SCAN_STEP_DEG    = 10;   // Angle step (degrees)
const int SERVO_SETTLE_MS  = 65;   // Delay for servo stabilization before ping
const int SWEEP_PAUSE_MS   = 2000; // Pause between complete sweep cycles

// Safety Distance Thresholds (in cm)
const float THRESHOLD_CLEAR    = 100.0; // > 100cm = CLEAR
const float THRESHOLD_WARNING  = 50.0;  // 20cm < dist <= 50cm = WARNING (50 < dist <= 100 = OBJECT DETECTED)
const float THRESHOLD_CRITICAL = 20.0;  // <= 20cm = VERY CLOSE

// Soil Moisture Calibration (Raw ADC 0-1023)
// In air (dry): ~800-1024, In water (wet): ~300-450
const int SOIL_AIR_VALUE   = 850;
const int SOIL_WATER_VALUE = 350;

// ============================================================================
// GLOBAL OBJECTS
// ============================================================================
DHT dht(PIN_DHT22, DHT_TYPE);
Servo radarServo;
WiFiClient wifiClient;

// Structure for storing scan point telemetry
struct ScanPoint {
  int angle;
  float distance;
  bool object_detected;
  const char* status;
};

const int MAX_POINTS = ((SCAN_END_ANGLE - SCAN_START_ANGLE) / SCAN_STEP_DEG) + 1;
ScanPoint scanBuffer[MAX_POINTS];
int pointCount = 0;

// ============================================================================
// HELPER: Connect / Reconnect Wi-Fi
// ============================================================================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.println();
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 25) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.println("[WiFi] Connected successfully!");
    Serial.print("[WiFi] ESP8266 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("[WiFi] Connection timeout. Will retry next cycle.");
  }
}

// ============================================================================
// HELPER: Measure Ultrasonic Distance (HC-SR04)
// ============================================================================
float measureDistanceCm() {
  // Clear trigger pin
  digitalWrite(PIN_HCSR04_TRIG, LOW);
  delayMicroseconds(4);

  // Send 10 microsecond HIGH pulse
  digitalWrite(PIN_HCSR04_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_HCSR04_TRIG, LOW);

  // Measure pulse duration on ECHO pin with 25ms timeout (~4.2 meters max)
  unsigned long duration = pulseIn(PIN_HCSR04_ECHO, HIGH, 25000);

  if (duration == 0) {
    // No echo received / out of range
    return -1.0;
  }

  // Speed of sound: 343 m/s = 0.0343 cm/microsecond.
  // Distance = (Duration * 0.0343) / 2
  float distanceCm = (duration * 0.0343) / 2.0;

  if (distanceCm > 400.0 || distanceCm < 2.0) {
    return -1.0;
  }

  return distanceCm;
}

// ============================================================================
// HELPER: Classify Distance Status
// ============================================================================
const char* classifyStatus(float distance, bool &detected) {
  if (distance <= 0.0) {
    detected = false;
    return "NO READING";
  }
  if (distance > THRESHOLD_CLEAR) {
    detected = false;
    return "CLEAR";
  } else if (distance > THRESHOLD_WARNING) {
    detected = true;
    return "OBJECT DETECTED";
  } else if (distance > THRESHOLD_CRITICAL) {
    detected = true;
    return "WARNING";
  } else {
    detected = true;
    return "VERY CLOSE";
  }
}

// ============================================================================
// HELPER: Read Calibrated Soil Moisture (0% to 100%)
// ============================================================================
float readSoilMoisturePercent() {
  int raw = analogRead(PIN_SOIL_ANALOG);
  // Map raw inverted value (higher raw = drier soil)
  float percent = map(raw, SOIL_AIR_VALUE, SOIL_WATER_VALUE, 0, 100);
  if (percent < 0.0) percent = 0.0;
  if (percent > 100.0) percent = 100.0;
  return percent;
}

// ============================================================================
// HELPER: Send JSON Telemetry to Backend
// ============================================================================
void sendTelemetry(float temp, float hum, float soil) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[HTTP] Wi-Fi offline. Skipping transmission.");
    return;
  }

  HTTPClient http;
  http.begin(wifiClient, SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  // Dynamic JSON document sizing (supports up to 25 scan points)
  DynamicJsonDocument doc(4096);
  doc["device_id"] = DEVICE_ID;
  doc["controller_type"] = CONTROLLER_TYPE;

  if (!isnan(temp)) doc["temperature"] = serialized(String(temp, 1));
  else doc["temperature"] = nullptr;

  if (!isnan(hum)) doc["humidity"] = serialized(String(hum, 1));
  else doc["humidity"] = nullptr;

  doc["soil_moisture"] = serialized(String(soil, 1));

  JsonArray scanArr = doc.createNestedArray("scan");
  for (int i = 0; i < pointCount; i++) {
    JsonObject pt = scanArr.createNestedObject();
    pt["angle"] = scanBuffer[i].angle;
    if (scanBuffer[i].distance > 0.0) {
      pt["distance"] = serialized(String(scanBuffer[i].distance, 1));
    } else {
      pt["distance"] = nullptr;
    }
    pt["object_detected"] = scanBuffer[i].object_detected;
    pt["status"] = scanBuffer[i].status;
  }

  String jsonString;
  serializeJson(doc, jsonString);

  Serial.println("[HTTP] Sending POST payload to MAITRI backend...");
  int httpCode = http.POST(jsonString);

  if (httpCode > 0) {
    Serial.print("[HTTP] Response code: ");
    Serial.println(httpCode);
    if (httpCode == HTTP_CODE_CREATED || httpCode == HTTP_CODE_OK) {
      String response = http.getString();
      Serial.println("[HTTP] Ingestion successful!");
    }
  } else {
    Serial.print("[HTTP] POST failed, error: ");
    Serial.println(http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ============================================================================
// SETUP
// ============================================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("==================================================");
  Serial.println("   MAITRI SMART AGRICULTURE - ESP8266 NODE        ");
  Serial.println("==================================================");

  // Pin Modes
  pinMode(PIN_HCSR04_TRIG, OUTPUT);
  pinMode(PIN_HCSR04_ECHO, INPUT);
  pinMode(PIN_SOIL_ANALOG, INPUT);

  // Initialize Sensors & Actuators
  dht.begin();
  radarServo.attach(PIN_SERVO);
  radarServo.write(90); // Center servo

  Serial.println("[INIT] Sensors and Servo initialized.");

  // Connect to Wi-Fi
  connectWiFi();
}

// ============================================================================
// MAIN LOOP
// ============================================================================
void loop() {
  // Ensure Wi-Fi is active
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }

  Serial.println("\n--------------------------------------------------");
  Serial.println("[SWEEP] Beginning Ultrasonic Radar Scan (20° -> 160°)...");

  pointCount = 0;

  // 1. Forward Radar Sweep: 20° to 160°
  for (int angle = SCAN_START_ANGLE; angle <= SCAN_END_ANGLE; angle += SCAN_STEP_DEG) {
    radarServo.write(angle);
    delay(SERVO_SETTLE_MS);

    float dist = measureDistanceCm();
    bool detected = false;
    const char* status = classifyStatus(dist, detected);

    scanBuffer[pointCount].angle = angle;
    scanBuffer[pointCount].distance = dist;
    scanBuffer[pointCount].object_detected = detected;
    scanBuffer[pointCount].status = status;

    Serial.print("  [Angle ");
    Serial.print(angle);
    Serial.print("°] Distance: ");
    if (dist > 0) {
      Serial.print(dist, 1);
      Serial.print(" cm");
    } else {
      Serial.print("NO ECHO");
    }
    Serial.print(" | Status: ");
    Serial.println(status);

    pointCount++;
  }

  // 2. Read Environmental Sensors
  float temperature = dht.readTemperature();
  float humidity    = dht.readHumidity();
  float soilMoisture = readSoilMoisturePercent();

  Serial.println("[ENV] Environmental Telemetry:");
  Serial.print("  Temperature  : ");
  if (!isnan(temperature)) {
    Serial.print(temperature, 1);
    Serial.println(" °C");
  } else {
    Serial.println("DHT22 Error (NaN)");
  }

  Serial.print("  Humidity     : ");
  if (!isnan(humidity)) {
    Serial.print(humidity, 1);
    Serial.println(" %");
  } else {
    Serial.println("DHT22 Error (NaN)");
  }

  Serial.print("  Soil Moisture: ");
  Serial.print(soilMoisture, 1);
  Serial.println(" %");

  // 3. Transmit complete payload to MAITRI Backend
  sendTelemetry(temperature, humidity, soilMoisture);

  // 4. Return Servo smoothly to 90° center
  delay(200);
  radarServo.write(90);

  // 5. Pause before next sweep cycle
  delay(SWEEP_PAUSE_MS);
}
