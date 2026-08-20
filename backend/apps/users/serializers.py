from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import validate_refresh_binding

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["email"] = self.user.email
        data["nickname"] = self.user.nickname
        return data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "password", "nickname")
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(
            email=validated_data["email"],
            username=validated_data["email"],
            nickname=validated_data.get("nickname", ""),
        )
        user.set_password(password)
        user.save()
        return user


class SsoBoundTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        if settings.PILGRIMAGE_SSO_ENABLED:
            refresh = RefreshToken(attrs["refresh"])
            validate_refresh_binding(
                request=self.context["request"],
                refresh_token=refresh,
            )
        return super().validate(attrs)
