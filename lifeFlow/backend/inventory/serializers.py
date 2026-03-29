from rest_framework import serializers

from .models import BloodInventory


class BloodInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BloodInventory
        fields = [
            "id",
            "blood_group",
            "component_type",
            "source_of_blood",
            "source_name",
            "units_available",
            "last_updated",
        ]
