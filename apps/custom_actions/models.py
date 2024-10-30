from django.db import models
from django.urls import reverse
from field_audit import audit_fields
from field_audit.models import AuditingManager

from apps.teams.models import BaseTeamModel


@audit_fields("team", "name", "prompt", "api_schema", audit_special_queryset_writes=True)
class CustomAction(BaseTeamModel):
    objects = AuditingManager()
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    prompt = models.TextField(blank=True)
    server_url = models.URLField()
    api_schema = models.JSONField()

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs):
        self.server_url = self.api_schema.get("servers", [{}])[0].get("url", "")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("custom_actions:edit", args=[self.team.slug, self.pk])
