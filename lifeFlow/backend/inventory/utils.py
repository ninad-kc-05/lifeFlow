from .models import BloodInventory


def _validate_units(units):
    if units is None:
        raise ValueError("units is required")
    if units <= 0:
        raise ValueError("units must be greater than 0")


def increase_stock(
    blood_group,
    units,
    component_type="whole_blood",
    source_of_blood="donation",
    source_name="",
):
    _validate_units(units)

    inventory, _ = BloodInventory.objects.get_or_create(
        blood_group=blood_group,
        component_type=component_type,
        source_of_blood=source_of_blood,
        source_name=source_name,
        defaults={"units_available": 0},
    )
    inventory.units_available += units
    inventory.save()
    return inventory


def decrease_stock(blood_group, units, component_type=None, source_of_blood=None, source_name=None):
    _validate_units(units)

    queryset = BloodInventory.objects.filter(blood_group=blood_group)
    if component_type:
        queryset = queryset.filter(component_type=component_type)
    if source_of_blood:
        queryset = queryset.filter(source_of_blood=source_of_blood)
    if source_name:
        queryset = queryset.filter(source_name=source_name)

    records = list(queryset.order_by("-units_available", "last_updated"))
    if not records:
        raise ValueError("blood group/component does not exist in inventory")

    total_available = sum(item.units_available for item in records)
    if total_available < units:
        raise ValueError("insufficient stock")

    remaining = units
    for inventory in records:
        if remaining <= 0:
            break

        deduct = min(inventory.units_available, remaining)
        inventory.units_available -= deduct
        inventory.save(update_fields=["units_available", "last_updated"])
        remaining -= deduct

    return records[0]
