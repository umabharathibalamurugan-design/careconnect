# CareConnect — Full Working Web App

CareConnect is a Django REST Framework emergency-response web application with role-based access, JWT authentication, society management, emergency contacts, one-tap SOS, GPS tracking, notifications, incident response, escalation and incident chat.

## Included
- Django + Django REST Framework + JWT
- SQLite local fallback; PostgreSQL through `DATABASE_URL`
- Role-based users: resident, guardian, volunteer, security, admin, society admin, super admin
- Society / block / flat structure and resident mapping
- Primary/secondary emergency contacts and verification
- One-tap SOS with emergency category, message and browser GPS
- Guardian / volunteer / security in-app notification records
- Response window and automatic escalation when the window expires and the admin queue is opened
- Responder acceptance, assignment and response status
- Live GPS updates through `/api/tracking/update/` and map views in the web app
- Incident chat and incident update history
- Admin response center with GPS map, filtering, status management, escalation and chat
- Push/SMS/email delivery tracking records. Real external delivery requires provider credentials; in-app delivery works locally.

## Run on Windows
1. Extract this ZIP.
2. Open PowerShell in the extracted `society_app` folder.
3. If your existing virtual environment is present:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python seed_demo.py
python manage.py check
python manage.py runserver
```

Or double-click `start_careconnect.bat`. It creates the virtual environment if needed, installs requirements, migrates, seeds demo users and starts Django.

Open:

- http://127.0.0.1:8000/ — CareConnect home
- http://127.0.0.1:8000/login/ — Login
- http://127.0.0.1:8000/register/ — Registration
- http://127.0.0.1:8000/dashboard/ — Role dashboard
- http://127.0.0.1:8000/sos/ — One-tap SOS
- http://127.0.0.1:8000/location/ — GPS tracker/map
- http://127.0.0.1:8000/emergency-contacts/ — Contacts
- http://127.0.0.1:8000/notifications/ — Notifications
- http://127.0.0.1:8000/emergency-history/ — Incidents
- http://127.0.0.1:8000/admin-portal/ — Admin response center
- http://127.0.0.1:8000/admin/ — Django admin

## Demo accounts
All demo accounts use:

`CareConnect@123`

- `admin_demo` — admin
- `resident_demo` — resident
- `guardian_demo` — guardian
- `volunteer_demo` — volunteer
- `security_demo` — security

## PostgreSQL
Set a `DATABASE_URL` before starting, for example:

`postgresql://USER:PASSWORD@HOST:5432/DBNAME`

If `DATABASE_URL` is not set, SQLite is used automatically for local development.

## Important browser permissions
The GPS page and SOS page use the browser Geolocation API. Allow location permission when Chrome asks. Map tiles use OpenStreetMap/Leaflet, so an internet connection is required for the map background.

## Main APIs
- `POST /api/auth/login/`
- `POST /api/auth/register/`
- `GET /api/auth/me/`
- `POST /api/response/sos/`
- `GET /api/emergency-alerts/`
- `GET /api/emergency-alerts/admin/`
- `PATCH /api/emergency-alerts/<id>/`
- `POST /api/response/alerts/<id>/respond/`
- `POST /api/response/alerts/<id>/assign/`
- `POST /api/response/alerts/<id>/escalate/`
- `GET/POST /api/response/alerts/<id>/chat/`
- `GET /api/response/alerts/<id>/updates/`
- `GET /api/response/notification-deliveries/`
- `POST /api/tracking/update/`
- `GET /api/tracking/me/`
- `GET /api/tracking/live/<user_id>/`
- `GET /api/tracking/society/<society_id>/live-map/`
- `GET/POST /api/` for emergency contacts
- `GET /api/notifications/`


## CareConnect v2 update
This build is emergency-first and login-first:
- `/` now redirects to `/login/`.
- Login is the first visible screen; authenticated users go to the role-aware dashboard.
- Resident, Guardian, Volunteer, Security, Society Admin and Super Admin have different workspace purposes.
- SOS creates a real incident, records GPS, notifies the response network, smart-matches a volunteer, and supports response lifecycle updates.
- Notifications have an in-app delivered record and read/unread lifecycle. Push/SMS/email are represented as pending delivery channels unless external providers are configured.
- Added Safety Check-In (30/60/120 minutes) with safe/cancel actions and missed-check-in guardian notification.
- Added emergency-mode status panel to the SOS screen.
- Added accessibility-focused styling, keyboard focus states, reduced-motion support and simplified emergency actions.
- The app remains a Django + REST + SQLite local-development project.

## CareConnect v3 emergency response update
- Emergency Mode now shows Guardian, Security, Responder and Emergency Services state.
- Resident can send a two-way incident chat message while an SOS is active.
- Resident can request emergency escalation from the SOS screen.
- Nearby police station lookup uses the current GPS position and opens a map search.
- Volunteers and security users get a live response queue directly on their dashboard with Accept, Responding, Arrived and Resolve actions.
- The resident-side timeline polls the backend so responder progress is reflected back on the user's screen.
- Automatic police dispatch is intentionally not faked: it requires an authorised emergency-service integration.

## v4 UI/Workflow Update
See `CARECONNECT_V4_FEATURES.md` for the role-specific response desks, live notification actions, two-way incident response, voice features, calling, police/emergency-service fallback and Python 3.14 dependency fix.

## CareConnect v5 - run locally

From the `society_app` folder on Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Demo password: `CareConnect@123`

Demo roles:
- `resident_demo` — Resident
- `guardian_demo` — Guardian
- `volunteer_demo` — Volunteer
- `security_admin_demo` — Security Admin
- `security_volunteer_demo` — Security Volunteer
- `society_admin_demo` — Society Admin
- `admin_demo` — Admin
- `superadmin_demo` — Super Admin

### v5 operational changes
- Security Admin and Security Volunteer are different roles and API permissions.
- Notifications create database records, websocket events, and an email delivery attempt when an email is configured. In local development the email backend logs the message to the terminal.
- Incident responses and status updates are visible in the incident timeline.
- SOS has a browser-safe long-press trigger in addition to the normal SOS button.
- The service worker caches the core shell and IndexedDB queues an SOS when the network is unavailable. The queued request is retried when connectivity returns.
- Call actions use `tel:` links; voice-to-text uses browser Web Speech support; incident voice notes use browser microphone/MediaRecorder support.
