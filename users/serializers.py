from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
            "society",
            "is_verified",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "society",
            "is_verified",
            "date_joined",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    confirm_password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "role",
        ]
        read_only_fields = ["id"]

    def validate_username(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Username is required.")

        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already registered."
            )

        return value

    def validate_phone_number(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Phone number is required.")

        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "This phone number is already registered."
            )

        return value

    def validate_role(self, value):
        valid_roles = {choice[0] for choice in User.Role.choices}

        if value not in valid_roles:
            raise serializers.ValidationError("Please select a valid role.")

        return value

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match."
            })

        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)

        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.is_active = True
        user.is_verified = True
        user.save()

        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        allow_blank=False,
    )
    password = serializers.CharField(
        required=True,
        allow_blank=False,
        write_only=True,
    )

    def validate(self, attrs):
        username = attrs["username"].strip()
        password = attrs["password"]

        user = authenticate(
            username=username,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError({
                "detail": "Invalid username or password."
            })

        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "This account is disabled."
            })

        attrs["user"] = user
        return attrs
