from django.db import models


class DonationRecord(models.Model):
    DONATION_STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    donor = models.ForeignKey(
        'users.Donor',
        on_delete=models.CASCADE,
        related_name='donations'
    )

    hospital = models.ForeignKey(
        'users.Hospital',               #user.   is added
        on_delete=models.CASCADE,
        related_name='donations'
    )

    blood_request = models.ForeignKey(
        'requests_app.BloodRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='donations'
    )

    blood_group = models.CharField(max_length=5)
    units_donated = models.PositiveIntegerField()
    donation_date = models.DateField()

    donation_status = models.CharField(
        max_length=20,
        choices=DONATION_STATUS_CHOICES,
        default='scheduled'
    )

    remarks = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.donor} - {self.donation_date}"
    
    
    # donations/models.py

from users.models import Donor

class DonorSurvey(models.Model):

    SCREENING_TYPE = (
        ('Hospital', 'Hospital'),
        ('Camp', 'Camp'),
    )

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="surveys")

    screening_type = models.CharField(max_length=20, choices=SCREENING_TYPE)

    # Physical Examination
    weight_kg = models.FloatField()
    height_cm = models.FloatField()
    systolic_bp = models.IntegerField()
    diastolic_bp = models.IntegerField()
    temperature_c = models.FloatField()
    pulse_rate = models.IntegerField()
    hemoglobin = models.FloatField(null=True, blank=True)

    # Medication
    is_on_medication = models.BooleanField(default=False)
    medication_details = models.TextField(null=True, blank=True)

    # Fever / Infection
    had_recent_fever = models.BooleanField(default=False)
    fever_details = models.TextField(null=True, blank=True)

    # Recent Donation
    donated_last_3_months = models.BooleanField(default=False)
    recent_donation_details = models.TextField(null=True, blank=True)

    # Chronic Illness (Camp Screening)
    has_chronic_illness = models.BooleanField(default=False)
    chronic_illness_details = models.TextField(null=True, blank=True)

    # Male Section
    used_steroids = models.BooleanField(null=True, blank=True)
    steroid_details = models.TextField(null=True, blank=True)

    had_major_surgery = models.BooleanField(null=True, blank=True)
    surgery_details = models.TextField(null=True, blank=True)

    # Female Section
    is_pregnant = models.BooleanField(null=True, blank=True)
    is_breastfeeding = models.BooleanField(null=True, blank=True)
    has_heavy_menstruation = models.BooleanField(null=True, blank=True)
    recent_delivery_or_miscarriage = models.BooleanField(null=True, blank=True)
    female_additional_details = models.TextField(null=True, blank=True)

    # Final Decision
    is_eligible = models.BooleanField(default=False)
    review_notes = models.TextField(null=True, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Survey - {self.donor.first_name} ({self.submitted_at.date()})"
    
    # donations/models.py

class SurveyDisease(models.Model):

    DISEASE_CHOICES = (
        ('Diabetes', 'Diabetes'),
        ('Heart Disease', 'Heart Disease'),
        ('Cancer', 'Cancer'),
        ('Tuberculosis', 'Tuberculosis'),
        ('Hepatitis', 'Hepatitis'),
        ('HIV', 'HIV'),
        ('None', 'None'),
    )

    survey = models.ForeignKey(
        DonorSurvey,
        on_delete=models.CASCADE,
        related_name="diseases"
    )

    disease_name = models.CharField(max_length=50, choices=DISEASE_CHOICES)

    def __str__(self):
        return f"{self.disease_name} - {self.survey.donor.first_name}"