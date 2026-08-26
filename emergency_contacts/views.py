from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import EmergencyContact
from .serializers import EmergencyContactSerializer

class EmergencyContactListCreateView(generics.ListCreateAPIView):
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        if self.request.user.role in ("admin","superadmin","security"):
            return EmergencyContact.objects.all().select_related("resident__user","guardian__user")
        return EmergencyContact.objects.filter(resident__user=self.request.user).select_related("resident__user","guardian__user")
    def perform_create(self, serializer):
        from residents.models import ResidentProfile
        serializer.save(resident=ResidentProfile.objects.get(user=self.request.user))

class EmergencyContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        if self.request.user.role in ("admin","superadmin","security"): return EmergencyContact.objects.all()
        return EmergencyContact.objects.filter(resident__user=self.request.user)

class EmergencyContactVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, pk):
        contact = EmergencyContact.objects.filter(pk=pk, resident__user=request.user).first()
        if not contact: return Response({"detail":"Contact not found."}, status=404)
        contact.is_verified=True; contact.save(update_fields=["is_verified"])
        return Response(EmergencyContactSerializer(contact).data)
