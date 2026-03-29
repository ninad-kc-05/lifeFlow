from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BloodInventory
from .serializers import BloodInventorySerializer


class ListInventoryView(APIView):
    def get(self, request):
        records = BloodInventory.objects.all().order_by("blood_group")
        serializer = BloodInventorySerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AddInventoryView(APIView):
    def post(self, request):
        blood_group = request.data.get("blood_group")
        units = request.data.get("units")

        if not blood_group or units is None:
            return Response(
                {"message": "blood_group and units are required"},
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

        inventory, _ = BloodInventory.objects.get_or_create(
            blood_group=blood_group,
            defaults={"units_available": 0},
        )
        inventory.units_available += units
        inventory.save()

        serializer = BloodInventorySerializer(inventory)
        return Response(serializer.data, status=status.HTTP_200_OK)
