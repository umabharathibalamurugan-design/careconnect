from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("residents", "0001_initial"),
        ("societies", "0001_initial"),
        ("emergency_alerts", "0002_response_fields"),
    ]
    operations = [
        migrations.CreateModel(
            name="SafetyProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("companion_enabled", models.BooleanField(default=True)),
                ("silent_sos_enabled", models.BooleanField(default=True)),
                ("fall_detection_enabled", models.BooleanField(default=True)),
                ("inactivity_detection_enabled", models.BooleanField(default=True)),
                ("voice_distress_enabled", models.BooleanField(default=False)),
                ("wellness_enabled", models.BooleanField(default=False)),
                ("triple_press_window_ms", models.PositiveIntegerField(default=900)),
                ("inactivity_minutes", models.PositiveIntegerField(default=60)),
                ("wellness_timeout_minutes", models.PositiveIntegerField(default=30)),
                ("safety_route_weight", models.DecimalField(decimal_places=2, default=2.0, max_digits=4)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resident", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="safety_profile", to="residents.residentprofile")),
            ],
        ),
        migrations.CreateModel(
            name="SafetyRouteSegment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_lat", models.DecimalField(decimal_places=6, max_digits=9)),
                ("start_lng", models.DecimalField(decimal_places=6, max_digits=9)),
                ("end_lat", models.DecimalField(decimal_places=6, max_digits=9)),
                ("end_lng", models.DecimalField(decimal_places=6, max_digits=9)),
                ("distance_m", models.PositiveIntegerField()),
                ("safety_score", models.DecimalField(decimal_places=2, default=50, max_digits=5)),
                ("reports", models.PositiveIntegerField(default=1)),
                ("one_way", models.BooleanField(default=False)),
                ("active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("contributor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_route_segments", to=settings.AUTH_USER_MODEL)),
                ("society", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_route_segments", to="societies.society")),
            ],
            options={"indexes":[
                models.Index(fields=["society","active"], name="safety_comp_society_3f0a0b_idx"),
                models.Index(fields=["start_lat","start_lng"], name="safety_comp_start_l_4e1f4b_idx"),
                models.Index(fields=["end_lat","end_lng"], name="safety_comp_end_lat_0db6b1_idx"),
            ]},
        ),
        migrations.CreateModel(
            name="SafetySignal",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("signal_type", models.CharField(choices=[("silent_sos","Silent SOS"),("fall","Fall"),("inactivity","Inactivity"),("voice_distress","Voice Distress")], max_length=30)),
                ("confidence", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("incident", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="safety_signals", to="emergency_alerts.emergencyalert")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="safety_signals", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-created_at"],"indexes":[models.Index(fields=["user","signal_type","created_at"], name="safety_comp_user_id_6a2c0c_idx")]},
        ),
        migrations.CreateModel(
            name="WellnessCheckIn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("scheduled_for", models.DateTimeField()),
                ("response_deadline", models.DateTimeField()),
                ("status", models.CharField(choices=[("scheduled","Scheduled"),("prompted","Prompted"),("completed","Completed"),("missed","Missed"),("cancelled","Cancelled")], default="scheduled", max_length=20)),
                ("prompt_sent_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("missed_notified_at", models.DateTimeField(blank=True, null=True)),
                ("message", models.CharField(default="Daily wellness check: are you okay?", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resident", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="companion_wellness_checks", to="residents.residentprofile")),
            ],
            options={"ordering":["-scheduled_for"],"indexes":[
                models.Index(fields=["status","scheduled_for"], name="safety_comp_status_0aee4b_idx"),
                models.Index(fields=["status","response_deadline"], name="safety_comp_status_8f77b6_idx"),
            ]},
        ),
    ]
