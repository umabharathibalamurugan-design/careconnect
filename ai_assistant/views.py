from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import AssistantSession, AssistantMessage
from .services import local_ai, context_for, optional_llm

class AssistantChatView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self, request):
        text=str(request.data.get('message','')).strip()
        if not text: return Response({'detail':'Message is required.'}, status=400)
        alert_id=request.data.get('alert_id')
        session_id=request.data.get('session_id')
        session=AssistantSession.objects.filter(id=session_id,user=request.user).first() if session_id else None
        if not session: session=AssistantSession.objects.create(user=request.user)
        intent, reply, actions=local_ai(request.user,text,alert_id)
        llm=optional_llm(request.user,text,context_for(request.user,alert_id))
        if llm: reply=llm
        AssistantMessage.objects.create(session=session,role='user',message=text,intent=intent)
        AssistantMessage.objects.create(session=session,role='assistant',message=reply,intent=intent)
        return Response({'reply':reply,'intent':intent,'actions':actions,'session_id':session.id,'context':context_for(request.user,alert_id)})

class AssistantBriefingView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request):
        ctx=context_for(request.user,request.query_params.get('alert_id'))
        role=ctx['role_label']
        if ctx['current_incident']:
            i=ctx['current_incident']
            text=f"AI briefing: Incident #{i['id']} is {i['status']} at {i['priority']} priority. {len(i['responses'])} recorded responder state(s) are available. Verify live location before making movement decisions."
        elif role in ('Security Admin','Society Admin','Admin','Super Admin'):
            text=f"AI operations briefing: {ctx['active_incidents']} active incident(s), {ctx['assigned_incidents']} response task(s) assigned to you, and {ctx['unread_notifications']} unread notification(s)."
        elif role in ('Volunteer','Security Guard','Security Volunteer'):
            text=f"AI responder briefing: you have {ctx['assigned_incidents']} active response task(s). Open the Response Center to act on assigned incidents."
        else:
            text=f"AI safety briefing: {ctx['active_incidents']} active incident(s) are visible to your role. Keep your emergency contacts current and use SOS if you need immediate assistance."
        return Response({'briefing':text,'context':ctx})
