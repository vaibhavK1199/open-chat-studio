# Generated by Django 4.2.7 on 2023-11-29 08:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("experiments", "0054_consentform_capture_identifier_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="consentform",
            name="confirmation_text",
            field=models.CharField(
                default="Respond with '1' if you agree",
                help_text="Use this text to tell the user to respond with '1' in order to give their consent",
            ),
        ),
        migrations.AddField(
            model_name="experiment",
            name="conversational_consent_enabled",
            field=models.BooleanField(
                default=False,
                help_text="If enabled, the consent form will be sent at the start of a conversation for external channels. Note: This requires the experiment to have a seed message.",
            ),
        ),
    ]
