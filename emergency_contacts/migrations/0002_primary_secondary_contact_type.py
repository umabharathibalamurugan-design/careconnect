from django.db import migrations, models

def backfill_contact_type(apps, schema_editor):
    Contact = apps.get_model("emergency_contacts", "EmergencyContact")
    seen = {}
    for c in Contact.objects.all().order_by("resident_id","created_at","id"):
        count = seen.get(c.resident_id, 0)
        if count == 0:
            c.contact_type = "primary"
            c.is_primary = True
            c.save(update_fields=["contact_type","is_primary"])
        elif count == 1:
            c.contact_type = "secondary"
            c.is_primary = False
            c.save(update_fields=["contact_type","is_primary"])
        else:
            # The new product intentionally supports two slots only.
            c.delete()
            continue
        seen[c.resident_id] = count + 1

class Migration(migrations.Migration):
    dependencies=[("emergency_contacts","0001_initial")]
    operations=[
        migrations.AddField(model_name="emergencycontact",name="contact_type",field=models.CharField(choices=[("primary","Primary"),("secondary","Secondary")],default="primary",max_length=12)),
        migrations.RunPython(backfill_contact_type,migrations.RunPython.noop),
        migrations.AddConstraint(model_name="emergencycontact",constraint=models.UniqueConstraint(fields=("resident","contact_type"),name="unique_resident_emergency_contact_type")),
    ]
