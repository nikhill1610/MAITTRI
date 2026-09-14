# MAITRI Backend — Complete API Authorization Matrix

This document provides the authoritative authorization and access-control matrix for all HTTP endpoints exposed by the MAITRI FastAPI production backend.

| Method | Path | Auth Required | Role | Resource Owner Check | Device Auth | Type | Production Status |
|---|---|---|---|---|---|---|---|
| **GET** | `/` | No | Public | No | No | Public | Enabled |
| **GET** | `/health` | No | Public | No | No | Public | Enabled |
| **GET** | `/api/health` | No | Public | No | No | Public | Enabled |
| **POST** | `/api/auth/register` | No | Public | No | No | Public | Enabled |
| **POST** | `/api/auth/login` | No | Public | No | No | Public | Enabled |
| **GET** | `/api/auth/me` | **Yes** | Any Valid Authenticated User | Yes (Self) | No | Private | Enabled |
| **GET** | `/api/farms` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Per-User Scope) | No | Private | Enabled |
| **POST** | `/api/farms` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Self Bind) | No | Private | Enabled |
| **GET** | `/api/farms/{id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **PUT** | `/api/farms/{id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **DELETE** | `/api/farms/{id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **POST** | `/api/farmer-plans` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Private | Enabled |
| **GET** | `/api/farmer-plans` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (User Scope) | No | Private | Enabled |
| **GET** | `/api/farmer-plans/{plan_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Plan Owner) | No | Private | Enabled |
| **GET** | `/api/farmer-plans/{plan_id}/today` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Plan Owner) | No | Private | Enabled |
| **GET** | `/api/farmer-plans/{plan_id}/week` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Plan Owner) | No | Private | Enabled |
| **GET** | `/api/farmer-plans/{plan_id}/timeline` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Plan Owner) | No | Private | Enabled |
| **PATCH** | `/api/farmer-plans/tasks/{task_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Task Owner) | No | Private | Enabled |
| **POST** | `/api/farmer-plans/tasks/{task_id}/complete` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Task Owner) | No | Private | Enabled |
| **POST** | `/api/farmer-plans/tasks/{task_id}/note` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Task Owner) | No | Private | Enabled |
| **GET** | `/api/farmer-plans/{plan_id}/history` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Plan Owner) | No | Private | Enabled |
| **GET** | `/api/crop-calendar` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/crop-calendar/{crop_name}` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/fertilizer/analyze` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **POST** | `/api/fertilizer/recommend` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **GET** | `/api/fertilizer/history` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **POST** | `/api/fertilizer/history` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Private | Enabled |
| **GET** | `/api/fertilizer/sources` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/fertilizer/sensor-latest` | No | Public (Indicative) | No | No | Public | Enabled (Honest Unavailable) |
| **POST** | `/api/pest/analyze` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/pest/recommend` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **POST** | `/api/pest/history` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Private | Enabled |
| **GET** | `/api/pest/sources` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/government-schemes` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/government-schemes/{id}` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/insurance` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/insurance/upcoming` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/insurance/{id}` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/parali/analyze` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **GET** | `/api/parali/crops` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/parali/methods` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/parali/action-plan` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/market-prices` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/market-prices/{commodity}` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/weather` | No | Public Reference | No | No | Public | Enabled |
| **GET** | `/api/location/search` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/soil/estimate` | No | Public Reference | No | No | Public | Enabled |
| **POST** | `/api/nutrients/analyze` | Optional (Required if `farm_id` provided) | FARMER / OPERATOR / ADMIN | Yes (Farm Owner) | No | Mixed | Enabled |
| **POST** | `/api/chat` | No | Public / Authenticated Context | Self Context | No | Public | Enabled |
| **GET** | `/api/chat/status` | No | Public | No | No | Public | Enabled |
| **POST** | `/api/chat/debug` | **Yes (Prod)** | ADMIN | No | No | Private | **Disabled in Prod (403)** |
| **POST** | `/api/iot/sensor-data` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **POST** | `/api/iot/telemetry` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **POST** | `/api/iot/data` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **POST** | `/sensor-data` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **POST** | `/api/sensor-data` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **POST** | `/telemetry` | No (Token Auth) | Any / Edge Hardware Node | Token Verification | **Yes (`X-Device-Token`)** | Edge | Enabled |
| **GET** | `/api/iot/latest` | Optional | FARMER / OPERATOR / ADMIN | Yes (When Authed) | No | Mixed | Enabled |
| **GET** | `/api/iot/devices` | Optional | FARMER / OPERATOR / ADMIN | Yes (When Authed) | No | Mixed | Enabled |
| **GET** | `/api/iot/history` | Optional | FARMER / OPERATOR / ADMIN | Yes (When Authed) | No | Mixed | Enabled |
| **GET** | `/api/iot/config` | No | Public / Edge Node | No (LAN IPs Hidden in Prod) | No | Public | Enabled |
| **POST** | `/api/iot/config` | **Yes (Farmers)** | AUTHORIZED_OPERATOR / ADMIN | No | No | Mixed | Enabled |
| **GET** | `/api/iot/lan-info` | **Yes (Prod)** | Internal Dev Utility | No | No | Private | **Disabled in Prod (403)** |
| **POST** | `/api/iot/simulate` | **Yes (Prod)** | Internal Dev Simulator | No | No | Private | **Disabled in Prod (403)** |
| **GET** | `/api/operators/dashboard` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **POST** | `/api/operators/farmers` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/operators/farmers` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/operators/farmers/{farmer_id}` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **PATCH** | `/api/operators/farmers/{farmer_id}` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/operators/farmers/{farmer_id}/card` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/farmer-profile/qr/{farmer_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Self or Operator) | No | Private | Enabled |
| **POST** | `/api/soil-tests` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farmer Owner or Operator) | No | Private | Enabled |
| **GET** | `/api/soil-tests` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farmer Scope) | No | Private | Enabled |
| **GET** | `/api/soil-tests/{req_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **PATCH** | `/api/soil-tests/{req_id}/status` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/soil-tests/{req_id}/report` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **POST** | `/api/soil-tests/{req_id}/report` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **POST** | `/api/service-requests` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farmer Owner or Operator) | No | Private | Enabled |
| **GET** | `/api/service-requests` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farmer Scope) | No | Private | Enabled |
| **GET** | `/api/service-requests/{req_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **PATCH** | `/api/service-requests/{req_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Farmer: Cancel only; Operator: Full) | No | Private | Enabled |
| **POST** | `/api/documents/upload` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Self Vault or Operator) | No | Private | Enabled |
| **GET** | `/api/documents` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Per-User Scope) | No | Private | Enabled |
| **GET** | `/api/documents/download/{doc_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **GET** | `/api/documents/signed-url/{doc_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **DELETE** | `/api/documents/{doc_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **GET** | `/api/farm-brain/today/{farm_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **GET** | `/api/farm-brain/week/{farm_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **GET** | `/api/communications/preferences/{farmer_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **PATCH** | `/api/communications/preferences/{farmer_id}` | **Yes** | FARMER / OPERATOR / ADMIN | Yes (Strict IDOR) | No | Private | Enabled |
| **POST** | `/api/communications/sms/send` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **GET** | `/api/communications/sms/logs` | **Yes** | AUTHORIZED_OPERATOR / ADMIN | Operator Scope | No | Private | Enabled |
| **POST** | `/api/communications/ivr/simulate` | **Yes** | FARMER / OPERATOR / ADMIN | Developer / Operator Tool | No | Private | Enabled |
| **POST** | `/api/communications/ivr/webhook` | No | Telephony Provider Webhook | Caller Phone Verification | No | Public Webhook | Enabled |
