from unittest.mock import patch

import pytest

from apps.experiments.models import Experiment, VersionsMixin
from apps.experiments.versioning import VersionDetails, VersionField, differs
from apps.pipelines.models import Node
from apps.utils.factories.events import EventActionFactory, EventActionType, StaticTriggerFactory
from apps.utils.factories.experiment import ExperimentFactory, ExperimentSessionFactory
from apps.utils.factories.pipelines import PipelineFactory
from apps.utils.factories.service_provider_factories import TraceProviderFactory


@pytest.mark.django_db()
def test_compare_models():
    experiment = ExperimentFactory(temperature=0.1)
    instance1 = Experiment.objects.get(id=experiment.id)
    instance2 = Experiment.objects.get(id=experiment.id)
    assert instance1.compare_with_model(instance2, exclude_fields=[]) == set()
    instance2.temperature = 0.2
    assert instance1.compare_with_model(instance2, exclude_fields=["temperature"]) == set()
    assert instance1.compare_with_model(instance2, exclude_fields=[]) == set(["temperature"])


@pytest.mark.django_db()
def test_differs():
    experiment1 = ExperimentFactory(temperature=0.1)
    experiment2 = ExperimentFactory(temperature=0.1)
    assert (
        differs(
            experiment1,
            experiment1,
            exclude_model_fields=VersionsMixin.DEFAULT_EXCLUDED_KEYS,
        )
        is False
    )
    assert (
        differs(
            experiment1,
            experiment2,
            exclude_model_fields=VersionsMixin.DEFAULT_EXCLUDED_KEYS,
        )
        is True
    )
    assert differs(1, 2) is True
    assert differs(True, False) is True


