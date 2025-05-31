from django import template

register = template.Library()


@register.simple_tag()
def get_object_model(obj):
    return obj._meta.object_name.lower()
