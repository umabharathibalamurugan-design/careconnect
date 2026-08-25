from rest_framework import generics, permissions
from .models import Volunteer, VolunteerTask
from .serializers import VolunteerSerializer, VolunteerTaskSerializer


class VolunteerListCreateView(generics.ListCreateAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        society_id = self.request.query_params.get('society')
        available = self.request.query_params.get('available_for_emergency')
        if role:
            qs = qs.filter(role=role)
        if society_id:
            qs = qs.filter(society_id=society_id)
        if available is not None:
            qs = qs.filter(available_for_emergency=available.lower() == 'true')
        return qs


class VolunteerDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Volunteer.objects.all()
    serializer_class = VolunteerSerializer


class VolunteerTaskListCreateView(generics.ListCreateAPIView):
    serializer_class = VolunteerTaskSerializer

    def get_queryset(self):
        qs = VolunteerTask.objects.all()
        volunteer_id = self.request.query_params.get('volunteer')
        if volunteer_id:
            qs = qs.filter(volunteer_id=volunteer_id)
        return qs

    def perform_create(self, serializer):
        volunteer_id = self.request.data.get('volunteer')
        serializer.save(volunteer_id=volunteer_id)
