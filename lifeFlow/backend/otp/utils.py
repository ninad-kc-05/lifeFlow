import random
import smtplib
from email.message import EmailMessage
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import EmailOTP


def generate_email_otp(email, user_type):
    """
    Generate a 6-digit OTP for email verification.
    Invalidates all previous OTPs for the same email.
    """
    # Delete all previous OTPs for this email (only latest should be valid)
    EmailOTP.objects.filter(email=email).delete()

    # Generate random 6-digit OTP
    otp_code = str(random.randint(100000, 999999))

    # Create new OTP record
    EmailOTP.objects.create(
        email=email,
        otp_code=otp_code,
        user_type=user_type,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    return otp_code


def send_otp_email(email, otp):
    """
    Send OTP to user's email using Gmail SMTP.
    """
    sender_email = settings.EMAIL_HOST_USER
    sender_password = settings.EMAIL_HOST_PASSWORD

    msg = EmailMessage()
    msg['Subject'] = 'LifeFlow Login OTP Verification'
    msg['From'] = sender_email
    msg['To'] = email
    msg.set_content(
        f"Dear User,\n\n"
        f"You are attempting to log in to the LifeFlow Blood Donation Management System.\n\n"
        f"Your One-Time Password (OTP) is: {otp}\n\n"
        f"This OTP is valid for 5 minutes.\n\n"
        f"Please do not share this OTP with anyone.\n\n"
        f"LifeFlow Team"
    )

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[LifeFlow] Email sending failed: {e}")
        return False
