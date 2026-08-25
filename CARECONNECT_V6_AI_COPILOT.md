# CareConnect v6 — AI Safety Copilot upgrade

## Purpose
This upgrade changes the assistant from a generic chat widget into a **CareConnect-specific AI Safety Copilot** connected to the application's emergency data and role permissions.

## AI functions
1. Emergency Copilot — explains and launches SOS-related actions.
2. Incident Copilot — summarizes the selected incident using actual response records.
3. Dispatch Copilot — explains responder workload/assignment context without inventing an ETA.
4. Location Copilot — reports location freshness and refuses to guess missing GPS data.
5. Safety Copilot — explains active Safety Check-In state.
6. Escalation Copilot — explains escalation rules and refuses to claim police dispatch without verified integration.
7. Accessibility Copilot — guides voice, large controls, screen-reader and simplified mode features.
8. Operations Copilot — gives role-specific safety briefings to security/society/admin users.
9. Action routing — assistant replies contain buttons that open the correct CareConnect page.
10. Conversation history — assistant messages are stored per authenticated user.
11. Offline-safe behavior — the assistant never becomes the emergency transport mechanism; SOS remains a direct application action.
12. Optional generative layer — if `CARECONNECT_AI_API_KEY` is configured, a compatible LLM can rewrite the context-aware answer. The specialized safety engine remains the fallback and works without an API key.

## Files added
- `ai_assistant/apps.py`
- `ai_assistant/models.py`
- `ai_assistant/services.py`
- `ai_assistant/views.py`
- `ai_assistant/urls.py`
- `ai_assistant/permissions.py`
- `ai_assistant/admin.py`
- `ai_assistant/migrations/0001_initial.py`
- `frontend/js/ai_assistant.js`

## Files updated
- `config/settings.py` — registers the AI app.
- `config/urls.py` — adds `/api/ai/` routes.
- `templates/base.html` — replaces the generic assistant UI with the Safety Copilot.
- `templates/dashboard.html` — adds a role-aware AI safety briefing panel.
- `frontend/js/app.js` — removes the old generic AI response engine.
- `frontend/js/dashboard.js` — loads the AI briefing.
- `frontend/css/style.css` — new Copilot and AI briefing UI.

## API
- `POST /api/ai/chat/` — authenticated Copilot chat.
- `GET /api/ai/briefing/` — authenticated role-aware safety briefing.

Optional query parameter:
- `alert_id=<id>` to make the Copilot incident-aware. Backend access checks prevent residents from asking about another resident's incident.

## Run
After extracting the project:

```powershell
python manage.py migrate
python manage.py runserver
```

No additional Python package is required for the built-in Copilot.

## Optional LLM
Environment variables:
- `CARECONNECT_AI_API_KEY`
- `CARECONNECT_AI_API_URL`
- `CARECONNECT_AI_MODEL`

The default URL is an OpenAI-compatible chat endpoint. If these variables are absent, the built-in CareConnect safety engine is used.

## Product boundary
This is not a medical diagnosis assistant, police dispatcher, or replacement for emergency services. It is a safety-navigation and response-coordination assistant. It must not claim that a person, responder, police station, call, GPS fix, or emergency service has acted unless the CareConnect system has a recorded event confirming it.
