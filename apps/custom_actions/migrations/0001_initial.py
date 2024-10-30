# Generated by Django 5.1.2 on 2024-10-30 11:19

import apps.utils.models
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("teams", "0006_remove_invitation_role_remove_membership_role"),
    ]

    operations = [
        migrations.CreateModel(
            name="CustomAction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("prompt", models.TextField(blank=True)),
                ("api_schema", models.JSONField()),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="teams.team",
                        verbose_name="Team",
                    ),
                ),
                ("server_url", models.URLField()),
            ],
            options={
                "ordering": ("name",),
            },
            bases=(models.Model, apps.utils.models.VersioningMixin),
        ),
    ]
