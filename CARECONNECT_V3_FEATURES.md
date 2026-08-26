# CareConnect v3 — Emergency-first working build

## Added in this build
- Emergency Mode with live response state
- Two-way responder lifecycle visible to the resident
- Resident-to-response-team incident chat from the emergency screen
- Responder dashboard queue for volunteers and security
- Accept → Responding → Arrived → Resolve actions
- Nearby police station lookup from the user's GPS through a map search
- Emergency-services call shortcut (India deployment default: 112)
- Explicit emergency escalation action with backend incident status update
- Guardian/security/responder status indicators during Emergency Mode
- Response timeline: SOS → Notified → Accepted → On Way → Arrived → Resolved
- Accessibility/focus/reduced-motion styling retained
- Existing Safety Check-In, smart matching, notifications, live GPS, admin command center, incident history and incident chat retained

## Important deployment note
CareConnect does not claim to dispatch police automatically. The police station button opens a nearby-station map search, while the escalation endpoint records the escalation inside CareConnect. Real police/SMS/push dispatch requires an authorised external service integration and credentials.

## Local run
Double-click `start_careconnect.bat` on Windows, or run:

```text
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Demo password: `CareConnect@123`
