from rest_framework import generics
from .models import Guardian
from .serializers import GuardianSerializer


class GuardianListCreateView(generics.ListCreateAPIView):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        resident_id = self.request.query_params.get('resident')
        role = self.request.query_params.get('role')
        if resident_id:
            qs = qs.filter(resident_id=resident_id)
        if role:
            qs = qs.filter(role=role)
        return qs


class GuardianDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Guardian.objects.all()
    serializer_class = GuardianSerializer
