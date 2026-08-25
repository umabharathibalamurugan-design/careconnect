# CareConnect AI Safety Copilot

CareConnect's AI is intentionally **not a generic chatbot**. It is a role-aware safety copilot integrated with the emergency system.

## What it does
- Emergency guidance tied to the SOS workflow.
- Incident-aware status summaries using real alert/response records.
- Responder guidance using permitted assignment/load information.
- Location freshness guidance without inventing GPS/ETA data.
- Safety Check-In reminders and explanations.
- Escalation explanations with a hard rule: never claim police dispatch without a verified integration.
- Accessibility and voice guidance.
- Role-aware operations briefings for security/society/admin roles.
- Action buttons that take the user to the correct CareConnect screen.
- Conversation history stored per authenticated user.
- Optional generative AI backend through environment variables, while the application remains runnable without an external AI key.

## Optional generative provider
Set these environment variables only if you want natural-language generation in addition to the built-in safety engine:

`CARECONNECT_AI_API_KEY`
`CARECONNECT_AI_API_URL` (defaults to an OpenAI-compatible chat endpoint)
`CARECONNECT_AI_MODEL`

Without a key, the specialized CareConnect safety engine still works locally and uses real database context.

## Safety boundary
The Copilot is a product assistant, not a medical diagnosis engine or emergency dispatcher. It must not invent responder locations, ETAs, police dispatches, successful calls, or incident states. For immediate danger, the UI keeps direct SOS/emergency-service actions available.
