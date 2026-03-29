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
                2 if row.get("location_match") == "PINCODE" else (1 if row.get("location_match") == "CITY" else 0),
                float(row.get("score") or 0),
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
        response_value = str(request.data.get("response") or "").strip().upper()

        if not request_id or not donor_id or response_value not in ("ACCEPTED", "DECLINED"):
            return Response(
                {"message": "request_id, donor_id and response(ACCEPTED/DECLINED) are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            blood_request = BloodRequest.objects.get(id=request_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            donor = Donor.objects.get(id=donor_id)
        except Donor.DoesNotExist:
            return Response({"message": "donor not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            donor_response = DonorResponse.objects.get(donor=donor, blood_request=blood_request)
        except DonorResponse.DoesNotExist:
            return Response({"message": "donor response not found"}, status=status.HTTP_404_NOT_FOUND)

        if response_value == "ACCEPTED":
            donor_response.response_status = "accepted"
            donor_response.save(update_fields=["response_status", "updated_at"])

            blood_request.status = "completed"
            blood_request.save(update_fields=["status", "updated_at"])
            _create_donation_record(blood_request, donor=donor)

            return Response(
                {"request_id": blood_request.id, "donor_id": donor.id, "status": "COMPLETED"},
                status=status.HTTP_200_OK,
            )

        donor_response.response_status = "declined"
        donor_response.save(update_fields=["response_status", "updated_at"])

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

        if not request_id or not donor_id:
            return Response(
                {"message": "request_id and donor_id are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = complete_donation(request_id=request_id, donor_id=donor_id)
        except BloodRequest.DoesNotExist:
            return Response({"message": "request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Donor.DoesNotExist:
            return Response({"message": "donor not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)
