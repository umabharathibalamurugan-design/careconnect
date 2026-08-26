from rest_framework import generics
from .models import ResidentProfile
from .serializers import ResidentProfileSerializer


class ResidentProfileListCreateView(generics.ListCreateAPIView):
    queryset = ResidentProfile.objects.all()
    serializer_class = ResidentProfileSerializer


class ResidentProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ResidentProfile.objects.all()
    serializer_class = ResidentProfileSerializer
