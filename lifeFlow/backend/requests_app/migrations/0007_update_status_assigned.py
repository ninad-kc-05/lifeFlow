from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0006_bloodrequest_special_note"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bloodrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("rejected", "Rejected"),
                    ("donor_needed", "Donor Needed"),
                    ("assigned", "Assigned"),
                    ("allocated", "Allocated"),
                    ("approved", "Approved"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
