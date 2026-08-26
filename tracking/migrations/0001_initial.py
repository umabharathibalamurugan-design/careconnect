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
            name='LiveLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('accuracy_meters', models.FloatField(blank=True, null=True)),
                ('battery_level', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('is_sharing', models.BooleanField(default=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('society', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='live_locations', to='societies.society')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='live_location', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='LocationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('longitude', models.DecimalField(decimal_places=6, max_digits=9)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='location_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-recorded_at']},
        ),
        migrations.AddIndex(
            model_name='locationhistory',
            index=models.Index(fields=['user', '-recorded_at'], name='tracking_lo_user_id_5e1a3b_idx'),
        ),
    ]