@pytest.mark.django_db()
class TestVersion:
    def test_compare(self):
        instance1 = ExperimentFactory.build(temperature=0.1)
        version1 = VersionDetails(
            instance=instance1,
            fields=[
                VersionField(group_name="G1", name="the_temperature", raw_value=instance1.temperature),
            ],
        )
        similar_instance = instance1
        similar_version2 = VersionDetails(
            instance=similar_instance,
            fields=[
                VersionField(group_name="G1", name="the_temperature", raw_value=similar_instance.temperature),
            ],
        )
        different_instance = ExperimentFactory.build(temperature=0.2)
        different_version2 = VersionDetails(
            instance=different_instance,
            fields=[
                VersionField(group_name="G1", name="the_temperature", raw_value=different_instance.temperature),
            ],
        )
        version1.compare(similar_version2)
        assert version1.fields_changed is False

        version1.compare(different_version2)
        assert version1.fields_changed is True

        changed_field = version1.fields[0]
        assert changed_field.name == "the_temperature"
        assert changed_field.label == "The Temperature"
        assert changed_field.raw_value == 0.1
        assert changed_field.changed is True
        assert changed_field.previous_field_version.raw_value == 0.2

    def test_early_abort(self):
        experiment = ExperimentFactory(name="One", temperature=0.1)
        exp_version = experiment.create_new_version()

        experiment.name = "Two"
        experiment.temperature = 1
        experiment.save()

        working_version = experiment.version_details
        version_version = exp_version.version_details

        working_version.compare(version_version)
        changed_fields = [field.name for field in working_version.fields if field.changed]
        assert len(changed_fields) == 2

        # Early abort should only detect one change
        working_version = experiment.version_details
        version_version = exp_version.version_details
        working_version.compare(version_version, early_abort=True)
        changed_fields = [field.name for field in working_version.fields if field.changed]
        assert len(changed_fields) == 1

    def test_compare_querysets_with_equal_results(self):
        experiment = ExperimentFactory()
        queryset = Experiment.objects.filter(id=experiment.id)
        # Compare with itself
        version_field = VersionField(queryset=queryset)
        version_field.previous_field_version = VersionField(queryset=queryset)
        version_field._compare_querysets(queryset)
        assert version_field.changed is False
        assert len(version_field.queryset_results) == 1
        queryset_result_version = version_field.queryset_results[0]
        assert queryset_result_version.raw_value == experiment
        assert queryset_result_version.previous_field_version.raw_value == experiment

    def test_compare_querysets_with_results_of_differing_versions(self):
        experiment = ExperimentFactory()
        queryset = Experiment.objects.filter(id=experiment.id)
        # Compare with new version
        new_version = experiment.create_new_version()
        experiment.prompt_text = "This now changed"
        experiment.save()
        version_field = VersionField(queryset=queryset)
        version_field.previous_field_version = VersionField(queryset=Experiment.objects.filter(id=new_version.id))
        version_field._compare_querysets()
        assert version_field.changed is True
        assert len(version_field.queryset_results) == 1
        queryset_result_version = version_field.queryset_results[0]
        assert queryset_result_version.raw_value == experiment
        assert queryset_result_version.previous_field_version.raw_value == new_version

    def test_compare_querysets_with_different_results(self):
        """
        When comparing different querysets, we expect two result versions to be created. One for the current queryset
        not having a match in the previous queryset and one for the previous queryset not having a match in the current
        queryset
        """
        experiment = ExperimentFactory()
        queryset = Experiment.objects.filter(id=experiment.id)
        # Compare with a totally different queryset
        another_experiment = ExperimentFactory()
        version_field = VersionField(queryset=queryset)
        version_field.previous_field_version = VersionField(
            queryset=Experiment.objects.filter(id=another_experiment.id)
        )
        version_field._compare_querysets()
        assert version_field.changed is True

        assert len(version_field.queryset_results) == 2
        first_result_version = version_field.queryset_results[0]
        assert first_result_version.raw_value == experiment
        assert first_result_version.previous_field_version is None

        second_result_version = version_field.queryset_results[1]
        assert second_result_version.raw_value is None
        assert second_result_version.previous_field_version.raw_value == another_experiment

    def test_type_error_raised(self):
        """A type error should be raised when comparing versions of differing types"""
        instance1 = ExperimentFactory.build()
        version1 = VersionDetails(
            instance=instance1,
            fields=[],
        )

        version2 = VersionDetails(
            instance=ExperimentSessionFactory.build(),
            fields=[],
        )

        with pytest.raises(TypeError, match=r"Cannot compare instances of different types."):
            version1.compare(version2)

    def test_fields_grouped(self, experiment):
        new_version = experiment.create_new_version()
        original_version = experiment.version_details
        original_version.compare(new_version.version_details)
        all_groups = set([field.group_name for field in experiment.version_details.fields])
        collected_group_names = []
        for group in original_version.fields_grouped:
            collected_group_names.append(group.name)
            assert group.has_changed_fields is False

        assert all_groups - set(collected_group_names) == set()

        # Let's change something
        new_version.temperature = new_version.temperature + 0.1

        original_version.compare(new_version.version_details)
        temerature_group_name = original_version.get_field("temperature").group_name
        # Find the temperature group and check that it reports a change
        for group in original_version.fields_grouped:
            if group.name == temerature_group_name:
                assert group.has_changed_fields is True

    def test_new_queryset_is_empty(self):
        """This tests the case where a queryset's previous results are not empty, but the current results are"""
        # Let's use experiment sessions as an example
        experiment = ExperimentFactory()
        ExperimentSessionFactory(experiment=experiment)
        previous_queryset = experiment.sessions
        # Compare with a totally different queryset
        new_experiment = ExperimentFactory()
        new_queryset = new_experiment.sessions
        # sanity check
        assert new_queryset.count() == 0

        version_field = VersionField(queryset=new_queryset)
        # another sanity check
        assert version_field.queryset is not None
        version_field.previous_field_version = VersionField(queryset=previous_queryset)
        version_field._compare_querysets()
        assert version_field.changed is True

    def test_compare_unversioned_models(self):
        trace_provider = TraceProviderFactory()
        experiment = ExperimentFactory()
        experiment_version = experiment.create_new_version()
        experiment.trace_provider = trace_provider
        experiment.save()
        experiment.version_details.compare(experiment_version.version_details)

    def test_action_params_expanded_into_fields(self):
        """
        Non-model fields that are considered part of a version (e.g. static trigger action params) are be expanded
        into separate versioned fields. If some of those parameters are removed in a new version, they should still
        show up as a versioned field in `version_details`, but only with an empty value.
        """
        experiment = ExperimentFactory()
        first_version_params = {"pipeline_id": 1}
        start_pipeline_action = EventActionFactory(
            action_type=EventActionType.PIPELINE_START,
            params=first_version_params,
        )
        static_trigger = StaticTriggerFactory(experiment=experiment, action=start_pipeline_action)
        experiment.create_new_version()

        # Now change the params
        action = static_trigger.action
        action.params = {"some_other_param": "a value"}
        action.save()

        curr_version_details = static_trigger.version_details
        # Since the params changed, we expect pipeline_id to be missing from the version details
        assert "pipeline_id" not in [f.name for f in curr_version_details.fields]
        curr_version_details.compare(static_trigger.latest_version.version_details)
        # We expect the missing field(s) from the previous version details to be added to the current version details
        assert "pipeline_id" in [f.name for f in curr_version_details.fields]
        # Since the field is missing, the value should be None
        assert curr_version_details.get_field("pipeline_id").raw_value is None

    @pytest.mark.parametrize(
        ("curr_value", "prev_value", "char_diff_calculated"),
        [(True, False, False), ("true", False, False), ("true", "false", True)],
    )
    @patch("apps.experiments.versioning.VersionField._compute_character_level_diff")
    def test_character_diffs_are_only_calculated_when_both_values_are_string(
        self, compute_character_level_diff, curr_value, prev_value, char_diff_calculated
    ):
        pipeline = PipelineFactory()
        node = Node.objects.create(pipeline=pipeline, type="AssistantNode", params={"citations_enabled": prev_value})
        new_version = node.create_new_version()
        node.params["citations_enabled"] = curr_value
        node.save()

        version_details = node.version_details
        version_details.compare(new_version.version_details)

        if char_diff_calculated:
            compute_character_level_diff.assert_called_once()
        else:
            compute_character_level_diff.assert_not_called()
