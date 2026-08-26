# CareConnect v4 – Working Emergency Response Update

This version addresses the issues found in the earlier UI review.

## What changed

### 1. No decorative workflow cards on the main dashboard
The previous "Response Flow" / "Response lifecycle" cards were removed from the dashboard. The application now shows live actions and live incident data instead of a diagram pretending to be a workflow.

### 2. Role-specific workspaces
- Resident: SOS, Safety Check-In, trusted contacts, live location, notifications.
- Guardian: linked resident incidents, location, response status, contact actions.
- Volunteer: response queue, Accept → On Way → Arrived → Resolve, resident call and incident chat.
- Security: society-scoped response desk, resident call, location and escalation.
- Society Admin: society command center, residents, responders, incidents, hotspots and intelligence.
- Admin: platform emergency operations and responder performance.
- Super Admin: global platform oversight, societies, configuration and audit visibility.

### 3. Real notification actions
Notifications are connected to incidents. If a notification belongs to an incident, users can open the incident directly. Volunteers/security can use "Respond now" and authorised roles can escalate.

### 4. Two-way incident response
Every responder action writes an incident update and notifies the other participants. The resident can see the response state while the responder can see the same incident and communicate through chat.

### 5. Calling
Resident SOS uses the primary emergency contact when available. Responder dashboards can call the resident when a phone number is available.

### 6. Voice features
- Resident SOS page: voice-to-text emergency message.
- Resident SOS page: voice-note recording.
- Incident chat: voice-note recording.
- Incident chat: speech-to-text message input.

These use browser capabilities and require microphone permission. Automatic transcription depends on browser support.

### 7. Police / emergency-services fallback
The SOS screen can locate nearby police stations using the current GPS and provides the configured emergency-services call shortcut. Automatic police dispatch is not claimed unless a real authorised emergency-service integration is connected.

### 8. Smart escalation
Response windows can auto-escalate expired incidents when the system processes the incident queue. Escalated incidents become critical and notify the response network.

### 9. Accessibility and emergency UI
The project keeps keyboard focus indicators, reduced-motion support, large emergency controls and simple emergency mode. Decorative visuals are used on calm screens, not in the emergency state where they could distract the user.

### 10. Python 3.14 installation fix
`psycopg[binary]` was changed from the unavailable exact 3.2.9 build to 3.2.10 so the supplied setup works with the Python 3.14 environment used during testing.

## Run on Windows

From the `society_app` folder:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Demo password: `CareConnect@123`

Demo users:
- resident_demo
- guardian_demo
- volunteer_demo
- security_demo
- society_admin_demo
- admin_demo
- superadmin_demo
