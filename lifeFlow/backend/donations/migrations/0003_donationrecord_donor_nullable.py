from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0002_donorsurvey_surveydisease"),
    ]

    operations = [
        migrations.AlterField(
            model_name="donationrecord",
            name="donor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="donations",
                to="users.donor",
            ),
        ),
    ]
