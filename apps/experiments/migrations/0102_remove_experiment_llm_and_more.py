# Generated by Django 5.1.2 on 2024-11-12 14:01

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0101_experiment_llm_provider_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='experiment',
            name='llm',
        ),
        migrations.RemoveField(
            model_name='experiment',
            name='max_token_limit_old',
        ),
    ]
