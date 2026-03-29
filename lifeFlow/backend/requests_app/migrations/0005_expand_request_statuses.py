from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0004_bloodrequest_pincode"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bloodrequest",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                    ("donor_needed", "Donor Needed"),
                    ("allocated", "Allocated"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
