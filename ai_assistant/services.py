import json, os, re, urllib.request
from django.db.models import Q, Count
from django.utils import timezone
from emergency_alerts.models import EmergencyAlert
from notifications.models import Notification
from response.models import ResponderAssignment, AlertResponse, SafetyCheckIn

ROLE_LABELS = {
    'resident':'Resident', 'guardian':'Guardian', 'volunteer':'Volunteer',
    'security':'Security Guard', 'security_admin':'Security Admin',
    'security_volunteer':'Security Volunteer', 'society_admin':'Society Admin',
    'admin':'Admin', 'superadmin':'Super Admin', 'visitor':'Visitor'
}


def _society_id(user):
    if getattr(user, 'society_id', None): return user.society_id
    try:
        if hasattr(user, 'resident_profile') and user.resident_profile.flat:
            return user.resident_profile.flat.block.society_id
    except Exception: pass
    for attr in ('guardian_profile','volunteer_profile','security_guard'):
        try:
            obj = getattr(user, attr)
            sid = getattr(obj, 'society_id', None)
            if sid: return sid
        except Exception: pass
    return None


def context_for(user, alert_id=None):
    role = getattr(user, 'role', 'resident')
    society_id = _society_id(user)
    qs = EmergencyAlert.objects.select_related('resident__user').all()
    if society_id:
        try: qs = qs.filter(resident__flat__block__society_id=society_id)
        except Exception: pass
    active = qs.filter(status__in=['open','acknowledged','active','escalated'])
    if role == 'resident':
        try: active = active.filter(resident__user=user)
        except Exception: pass
    current = None
    if alert_id:
        try:
            current = qs.get(pk=alert_id)
            # Never expose an unrelated incident to the assistant context.
            if role == 'resident' and current.resident.user_id != user.id: current = None
        except EmergencyAlert.DoesNotExist: pass
    assigned = ResponderAssignment.objects.filter(responder=user, status__in=['assigned','accepted','on_way','arrived']).count()
    notifications = Notification.objects.filter(recipient=user, is_read=False).count() if hasattr(Notification, 'is_read') else 0
    checkin = SafetyCheckIn.objects.filter(user=user, status='active').order_by('due_at').first()
    return {
        'role': role, 'role_label': ROLE_LABELS.get(role, role), 'society_id': society_id,
        'active_incidents': active.count(), 'assigned_incidents': assigned,
        'unread_notifications': notifications,
        'safety_checkin': {'active': bool(checkin), 'due_at': checkin.due_at.isoformat() if checkin else None},
        'current_incident': incident_context(current) if current else None,
    }


def incident_context(alert):
    if not alert: return None
    responses = list(alert.responses.select_related('responder').order_by('-updated_at')[:8])
    assignments = list(alert.assignments.select_related('responder').order_by('-updated_at')[:8])
    return {
        'id': alert.id, 'type': alert.alert_type, 'priority': alert.priority, 'status': alert.status,
        'message': alert.message[:500], 'created_at': alert.created_at.isoformat(),
        'location': {'lat': float(alert.latitude) if alert.latitude is not None else None, 'lng': float(alert.longitude) if alert.longitude is not None else None},
        'responses': [{'name': r.responder.get_full_name() or r.responder.username, 'role': ROLE_LABELS.get(r.responder.role,r.responder.role), 'status': r.status} for r in responses],
        'assignments': [{'name': a.responder.get_full_name() or a.responder.username, 'status': a.status} for a in assignments],
    }


def detect_intent(text):
    x = text.lower()
    patterns = [
        ('emergency', r'\b(sos|emergency|help|danger|panic|unsafe|threat|accident)\b'),
        ('incident_status', r'(incident|alert).*(status|update)|status.*(incident|alert)'),
        ('responder', r'(best|nearest|available).*(responder|volunteer|security)|who.*(respond|help)'),
        ('location', r'(where|location|gps|map|track|responder.*where)'),
        ('call', r'(call|phone|contact).*(guardian|security|volunteer|police|emergency)'),
        ('checkin', r'(check.?in|safe|safety timer|remind me)'),
        ('escalation', r'(escalat|no one.*respond|police|station|emergency service)'),
        ('accessibility', r'(voice|screen reader|large text|accessib|elderly|hearing|vision)'),
        ('admin_insight', r'(analytics|response time|performance|hotspot|incident count|volunteer load)'),
    ]
    for name, pat in patterns:
        if re.search(pat, x): return name
    return 'general'


