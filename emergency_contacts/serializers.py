from rest_framework import serializers
from .models import EmergencyContact

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = ["id","resident","guardian","name","phone_number","relation","contact_type","is_verified","is_primary","created_at"]
        read_only_fields = ["id","resident","guardian","is_verified","is_primary","created_at"]

    def validate_phone_number(self, value):
        value = value.strip()
        compact = "".join(ch for ch in value if ch.isdigit() or ch == "+")
        if len(compact.replace("+","")) < 7:
            raise serializers.ValidationError("Enter a valid phone number.")
        return compact

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.is_authenticated and not getattr(request.user, "residentprofile", None):
            raise serializers.ValidationError("Emergency contacts are available for resident accounts.")
        contact_type = attrs.get("contact_type", self.instance.contact_type if self.instance else EmergencyContact.ContactType.PRIMARY)
        if request and request.user.is_authenticated:
            resident = request.user.residentprofile
            qs = EmergencyContact.objects.filter(resident=resident, contact_type=contact_type)
            if self.instance: qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError({"contact_type": f"A {contact_type} contact already exists. Edit it instead."})
        return attrs
