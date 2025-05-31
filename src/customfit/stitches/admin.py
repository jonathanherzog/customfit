from django.contrib import admin

from .models import (
    ButtonBandTemplate,
    ButtonBandVeeneckTemplate,
    SleeveHemTemplate,
    Stitch,
    TrimArmholeTemplate,
    TrimNecklineTemplate,
    WaistHemTemplate,
)


class StitchAdmin(admin.ModelAdmin):
    list_display = ("name", "user_visible", "stitch_type")
    list_filter = (
        "user_visible",
        "stitch_type",
        "is_waist_hem_stitch",
        "is_sleeve_hem_stitch",
        "is_neckline_hem_stitch",
        "is_buttonband_hem_stitch",
        "is_allover_stitch",
        "is_panel_stitch",
    )


admin.site.register(Stitch, StitchAdmin)
admin.site.register(WaistHemTemplate)
admin.site.register(SleeveHemTemplate)
admin.site.register(TrimArmholeTemplate)
admin.site.register(TrimNecklineTemplate)
admin.site.register(ButtonBandTemplate)
admin.site.register(ButtonBandVeeneckTemplate)
