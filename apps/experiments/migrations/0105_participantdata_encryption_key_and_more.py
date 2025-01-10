# Generated by Django 5.1.2 on 2025-01-10 13:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0104_consentform_unique_default_consent_form_per_team'),
    ]

    operations = [
        migrations.AddField(
            model_name='participantdata',
            name='encryption_key',
            field=models.CharField(blank=True, help_text='The base64 encoded encryption key', max_length=255),
        ),
        migrations.AddField(
            model_name='participantdata',
            name='system_metadata',
            field=models.JSONField(default=dict),
        ),
    ]
