from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum

from .models import BloodInventory
from .serializers import BloodInventorySerializer


class InventorySummaryView(APIView):
    def get(self, request):
        total_units = BloodInventory.objects.aggregate(total=Sum("units_available"))["total"] or 0
        group_summary = (
            BloodInventory.objects.values("blood_group")
            .annotate(total_units=Sum("units_available"))
            .order_by("blood_group")
        )
        
        by_group = {item["blood_group"]: item["total_units"] for item in group_summary}
        
        return Response({
            "total": total_units,
            "by_group": by_group
        }, status=status.HTTP_200_OK)


class ListInventoryView(APIView):
    def get(self, request):
        blood_group = request.query_params.get("blood_group")
        component_type = request.query_params.get("component_type")
        source_of_blood = request.query_params.get("source_of_blood")
        source_name = request.query_params.get("source_name")

        records = BloodInventory.objects.all()
        if blood_group:
            records = records.filter(blood_group=blood_group)
        if component_type:
            records = records.filter(component_type=component_type)
        if source_of_blood:
            records = records.filter(source_of_blood=source_of_blood)
        if source_name:
            records = records.filter(source_name__icontains=source_name)

        records = records.order_by("blood_group", "component_type", "source_of_blood", "source_name")
        serializer = BloodInventorySerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddInventoryView(APIView):
    def post(self, request):
        blood_group = request.data.get("blood_group")
        component_type = request.data.get("component_type")
        source_of_blood = request.data.get("source_of_blood")
        source_name = (request.data.get("source_name") or "").strip()
        units = request.data.get("units")

        if not blood_group or not component_type or not source_of_blood or units is None:
            return Response(
                {"message": "blood_group, component_type, source_of_blood and units are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            units = int(units)
        except (TypeError, ValueError):
            return Response(
                {"message": "units must be > 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if units <= 0:
            return Response(
                {"message": "units must be > 0"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allowed_sources = {"donation", "camp"}
        if source_of_blood not in allowed_sources:
            return Response(
                {"message": "source_of_blood must be donation or camp"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if source_of_blood == "donation" and units != 1:
            return Response(
                {"message": "units must be exactly 1 for donation source"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not source_name:
            return Response(
                {"message": "source_name is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventory, _ = BloodInventory.objects.get_or_create(
            blood_group=blood_group,
            component_type=component_type,
            source_of_blood=source_of_blood,
            source_name=source_name,
            defaults={"units_available": 0},
        )
        inventory.units_available += units
        inventory.save()

        serializer = BloodInventorySerializer(inventory)
        return Response(serializer.data, status=status.HTTP_200_OK)
