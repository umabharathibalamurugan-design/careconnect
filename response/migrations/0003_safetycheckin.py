from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies = [('response','0002_incidentaudio')]
    operations = [
        migrations.CreateModel(
            name='SafetyCheckIn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('due_at', models.DateTimeField()),
                ('status', models.CharField(choices=[('active','Active'),('completed','Completed'),('missed','Missed'),('cancelled','Cancelled')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('reminder_sent', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='safety_checkins', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-created_at']},
        ),
    ]
