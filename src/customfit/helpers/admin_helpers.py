from django.urls import reverse
from django.utils.safestring import mark_safe

def make_link_function(field_name, display_name=None):
    """
    Returns a function which can be used by a ModelAdmin
    to make a link to a related object.
    """

    def f(self, obj):
        if hasattr(obj, field_name):
            field_obj = getattr(obj, field_name)
            model = field_obj.__class__
            model_name = model.__name__
            app_name = model._meta.app_label
            view_name = "admin:%s_%s_change" % (app_name, model_name.lower())
            url = reverse(view_name, args=(field_obj.pk,))
            html = '<a href="%s">%s %s</a>' % (url, model_name, field_obj.pk)
            return mark_safe(html)
        else:
            return ""

    f.allow_tags = True
    if display_name is None:
        display_name = field_name
    f.short_description = display_name
    return f
