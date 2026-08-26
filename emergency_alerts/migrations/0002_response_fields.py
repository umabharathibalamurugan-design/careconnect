from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('emergency_alerts','0001_initial'),('users','0001_initial')]
    operations=[
        migrations.AddField(model_name='emergencyalert',name='response_window_minutes',field=models.PositiveIntegerField(default=2)),
        migrations.AddField(model_name='emergencyalert',name='escalation_deadline',field=models.DateTimeField(blank=True,null=True)),
        migrations.AddField(model_name='emergencyalert',name='resolved_at',field=models.DateTimeField(blank=True,null=True)),
        migrations.AddField(model_name='emergencyalert',name='closed_by',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='closed_emergency_alerts',to='users.user')),
        migrations.AddField(model_name='emergencyalert',name='closure_note',field=models.TextField(blank=True)),
    ]
