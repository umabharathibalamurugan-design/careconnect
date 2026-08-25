from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ('societies', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Volunteer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('security_helper', 'Security Helper'), ('event_coordinator', 'Event Coordinator'), ('maintenance', 'Maintenance & Repairs'), ('cleanliness', 'Cleanliness Drive'), ('sports_fitness', 'Sports & Fitness'), ('elderly_care', 'Elderly Care'), ('disaster_response', 'Disaster / Emergency Response'), ('general', 'General Volunteer')], default='general', max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('available_for_emergency', models.BooleanField(default=False)),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('assigned_block', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='volunteers', to='societies.block')),
                ('society', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='volunteers', to='societies.society')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='volunteer_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='VolunteerTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('assigned', 'Assigned'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='assigned', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('volunteer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tasks', to='volunteers.volunteer')),
            ],
        ),
    ]
