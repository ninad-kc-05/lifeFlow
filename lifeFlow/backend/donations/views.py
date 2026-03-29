from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Donor

from .models import DonorSurvey, SurveyDisease


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
