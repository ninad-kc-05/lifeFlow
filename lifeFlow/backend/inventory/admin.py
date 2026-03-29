from django.contrib import admin

from .models import BloodInventory


@admin.register(BloodInventory)
class BloodInventoryAdmin(admin.ModelAdmin):
    list_display = ("blood_group", "units_available", "last_updated")

# Register your models here.
