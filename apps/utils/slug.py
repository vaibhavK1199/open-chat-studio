import hashlib
import uuid

from django.db.models import Model
from django.utils.text import slugify


def get_next_unique_slug(model_class: type[Model], input_value: str, field_name: str, model_instance=None) -> str:
    """
    Gets the next unique slug based on the name. Appends -1, -2, etc. until it finds
    a unique value.

    Args:
        model_class: The Django model class to check for uniqueness.
        input_value: The input value to generate the slug.
        field_name: The field name to check for uniqueness.
        model_instance: The model instance to exclude from the uniqueness check.
    """
    return _get_next_unique_value(next_slug_iterator(input_value), model_class, field_name, model_instance)


def get_next_unique_id(model_class: type[Model], inputs: list, field_name: str, length=8, model_instance=None) -> str:
    """
    Gets the next unique hashed ID based on the inputs. Passing in unique inputs will generate a unique ID.
    If the ID already exists, a new one will be generated by appending random data to the inputs.

    Args:
        model_class: The Django model class to check for uniqueness.
        inputs: The inputs to hash to generate the ID. Each input is converted to a string.
        field_name: The field name to check for uniqueness.
        length: The desired length of the ID.
        model_instance: The model instance to exclude from the uniqueness check.
    """
    iterator = next_hash_id_iterator(inputs, length=length)
    return _get_next_unique_value(iterator, model_class, field_name, model_instance)


def _get_next_unique_value(value_iterator, model_class, field_name, model_instance=None):
    max_iterations = 20
    for count, next_value in enumerate(value_iterator):
        if not _instance_exists(model_class, field_name, next_value, model_instance):
            return next_value

        if count > max_iterations:
            raise ValueError(f"Unable to generate a unique value after {max_iterations} attempts.")


def next_hash_id_iterator(inputs, length=8):
    base_id = _generate_hash(*inputs, length=length)
    yield base_id

    while True:
        yield _generate_hash(uuid.uuid4().hex, *inputs, length=length)


def _generate_hash(*inputs, length=8) -> str:
    """Generate an ID by hashing the input based on the inputs."""
    data = "".join(str(i) for i in inputs)
    return hashlib.shake_128(data.encode()).hexdigest(length)[:length].upper()


def _instance_exists(model_class, field_name, field_value, model_instance=None):
    base_qs = model_class.objects.all()
    if model_instance and model_instance.pk:
        base_qs = base_qs.exclude(pk=model_instance.id)

    return base_qs.filter(**{f"{field_name}__exact": field_value}).exists()


def next_slug_iterator(display_name):
    base_slug = slugify(display_name)
    yield base_slug

    suffix = 2
    while True:
        yield get_next_slug(base_slug, suffix)
        suffix += 1


def get_next_slug(base_value, suffix, max_length=100):
    """
    Gets the next slug from base_value such that "base_value-suffix" will not exceed max_length characters.
    """
    suffix_length = len(str(suffix)) + 1  # + 1 for the "-" character
    if suffix_length >= max_length:
        raise ValueError(f"Suffix {suffix} is too long to create a unique slug! ")

    return f"{base_value[: max_length - suffix_length]}-{suffix}"
