from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta

from users.models import Donor
from .models import DonorSurvey, SurveyDisease, DonationRecord


def _to_bool(value):
	if isinstance(value, bool):
		return value
	return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _to_float(value, field_name):
	try:
		return float(value)
	except (TypeError, ValueError):
		raise ValueError(f"{field_name} must be a number")


def _to_int(value, field_name):
	try:
		return int(value)
	except (TypeError, ValueError):
		raise ValueError(f"{field_name} must be a whole number")


def _screening_label(value):
	normalized = str(value or "").strip().lower()
	if normalized == "hospital":
		return "Hospital"
	if normalized == "camp":
		return "Camp"
	return ""


def _compute_eligibility(payload, bmi):
	if payload.get("weight_kg", 0) < 50:
		return False
	if bmi < 18.5 or bmi > 29.9:
		return False
	if payload.get("had_recent_fever"):
		return False
	if payload.get("donated_last_3_months"):
		return False
	if payload.get("is_on_medication"):
		return False
	if payload.get("has_chronic_illness"):
		return False
	if payload.get("is_pregnant"):
		return False
	if payload.get("is_breastfeeding"):
		return False
	if payload.get("has_heavy_menstruation"):
		return False
	if payload.get("recent_delivery_or_miscarriage"):
		return False
	if payload.get("used_steroids"):
		return False
	if payload.get("had_major_surgery"):
		return False
	return True


