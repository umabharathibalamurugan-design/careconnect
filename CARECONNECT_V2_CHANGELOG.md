# CareConnect v2 — Upgrade Summary

## Fixed
- Login-first application flow: `/` redirects to `/login/`.
- Auth pages use a clean, focused layout without the application dashboard chrome.
- Role-aware dashboard routing after successful authentication.
- Society Admin accounts are assigned to a society and society-level incident views are scoped.
- Live-location access is restricted for guardians and society admins.
- Notifications continue to use a real in-app delivered/read lifecycle.

## New working features
- Safety Check-In: 30 min / 1 hour / 2 hours.
- Missed check-in state and guardian notification when the timer is checked after expiry.
- Emergency Mode on SOS with incident ID, location, alert and responder state.
- Resident can confirm “I'm Safe” to close an active incident.
- Accessibility improvements: focus states, reduced-motion support, large emergency controls and semantic labels.

## Role boundaries
- Super Admin: platform-wide command and configuration visibility.
- Admin: emergency operations and platform-wide monitoring.
- Society Admin: emergency operations within the assigned society.
- Security: on-site emergency response.
- Volunteer: response actions and availability.
- Guardian: receive alerts and permitted location sharing.
- Resident: SOS, safety check-in, contacts and personal incident access.

## Important deployment note
Push/SMS/email delivery records are created as `pending` until external providers are configured. The in-app notification channel is marked `delivered` immediately. GPS uses the browser/device geolocation permission.

## Run
1. Run `start_careconnect.bat`.
2. It creates the virtual environment, installs requirements, runs migrations, seeds demo accounts, checks Django, and starts the server.
3. Open `http://127.0.0.1:8000/`.
4. The first screen is the login page.

Demo password: `CareConnect@123`
