# Generated by Django 5.1 on 2024-09-10 06:30

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0093_participant_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentform',
            name='working_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='experiments.consentform'),
        ),
        migrations.AddField(
            model_name='experiment',
            name='version_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='survey',
            name='working_version',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='versions', to='experiments.survey'),
        ),
    ]
