from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.utils import decrease_stock
from users.models import Hospital

from .models import BloodRequest


def _request_to_dict(item):
    return {
        "id": item.id,
        "patient_name": item.patient_name,
        "blood_group": item.blood_group,
        "component_type": item.component_type,
        "units": item.units_required,
        "urgency": item.urgency_level,
        "required_by": str(item.required_by_date),
        "hospital_id": item.hospital_id,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
    }


class CreateBloodRequestView(APIView):
    def post(self, request):
        patient_name = request.data.get("patient_name")
        blood_group = request.data.get("blood_group")
        component_type = request.data.get("component_type")
        units = request.data.get("units")
        urgency = request.data.get("urgency")
        required_by = request.data.get("required_by")
        hospital_id = request.data.get("hospital_id")

        if not all([patient_name, blood_group, component_type, units, urgency, required_by, hospital_id]):
            return Response(
                {"message": "patient_name, blood_group, component_type, units, urgency, required_by, hospital_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            return Response(
                {"message": "hospital not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        blood_request = BloodRequest.objects.create(
            hospital=hospital,
            patient_name=patient_name,
            patient_age=0,
            blood_group=blood_group,
            component_type=component_type,
            units_required=units,
            urgency_level=urgency,
            required_by_date=required_by,
            hospital_contact_number="",
            address_line="",
            city="",
            state="",
            status="pending",
        )

        return Response(
            _request_to_dict(blood_request),
            status=status.HTTP_201_CREATED,
        )


class ListBloodRequestView(APIView):
    def get(self, request):
        status_filter = request.query_params.get("status")

        requests_qs = BloodRequest.objects.all().order_by("-created_at")
        if status_filter:
            normalized = status_filter.strip().lower()
            if normalized == "rejected":
                normalized = "cancelled"
            requests_qs = requests_qs.filter(status=normalized)

        data = [_request_to_dict(item) for item in requests_qs]
        return Response(data, status=status.HTTP_200_OK)


class UpdateBloodRequestStatusView(APIView):
    def patch(self, request, id):
        status_value = request.data.get("status", "").strip().lower()
        if status_value not in ("approved", "rejected"):
            return Response(
                {"message": "status must be approved or rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        target_status = "cancelled" if status_value == "rejected" else "approved"

        if status_value == "approved" and blood_request.status != "approved":
            try:
                decrease_stock(blood_request.blood_group, blood_request.units_required)
            except ValueError as exc:
                return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

            # Avoid duplicate deduction from pre_save signal for this save call.
            blood_request._skip_stock_signal = True

        blood_request.status = target_status
        blood_request.save(update_fields=["status", "updated_at"])

        return Response(_request_to_dict(blood_request), status=status.HTTP_200_OK)