class SubmitDonorSurveyView(APIView):
	@transaction.atomic
	def post(self, request):
		donor_id = request.data.get("donor_id")
		donor_mobile = (request.data.get("donor_mobile") or request.data.get("mobile_number") or "").strip()

		donor = None
		if donor_id:
			donor = Donor.objects.filter(id=donor_id).first()
		if donor is None and donor_mobile:
			donor = Donor.objects.filter(mobile_number=donor_mobile).first()

		if donor is None:
			return Response(
				{"status": "error", "message": "Valid donor_id or donor_mobile is required"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		screening_type = _screening_label(request.data.get("screening_type"))
		if screening_type not in {"Hospital", "Camp"}:
			return Response(
				{"status": "error", "message": "screening_type must be hospital or camp"},
				status=status.HTTP_400_BAD_REQUEST,
			)

		try:
			weight_kg = _to_float(request.data.get("weight_kg"), "weight_kg")
			height_cm = _to_float(request.data.get("height_cm"), "height_cm")
			systolic_bp = _to_int(request.data.get("systolic_bp"), "systolic_bp")
			diastolic_bp = _to_int(request.data.get("diastolic_bp"), "diastolic_bp")
			temperature_c = _to_float(request.data.get("temperature_c"), "temperature_c")
			pulse_rate = _to_int(request.data.get("pulse_rate"), "pulse_rate")
			hemoglobin_raw = request.data.get("hemoglobin")
			hemoglobin = None if hemoglobin_raw in (None, "") else _to_float(hemoglobin_raw, "hemoglobin")
		except ValueError as exc:
			return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

		if height_cm <= 0:
			return Response({"status": "error", "message": "height_cm must be greater than 0"}, status=status.HTTP_400_BAD_REQUEST)

		bmi = weight_kg / ((height_cm / 100.0) ** 2)

		payload = {
			"weight_kg": weight_kg,
			"is_on_medication": _to_bool(request.data.get("is_on_medication")),
			"had_recent_fever": _to_bool(request.data.get("had_recent_fever")),
			"donated_last_3_months": _to_bool(request.data.get("donated_last_3_months")),
			"has_chronic_illness": _to_bool(request.data.get("has_chronic_illness")),
			"used_steroids": request.data.get("used_steroids"),
			"had_major_surgery": request.data.get("had_major_surgery"),
			"is_pregnant": request.data.get("is_pregnant"),
			"is_breastfeeding": request.data.get("is_breastfeeding"),
			"has_heavy_menstruation": request.data.get("has_heavy_menstruation"),
			"recent_delivery_or_miscarriage": request.data.get("recent_delivery_or_miscarriage"),
		}

		survey = DonorSurvey.objects.create(
			donor=donor,
			screening_type=screening_type,
			weight_kg=weight_kg,
			height_cm=height_cm,
			systolic_bp=systolic_bp,
			diastolic_bp=diastolic_bp,
			temperature_c=temperature_c,
			pulse_rate=pulse_rate,
			hemoglobin=hemoglobin,
			is_on_medication=payload["is_on_medication"],
			medication_details=(request.data.get("medication_details") or "").strip() or None,
			had_recent_fever=payload["had_recent_fever"],
			fever_details=(request.data.get("fever_details") or "").strip() or None,
			donated_last_3_months=payload["donated_last_3_months"],
			recent_donation_details=(request.data.get("recent_donation_details") or "").strip() or None,
			has_chronic_illness=payload["has_chronic_illness"],
			chronic_illness_details=(request.data.get("chronic_illness_details") or "").strip() or None,
			used_steroids=(None if payload["used_steroids"] is None else _to_bool(payload["used_steroids"])),
			steroid_details=(request.data.get("steroid_details") or "").strip() or None,
			had_major_surgery=(None if payload["had_major_surgery"] is None else _to_bool(payload["had_major_surgery"])),
			surgery_details=(request.data.get("surgery_details") or "").strip() or None,
			is_pregnant=(None if payload["is_pregnant"] is None else _to_bool(payload["is_pregnant"])),
			is_breastfeeding=(None if payload["is_breastfeeding"] is None else _to_bool(payload["is_breastfeeding"])),
			has_heavy_menstruation=(None if payload["has_heavy_menstruation"] is None else _to_bool(payload["has_heavy_menstruation"])),
			recent_delivery_or_miscarriage=(
				None if payload["recent_delivery_or_miscarriage"] is None else _to_bool(payload["recent_delivery_or_miscarriage"])
			),
			female_additional_details=(request.data.get("female_additional_details") or "").strip() or None,
			is_eligible=_compute_eligibility(payload, bmi),
			review_notes=(request.data.get("review_notes") or "").strip() or "Auto-generated from form submission",
		)

		disease_names = request.data.get("diseases") or []
		if isinstance(disease_names, str):
			disease_names = [d.strip() for d in disease_names.split(",") if d.strip()]

		valid_diseases = {choice for choice, _ in SurveyDisease.DISEASE_CHOICES}
		normalized = []
		for disease in disease_names:
			if disease in valid_diseases and disease not in normalized:
				normalized.append(disease)

		if not normalized:
			normalized = ["None"]

		for disease in normalized:
			SurveyDisease.objects.create(survey=survey, disease_name=disease)

		return Response(
			{
				"status": "success",
				"message": "Survey saved successfully",
				"data": {
					"survey_id": survey.id,
					"donor_id": donor.id,
					"bmi": round(bmi, 2),
					"is_eligible": survey.is_eligible,
				},
			},
			status=status.HTTP_201_CREATED,
		)


class DonorDashboardSummaryView(APIView):
	def get(self, request):
		donor_id = request.query_params.get("donor_id")
		donor_mobile = request.query_params.get("donor_mobile")

		donor = None
		if donor_id:
			donor = Donor.objects.filter(id=donor_id).first()
		elif donor_mobile:
			donor = Donor.objects.filter(mobile_number=donor_mobile).first()

		if not donor:
			return Response({"status": "error", "message": "Donor not found"}, status=status.HTTP_404_NOT_FOUND)

		donations = DonationRecord.objects.filter(donor=donor, donation_status="completed").order_by("-donation_date")
		total_donations = donations.count()
		last_donation = donations.first()
		
		# Prefer actual completed donations; fallback to donor's registration/provided last_donation_date.
		last_donation_date = last_donation.donation_date if last_donation else donor.last_donation_date
		
		current_date = timezone.now().date()
		days_ago = None
		if last_donation_date:
			# Handle potential datetime objects
			if hasattr(last_donation_date, 'date'):
				last_donation_date = last_donation_date.date()
			days_ago = max((current_date - last_donation_date).days, 0)
		
		# Eligibility: 120 days gap required for blood donation
		can_donate = True
		days_to_wait = 0
		if last_donation_date:
			days_since = days_ago
			if days_since < 120:
				can_donate = False
				days_to_wait = 120 - days_since

		# Check latest survey for health eligibility and validity (90 days)
		latest_survey = DonorSurvey.objects.filter(donor=donor).order_by("-submitted_at").first()
		
		survey_valid = True
		if latest_survey:
			survey_age = (timezone.now() - latest_survey.submitted_at).days
			if survey_age > 90:
				survey_valid = False
		else:
			survey_valid = False

		health_eligible = latest_survey.is_eligible if latest_survey and survey_valid else False

		# Overall eligibility includes donor status and survey validity
		overall_eligible = (can_donate and health_eligible and donor.status == 'active' and survey_valid)

		# Check for active requests/responses
		from requests_app.models import DonorResponse
		active_response = DonorResponse.objects.filter(
			donor=donor,
			is_active=True,
			response_status__in=["pending", "accepted"]
		).first()

		# Check for post-donation screening requirement
		# If last donation was within 7 days and status is donated/completed
		needs_post_donation_screening = False
		latest_screening = None
		if total_donations > 0 and days_ago is not None and days_ago <= 7:
			# Get the screening data from the latest successful response
			screening_response = DonorResponse.objects.filter(
				donor=donor,
				status__in=["donated", "completed"]
			).order_by("-updated_at").first()
			
			if screening_response:
				latest_screening = {
					"weight": screening_response.weight,
					"height": screening_response.height,
					"hospital_name": screening_response.blood_request.hospital.hospital_name if screening_response.blood_request.hospital else "N/A",
					"date": screening_response.updated_at.date()
				}
				# Logic to determine if they've already "acknowledged" this report
				# For now, let's assume we want them to see it at least once
				# We can use a simple flag in the response metadata if needed

		return Response({
			"status": "success",
			"data": {
				"first_name": donor.first_name,
				"last_name": donor.last_name,
				"total_donations": total_donations,
				"last_donation_date": last_donation_date,
				"days_ago": days_ago,
				"can_donate": overall_eligible,
				"days_to_wait": days_to_wait,
				"health_eligible": health_eligible,
				"survey_valid": survey_valid,
				"blood_group": donor.blood_group,
				"donor_status": donor.status,
				"status_reason": donor.status_reason,
				"has_active_request": active_response is not None,
				"active_request_status": active_response.status if active_response else None,
				"latest_screening": latest_screening
			}
		})


class DonorDonationHistoryView(APIView):
	def get(self, request):
		donor_id = request.query_params.get("donor_id")
		donor_mobile = request.query_params.get("donor_mobile")

		donor = None
		if donor_id:
			donor = Donor.objects.filter(id=donor_id).first()
		elif donor_mobile:
			donor = Donor.objects.filter(mobile_number=donor_mobile).first()

		if not donor:
			return Response({"status": "error", "message": "Donor not found"}, status=status.HTTP_404_NOT_FOUND)

		donations = DonationRecord.objects.filter(donor=donor).order_by("-donation_date")
		data = []
		for d in donations:
			data.append({
				"id": d.id,
				"hospital": d.hospital.hospital_name,
				"blood_group": d.blood_group,
				"component": d.component,
				"units": d.units_donated,
				"date": d.donation_date,
				"status": d.donation_status,
				"remarks": d.remarks
			})

		return Response({"status": "success", "data": data})
