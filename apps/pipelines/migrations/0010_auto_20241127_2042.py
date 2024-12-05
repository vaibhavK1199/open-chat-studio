# Generated by Django 5.1.2 on 2024-11-27 20:42
from uuid import uuid4

from django.db import migrations

from apps.pipelines.flow import FlowNode
from apps.pipelines.graph import PipelineGraph
from apps.pipelines.migrations.utils.migrate_start_end_nodes import add_missing_start_end_nodes, _set_new_nodes, remove_all_start_end_nodes
from apps.pipelines.models import Pipeline
from apps.pipelines.nodes.nodes import EndNode, StartNode


def _add_all_missing_start_end_nodes(apps, schema_editor):
    Pipeline = apps.get_model("pipelines", "Pipeline")
    Node = apps.get_model("pipelines", "Node")

    for pipeline in Pipeline.objects.all():
        add_missing_start_end_nodes(pipeline, Node)

def _remove_all_start_end_nodes(apps, schema_editor):
    Node = apps.get_model("pipelines", "Node")
    remove_all_start_end_nodes(Node)



class Migration(migrations.Migration):

    dependencies = [
        ('pipelines', '0009_alter_pipelinechathistory_type'),
    ]

    operations = [
        migrations.RunPython(_add_all_missing_start_end_nodes, reverse_code=_remove_all_start_end_nodes)
    ]
