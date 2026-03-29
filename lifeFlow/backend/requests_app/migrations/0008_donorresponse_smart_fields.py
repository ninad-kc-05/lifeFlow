from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_remove_admin_role_type"),
        ("requests_app", "0007_update_status_assigned"),
    ]

    operations = [
        migrations.AddField(
            model_name="donorresponse",
            name="hospital",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="donor_responses",
                to="users.hospital",
            ),
        ),
        migrations.AddField(
            model_name="donorresponse",
            name="remarks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="donorresponse",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("testing", "Testing"),
                    ("selected", "Selected"),
                    ("rejected", "Rejected"),
                    ("completed", "Completed"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
