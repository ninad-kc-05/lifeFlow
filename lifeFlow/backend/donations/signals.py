from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from inventory.utils import increase_stock

from .models import DonationRecord


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
