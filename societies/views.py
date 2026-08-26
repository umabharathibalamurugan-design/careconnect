from rest_framework import generics
from .models import Society, Block, Flat
from .serializers import SocietySerializer, BlockSerializer, FlatSerializer


class SocietyListCreateView(generics.ListCreateAPIView):
    queryset = Society.objects.all()
    serializer_class = SocietySerializer


class BlockListCreateView(generics.ListCreateAPIView):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer


class FlatListCreateView(generics.ListCreateAPIView):
    queryset = Flat.objects.all()
    serializer_class = FlatSerializer
