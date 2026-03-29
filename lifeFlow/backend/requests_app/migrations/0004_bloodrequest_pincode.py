from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0003_bloodrequest_component_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="bloodrequest",
            name="pincode",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
    ]
