# Generated by Django 4.2.7 on 2024-03-05 11:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("experiments", "0066_alter_experimentsession_options"),
        ("chat", "0010_celery_periodic"),
        ("events", "0001_create_tasks"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventAction",
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
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("log", "Log"),
                            ("end_conversation", "End Conversation"),
                        ]
                    ),
                ),
                ("params", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="TimeoutTrigger",
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
                (
                    "delay",
                    models.PositiveIntegerField(
                        help_text="The amount of time in seconds to fire this trigger."
                    ),
                ),
                (
                    "total_num_triggers",
                    models.IntegerField(
                        default=1, help_text="The number of times to fire this trigger"
                    ),
                ),
                (
                    "action",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timeout_trigger",
                        to="events.eventaction",
                    ),
                ),
                (
                    "experiment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timeout_triggers",
                        to="experiments.experiment",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="StaticTrigger",
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
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("conversation_end", "Conversation End"),
                            ("last_timeout", "Last Timeout"),
                        ],
                        db_index=True,
                    ),
                ),
                (
                    "action",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="static_trigger",
                        to="events.eventaction",
                    ),
                ),
                (
                    "experiment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="static_triggers",
                        to="experiments.experiment",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="EventLog",
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
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("failure", "Failure")]
                    ),
                ),
                (
                    "chat_message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_logs",
                        to="chat.chatmessage",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_logs",
                        to="experiments.experimentsession",
                    ),
                ),
                (
                    "trigger",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_logs",
                        to="events.timeouttrigger",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
