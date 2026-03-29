from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import BloodRequest
from .services import apply_stock_on_request_approval


@receiver(pre_save, sender=BloodRequest)
def decrease_inventory_on_approval(sender, instance, **kwargs):
    if getattr(instance, "_skip_stock_signal", False):
        return

    previous_status = None
    if instance.pk:
        previous_status = sender.objects.filter(pk=instance.pk).values_list(
            "status",
            flat=True,
        ).first()

    apply_stock_on_request_approval(instance, previous_status)
