# CareConnect v5 upgrade

## Fixed
- Distinct `security_admin` and `security_volunteer` roles with API-level permission checks.
- Real-time per-user notifications through Django Channels.
- Persistent in-app notification fallback when a recipient is offline.
- Response actions are stored and shown as a real incident timeline.
- Call links use the device dialer (`tel:`).
- Browser voice-to-text and incident voice-note upload are supported where the browser permits microphone access.
- `psycopg[binary]` is relaxed to `>=3.2.10` for Python 3.14 compatibility.

## Offline service
- Service worker caches the core UI shell.
- IndexedDB stores an SOS POST when the network is unavailable.
- The queued SOS is retried automatically when the browser returns online.
- The UI displays an offline banner instead of pretending the server received the emergency.

## Existing innovation retained
- Live Leaflet/OpenStreetMap incident map.
- Smart responder matching.
- Severity/priority levels.
- Escalation deadline and automatic escalation checks.
- Safety check-in.
- Incident chat and audio notes.
- Society analytics and responder reliability.

## Important deployment limits
- Browser voice-to-text depends on browser support.
- `tel:` opens the device dialer; it does not place a call from the server.
- Actual SMS/push/email delivery requires provider configuration.
- Browser shake-to-alert is not implemented as a guaranteed background feature; a long-press/visible SOS remains the reliable browser interaction.
