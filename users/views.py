from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        from societies.models import Society, Block, Flat
        from residents.models import ResidentProfile

        society, _ = Society.objects.get_or_create(
            name="CareConnect Demo Society",
            defaults={
                "address": "CareConnect Community",
                "city": "Chennai",
                "pincode": "600001",
            },
        )

        block, _ = Block.objects.get_or_create(
            society=society,
            name="Tower A",
        )

        flat, _ = Flat.objects.get_or_create(
            block=block,
            flat_number="101",
        )

        if not user.society_id:
            user.society = society
            user.save(update_fields=["society"])

        # Every registered user receives a ResidentProfile.
        # This allows Safety Companion to work for any selected role
        # without requiring a hard-coded demo account.
        resident, _ = ResidentProfile.objects.get_or_create(
            user=user,
            defaults={
                "flat": flat,
                "is_owner": user.role == User.Role.RESIDENT,
            },
        )

        # Existing role-specific records are preserved.
        if user.role == User.Role.GUARDIAN:
            from guardians.models import Guardian

            Guardian.objects.get_or_create(
                user=user,
                resident=resident,
                defaults={
                    "relation": "Family Guardian",
                    "is_primary": True,
                },
            )

        elif user.role == User.Role.VOLUNTEER:
            from volunteers.models import Volunteer

            Volunteer.objects.get_or_create(
                user=user,
                society=society,
                defaults={
                    "assigned_block": block,
                    "available_for_emergency": True,
                },
            )

        elif user.role == User.Role.SECURITY:
            from security.models import SecurityGuard

            SecurityGuard.objects.get_or_create(
                user=user,
                society=society,
                defaults={
                    "gate_assigned": "Main Gate",
                    "is_on_duty": True,
                },
            )

        # Generate both existing token format and JWT.
        token, _ = Token.objects.get_or_create(user=user)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "token": token.key,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "success": True,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "token": token.key,
            "user": UserSerializer(user).data,
        })


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user
