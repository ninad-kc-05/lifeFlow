from django.core.exceptions import ValidationError

from inventory.utils import decrease_stock


def apply_stock_on_request_approval(blood_request, previous_status):
    should_decrease = (
        blood_request.status == "approved"
        and previous_status != "approved"
    )
    if not should_decrease:
        return

    try:
        decrease_stock(blood_request.blood_group, blood_request.units_required)
    except ValueError as exc:
        raise ValidationError({"status": str(exc)}) from exc
