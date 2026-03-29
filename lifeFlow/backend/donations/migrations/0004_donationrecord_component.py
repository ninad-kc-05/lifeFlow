from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0003_donationrecord_donor_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="donationrecord",
            name="component",
            field=models.CharField(
                choices=[
                    ("whole_blood", "Whole Blood"),
                    ("plasma", "Plasma"),
                    ("platelets", "Platelets"),
                ],
                default="whole_blood",
                max_length=20,
            ),
        ),
    ]
