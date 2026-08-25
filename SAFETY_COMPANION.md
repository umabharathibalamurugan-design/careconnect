# CareConnect Safety & Companion — v1.0

This module is an **additive** Django app. It does not replace ResidentProfile, Guardian, or EmergencyAlert. It references the existing models and creates a normal `EmergencyAlert` whenever an automatic/high-priority safety signal fires.

## Included

1. Silent/discreet SOS — rapid triple press, with a browser test and native Android implementation.
2. Local fake-call/decoy exit — no server request.
3. Crowd-sourced safety graph + weighted Dijkstra route.
4. Fall/inactivity event API + native Android/iOS sensor algorithms.
5. On-device TFLite distress inference integration; audio is sent to the server only after the local threshold fires.
6. Daily wellness scheduling and guardian-only lower-severity escalation.

The dashboard receives one new, scoped **Safety & Companion** section. Existing dashboard cards, layout, colors and JavaScript are not restyled or replaced.

---

## 1. Install

The module uses only packages already present in the supplied project.

```powershell
cd society_app
python manage.py check
python manage.py migrate
python manage.py test safety_companion
python manage.py runserver
```

Then sign in as a Resident and open:

`http://127.0.0.1:8000/dashboard/`

The new section is shown only to Resident accounts.

### Production

Commit the new `safety_companion/` directory, the dashboard additive files, and settings/URL changes.

For a production scheduler, run this command every minute:

```bash
python manage.py process_safety_companion
```

For Render, create a small Cron Job using the same repository/environment and command. The job does two things: sends due wellness notifications and converts overdue wellness checks into guardian welfare notifications.

---

# 2. API

All endpoints use the project's existing JWT authentication:

`Authorization: Bearer <access_token>`

Base URL:

`/api/safety-companion/`

### Safety profile

**GET `/profile/`**

Response:

```json
{
  "companion_enabled": true,
  "silent_sos_enabled": true,
  "fall_detection_enabled": true,
  "inactivity_detection_enabled": true,
  "voice_distress_enabled": false,
  "wellness_enabled": false,
  "triple_press_window_ms": 900,
  "inactivity_minutes": 60,
  "wellness_timeout_minutes": 30,
  "safety_route_weight": "2.00",
  "updated_at": "2026-08-25T03:30:00Z"
}
```

**PATCH `/profile/`**

```json
{
  "voice_distress_enabled": true,
  "wellness_enabled": true,
  "inactivity_minutes": 45
}
```

---

### 2.1 Silent SOS

**POST `/silent-sos/`**

```json
{
  "latitude": 13.0827,
  "longitude": 80.2707,
  "trigger_id": "9b6c2e0c-7f16-4a5e-8f8c-123456789abc",
  "client_timestamp": "2026-08-25T08:30:00+05:30",
  "source": "rapid_triple_press"
}
```

Response:

```json
{
  "incident_id": 42,
  "signal_id": 7,
  "status": "active",
  "priority": "critical",
  "notified_users": 5,
  "silent": true
}
```

The server creates a normal `EmergencyAlert`, records a `SafetySignal`, writes an `IncidentUpdate`, and calls the existing CareConnect notification/guardian/responder pipeline.

The **client** is responsible for not showing UI, vibration, toast or sound when the trigger fires.

---

### 2.2 Fall / inactivity / voice distress

**POST `/signals/`**

Fall:

```json
{
  "signal_type": "fall",
  "confidence": 0.94,
  "latitude": 13.0827,
  "longitude": 80.2707,
  "metadata": {
    "impact_g": 4.7,
    "post_fall_stillness_seconds": 12
  }
}
```

Inactivity:

```json
{
  "signal_type": "inactivity",
  "confidence": 0.91,
  "latitude": 13.0827,
  "longitude": 80.2707,
  "metadata": {
    "inactive_minutes": 65
  }
}
```

Voice:

```json
{
  "signal_type": "voice_distress",
  "confidence": 0.89,
  "latitude": 13.0827,
  "longitude": 80.2707,
  "metadata": {
    "model": "distress_detector_v1",
    "window_ms": 2000
  }
}
```

Voice scores below `0.75` are deliberately rejected as non-triggering.

A successful signal becomes an `EmergencyAlert` with `status=active` and `priority=critical`.

---

### 2.3 Crowd-sourced safety segments

**POST `/route-segments/`**

```json
{
  "start_lat": 13.082700,
  "start_lng": 80.270700,
  "end_lat": 13.083200,
  "end_lng": 80.271200,
  "distance_m": 82,
  "safety_score": 85,
  "one_way": false
}
```

Repeated reports for the same edge are aggregated into a running average and report count.

**GET `/route-segments/`**

Returns up to 500 active graph segments for the resident's society.

---

### 2.4 Safe route

**POST `/safe-route/`**

```json
{
  "start": {"lat": 13.0827, "lng": 80.2707},
  "end": {"lat": 13.0900, "lng": 80.2800},
  "safety_weight": 2.0,
  "max_snap_m": 250
}
```

The backend uses Dijkstra. Each road edge has:

`weighted_cost = distance_m × (1 + safety_weight × (1 - safety_score / 100))`

So a route can deliberately be longer when it has a much higher safety score.

Response contains the ordered path, distance, weighted cost, average safety and segment details.

