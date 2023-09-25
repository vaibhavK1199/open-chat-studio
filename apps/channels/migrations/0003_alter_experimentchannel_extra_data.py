# Generated by Django 4.2 on 2023-07-20 14:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("channels", "0002_experimentchannel_external_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="experimentchannel",
            name="extra_data",
            field=models.JSONField(default=dict, help_text="Fields needed for channel authorization. Format is JSON"),
        ),
    ]
