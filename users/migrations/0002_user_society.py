from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('users','0001_initial'),('societies','0001_initial')]
    operations=[migrations.AddField(
        model_name='user',
        name='society',
        field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='societies.society'),
    )]
