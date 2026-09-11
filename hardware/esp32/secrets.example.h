#ifndef MAITRI_SECRETS_H
#define MAITRI_SECRETS_H

// ============================================================================
// MAITRI IoT Hardware - Network Secrets Configuration Template
// ============================================================================
// Copy this file to "secrets.h" in this folder and enter your credentials.
// "secrets.h" is included in .gitignore and will NOT be committed to Git.
//
// In your .ino sketch, you can optionally include:
//   #include "secrets.h"
// ============================================================================

#define SECRET_WIFI_SSID     "YOUR_WIFI_SSID"
#define SECRET_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define SECRET_SERVER_URL    "http://192.168.137.1:8000/api/iot/sensor-data"

#endif // MAITRI_SECRETS_H
