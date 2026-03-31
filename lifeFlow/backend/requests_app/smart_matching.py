from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from donations.models import DonationRecord, DonorSurvey
from users.models import Donor

from .models import BloodRequest, DonorResponse


@dataclass
class DonorProfile:
    donor: Donor
    bmi: float
    weight: float
    age: int


def _normalize_component(component: str) -> str:
    return str(component or "whole_blood").strip().lower()


def _split_group(blood_group: str):
    group = str(blood_group or "").strip().upper()
    if not group:
        return "", "+"
    # Handle cases like "O POSITIVE" or "O+"
    if "POS" in group: return group.split(" ")[0], "+"
    if "NEG" in group: return group.split(" ")[0], "-"
    if group[-1] in ["+", "-"]:
        return group[:-1], group[-1]
    return group, "+"


def _age_from_dob(date_of_birth):
    if not date_of_birth:
        return 0
    today = timezone.now().date()
    years = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        years -= 1
    return max(years, 0)


def _latest_survey(donor: Donor):
    return DonorSurvey.objects.filter(donor=donor).order_by("-submitted_at").first()


def _has_recent_vitals(donor: Donor):
    return all(
        value is not None
        for value in [
            donor.last_systolic_bp,
            donor.last_diastolic_bp,
            donor.last_pulse_rate,
            donor.last_temperature_c,
        ]
    )


def _profile_for_donor(donor: Donor):
    # Try to get BMI directly from donor first (it's saved there after survey)
    if donor.bmi is not None:
        age = _age_from_dob(donor.date_of_birth)
        return DonorProfile(donor=donor, bmi=float(donor.bmi), weight=55.0, age=age) # Default weight if only BMI exists

    survey = _latest_survey(donor)
    if not survey or not survey.weight_kg or not survey.height_cm:
        return None

    height_m = float(survey.height_cm) / 100.0
    if height_m <= 0:
        return None

    weight = float(survey.weight_kg)
    bmi = weight / (height_m * height_m)
    age = _age_from_dob(donor.date_of_birth)
    return DonorProfile(donor=donor, bmi=bmi, weight=weight, age=age)


def is_compatible(donor_group, recipient_group, component):
    component_key = _normalize_component(component)
    donor_abo, donor_rh = _split_group(donor_group)
    recipient_abo, recipient_rh = _split_group(recipient_group)

    if component_key == "whole_blood":
        whole_blood_compatibility = {
            "O": {"O", "A", "B", "AB"},
            "A": {"A", "AB"},
            "B": {"B", "AB"},
            "AB": {"AB"},
        }
        abo_ok = recipient_abo in whole_blood_compatibility.get(donor_abo, set())
        rh_ok = recipient_rh == "+" or donor_rh == "-"
        return abo_ok and rh_ok

    # Plasma and platelets: ABO-only compatibility, AB as universal donor.
    plasma_like_compatibility = {
        "AB": {"O", "A", "B", "AB"},
        "A": {"O", "A"},
        "B": {"O", "B"},
        "O": {"O"},
    }
    return recipient_abo in plasma_like_compatibility.get(donor_abo, set())


def is_eligible(donor):
    profile = _profile_for_donor(donor)
    # If no profile (no survey/BMI), we'll still allow matching but with lower score
    # if profile is None:
    #     return False, "missing survey height/weight"

    # Only 'active' status is eligible for matching
    if donor.status != 'active':
        return False, f"donor status is {donor.status}"

    if not donor.is_available:
        return False, "donor unavailable"

    if not donor.is_active:
        return False, "donor inactive"

    # if not donor.is_verified:
    #     return False, "donor not verified"

    age = _age_from_dob(donor.date_of_birth)
    if age < 18 or age > 65:
        return False, "age out of range"

    if profile:
        if profile.weight < 50:
            return False, "weight below minimum"

        if profile.bmi < 18.5 or profile.bmi > 29.9:
            return False, "bmi out of range"

    if donor.last_donation_date:
        days_since = (timezone.now().date() - donor.last_donation_date).days
        if days_since < 120:
            return False, f"donated recently ({days_since} days ago)"

    return True, "all eligibility rules passed"