**Important:** a road graph must be populated first. The module intentionally does not pretend to know road geometry. In production, feed road segments from the map provider used by the mobile app, then let CareConnect add the crowd-sourced safety layer.

---

### 2.5 Daily wellness

**POST `/wellness/`**

```json
{
  "scheduled_for": "2026-08-26T09:00:00+05:30",
  "timeout_minutes": 30,
  "message": "Good morning. Please confirm that you are okay."
}
```

**POST `/wellness/<id>/action/`**

```json
{"action": "safe"}
```

or:

```json
{"action": "cancel"}
```

The scheduled maintenance command marks due checks as `prompted`. If a resident does not answer by `response_deadline`, it changes the check to `missed` and sends a **wellness** notification to linked guardians. It does **not** create a critical SOS incident.

---

# 3. Incident lifecycle integration

The new module does not create a second incident system.

Automatic events create the existing:

`EmergencyAlert`

with:

`OPEN → ACTIVE → ESCALATED → RESOLVED`

The module creates the alert initially as `ACTIVE` because an automatic safety trigger is already actionable. Existing responders, guardians, notification deliveries, Response Center pages and incident history can therefore see the same incident.

Existing response endpoints remain responsible for:

- responder acceptance
- on-the-way
- arrival
- resolution
- escalation
- incident chat
- incident updates

This keeps the feature small enough for an 8-week student project.

---

# 4. Android implementation

Copy the snippets from `mobile/android/SafetyCompanion.kt`.

Recommended dependencies:

```gradle
implementation("androidx.work:work-runtime-ktx:2.9.1")
implementation("com.squareup.okhttp3:okhttp:4.12.0")
implementation("org.tensorflow:tensorflow-lite-task-audio:0.4.4")
implementation("org.tensorflow:tensorflow-lite:2.14.0")
```

Permissions:

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.VIBRATE"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE"/>
```

For a background hardware-key implementation, Android requires an explicit foreground/accessibility design. Do not silently install an AccessibilityService. The user must enable it in Android settings, and Play Store distribution has additional policy requirements. The included `SafetyCompanionKeyService` is therefore opt-in.

### Fall logic

The native algorithm watches accelerometer magnitude:

- free-fall / unloading: magnitude below about `0.6 g`
- impact: magnitude above about `2.5 g`
- post-impact stillness: low variance for about 8–15 seconds

Only after the sequence is observed does the app send `/signals/`.

### Inactivity

Store the last meaningful motion timestamp locally. A WorkManager task checks it periodically. If it exceeds the configured threshold, send `/signals/` with `signal_type=inactivity`.

Do not wake the CPU every second. Use WorkManager/foreground sensor processing where permitted.

### Voice

Use the TensorFlow Lite Task Audio API with a local model in:

`app/src/main/assets/distress_detector.tflite`

The model should output a distress/scream probability. Keep a rolling 1–2 second audio window. Trigger only after a threshold such as `0.75` for consecutive windows. Stop recording/uploading after the local decision.

---

# 5. iOS implementation

See `mobile/ios/SafetyCompanion.swift`.

Native APIs:

- `CoreMotion` → `CMMotionManager` for fall/inactivity
- `CoreLocation` → GPS
- `AVAudioEngine` → local microphone stream
- TensorFlow Lite Swift runtime → on-device classification
- `CallKit` → local decoy incoming-call UI
- `UserNotifications` → wellness reminders

iOS does **not** allow an ordinary app to globally intercept arbitrary hardware key presses. The provided triple-press implementation is therefore an in-app/key-command implementation. For a production background trigger, use an approved iOS mechanism such as an app shortcut, Action Button/Control, or an OS-supported accessibility workflow rather than claiming that an arbitrary global key listener exists.

Similarly, a local fake call can be presented through CallKit when the app is active and the user taps the decoy control. Background VoIP-style incoming calls require Apple's PushKit/CallKit architecture and should not be faked with an unsupported background mechanism.

---

# 6. Privacy / security rules

- Do not upload continuous microphone audio.
- Do not store raw audio on the server for distress detection.
- Send only event metadata after the on-device threshold fires.
- Request location/microphone permissions only when the relevant feature is enabled.
- Allow the user to disable every automatic detector.
- Treat fall/voice/inactivity as probabilistic signals and label them accordingly.
- Keep a server-side incident audit trail.
- Rate-limit automatic triggers in production to prevent repeated incident storms.
- Use HTTPS and short-lived JWT access tokens in production.

---

# 7. Eight-week implementation plan

**Week 1:** migrate module, profile API, dashboard section, Android/iOS API client.

**Week 2:** silent SOS + incident integration + responder/guardian notification testing.

**Week 3:** fake call/decoy flows and accessibility testing.

**Week 4:** crowd safety data collection and safe-route graph.

**Week 5:** fall detector calibration using real device sensor logs.

**Week 6:** TFLite distress model integration and false-positive testing.

**Week 7:** wellness scheduling, guardian escalation, offline handling and permissions.

**Week 8:** end-to-end testing, security review, battery tests, UI polish and deployment.

A student team should keep the first release to **one society, Android + iOS client triggers, the existing CareConnect incident engine, and a bounded safety graph**. Avoid building a full replacement for Google Maps/Apple Maps.
