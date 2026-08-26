from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial=True
    dependencies=[migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(name='AssistantSession',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='careconnect_ai_sessions',to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name='AssistantMessage',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('role',models.CharField(choices=[('user','User'),('assistant','Assistant')],max_length=20)),('message',models.TextField()),('intent',models.CharField(blank=True,max_length=50)),('created_at',models.DateTimeField(auto_now_add=True)),('session',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='messages',to='ai_assistant.assistantsession'))]),
    ]
