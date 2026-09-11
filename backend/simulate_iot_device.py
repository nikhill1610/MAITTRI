#!/usr/bin/env python3
"""
MAITRI IoT Hardware Prototype Simulator
---------------------------------------
Simulates an ESP8266 or ESP32 microcontroller with:
- DHT22 (Temperature & Humidity)
- Resistive Soil Moisture Sensor
- Servo-mounted HC-SR04 Ultrasonic Sensor (20° to 160° radar sweep)

Usage:
  python simulate_iot_device.py --device MAITRI_ESP8266_01 --controller ESP8266 --interval 3
  python simulate_iot_device.py --device MAITRI_ESP32_01   --controller ESP32   --interval 2
"""

import sys
import time
import math
import random
import argparse
import requests
from datetime import datetime

DEFAULT_SERVER = "http://127.0.0.1:8000/api/iot/sensor-data"


def classify_distance(dist):
    if dist is None or dist <= 0:
        return False, "NO READING"
    if dist > 100.0:
        return False, "CLEAR"
    elif dist > 50.0:
        return True, "OBJECT DETECTED"
    elif dist > 20.0:
        return True, "WARNING"
    else:
        return True, "VERY CLOSE"


def generate_radar_sweep(step_deg=10, obstacle_angle=70, obstacle_dist=34.2):
    """Generates angle + distance readings from 20° to 160°."""
    angles = list(range(20, 161, step_deg))
    scan = []
    for a in angles:
        diff = abs(a - obstacle_angle)
        if diff <= 15:
            # Obstacle presence profile
            dist = round(obstacle_dist + diff * 2.8 + random.uniform(-1.0, 1.5), 1)
        elif a in (30, 40) and random.random() > 0.7:
            dist = round(78.0 + random.uniform(-4, 8), 1)
        else:
            dist = round(115.0 + random.uniform(5, 45), 1)

        detected, status = classify_distance(dist)
        scan.append({
            "angle": a,
            "distance": dist,
            "object_detected": detected,
            "status": status
        })
    return scan


def main():
    parser = argparse.ArgumentParser(description="MAITRI IoT Prototype Simulator")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"Backend URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--device", default="MAITRI_ESP8266_01", help="Device ID")
    parser.add_argument("--controller", default="ESP8266", choices=["ESP8266", "ESP32"], help="Controller Type")
    parser.add_argument("--interval", type=float, default=3.0, help="Sweep transmission interval in seconds")
    parser.add_argument("--count", type=int, default=0, help="Number of sweeps to send (0 = infinite loop)")
    args = parser.parse_args()

    print("=" * 65)
    print("  MAITRI IoT Hardware Prototype Simulator (ESP8266 / ESP32)")
    print("=" * 65)
    print(f"  Target Server   : {args.server}")
    print(f"  Device ID       : {args.device}")
    print(f"  Controller      : {args.controller}")
    print(f"  Sweep Interval  : {args.interval}s")
    print(f"  Press Ctrl+C to stop.\n")

    iteration = 0
    while True:
        iteration += 1
        now_ts = time.time()

        # Dynamic oscillating obstacle (moves slowly across field)
        target_angle = int(60 + 35 * (0.5 + 0.5 * math.sin(now_ts / 6.0)))
        target_dist = round(28.0 + 18.0 * (0.5 + 0.5 * math.cos(now_ts / 5.0)), 1)

        scan_data = generate_radar_sweep(step_deg=10, obstacle_angle=target_angle, obstacle_dist=target_dist)

        temp = round(28.4 + 1.5 * math.sin(now_ts / 15.0) + random.uniform(-0.2, 0.2), 1)
        humidity = round(66.8 + 2.5 * math.cos(now_ts / 18.0) + random.uniform(-0.4, 0.4), 1)
        soil = round(45.0 + 3.0 * math.sin(now_ts / 20.0) + random.uniform(-0.5, 0.5), 1)

        payload = {
            "device_id": args.device,
            "controller_type": args.controller,
            "temperature": temp,
            "humidity": humidity,
            "soil_moisture": soil,
            "scan": scan_data
        }

        timestamp_str = datetime.now().strftime("%H:%M:%S")
        try:
            res = requests.post(args.server, json=payload, timeout=4.0)
            if res.status_code == 201:
                res_json = res.json()
                data = res_json.get("data", {})
                nearest = data.get("nearest_object") or {}
                n_dist = nearest.get("distance", "None")
                n_ang = nearest.get("angle", "--")
                status = data.get("object_status", "CLEAR")

                print(f"[{timestamp_str}] Sweep #{iteration:03d} | "
                      f"Temp: {temp}°C | Hum: {humidity}% | Soil: {soil}% | "
                      f"Nearest: {n_dist}cm @ {n_ang}° | Status: {status} | HTTP 201 OK")
            else:
                print(f"[{timestamp_str}] HTTP {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[{timestamp_str}] [ERROR] Could not connect to backend: {e}")

        if args.count > 0 and iteration >= args.count:
            print(f"\nCompleted {args.count} sweeps. Exiting.")
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulator stopped by user.")
        sys.exit(0)
