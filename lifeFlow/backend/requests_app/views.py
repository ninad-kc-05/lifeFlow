from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from donations.models import DonationRecord, DonorSurvey
from users.models import Donor, Hospital

from .models import BloodRequest, DonorResponse
from .smart_matching import (
    assign_top_donors,
    calculate_score,
    complete_donation,
    hospital_select_donor,
    is_compatible,
    is_eligible,
    match_donors,
)


API_STATUS_MAP = {
    "pending": "PENDING",
    "approved": "APPROVED",
    "rejected": "REJECTED",
    "cancelled": "REJECTED",
    "donor_needed": "DONOR_NEEDED",
    "allocated": "ASSIGNED",
    "assigned": "ASSIGNED",
    "completed": "COMPLETED",
}


def _normalize_status(value):
    normalized = str(value or "").strip().lower()
    if normalized == "cancelled":
        return "rejected"
    return normalized


def _status_for_api(db_status):
    return API_STATUS_MAP.get(db_status, str(db_status or "").upper())


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
        "hospital_contact_number": item.hospital_contact_number,
        "address_line": item.address_line,
        "city": item.city,
        "state": item.state,
        "pincode": item.pincode,
        "special_note": item.special_note,
        "status": item.status,
        "status_code": _status_for_api(item.status),
        "created_at": item.created_at.isoformat(),
    }


def _donor_to_dict(donor):
    latest_survey = DonorSurvey.objects.filter(donor=donor).order_by("-submitted_at").first()
    eligibility_status = "UNKNOWN"
    eligibility_reason = "No screening report submitted yet"
    survey_note = ""
    if latest_survey is not None:
        is_ok, reason = is_eligible(donor)
        eligibility_status = "ELIGIBLE" if is_ok else "NOT_ELIGIBLE"
        eligibility_reason = reason
        survey_note = latest_survey.review_notes or ""

    return {
        "id": donor.id,
        "name": f"{donor.first_name} {donor.last_name}".strip(),
        "blood_group": donor.blood_group,
        "city": donor.city,
        "pincode": donor.pincode,
        "last_donation_date": str(donor.last_donation_date) if donor.last_donation_date else None,
        "available": donor.is_available,
        "eligibility": eligibility_status,
        "eligibility_reason": eligibility_reason,
        "survey_note": survey_note,
    }


def _create_donation_record(blood_request, donor=None):
    DonationRecord.objects.get_or_create(
        blood_request=blood_request,
        donor=donor,
        defaults={
            "hospital": blood_request.hospital,
            "blood_group": blood_request.blood_group,
            "units_donated": blood_request.units_required,
            "donation_date": timezone.now().date(),
            "donation_status": "completed",
            "remarks": "Auto-created from request workflow",
        },
    )


