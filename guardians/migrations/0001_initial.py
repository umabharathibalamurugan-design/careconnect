from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True
    dependencies = [
        ('residents', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Guardian',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relation', models.CharField(max_length=50)),
                ('is_primary', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('role', models.CharField(choices=[('primary', 'Primary Guardian'), ('secondary', 'Secondary Guardian'), ('emergency_contact', 'Emergency Contact'), ('caretaker', 'Caretaker'), ('legal_guardian', 'Legal Guardian')], default='secondary', max_length=30)),
                ('can_approve_visitors', models.BooleanField(default=False)),
                ('can_receive_alerts', models.BooleanField(default=True)),
                ('can_track_location', models.BooleanField(default=False)),
                ('resident', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='guardians', to='residents.residentprofile')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
