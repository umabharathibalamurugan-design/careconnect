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
            name='SecurityGuard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gate_assigned', models.CharField(blank=True, max_length=100)),
                ('shift', models.CharField(choices=[('morning', 'Morning (6AM-2PM)'), ('evening', 'Evening (2PM-10PM)'), ('night', 'Night (10PM-6AM)')], default='morning', max_length=20)),
                ('is_on_duty', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('society', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='security_guards', to='societies.society')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='guard_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
