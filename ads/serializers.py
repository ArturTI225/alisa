from rest_framework import serializers

from accounts.serializers import UserSerializer
from services.models import ServiceCategory
from .models import Ad, Offer


class AdSerializer(serializers.ModelSerializer):
    client = UserSerializer(read_only=True)
    assigned_craftsman = UserSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        source="category",
        write_only=True,
    )

    class Meta:
        model = Ad
        fields = [
            "id",
            "title",
            "description",
            "category",
            "category_id",
            "city",
            "district",
            "budget_min",
            "budget_max",
            "status",
            "is_urgent",
            "deadline",
            "preferred_date",
            "client",
            "assigned_craftsman",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category",
            "status",
            "client",
            "assigned_craftsman",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        validated_data["client"] = self.context["request"].user
        return super().create(validated_data)


class OfferSerializer(serializers.ModelSerializer):
    craftsman = UserSerializer(read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "ad",
            "craftsman",
            "message",
            "proposed_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "craftsman", "status", "created_at"]