def calculate_score(donor, blood_request):
    profile = _profile_for_donor(donor)
    # score = 0 if profile is None else 0 # Start at 0
    
    score = 0

    if str(donor.blood_group or "").upper() == str(blood_request.blood_group or "").upper():
        score += 40
    elif is_compatible(donor.blood_group, blood_request.blood_group, blood_request.component_type):
        score += 25
    else:
        return 0

    if str(donor.pincode or "").strip() and str(donor.pincode).strip() == str(blood_request.pincode or "").strip():
        score += 30
    elif str(donor.city or "").strip().lower() == str(blood_request.city or "").strip().lower():
        score += 20

    if profile:
        if 18.5 <= profile.bmi <= 24.9:
            score += 20
        elif 25.0 <= profile.bmi <= 29.9:
            score += 10

    if donor.last_donation_date:
        days_since = (timezone.now().date() - donor.last_donation_date).days
        if days_since > 180:
            score += 15
        elif days_since >= 120:
            score += 10
    else:
        # Never donated donors get the availability freshness bonus.
        score += 10

    # Slightly prioritize donors with recent vitals/BP history for comparison.
    if _has_recent_vitals(donor):
        score += 5

    # Slight preference to hospital-screened donors due richer screening packet.
    screening_type = str(donor.last_screening_type or "").strip().lower()
    if screening_type == "hospital":
        score += 3
    elif screening_type == "camp":
        score += 1

    return score


def match_donors(request_id):
    blood_request = BloodRequest.objects.select_related("hospital").get(id=request_id)
    donors = Donor.objects.filter(is_active=True)

    matches = []
    for donor in donors:
        # Debugging donor matching
        print(f"[DEBUG] Matching donor {donor.id} ({donor.blood_group}) in {donor.city}/{donor.pincode}")
        
        same_pincode = str(donor.pincode or "").strip() == str(blood_request.pincode or "").strip()
        same_city = str(donor.city or "").strip().lower() == str(blood_request.city or "").strip().lower()

        # Location filter is mandatory: first same pincode, otherwise same city.
        if not same_pincode and not same_city:
            print(f"[DEBUG] Donor {donor.id} failed location check")
            continue

        if not is_compatible(donor.blood_group, blood_request.blood_group, blood_request.component_type):
            print(f"[DEBUG] Donor {donor.id} failed compatibility check")
            continue

        eligible, reason = is_eligible(donor)
        if not eligible:
            print(f"[DEBUG] Donor {donor.id} failed eligibility: {reason}")
            continue

        score = calculate_score(donor, blood_request)
        if score <= 0:
            print(f"[DEBUG] Donor {donor.id} score is 0")
            continue

        profile = _profile_for_donor(donor)
        matches.append(
            {
                "donor": donor,
                "score": score,
                "bmi": round(profile.bmi, 2) if profile else "N/A",
                "age": _age_from_dob(donor.date_of_birth),
                "weight": profile.weight if profile else "N/A",
                "location_priority": (
                    "pincode"
                    if str(donor.pincode or "").strip() == str(blood_request.pincode or "").strip()
                    else "city"
                ),
                "eligibility_reason": reason,
            }
        )

    matches.sort(
        key=lambda row: (
            1 if row["location_priority"] == "pincode" else 0,
            row["score"],
            -row["donor"].id,
        ),
        reverse=True,
    )
    return matches


@transaction.atomic
def assign_top_donors(request_id):
    blood_request = BloodRequest.objects.select_related("hospital").get(id=request_id)
    matches = match_donors(request_id)
    top_matches = matches[:3]

    DonorResponse.objects.filter(blood_request=blood_request, status="testing").update(
        status="rejected",
        response_status="declined",
        is_active=False,
        remarks="Replaced by new shortlist",
    )

    assigned = []
    for row in top_matches:
        donor = row["donor"]
        response, _ = DonorResponse.objects.get_or_create(
            donor=donor,
            blood_request=blood_request,
            defaults={
                "hospital": blood_request.hospital,
                "status": "testing",
                "response_status": "pending",
                "is_active": True,
                "remarks": "Shortlisted for hospital testing (1-2 day buffer)",
                "response_message": "Shortlisted for hospital testing",
            },
        )
        response.hospital = blood_request.hospital
        response.status = "testing"
        response.response_status = "pending"
        response.is_active = True
        response.remarks = "Shortlisted for hospital testing (1-2 day buffer)"
        response.response_message = "Shortlisted for hospital testing"
        response.save(
            update_fields=[
                "hospital",
                "status",
                "response_status",
                "is_active",
                "remarks",
                "response_message",
                "updated_at",
            ]
        )

        donor.is_available = False
        donor.save(update_fields=["is_available", "updated_at"])

        assigned.append(
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
                "status": "testing",
            }
        )

    if assigned:
        blood_request.status = "assigned"
    else:
        blood_request.status = "donor_needed"
    blood_request.save(update_fields=["status", "updated_at"])

    return {
        "request_id": blood_request.id,
        "request_status": blood_request.status,
        "shortlisted_count": len(assigned),
        "shortlisted_donors": assigned,
    }


