from django.db import models

from users.models import Donor


class BloodInventory(models.Model):
    blood_group = models.CharField(
        max_length=5,
        choices=Donor.BLOOD_GROUP_CHOICES,
        unique=True,
    )
    units_available = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.blood_group} - {self.units_available} units"
