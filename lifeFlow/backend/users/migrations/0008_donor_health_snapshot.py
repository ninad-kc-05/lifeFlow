from django.db import migrations, models


def backfill_donor_health_snapshot(apps, schema_editor):
    Donor = apps.get_model("users", "Donor")
    DonorSurvey = apps.get_model("donations", "DonorSurvey")

    seen = set()
    latest_surveys = DonorSurvey.objects.order_by("donor_id", "-submitted_at")

    for survey in latest_surveys:
        donor_id = survey.donor_id
        if donor_id in seen:
            continue
        seen.add(donor_id)

        donor = Donor.objects.filter(id=donor_id).first()
        if not donor:
            continue

        bmi = None
        try:
            height_m = float(survey.height_cm) / 100.0
            weight = float(survey.weight_kg)
            if height_m > 0:
                bmi = round(weight / (height_m * height_m), 2)
        except (TypeError, ValueError, ZeroDivisionError):
            bmi = None

        donor.bmi = bmi
        donor.last_systolic_bp = survey.systolic_bp
        donor.last_diastolic_bp = survey.diastolic_bp
        donor.last_pulse_rate = survey.pulse_rate
        donor.last_temperature_c = survey.temperature_c
        donor.last_screening_type = survey.screening_type or ""
        donor.vitals_recorded_at = survey.submitted_at
        donor.save(
            update_fields=[
                "bmi",
                "last_systolic_bp",
                "last_diastolic_bp",
                "last_pulse_rate",
                "last_temperature_c",
                "last_screening_type",
                "vitals_recorded_at",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("donations", "0004_donationrecord_component"),
        ("users", "0007_remove_admin_role_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="donor",
            name="bmi",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donor",
            name="last_diastolic_bp",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donor",
            name="last_pulse_rate",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donor",
            name="last_screening_type",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="donor",
            name="last_systolic_bp",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donor",
            name="last_temperature_c",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="donor",
            name="vitals_recorded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_donor_health_snapshot, migrations.RunPython.noop),
    ]
