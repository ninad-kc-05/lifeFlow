import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Donor, Hospital, Admin


@csrf_exempt
def register_donor(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)

        # Required fields validation
        required_fields = [
            'first_name', 'last_name', 'mobile_number', 'date_of_birth',
            'gender', 'blood_group', 'address_line', 'city', 'state', 'pincode'
        ]
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'status': 'error', 'message': f'{field} is required'}, status=400)

        # Duplicate mobile number check
        if Donor.objects.filter(mobile_number=data['mobile_number']).exists():
            return JsonResponse({'status': 'error', 'message': 'Mobile number already exists'}, status=400)

        Donor.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            mobile_number=data['mobile_number'],
            date_of_birth=data['date_of_birth'],
            gender=data['gender'],
            blood_group=data['blood_group'],
            address_line=data['address_line'],
            city=data['city'],
            state=data['state'],
            pincode=data['pincode'],
            last_donation_date=data.get('last_donation_date') or None,
            is_available=True,
            is_verified=False,
            is_active=True,
        )

        return JsonResponse({'status': 'success', 'message': 'Donor registered successfully'}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def register_hospital(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)

        required_fields = [
            'hospital_name', 'license_number', 'contact_person_name',
            'mobile_number', 'email', 'address_line', 'city', 'state', 'pincode'
        ]
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'status': 'error', 'message': f'{field} is required'}, status=400)

        if Hospital.objects.filter(license_number=data['license_number']).exists():
            return JsonResponse({'status': 'error', 'message': 'License number already exists'}, status=400)

        if Hospital.objects.filter(mobile_number=data['mobile_number']).exists():
            return JsonResponse({'status': 'error', 'message': 'Mobile number already exists'}, status=400)

        Hospital.objects.create(
            hospital_name=data['hospital_name'],
            license_number=data['license_number'],
            contact_person_name=data['contact_person_name'],
            mobile_number=data['mobile_number'],
            email=data['email'],
            address_line=data['address_line'],
            city=data['city'],
            state=data['state'],
            pincode=data['pincode'],
            is_verified=False,
            is_active=True,
        )

        return JsonResponse({'status': 'success', 'message': 'Hospital registered successfully'}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def register_admin(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)

        required_fields = ['full_name', 'mobile_number', 'email']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'status': 'error', 'message': f'{field} is required'}, status=400)

        if Admin.objects.filter(mobile_number=data['mobile_number']).exists():
            return JsonResponse({'status': 'error', 'message': 'Mobile number already exists'}, status=400)

        if Admin.objects.filter(email=data['email']).exists():
            return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)

        Admin.objects.create(
            full_name=data['full_name'],
            mobile_number=data['mobile_number'],
            email=data['email'],
            is_active=True,
        )

        return JsonResponse({'status': 'success', 'message': 'Admin registered successfully'}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
