# Generated by Django 5.1.5 on 2025-03-11 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assistants', '0012_remove_openaiassistant_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='toolresources',
            name='allow_file_downloads',
            field=models.BooleanField(default=False),
        ),
    ]
