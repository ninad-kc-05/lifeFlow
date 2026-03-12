from datetime import timedelta

from django.db import models
from django.utils import timezone


# -------------------------
# Mobile OTP Model (Existing - for Donor)
# -------------------------
class OTPVerification(models.Model):

    USER_TYPE_CHOICES = [
        ('donor', 'Donor'),
        ('hospital', 'Hospital'),
        ('admin', 'Admin'),
    ]

    mobile_number = models.CharField(max_length=15)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto set expiry time (5 minutes)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.mobile_number} - {self.user_type}"


# -------------------------
# Email OTP Model (for Admin & Hospital)
# -------------------------
class EmailOTP(models.Model):

    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('hospital', 'Hospital'),
    ]

    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - {self.user_type}"
