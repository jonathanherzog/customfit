from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Body, Grade, GradeSet


class BodyAdmin(admin.ModelAdmin):
    search_fields = ("user__username", "name")
    list_display = ("name", "user", "user_view", "id")
    raw_id_fields = ("user",)
    list_filter = ("archived",)

    def user_view(self, instance):
        if instance.archived:
            response = "This body has been archived."
        else:
            url = reverse("bodies:body_detail_view", args=(instance.id,))
            response = """<a href="{0}">{0}</a>""".format(url)
        return response

    def get_queryset(self, request):
        qs = Body.even_archived
        return qs

    user_view.short_description = "See the body page"
    user_view.allow_tags = True


admin.site.register(Body, BodyAdmin)


class GradeInline(admin.TabularInline):
    model = Grade
    fields = [  # The order should match that in the user-facing 'enter body' page
        "bust_circ",
        "waist_circ",
        "med_hip_circ",
        "armhole_depth",
        "armpit_to_med_hip",
        "armpit_to_full_sleeve",
        "wrist_circ",
        "bicep_circ",
        "upper_torso_circ",
        "elbow_circ",
        "forearm_circ",
        "armpit_to_short_sleeve",
        "armpit_to_elbow_sleeve",
        "armpit_to_three_quarter_sleeve",
        "armpit_to_waist",
        "armpit_to_high_hip",
        "high_hip_circ",
        "armpit_to_low_hip",
        "low_hip_circ",
        "armpit_to_tunic",
        "tunic_circ",
    ]


class GradeSetAdmin(admin.ModelAdmin):
    inlines = [GradeInline]

    def get_form(self, request, obj=None, **kwargs):
        form = super(GradeSetAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["user"].queryset = User.objects.filter(is_staff=True)
        return form


admin.site.register(GradeSet, GradeSetAdmin)
