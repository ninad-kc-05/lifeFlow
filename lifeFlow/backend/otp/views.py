from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from users.models import Admin, Hospital, Donor
from .utils import generate_email_otp, send_otp_email, generate_mobile_otp, send_otp_sms
from .models import EmailOTP, OTPVerification


# -------------------------
# Mobile OTP APIs (for Donor)
# -------------------------

@csrf_exempt
def request_mobile_otp(request):
    """
    POST /api/auth/request-mobile-otp/
    Request body: { "mobile_number": "..." }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    mobile_number = data.get('mobile_number', '').strip()

    if not mobile_number:
        return JsonResponse({'status': 'error', 'message': 'mobile_number is required'}, status=400)

    # Verify donor exists
    if not Donor.objects.filter(mobile_number=mobile_number).exists():
        print(f"[DEBUG] Donor not found for {mobile_number}")
        return JsonResponse({'status': 'error', 'message': 'Donor with this mobile number does not exist'}, status=404)

    print(f"[DEBUG] Donor found. Generating OTP...")

    # Generate OTP and save to DB
    otp = generate_mobile_otp(mobile_number)

    # Try to send via SMS gateway
    sms_sent = send_otp_sms(mobile_number, otp)

    if not sms_sent:
        print(f"[DEBUG] SMS failed but OTP {otp} is saved in DB for {mobile_number}")
        return JsonResponse({
            'status': 'success',
            'message': 'OTP generated but SMS delivery failed. Check server logs for OTP.',
            'sms_sent': False
        })

    print(f"[DEBUG] OTP sent successfully to {mobile_number}")
    return JsonResponse({'status': 'success', 'message': 'OTP sent successfully', 'sms_sent': True})


@csrf_exempt
def verify_mobile_otp(request):
    """
    POST /api/auth/verify-mobile-otp/
    Request body: { "mobile_number": "...", "otp": "123456" }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    mobile_number = data.get('mobile_number', '').strip()
    otp = data.get('otp', '').strip()

    if not mobile_number or not otp:
        return JsonResponse({'status': 'error', 'message': 'mobile_number and otp are required'}, status=400)

    # Fetch latest OTP record for this number
    try:
        otp_record = OTPVerification.objects.filter(mobile_number=mobile_number).latest('created_at')
    except OTPVerification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    if otp_record.is_expired():
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    if otp_record.otp_code != otp:
        return JsonResponse({'status': 'error', 'message': 'Invalid or expired OTP'}, status=400)

    # Mark as verified
    otp_record.is_verified = True
    otp_record.save()

    return JsonResponse({'status': 'success', 'message': 'OTP verified successfully'})


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

    response_payload = {
        'status': 'success',
        'message': 'OTP verified successfully',
        'user_type': otp_record.user_type,
    }

    if otp_record.user_type == 'hospital':
        hospital = Hospital.objects.filter(email=email).first()
        response_payload['hospital_id'] = hospital.id if hospital else None
    elif otp_record.user_type == 'admin':
        admin_user = Admin.objects.filter(email=email).first()
        response_payload['admin_id'] = admin_user.id if admin_user else None

    return JsonResponse(response_payload)
