from rest_framework import serializers

from services.models import Service
from .models import (
    Address,
    FavoriteProvider,
    FavoriteService,
    Notification,
    NotificationPreference,
    ProviderProfile,
    User,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "city",
            "role",
            "is_verified",
            "rating_avg",
            "rating_count",
        ]
        read_only_fields = ["id", "is_verified", "role", "rating_avg", "rating_count"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id",
            "label",
            "city",
            "street",
            "details",
            "latitude",
            "longitude",
            "is_default",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Address.objects.create(user=user, **validated_data)


class ProviderProfileSerializer(serializers.ModelSerializer):
    skills = serializers.StringRelatedField(many=True)
    user = UserSerializer(read_only=True)
    rating_avg = serializers.DecimalField(
        max_digits=4, decimal_places=2, read_only=True, source="user.rating_avg"
    )
    rating_count = serializers.IntegerField(read_only=True, source="user.rating_count")

    class Meta:
        model = ProviderProfile
        fields = [
            "id",
            "user",
            "bio",
            "skills",
            "hourly_rate",
            "city",
            "experience_years",
            "verification_status",
            "availability_notes",
            "rating_avg",
            "rating_count",
        ]


class ServiceSlimSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ["id", "name", "base_price"]


class FavoriteServiceSerializer(serializers.ModelSerializer):
    service = ServiceSlimSerializer(read_only=True)

    class Meta:
        model = FavoriteService
        fields = ["id", "service", "created_at"]
        read_only_fields = fields


class FavoriteProviderSerializer(serializers.ModelSerializer):
    provider = UserSerializer(read_only=True)

    class Meta:
        model = FavoriteProvider
        fields = ["id", "provider", "created_at"]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "type", "title", "body", "link", "is_read", "created_at"]
        read_only_fields = ["id", "title", "body", "link", "created_at"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "booking_updates",
            "disputes",
            "marketing",
            "recurring",
            "chat_messages",
            "bids",
            "urgent_ads",
            "reviews",
        ]