class CreateBloodRequestView(APIView):
    def post(self, request):
        patient_name = request.data.get("patient_name") or "Unknown"
        patient_age = request.data.get("patient_age", 0)
        blood_group = request.data.get("blood_group")
        component_type = request.data.get("component_type") or request.data.get("component")
        units = request.data.get("units") or request.data.get("units_required")
        urgency = request.data.get("urgency") or request.data.get("urgency_level") or "normal"
        required_by = request.data.get("required_by") or request.data.get("required_by_date")
        hospital_id = request.data.get("hospital_id")
        hospital_contact_number = request.data.get("hospital_contact_number")
        address_line = request.data.get("address_line")
        city = request.data.get("city")
        state_name = request.data.get("state")
        pincode = request.data.get("pincode")
        special_note = (request.data.get("special_note") or "").strip()

        if not all([blood_group, component_type, units, urgency, required_by, hospital_id]):
            return Response(
                {"message": "blood_group, component/component_type, units/units_required, urgency, required_by, hospital_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            hospital = Hospital.objects.get(id=hospital_id)
        except Hospital.DoesNotExist:
            return Response(
                {"message": "hospital not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # If these fields are not provided, use canonical values from hospital master data.
        hospital_contact_number = (hospital_contact_number or hospital.mobile_number or "").strip()
        address_line = (address_line or hospital.address_line or "").strip()
        city = (city or hospital.city or "").strip()
        state_name = (state_name or hospital.state or "").strip()
        pincode = (pincode or hospital.pincode or "").strip()

        if not pincode:
            return Response(
                {"message": "pincode is required for request location handling"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            patient_age = int(patient_age or 0)
        except (TypeError, ValueError):
            patient_age = 0

        try:
            units = int(units)
        except (TypeError, ValueError):
            return Response(
                {"message": "units must be a number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blood_request = BloodRequest.objects.create(
            hospital=hospital,
            patient_name=patient_name,
            patient_age=max(patient_age, 0),
            blood_group=blood_group,
            component_type=component_type,
            units_required=units,
            urgency_level=urgency,
            required_by_date=required_by,
            hospital_contact_number=hospital_contact_number,
            address_line=address_line,
            city=city,
            state=state_name,
            pincode=pincode,
            special_note=special_note,
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
            normalized = _normalize_status(status_filter)
            if normalized == "rejected":
                requests_qs = requests_qs.filter(status__in=["rejected", "cancelled"])
            else:
                requests_qs = requests_qs.filter(status=normalized)

        data = [_request_to_dict(item) for item in requests_qs]
        return Response(data, status=status.HTTP_200_OK)


class UpdateBloodRequestStatusView(APIView):
    def patch(self, request, id):
        status_value = _normalize_status(request.data.get("status", ""))
        if status_value not in ("approved", "rejected"):
            return Response(
                {"message": "status must be approved or rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        target_status = "rejected" if status_value == "rejected" else "approved"

        blood_request.status = target_status
        blood_request.save(update_fields=["status", "updated_at"])

        return Response(_request_to_dict(blood_request), status=status.HTTP_200_OK)


class AdminBloodRequestListView(APIView):
    def get(self, request):
        requests_qs = BloodRequest.objects.all().order_by("-created_at")
        data = []
        for item in requests_qs:
            payload = _request_to_dict(item)
            payload["status"] = _status_for_api(item.status)
            data.append(payload)
        return Response(data, status=status.HTTP_200_OK)


class AdminApproveRequestView(APIView):
    def post(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        blood_request.status = "approved"
        blood_request.save(update_fields=["status", "updated_at"])
        payload = _request_to_dict(blood_request)
        payload["status"] = "APPROVED"
        return Response(payload, status=status.HTTP_200_OK)


class AdminMarkReadRequestView(APIView):
    def post(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        if _normalize_status(blood_request.status) != "pending":
            return Response(
                {"message": "only pending requests can be marked as read"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        blood_request.status = "donor_needed"
        blood_request.save(update_fields=["status", "updated_at"])
        payload = _request_to_dict(blood_request)
        payload["status"] = "DONOR_NEEDED"
        return Response(payload, status=status.HTTP_200_OK)


class AdminRejectRequestView(APIView):
    def post(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        blood_request.status = "rejected"
        blood_request.save(update_fields=["status", "updated_at"])
        payload = _request_to_dict(blood_request)
        payload["status"] = "REJECTED"
        return Response(payload, status=status.HTTP_200_OK)


class AdminInventoryAllotView(APIView):
    def post(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        # Removed strict urgency check to allow fallback allotment when no donors are found
        # if blood_request.urgency_level not in ["urgent", "emergency"]:
        #     ...

        from inventory.models import BloodInventory

        # Try to find inventory matching blood group and component
        # We look for ANY source that has enough units
        inventory_items = BloodInventory.objects.filter(
            blood_group=blood_request.blood_group,
            component_type=blood_request.component_type,
            units_available__gte=blood_request.units_required,
        ).order_by("-units_available")

        if not inventory_items.exists():
            return Response(
                {"message": f"Insufficient inventory for {blood_request.blood_group} {blood_request.component_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use the first available item
        item = inventory_items.first()
        item.units_available -= blood_request.units_required
        item.save(update_fields=["units_available", "last_updated"])

        blood_request.status = "completed"
        blood_request.save(update_fields=["status", "updated_at"])

        # Create a donation record for tracking (without donor)
        _create_donation_record(blood_request, donor=None)

        return Response(
            {"message": "Units allotted from inventory and request completed", "status": "COMPLETED"},
            status=status.HTTP_200_OK,
        )


class AdminSearchDonorView(APIView):
    def post(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        if _normalize_status(blood_request.status) != "donor_needed":
            return Response(
                {"message": "request must be DONOR_NEEDED before donor search"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donor_rows = match_donors(blood_request.id)

        donor_payload = []
        for row in donor_rows:
            donor = row["donor"]
            DonorResponse.objects.get_or_create(
                donor=donor,
                blood_request=blood_request,
                defaults={"response_status": "pending", "is_active": True},
            )
            donor_data = _donor_to_dict(donor)
            donor_data["score"] = row.get("score", 0)
            donor_data["match_type"] = (
                "EXACT"
                if str(donor.blood_group or "").upper() == str(blood_request.blood_group or "").upper()
                else "COMPATIBLE"
            )
            donor_data["location_match"] = "PINCODE" if row.get("location_priority") == "pincode" else "CITY"
            donor_payload.append(donor_data)

        blood_request.status = "donor_needed"
        blood_request.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "request_id": blood_request.id,
                "status": "DONOR_NEEDED",
                "special_note": blood_request.special_note,
                "donors": donor_payload,
            },
            status=status.HTTP_200_OK,
        )


class AdminRequestDonorsView(APIView):
    def get(self, request, id):
        try:
            blood_request = BloodRequest.objects.get(id=id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        q = str(request.query_params.get("q") or "").strip().lower()
        city_filter = str(request.query_params.get("city") or "").strip().lower()
        eligibility_filter = str(request.query_params.get("eligibility") or "").strip().upper()
        response_filter = str(request.query_params.get("response_status") or "").strip().upper()

        responses = DonorResponse.objects.filter(blood_request=blood_request, is_active=True).select_related("donor")

        # Automatically trigger matching if no donors found yet
        if not responses.exists():
            donor_rows = match_donors(blood_request.id)
            for row in donor_rows:
                donor = row["donor"]
                DonorResponse.objects.get_or_create(
                    donor=donor,
                    blood_request=blood_request,
                    defaults={"response_status": "pending", "is_active": True},
                )
            responses = DonorResponse.objects.filter(blood_request=blood_request, is_active=True).select_related("donor")

        if response_filter in {"PENDING", "ACCEPTED", "DECLINED"}:
            responses = responses.filter(response_status=response_filter.lower())

        data = []
        assigned_count = DonorResponse.objects.filter(
            blood_request=blood_request,
            is_active=True,
        ).filter(status__in=["testing", "selected"]).count()

        for item in responses:
            donor_data = _donor_to_dict(item.donor)
            donor_data["response_status"] = item.response_status.upper()
            donor_data["assignment_status"] = item.status

            compatible = is_compatible(item.donor.blood_group, blood_request.blood_group, blood_request.component_type)
            donor_data["match_type"] = (
                "EXACT"
                if str(item.donor.blood_group or "").upper() == str(blood_request.blood_group or "").upper()
                else ("COMPATIBLE" if compatible else "NOT_COMPATIBLE")
            )

            donor_data["score"] = calculate_score(item.donor, blood_request) if compatible else 0
            donor_data["location_match"] = (
                "PINCODE"
                if str(item.donor.pincode or "").strip() == str(blood_request.pincode or "").strip()
                else (
                    "CITY"
                    if str(item.donor.city or "").strip().lower() == str(blood_request.city or "").strip().lower()
                    else "NONE"
                )
            )

            if city_filter and str(donor_data.get("city") or "").strip().lower() != city_filter:
                continue

            if eligibility_filter in {"ELIGIBLE", "NOT_ELIGIBLE", "UNKNOWN"} and donor_data.get("eligibility") != eligibility_filter:
                continue

            if q:
                haystack = " ".join([
                    str(donor_data.get("name") or ""),
                    str(donor_data.get("city") or ""),
                    str(donor_data.get("blood_group") or ""),
                    str(donor_data.get("survey_note") or ""),
                ]).lower()
                if q not in haystack:
                    continue

            data.append(donor_data)

        data.sort(
            key=lambda row: (
                float(row.get("score") or 0),
                2 if row.get("location_match") == "PINCODE" else (1 if row.get("location_match") == "CITY" else 0),
            ),
            reverse=True,
        )

        return Response(
            {
                "request_id": blood_request.id,
                "patient_name": blood_request.patient_name,
                "blood_group": blood_request.blood_group,
                "component_type": blood_request.component_type,
                "city": blood_request.city,
                "special_note": blood_request.special_note,
                "assigned_count": assigned_count,
                "max_assignable": 3,
                "donors": data,
            },
            status=status.HTTP_200_OK,
        )


class AdminAllocateDonorView(APIView):
    def post(self, request):
        request_id = request.data.get("request_id")
        donor_id = request.data.get("donor_id")
        if not request_id or not donor_id:
            return Response({"message": "request_id and donor_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            return Response({"message": "donor not found"}, status=status.HTTP_404_NOT_FOUND)

        if _normalize_status(blood_request.status) not in ("donor_needed", "assigned"):
            return Response(
                {"message": "donors can only be assigned when request is DONOR_NEEDED or ASSIGNED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_shortlist_count = DonorResponse.objects.filter(
            blood_request=blood_request,
            is_active=True,
            status__in=["testing", "selected"],
        ).exclude(donor=donor).count()

        if active_shortlist_count >= 3:
            return Response(
                {"message": "maximum 3 donors can be assigned for testing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        donor_response, _ = DonorResponse.objects.get_or_create(
            donor=donor,
            blood_request=blood_request,
            defaults={
                "hospital": blood_request.hospital,
                "status": "testing",
                "response_status": "pending",
                "remarks": "Shortlisted for testing",
                "is_active": True,
            },
        )
        donor_response.hospital = blood_request.hospital
        donor_response.status = "testing"
        donor_response.response_status = "pending"
        donor_response.remarks = "Shortlisted for testing"
        donor_response.is_active = True
        donor_response.save(update_fields=["hospital", "status", "response_status", "remarks", "is_active", "updated_at"])

        blood_request.status = "assigned"
        blood_request.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "request_id": blood_request.id,
                "donor_id": donor.id,
                "status": "ASSIGNED",
                "assigned_count": DonorResponse.objects.filter(
                    blood_request=blood_request,
                    is_active=True,
                    status__in=["testing", "selected"],
                ).count(),
                "max_assignable": 3,
            },
            status=status.HTTP_200_OK,
        )


class DonorRespondView(APIView):
    def post(self, request):
        request_id = request.data.get("request_id")
        donor_id = request.data.get("donor_id")
        donor_mobile = request.data.get("donor_mobile")
        response_value = str(request.data.get("response") or "").strip().upper()

        if not request_id or (not donor_id and not donor_mobile) or response_value not in ("ACCEPTED", "DECLINED"):
            return Response(
                {"message": "request_id, donor_id/donor_mobile and response(ACCEPTED/DECLINED) are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        donor = None
        if donor_id:
            donor = Donor.objects.filter(id=donor_id).first()
        elif donor_mobile:
            donor = Donor.objects.filter(mobile_number=donor_mobile).first()

        if not donor:
            return Response({"message": "donor not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            donor_response = DonorResponse.objects.get(donor=donor, blood_request=blood_request)
            # Protection: cannot change response if already accepted or further in the cycle
            if donor_response.response_status == "accepted" and response_value == "DECLINED":
                return Response({"message": "Cannot decline a request after it has been accepted"}, status=status.HTTP_400_BAD_REQUEST)
        except DonorResponse.DoesNotExist:
            return Response({"message": "donor response not found"}, status=status.HTTP_404_NOT_FOUND)

        if response_value == "ACCEPTED":
            # Extract screening data from request body
            donor_response.weight = request.data.get("weight")
            donor_response.height = request.data.get("height")

            donor_response.response_status = "accepted"
            donor_response.status = "accepted"
            donor_response.save(update_fields=[
                "response_status", "status", "updated_at",
                "weight", "height"
            ])

            blood_request.status = "donor_accepted"
            blood_request.save(update_fields=["status", "updated_at"])

            return Response(
                {"request_id": blood_request.id, "donor_id": donor.id, "status": "DONOR_ACCEPTED"},
                status=status.HTTP_200_OK,
            )

        donor_response.response_status = "declined"
        donor_response.status = "rejected" # Update internal status too
        donor_response.save(update_fields=["response_status", "status", "updated_at"])

        # Restore donor availability if they were scheduled
        if not donor.is_available:
            donor.is_available = True
            donor.save(update_fields=["is_available", "updated_at"])

        accepted_exists = DonorResponse.objects.filter(
            blood_request=blood_request,
            response_status="accepted",
            is_active=True,
        ).exists()

        if not accepted_exists:
            blood_request.status = "donor_needed"
            blood_request.save(update_fields=["status", "updated_at"])

        return Response(
            {"request_id": blood_request.id, "donor_id": donor.id, "status": _status_for_api(blood_request.status)},
            status=status.HTTP_200_OK,
        )


class MatchDonorsView(APIView):
    def get(self, request, request_id):
        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        donor_rows = match_donors(request_id)
        payload = []
        for row in donor_rows:
            donor = row["donor"]
            payload.append(
                {
                    "donor_id": donor.id,
                    "name": f"{donor.first_name} {donor.last_name}".strip(),
                    "blood_group": donor.blood_group,
                    "city": donor.city,
                    "pincode": donor.pincode,
                    "score": row["score"],
                    "bmi": row["bmi"],
                    "age": row["age"],
                    "weight": row["weight"],
                    "location_priority": row["location_priority"],
                }
            )

        return Response(
            {
                "request_id": blood_request.id,
                "request_blood_group": blood_request.blood_group,
                "component": blood_request.component_type,
                "total_matches": len(payload),
                "matches": payload,
            },
            status=status.HTTP_200_OK,
        )


class AssignTopDonorsView(APIView):
    def post(self, request, request_id):
        try:
            result = assign_top_donors(request_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(result, status=status.HTTP_200_OK)


class DonorActiveRequestView(APIView):
    def get(self, request):
        donor_id = request.query_params.get("donor_id")
        donor_mobile = request.query_params.get("donor_mobile")

        donor = None
        if donor_id:
            donor = Donor.objects.filter(id=donor_id).first()
        elif donor_mobile:
            donor = Donor.objects.filter(mobile_number=donor_mobile).first()

        if donor is None:
            return Response({"message": "Valid donor_id or donor_mobile is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the latest active request for this donor
        active_response = DonorResponse.objects.filter(
            donor=donor,
            is_active=True,
            response_status__in=["pending", "accepted"]
        ).select_related("blood_request", "blood_request__hospital").first()

        if not active_response:
            return Response({"message": "No active requests found", "request": None}, status=status.HTTP_200_OK)

        blood_request = active_response.blood_request
        hospital = blood_request.hospital

        return Response({
            "request": {
                "request_id": blood_request.id,
                "hospital_name": hospital.hospital_name if hospital else "Unknown Hospital",
                "patient_name": blood_request.patient_name,
                "blood_group": blood_request.blood_group,
                "units_needed": blood_request.units_required,
                "urgency": blood_request.urgency_level,
                "city": blood_request.city,
                "address": blood_request.address_line,
                "status": active_response.status,
                "active_request_status": active_response.status,
                "scheduled_date": str(active_response.scheduled_date) if active_response.scheduled_date else None,
                "donor_gender": donor.gender
            }
        }, status=status.HTTP_200_OK)


class DonorAcceptScheduleView(APIView):
    def post(self, request):
        request_id = request.data.get("request_id")
        donor_id = request.data.get("donor_id")
        donor_mobile = request.data.get("donor_mobile")

        donor = None
        if donor_id:
            donor = Donor.objects.filter(id=donor_id).first()
        elif donor_mobile:
            donor = Donor.objects.filter(mobile_number=donor_mobile).first()

        if donor is None or not request_id:
            return Response({"message": "Valid donor identification and request_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            donor_response = DonorResponse.objects.get(donor=donor, blood_request_id=request_id, status="scheduled")
        except DonorResponse.DoesNotExist:
            return Response({"message": "No scheduled request found for this donor"}, status=status.HTTP_404_NOT_FOUND)

        donor_response.status = "schedule_accepted"
        donor_response.save(update_fields=["status", "updated_at"])

        blood_request = donor_response.blood_request
        blood_request.status = "schedule_accepted"
        blood_request.save(update_fields=["status", "updated_at"])

        return Response({"message": "Schedule accepted by donor", "status": "SCHEDULE_ACCEPTED"}, status=status.HTTP_200_OK)


class HospitalSelectDonorView(APIView):
    def post(self, request):
        donor_response_id = request.data.get("donor_response_id")
        if not donor_response_id:
            return Response(
                {"message": "donor_response_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = hospital_select_donor(donor_response_id)
        except DonorResponse.DoesNotExist:
            return Response({"message": "donor response not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class CompleteDonationView(APIView):
    def post(self, request):
        request_id = request.data.get("request_id")
        donor_id = request.data.get("donor_id")
        response_id = request.data.get("response_id")

        if not response_id and (not request_id or not donor_id):
            return Response(
                {"message": "response_id or (request_id and donor_id) are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if response_id:
                donor_response = DonorResponse.objects.get(id=response_id)
                blood_request = donor_response.blood_request
                donor = donor_response.donor
            else:
                blood_request = BloodRequest.objects.get(id=request_id)
                donor = Donor.objects.get(id=donor_id)
                donor_response = DonorResponse.objects.get(donor=donor, blood_request=blood_request)
        except (BloodRequest.DoesNotExist, Donor.DoesNotExist, DonorResponse.DoesNotExist):
            return Response({"message": "request, donor, or response not found"}, status=status.HTTP_404_NOT_FOUND)

        # Mark as donated/completed
        donor_response.status = "donated"
        donor_response.save(update_fields=["status", "updated_at"])

        blood_request.status = "completed"
        blood_request.save(update_fields=["status", "updated_at"])

        # Update donor's last donation date
        donor.last_donation_date = timezone.now().date()
        donor.is_available = True
        donor.save(update_fields=["last_donation_date", "is_available", "updated_at"])

        # Create the actual donation record
        _create_donation_record(blood_request, donor=donor)

        return Response({"message": "Donation completed successfully", "status": "COMPLETED"}, status=status.HTTP_200_OK)


class HospitalReturnToInventoryView(APIView):
    @transaction.atomic
    def post(self, request):
        request_id = request.data.get("request_id")
        response_id = request.data.get("response_id")
        
        if not request_id and not response_id:
            return Response({"message": "request_id or response_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if response_id:
                donor_response = DonorResponse.objects.get(id=response_id)
                blood_request = donor_response.blood_request
            else:
                blood_request = BloodRequest.objects.get(id=request_id)
                # If only request_id provided, we look for all 'donated' records for this request
                # This is for backward compatibility or bulk return
        except (BloodRequest.DoesNotExist, DonorResponse.DoesNotExist):
            return Response({"message": "request or response not found"}, status=status.HTTP_404_NOT_FOUND)

        from inventory.models import BloodInventory

        # Logic for returning specific donor response
        if response_id:
            # Check if this specific response was already returned
            if DonationRecord.objects.filter(blood_request=blood_request, donor=donor_response.donor, donation_status="returned").exists():
                return Response({"message": "Units for this donor already returned to inventory"}, status=status.HTTP_400_BAD_REQUEST)

            # Update inventory (assume 1 unit/bag per donor as per previous requirement)
            inv_item, _ = BloodInventory.objects.get_or_create(
                blood_group=blood_request.blood_group,
                component_type=blood_request.component_type,
                source_of_blood="receiver_recovery",
                defaults={"units_available": 0, "source_name": f"Return from Request #{blood_request.id} (Donor {donor_response.donor.id})"}
            )
            inv_item.units_available += 1 # 1 bag
            inv_item.save(update_fields=["units_available", "last_updated"])

            # Update donation record status
            DonationRecord.objects.filter(blood_request=blood_request, donor=donor_response.donor).update(
                donation_status="returned",
                remarks=f"Patient recovered. Units returned to inventory on {timezone.now().date()}."
            )
            
            # Deactivate this response
            donor_response.is_active = False
            donor_response.save(update_fields=["is_active", "updated_at"])
        else:
            # Bulk return for all donors of this request (legacy/fallback)
            donations = DonationRecord.objects.filter(blood_request=blood_request, donation_status="completed")
            units_to_return = donations.count() # Number of bags
            
            if units_to_return == 0:
                return Response({"message": "No completed donations found to return"}, status=status.HTTP_400_BAD_REQUEST)

            inv_item, _ = BloodInventory.objects.get_or_create(
                blood_group=blood_request.blood_group,
                component_type=blood_request.component_type,
                source_of_blood="receiver_recovery",
                defaults={"units_available": 0, "source_name": f"Bulk Return Request #{blood_request.id}"}
            )
            inv_item.units_available += units_to_return
            inv_item.save(update_fields=["units_available", "last_updated"])

            donations.update(
                donation_status="returned",
                remarks=f"Bulk Return: Patient recovered. Returned on {timezone.now().date()}."
            )
            DonorResponse.objects.filter(blood_request=blood_request).update(is_active=False)

        # Check if all units for the request are handled
        total_donated = DonationRecord.objects.filter(blood_request=blood_request, donation_status="completed").count()
        if total_donated >= blood_request.units_required:
            blood_request.status = "completed"
        
        blood_request.special_note = (blood_request.special_note or "") + f" [UNITS RETURNED TO INVENTORY ON {timezone.now().date()}]"
        blood_request.save(update_fields=["special_note", "updated_at", "status"])

        return Response({"message": "Units successfully returned to inventory", "status": "RETURNED"}, status=status.HTTP_200_OK)


class HospitalAcceptedDonorsView(APIView):
    def get(self, request):
        hospital_id = request.query_params.get("hospital_id")
        if not hospital_id:
            return Response({"message": "hospital_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Get all active donor responses for this hospital where donor has accepted
        responses = DonorResponse.objects.filter(
            blood_request__hospital_id=hospital_id,
            is_active=True,
            response_status="accepted"
        ).select_related("donor", "blood_request").order_by("-updated_at")

        data = []
        for item in responses:
            data.append({
                "response_id": item.id,
                "request_id": item.blood_request.id,
                "donor_id": item.donor.id,
                "donor_name": f"{item.donor.first_name} {item.donor.last_name}",
                "donor_blood_group": item.donor.blood_group,
                "patient_name": item.blood_request.patient_name,
                "blood_request_group": item.blood_request.blood_group,
                "status": item.status,
                "scheduled_date": str(item.scheduled_date) if item.scheduled_date else None,
                "deadline": str(item.blood_request.required_by_date),
            })

        return Response(data, status=status.HTTP_200_OK)


class HospitalAcknowledgeDonorView(APIView):
    def post(self, request):
        response_id = request.data.get("response_id")
        scheduled_date = request.data.get("scheduled_date")

        if not response_id or not scheduled_date:
            return Response({"message": "response_id and scheduled_date are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            donor_response = DonorResponse.objects.get(id=response_id)
        except DonorResponse.DoesNotExist:
            return Response({"message": "donor response not found"}, status=status.HTTP_404_NOT_FOUND)

        # Ensure scheduled date is before or on the request deadline
        deadline = donor_response.blood_request.required_by_date
        if str(scheduled_date) > str(deadline):
            return Response({"message": f"Scheduled date must be on or before the deadline ({deadline})"}, status=status.HTTP_400_BAD_REQUEST)

        donor_response.status = "scheduled"
        donor_response.scheduled_date = scheduled_date
        donor_response.save(update_fields=["status", "scheduled_date", "updated_at"])

        # Mark donor as temporarily unavailable while scheduled
        donor = donor_response.donor
        donor.is_available = False
        donor.save(update_fields=["is_available", "updated_at"])

        blood_request = donor_response.blood_request
        blood_request.status = "scheduled"
        blood_request.save(update_fields=["status", "updated_at"])

        return Response({"message": "Donor acknowledged and donation scheduled", "status": "SCHEDULED"}, status=status.HTTP_200_OK)
