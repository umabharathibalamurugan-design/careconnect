from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):
    dependencies=[('response','0001_initial')]
    operations=[migrations.CreateModel(name='IncidentAudio',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('audio',models.FileField(upload_to='incident_audio/%Y/%m/%d/')),('created_at',models.DateTimeField(auto_now_add=True)),('alert',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='audio_notes',to='emergency_alerts.emergencyalert')),('sender',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='incident_audio',to=settings.AUTH_USER_MODEL))])]
