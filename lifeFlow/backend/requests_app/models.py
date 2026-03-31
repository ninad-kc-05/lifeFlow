from django.db import models

class BloodRequest(models.Model):

    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('donor_needed', 'Donor Needed'),
        ('assigned', 'Assigned'),
        ('donor_accepted', 'Donor Accepted'),
        ('scheduled', 'Scheduled'),
        ('schedule_accepted', 'Schedule Accepted'),
        # Legacy compatibility
        ('allocated', 'Allocated'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    COMPONENT_CHOICES = [
        ('whole_blood', 'Whole Blood'),
        ('plasma', 'Plasma'),
        ('platelets', 'Platelets'),
    ]

    hospital = models.ForeignKey(
        'users.Hospital',
        on_delete=models.CASCADE,
        related_name='blood_requests'
    )

    patient_name = models.CharField(max_length=100)
    patient_age = models.PositiveIntegerField()

    blood_group = models.CharField(max_length=5)
    component_type = models.CharField(
        max_length=20,
        choices=COMPONENT_CHOICES,
        default='whole_blood'
    )
    units_required = models.PositiveIntegerField()

    urgency_level = models.CharField(
        max_length=10,
        choices=URGENCY_CHOICES,
        default='normal'
    )

    required_by_date = models.DateField()

    hospital_contact_number = models.CharField(max_length=15)

    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, blank=True, default="")
    special_note = models.TextField(blank=True, default="")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_name} - {self.blood_group}"

from django.db import models


class DonorResponse(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('testing', 'Testing'),
        ('accepted', 'Accepted'),
        ('scheduled', 'Scheduled'),
        ('schedule_accepted', 'Schedule Accepted'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('donated', 'Donated'),
        ('completed', 'Completed'),
    ]

    RESPONSE_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    donor = models.ForeignKey(
        'users.Donor',
        on_delete=models.CASCADE,
        related_name='responses'
    )

    blood_request = models.ForeignKey(
        'requests_app.BloodRequest',
        on_delete=models.CASCADE,
        related_name='donor_responses'
    )

    hospital = models.ForeignKey(
        'users.Hospital',
        on_delete=models.CASCADE,
        related_name='donor_responses',
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    remarks = models.TextField(
        blank=True,
        default=''
    )

    response_status = models.CharField(
        max_length=20,
        choices=RESPONSE_STATUS_CHOICES,
        default='pending'
    )

    response_message = models.TextField(
        blank=True,
        null=True
    )

    response_date = models.DateTimeField(
        auto_now_add=True
    )

    scheduled_date = models.DateField(
        null=True,
        blank=True
    )

    # Screening Data (Hospital Visit/Acceptance)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = ('donor', 'blood_request')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.donor} - {self.blood_request} ({self.response_status})"
