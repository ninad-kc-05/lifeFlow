import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from donations.models import DonorSurvey
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
def get_donor_profile(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Only GET method is allowed'}, status=405)

    donor_id = request.GET.get('donor_id')
    donor_mobile = request.GET.get('donor_mobile')

    donor = None
    if donor_id:
        donor = Donor.objects.filter(id=donor_id).first()
    elif donor_mobile:
        donor = Donor.objects.filter(mobile_number=donor_mobile).first()

    if not donor:
        return JsonResponse({'status': 'error', 'message': 'Donor not found'}, status=404)

    return JsonResponse({
        'status': 'success',
        'data': {
            'id': donor.id,
            'first_name': donor.first_name,
            'last_name': donor.last_name,
            'mobile_number': donor.mobile_number,
            'blood_group': donor.blood_group,
            'city': donor.city,
            'state': donor.state,
            'address_line': donor.address_line,
            'pincode': donor.pincode,
            'gender': donor.gender,
            'date_of_birth': donor.date_of_birth,
            'is_available': donor.is_available,
            'status': donor.status,
            'status_reason': donor.status_reason
        }
    })


@csrf_exempt
def update_donor_status(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        donor_id = data.get('donor_id')
        new_status = data.get('status')
        reason = data.get('reason', "")

        if not donor_id or not new_status:
            return JsonResponse({'status': 'error', 'message': 'donor_id and status are required'}, status=400)

        donor = Donor.objects.filter(id=donor_id).first()
        if not donor:
            return JsonResponse({'status': 'error', 'message': 'Donor not found'}, status=404)

        # Update status
        donor.status = new_status
        donor.status_reason = reason
        
        # Keep is_available and is_active synced for safety
        if new_status == 'active':
            donor.is_available = True
            donor.is_active = True
        else:
            donor.is_available = False
            # Only set is_active to False if it's 'inactive'
            if new_status == 'inactive':
                donor.is_active = False
            else:
                donor.is_active = True

        donor.save()
        return JsonResponse({'status': 'success', 'message': 'Status updated successfully', 'new_status': donor.status})

    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def update_donor_profile(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST method is allowed'}, status=405)

    try:
        data = json.loads(request.body)
        donor_id = data.get('donor_id')
        if not donor_id:
            return JsonResponse({'status': 'error', 'message': 'donor_id is required'}, status=400)

        donor = Donor.objects.filter(id=donor_id).first()
        if not donor:
            return JsonResponse({'status': 'error', 'message': 'Donor not found'}, status=404)

        # Update only allowed fields (excluding name and blood group as per user request)
        if 'city' in data: donor.city = data['city']
        if 'state' in data: donor.state = data['state']
        if 'address_line' in data: donor.address_line = data['address_line']
        if 'pincode' in data: donor.pincode = data['pincode']

        donor.save()
        return JsonResponse({'status': 'success', 'message': 'Profile updated successfully'})

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


@csrf_exempt
def admin_users_list(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Only GET method is allowed'}, status=405)

    try:
        donors = Donor.objects.all().order_by('-created_at')
        hospitals = Hospital.objects.all().order_by('-created_at')
        admins = Admin.objects.all().order_by('-created_at')

        donor_rows = [
            {
                'id': item.id,
                'name': f"{item.first_name} {item.last_name}".strip(),
                'role': 'Donor',
                'email': '-',
                'mobile_number': item.mobile_number,
                'city': item.city,
                'status': 'Active' if item.is_active else 'Inactive',
                'verified': bool(item.is_verified),
                'created_at': item.created_at.isoformat(),
            }
            for item in donors
        ]

        hospital_rows = [
            {
                'id': item.id,
                'name': item.hospital_name,
                'role': 'Hospital',
                'email': item.email or '-',
                'mobile_number': item.mobile_number,
                'city': item.city,
                'status': 'Active' if item.is_active else 'Inactive',
                'verified': bool(item.is_verified),
                'created_at': item.created_at.isoformat(),
            }
            for item in hospitals
        ]

        admin_rows = [
            {
                'id': item.id,
                'name': item.full_name,
                'role': 'Admin',
                'email': item.email,
                'mobile_number': item.mobile_number,
                'city': '-',
                'status': 'Active' if item.is_active else 'Inactive',
                'verified': True,
                'created_at': item.created_at.isoformat(),
            }
            for item in admins
        ]

        all_users = donor_rows + hospital_rows + admin_rows
        all_users.sort(key=lambda row: row['created_at'], reverse=True)

        return JsonResponse(
            {
                'status': 'success',
                'counts': {
                    'donors': len(donor_rows),
                    'hospitals': len(hospital_rows),
                    'admins': len(admin_rows),
                    'total': len(all_users),
                },
                'data': all_users,
            },
            status=200,
        )
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
def admin_dashboard_summary(request):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Only GET method is allowed'}, status=405)

    try:
        donor_total = Donor.objects.count()
        donor_survey_count = DonorSurvey.objects.values('donor_id').distinct().count()

        return JsonResponse(
            {
                'status': 'success',
                'data': {
                    'total_donors': donor_total,
                    'survey_donor_count': donor_survey_count,
                },
            },
            status=200,
        )
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
