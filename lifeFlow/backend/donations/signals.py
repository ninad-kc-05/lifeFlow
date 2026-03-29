from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from inventory.utils import increase_stock

from .models import DonationRecord, DonorSurvey


@receiver(pre_save, sender=DonationRecord)
def capture_previous_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_donation_status = None
        return

    previous = sender.objects.filter(pk=instance.pk).values_list(
        "donation_status",
        flat=True,
    ).first()
    instance._previous_donation_status = previous


@receiver(post_save, sender=DonationRecord)
def update_inventory_on_completed_donation(sender, instance, created, **kwargs):
    is_completed = instance.donation_status == "completed"
    was_completed = getattr(instance, "_previous_donation_status", None) == "completed"

    if is_completed and (created or not was_completed):
        increase_stock(instance.blood_group, instance.units_donated)


@receiver(post_save, sender=DonorSurvey)
def sync_donor_health_snapshot(sender, instance, **kwargs):
    donor = instance.donor

    bmi = None
    try:
        height_m = float(instance.height_cm) / 100.0
        weight = float(instance.weight_kg)
        if height_m > 0:
            bmi = round(weight / (height_m * height_m), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        bmi = None

    donor.bmi = bmi
    donor.last_systolic_bp = instance.systolic_bp
    donor.last_diastolic_bp = instance.diastolic_bp
    donor.last_pulse_rate = instance.pulse_rate
    donor.last_temperature_c = instance.temperature_c
    donor.last_screening_type = instance.screening_type or ""
    donor.vitals_recorded_at = instance.submitted_at
    donor.save(
        update_fields=[
            "bmi",
            "last_systolic_bp",
            "last_diastolic_bp",
            "last_pulse_rate",
            "last_temperature_c",
            "last_screening_type",
            "vitals_recorded_at",
            "updated_at",
        ]
    )
