import random
import smtplib
import logging
from email.message import EmailMessage
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import EmailOTP, OTPVerification

logger = logging.getLogger(__name__)


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


# -------------------------
# Mobile OTP Helpers
# -------------------------

def generate_mobile_otp(mobile_number):
    """
    Generate a 6-digit OTP for mobile verification.
    Invalidates all previous OTPs for the same number.
    """
    print(f"[DEBUG] generate_mobile_otp called for {mobile_number}")

    deleted, _ = OTPVerification.objects.filter(mobile_number=mobile_number).delete()
    print(f"[DEBUG] Deleted {deleted} old OTP records")

    otp_code = str(random.randint(100000, 999999))
    print(f"[DEBUG] Generated OTP: {otp_code}")

    record = OTPVerification.objects.create(
        mobile_number=mobile_number,
        otp_code=otp_code,
        user_type='donor',
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    print(f"[DEBUG] OTP saved to DB with id={record.id}")

    return otp_code


def send_otp_sms(phone, otp):
    """
    Send OTP to user's phone via SMS gateway.
    Returns True if sent successfully, False otherwise.
    """
    gateway_url = settings.SMS_GATEWAY_URL
    gateway_token = settings.SMS_GATEWAY_TOKEN

    print(f"[DEBUG] SMS_GATEWAY_URL = {gateway_url}")
    print(f"[DEBUG] SMS_GATEWAY_TOKEN = {'set' if gateway_token else 'NOT SET'}")
    print(f"[DEBUG] Sending OTP {otp} to {phone}")

    if not gateway_url:
        print("[LifeFlow ERROR] SMS_GATEWAY_URL is not configured in .env")
        return False

    message = (
        f"Dear Donor,\n\n"
        f"You are attempting to log in to the Blood Donation Management System.\n"
        f"Your One-Time \nPassword (OTP) is: {otp}.\n"
        f"This OTP is valid for 5 minutes.Please do not share this code with anyone.\n\n"
        f"- BDMS Team"
    )

    payload = {
        "to": phone,
        "message": message
    }

    headers = {}
    if gateway_token:
        headers["Authorization"] = gateway_token

    print(f"[DEBUG] Payload: {payload}")
    print(f"[DEBUG] POSTing to {gateway_url} ...")

    try:
        response = requests.post(gateway_url, json=payload, headers=headers, timeout=10)
        print(f"[DEBUG] Gateway response status: {response.status_code}")
        print(f"[DEBUG] Gateway response body: {response.text}")
        if response.ok:
            print("[DEBUG] SMS sent successfully!")
            return True
        print(f"[LifeFlow ERROR] SMS gateway returned {response.status_code}: {response.text}")
        return False
    except requests.RequestException as e:
        print(f"[LifeFlow ERROR] SMS gateway unreachable: {e}")
        return False
