from rest_framework import serializers

from .models import Asset, AssetAssignment, AssetCategory


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ["id", "organisation", "name", "description"]
        read_only_fields = ["organisation"]


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id", "organisation", "category", "category_name", "name", "tracking_id",
            "description", "purchase_date", "purchase_cost", "status",
        ]
        read_only_fields = ["organisation"]


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_name = serializers.CharField(source="asset.name", read_only=True)
    person_name = serializers.SerializerMethodField()

    class Meta:
        model = AssetAssignment
        fields = [
            "id", "asset", "asset_name", "person", "person_name", "assigned_date", "assigned_by",
            "return_date", "return_condition", "status",
        ]
        read_only_fields = ["assigned_date", "assigned_by", "return_date"]

    def get_person_name(self, obj):
        return f"{obj.person.first_name} {obj.person.last_name}"
