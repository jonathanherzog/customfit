from django.contrib import admin
from django.urls import reverse

from .models import Swatch


class SwatchAdmin(admin.ModelAdmin):
    search_fields = ("user__username", "name")
    list_display = ("name", "user", "user_view", "id")
    raw_id_fields = ("user",)
    list_filter = ("archived",)

    def user_view(self, instance):
        if instance.archived:
            response = "This swatch has been archived."
        else:
            url = reverse("swatches:swatch_detail_view", args=(instance.id,))
            response = """<a href="{0}">{0}</a>""".format(url)
        return response

    def get_queryset(self, request):
        qs = Swatch.even_archived
        return qs

    user_view.short_description = "See the swatch page"
    user_view.allow_tags = True


admin.site.register(Swatch, SwatchAdmin)