def local_ai(user, text, alert_id=None):
    intent = detect_intent(text)
    ctx = context_for(user, alert_id)
    role = ctx['role_label']
    incident = ctx['current_incident']
    actions = []
    if intent == 'emergency':
        actions = [{'label':'Open SOS','url':'/sos/','style':'danger'},{'label':'Open Incidents','url':'/emergency-history/','style':'primary'}]
        if incident:
            return intent, f"Emergency Copilot: Incident #{incident['id']} is {incident['status']} with {incident['priority']} priority. Stay on the incident screen and use the responder status, call, location, and I'm Safe controls. I will not claim that police or responders were contacted unless CareConnect has a recorded delivery/response event.", actions
        return intent, "Emergency Copilot: If you are in immediate danger, use SOS. CareConnect will capture the available location, create an incident, notify the configured response network, and show response status. If the situation is life-threatening, use your local emergency service as well.", actions
    if intent == 'incident_status':
        if incident:
            responders = ', '.join(f"{r['name']}: {r['status']}" for r in incident['responses'][:4]) or 'No responder acknowledgement recorded yet.'
            return intent, f"Incident #{incident['id']} is currently {incident['status']} ({incident['priority']}). Recorded responder states: {responders}", actions
        return intent, f"{role}: there is no incident selected. You currently have {ctx['active_incidents']} active incident(s) in your permitted view.", [{'label':'Open Incidents','url':'/emergency-history/','style':'primary'}]
    if intent == 'responder':
        if role in ('resident','guardian'):
            return intent, f"Response Copilot: I can help you follow the assigned responder status. Your permitted view currently contains {ctx['active_incidents']} active incident(s). I will not invent a responder or ETA that the tracking/response data does not contain.", [{'label':'View Live GPS','url':'/location/','style':'primary'}]
        return intent, f"Dispatch Copilot: your current assigned response load is {ctx['assigned_incidents']}. Use the Response Center to accept or update eligible incidents. Assignment decisions should use live availability and recorded response data.", [{'label':'Response Center','url':'/admin-portal/','style':'primary'}]
    if intent == 'location':
        return intent, "Location Copilot: CareConnect can show the latest recorded GPS position and responder tracking data. A stale or missing GPS fix is reported as such rather than being replaced with a guessed location.", [{'label':'Open Live GPS','url':'/location/','style':'primary'}]
    if intent == 'call':
        return intent, "Communication Copilot: use the Call action on the incident/contact card to open the device dialer. For browser-only use, CareConnect keeps the call as a tel: action instead of pretending a call was completed.", [{'label':'Emergency Contacts','url':'/emergency-contacts/','style':'primary'}]
    if intent == 'checkin':
        if ctx['safety_checkin']['active']:
            return intent, f"Safety Copilot: your check-in is active and due at {ctx['safety_checkin']['due_at']}. Confirm I'm Safe before the deadline if everything is okay.", [{'label':'Dashboard','url':'/dashboard/','style':'primary'}]
        return intent, "Safety Copilot: no active check-in is recorded for you. Start one from the safety check-in control when you want CareConnect to expect a safe confirmation.", [{'label':'Dashboard','url':'/dashboard/','style':'primary'}]
    if intent == 'escalation':
        return intent, "Escalation Copilot: escalation is based on configured response rules and recorded acknowledgements. CareConnect can record and surface an escalation, but it must not claim that police were dispatched without a verified emergency-service integration. Nearby station/call actions can be offered as a fallback.", [{'label':'Response Center','url':'/admin-portal/','style':'primary'}]
    if intent == 'accessibility':
        return intent, "Accessibility Copilot: use the large-control/simple mode, keyboard focus, high-contrast styling, screen-reader labels, and voice-to-text where supported. Emergency actions should remain usable without relying on tiny visual controls.", [{'label':'Dashboard','url':'/dashboard/','style':'primary'}]
    if intent == 'admin_insight':
        return intent, f"Operations Copilot: your permitted view currently has {ctx['active_incidents']} active incident(s), {ctx['assigned_incidents']} assigned response task(s), and {ctx['unread_notifications']} unread notification(s). Use the Response Center for the detailed incident and responder analytics.", [{'label':'Response Center','url':'/admin-portal/','style':'primary'}]
    return intent, f"CareConnect Copilot: I am connected to your {role} workspace. I can explain current incident status, response activity, location freshness, escalation, safety check-ins, accessibility, calls, and responder actions. I only use information available to your role and I do not invent emergency events.", [{'label':'Incident status','url':'/emergency-history/','style':'primary'},{'label':'Response Center','url':'/admin-portal/','style':'primary'}]


def optional_llm(user, text, ctx):
    """Optional OpenAI-compatible backend. Disabled unless CARECONNECT_AI_API_KEY is configured."""
    key = os.environ.get('CARECONNECT_AI_API_KEY')
    if not key: return None
    url = os.environ.get('CARECONNECT_AI_API_URL', 'https://api.openai.com/v1/chat/completions')
    model = os.environ.get('CARECONNECT_AI_MODEL', 'gpt-4o-mini')
    system = ("You are CareConnect Emergency Copilot, not a general chatbot. "
              "Help users navigate a community emergency-response system. Never invent an alert, responder, location, ETA, police dispatch, medical diagnosis, or successful call. "
              "Use only the supplied context. If an immediate danger is described, direct the user to the app's SOS and appropriate local emergency services. "
              "Respect role-based privacy and do not reveal data outside the user's permitted context. Give concise actionable answers.\nCONTEXT:\n" + json.dumps(ctx))
    payload = json.dumps({'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':text}],'temperature':0.2,'max_tokens':300}).encode()
    req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data=json.loads(resp.read().decode())
        return data['choices'][0]['message']['content'].strip()
    except Exception:
        return None
