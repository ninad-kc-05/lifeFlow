from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import requests

from users.models import Admin, Hospital
from .utils import generate_email_otp, send_otp_email
from .models import EmailOTP


# -------------------------
# Existing SMS API (for Donor mobile OTP)
# -------------------------
@csrf_exempt
def sms_api(request):
    if request.method == "POST":
        data = json.loads(request.body)

        phone = data.get("to")
        message = data.get("message")

        print("Sending to phone gateway...")

        gateway_url = "http://10.142.117.231:8082/"

        payload = {
            "to": phone,
            "message": message
        }

        response = requests.post(gateway_url, json=payload)

        print("Phone response:", response.text)

        return JsonResponse({
            "status": "Sent to phone",
            "phone_response": response.text
        })

    return JsonResponse({"message": "Server running"})


# -------------------------
# Email OTP APIs (for Admin & Hospital)
# -------------------------

@csrf_exempt
def request_email_otp(request):
    """
    POST /api/auth/request-email-otp/
    Request body: { "email": "...", "user_type": "admin" | "hospital" }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip()
    user_type = data.get('user_type', '').strip().lower()

    if not email or not user_type:
        return JsonResponse({'status': 'error', 'message': 'Email and user_type are required'}, status=400)

    if user_type not in ['admin', 'hospital']:
        return JsonResponse({'status': 'error', 'message': 'Invalid user_type. Must be admin or hospital'}, status=400)

    # Verify email exists in the respective model
    if user_type == 'admin':
        if not Admin.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Admin with this email does not exist'}, status=404)
    elif user_type == 'hospital':
        if not Hospital.objects.filter(email=email).exists():
            return JsonResponse({'status': 'error', 'message': 'Hospital with this email does not exist'}, status=404)

    # Generate and send OTP
    otp = generate_email_otp(email, user_type)
    email_sent = send_otp_email(email, otp)

    if not email_sent:
        return JsonResponse({'status': 'error', 'message': 'Failed to send OTP email. Please try again.'}, status=500)

    return JsonResponse({'status': 'success', 'message': 'OTP sent successfully'})


@csrf_exempt
def verify_email_otp(request):
    """
    POST /api/auth/verify-email-otp/
    Request body: { "email": "...", "otp": "123456" }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    email = data.get('email', '').strip()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return JsonResponse({'status': 'error', 'message': 'Email and OTP are required'}, status=400)

    # Fetch latest OTP record for this email
    try:
        otp_record = EmailOTP.objects.filter(email=email).latest('created_at')
    except EmailOTP.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    # Check if OTP is expired
    if otp_record.is_expired():
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    # Compare OTP
    if otp_record.otp_code != otp:
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    # Mark as verified
    otp_record.is_verified = True
    otp_record.save()

    return JsonResponse({'status': 'success', 'message': 'OTP verified successfully'})
