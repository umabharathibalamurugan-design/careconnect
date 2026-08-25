from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone
from datetime import timedelta
from residents.models import ResidentProfile
from societies.models import Society, Block, Flat
from .models import SafetyProfile, SafetyRouteSegment, WellnessCheckIn


class SafetyCompanionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="scresident", password="Pass12345!", role="resident", phone_number="9000000001"
        )
        society = Society.objects.create(name="Test Society", address="Test", city="Chennai", pincode="600001")
        block = Block.objects.create(society=society, name="A")
        flat = Flat.objects.create(block=block, flat_number="101")
        self.resident = ResidentProfile.objects.create(user=self.user, flat=flat)
        SafetyProfile.objects.create(resident=self.resident, wellness_enabled=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_profile_is_created_and_read(self):
        r = self.client.get("/api/safety-companion/profile/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["companion_enabled"])

    def test_route_prefers_safety_when_weighted(self):
        # A->B->D is longer but safer; A->C->D is shorter but unsafe.
        pts = {
            "a": (13.000000, 80.000000), "b": (13.000000, 80.002000),
            "c": (13.001000, 80.001000), "d": (13.002000, 80.002000)
        }
        for u,v,dist,score in [
            ("a","b",300,95),("b","d",300,95),
            ("a","c",150,15),("c","d",150,15),
        ]:
            SafetyRouteSegment.objects.create(
                contributor=self.user, society=self.resident.flat.block.society,
                start_lat=pts[u][0], start_lng=pts[u][1],
                end_lat=pts[v][0], end_lng=pts[v][1],
                distance_m=dist, safety_score=score
            )
        r = self.client.post("/api/safety-companion/safe-route/", {
            "start":{"lat":pts["a"][0],"lng":pts["a"][1]},
            "end":{"lat":pts["d"][0],"lng":pts["d"][1]},
            "safety_weight":4
        }, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.data["average_safety_score"], 90)

    def test_wellness_completion(self):
        check = WellnessCheckIn.objects.create(
            resident=self.resident,
            scheduled_for=timezone.now(),
            response_deadline=timezone.now()+timedelta(minutes=30)
        )
        r = self.client.post(f"/api/safety-companion/wellness/{check.id}/action/", {"action":"safe"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "completed")
