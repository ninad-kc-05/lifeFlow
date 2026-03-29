from .models import BloodInventory


def _validate_units(units):
    if units is None:
        raise ValueError("units is required")
    if units <= 0:
        raise ValueError("units must be greater than 0")


def increase_stock(blood_group, units):
    _validate_units(units)

    inventory, _ = BloodInventory.objects.get_or_create(
        blood_group=blood_group,
        defaults={"units_available": 0},
    )
    inventory.units_available += units
    inventory.save()
    return inventory


def decrease_stock(blood_group, units):
    _validate_units(units)

    try:
        inventory = BloodInventory.objects.get(blood_group=blood_group)
    except BloodInventory.DoesNotExist as exc:
        raise ValueError("blood group does not exist in inventory") from exc

    if inventory.units_available < units:
        raise ValueError("insufficient stock")

    inventory.units_available -= units
    inventory.save()
    return inventory