@transaction.atomic
def hospital_select_donor(donor_response_id):
    response = DonorResponse.objects.select_related("donor", "blood_request", "blood_request__hospital").get(
        id=donor_response_id
    )
    blood_request = response.blood_request

    if response.status not in ["testing", "selected"]:
        raise ValueError("Only testing/selected donors can be chosen")

    selected_donor = response.donor

    response.status = "selected"
    response.response_status = "accepted"
    response.is_active = True
    response.remarks = "Selected by hospital after testing"
    response.response_message = "Selected by hospital"
    response.hospital = blood_request.hospital
    response.save(
        update_fields=[
            "status",
            "response_status",
            "is_active",
            "remarks",
            "response_message",
            "hospital",
            "updated_at",
        ]
    )

    alternatives = DonorResponse.objects.filter(
        blood_request=blood_request,
        status="testing",
    ).exclude(id=response.id).select_related("donor")

    for alt in alternatives:
        alt.status = "rejected"
        alt.response_status = "declined"
        alt.is_active = False
        alt.remarks = "Not selected after hospital testing"
        alt.response_message = "Not selected"
        alt.save(
            update_fields=["status", "response_status", "is_active", "remarks", "response_message", "updated_at"]
        )
        alt.donor.is_available = True
        alt.donor.save(update_fields=["is_available", "updated_at"])

    blood_request.status = "assigned"
    blood_request.save(update_fields=["status", "updated_at"])

    return {
        "request_id": blood_request.id,
        "selected_donor": {
            "donor_id": selected_donor.id,
            "name": f"{selected_donor.first_name} {selected_donor.last_name}".strip(),
            "blood_group": selected_donor.blood_group,
            "status": "selected",
        },
    }


@transaction.atomic
def complete_donation(request_id, donor_id):
    blood_request = BloodRequest.objects.select_related("hospital").get(id=request_id)
    donor = Donor.objects.get(id=donor_id)

    response = DonorResponse.objects.filter(
        blood_request=blood_request,
        donor=donor,
    ).first()

    if not response:
        raise ValueError("No donor response found for this request/donor")

    response.status = "completed"
    response.response_status = "accepted"
    response.is_active = False
    response.remarks = "Donation completed"
    response.response_message = "Donation completed"
    response.hospital = blood_request.hospital
    response.save(
        update_fields=[
            "status",
            "response_status",
            "is_active",
            "remarks",
            "response_message",
            "hospital",
            "updated_at",
        ]
    )

    donation_date = timezone.now().date()
    DonationRecord.objects.create(
        donor=donor,
        hospital=blood_request.hospital,
        blood_request=blood_request,
        blood_group=blood_request.blood_group,
        component=blood_request.component_type,
        units_donated=blood_request.units_required,
        donation_date=donation_date,
        donation_status="completed",
        remarks="Donation completed via smart donor matching",
    )

    donor.last_donation_date = donation_date
    donor.is_available = False
    donor.save(update_fields=["last_donation_date", "is_available", "updated_at"])

    blood_request.status = "completed"
    blood_request.save(update_fields=["status", "updated_at"])

    # Any remaining shortlisted donors become available again.
    others = DonorResponse.objects.filter(blood_request=blood_request).exclude(donor=donor).select_related("donor")
    for other in others:
        if other.status in ["testing", "selected"]:
            other.status = "rejected"
            other.response_status = "declined"
            other.is_active = False
            other.remarks = "Donation completed by another shortlisted donor"
            other.response_message = "Released"
            other.save(
                update_fields=["status", "response_status", "is_active", "remarks", "response_message", "updated_at"]
            )
            other.donor.is_available = True
            other.donor.save(update_fields=["is_available", "updated_at"])

    return {
        "request_id": blood_request.id,
        "donor_id": donor.id,
        "status": "completed",
        "donation_date": str(donation_date),
    }
