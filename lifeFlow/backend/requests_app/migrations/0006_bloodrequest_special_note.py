from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("requests_app", "0005_expand_request_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="bloodrequest",
            name="special_note",
            field=models.TextField(blank=True, default=""),
        ),
    ]
