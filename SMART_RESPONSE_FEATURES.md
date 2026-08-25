# CareConnect Smart Response Upgrade

Added three core innovations without removing the existing SOS, multilingual AI assistant, GPS, roles, notifications or incident workflow.

## 1. Smart Volunteer Matching
`POST /api/response/sos/` now evaluates eligible emergency volunteers using:
- live GPS distance when available
- emergency/disaster-response role
- current emergency workload
- response history / reliability score

The selected responder is automatically assigned and receives a Smart Match notification.

## 2. Live Responder Availability
`GET /api/response/responder-availability/`

Shows total, available, busy and offline volunteers plus:
- role
- block
- reliability score
- completed incidents
- live distance when latitude/longitude is supplied

The dashboard displays this for volunteer/security/admin/society-admin roles.

## 3. Two-Way Incident Closure
The existing lifecycle remains:
SOS -> Notified -> Accepted -> On Way -> Arrived -> Resolved

When resolved:
- resident receives resolution confirmation
- guardians/society/security are notified
- responders who were handling the incident receive `No further response required`
- responder assignments are closed
- incident update history records the resolution

## Run
From the folder containing `manage.py`:

```powershell
python manage.py check
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000/login-page/`.
