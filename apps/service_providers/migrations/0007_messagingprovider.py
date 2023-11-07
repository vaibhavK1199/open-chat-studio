# Generated by Django 4.2 on 2023-11-07 07:50

from django.db import migrations, models
import django.db.models.deletion
import django_cryptography.fields


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0003_flag"),
        ("service_providers", "0006_alter_llmprovider_team"),
    ]

    operations = [
        migrations.CreateModel(
            name="MessagingProvider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "type",
                    models.CharField(choices=[("aws", "AWS Polly"), ("azure", "Azure Text to Speech")], max_length=255),
                ),
                ("name", models.CharField(max_length=255)),
                ("config", django_cryptography.fields.encrypt(models.JSONField(default=dict))),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="teams.team", verbose_name="Team"
                    ),
                ),
            ],
            options={
                "ordering": ("type", "name"),
            },
        ),
    ]
