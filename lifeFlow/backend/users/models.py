from django.db import models
from django.utils import timezone
from datetime import timedelta




class Donor(models.Model):

    # -------------------------
    # Choices
    # -------------------------
    GENDER_CHOICES = (
        ('Male', 'Male'),
        ('Female', 'Female'),
    )

    BLOOD_GROUP_CHOICES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )

    # -------------------------
    # Personal Details
    # -------------------------
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    mobile_number = models.CharField(max_length=15, unique=True)

    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES)

    # -------------------------
    # Address
    # -------------------------
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    # -------------------------
    # Donation Info
    # -------------------------
    last_donation_date = models.DateField(null=True, blank=True)

    # Latest computed/recorded health snapshot from donor survey.
    bmi = models.FloatField(null=True, blank=True)
    last_systolic_bp = models.IntegerField(null=True, blank=True)
    last_diastolic_bp = models.IntegerField(null=True, blank=True)
    last_pulse_rate = models.IntegerField(null=True, blank=True)
    last_temperature_c = models.FloatField(null=True, blank=True)
    last_screening_type = models.CharField(max_length=20, blank=True, default="")
    vitals_recorded_at = models.DateTimeField(null=True, blank=True)

    # -------------------------
    # Status
    # -------------------------
    is_available = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # -------------------------
    # Timestamps
    # -------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.blood_group})"
    
class Hospital(models.Model):
    hospital_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    contact_person_name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)

    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.hospital_name
    
class Admin(models.Model):

    

    full_name = models.CharField(max_length=150)
    mobile_number = models.CharField(max_length=15, unique=True)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name
    

