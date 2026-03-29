from django.db import models

from users.models import Donor


class BloodInventory(models.Model):
    COMPONENT_CHOICES = [
        ("whole_blood", "Whole Blood"),
        ("plasma", "Plasma"),
        ("platelets", "Platelets"),
    ]

    SOURCE_CHOICES = [
        ("donation", "Donation"),
        ("receiver_recovery", "Receiver Recovery Return"),
        ("camp", "Camp"),
    ]

    blood_group = models.CharField(
        max_length=5,
        choices=Donor.BLOOD_GROUP_CHOICES,
    )
    component_type = models.CharField(
        max_length=20,
        choices=COMPONENT_CHOICES,
        default="whole_blood",
    )
    source_of_blood = models.CharField(
        max_length=30,
        choices=SOURCE_CHOICES,
        default="donation",
    )
    source_name = models.CharField(max_length=255, blank=True, default="")
    units_available = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("blood_group", "component_type", "source_of_blood", "source_name")
        ordering = ["blood_group", "component_type", "source_of_blood", "source_name"]

    def __str__(self):
        return f"{self.blood_group} | {self.component_type} | {self.source_of_blood} | {self.source_name} - {self.units_available} units"
