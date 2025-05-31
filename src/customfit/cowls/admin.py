# -*- coding: utf-8 -*-


from django.contrib import admin

from .models import (
    CowlDesign,
    FinalEdgingTemplate,
    FirstEdgingTemplate,
    MainSectionTemplate,
)

# Register your models here.


class CowlDesignAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "id", "visibility", "designer")
    list_filter = ("visibility", "designer", "is_basic")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "designer",
                    "collection",
                    "visibility",
                    "difficulty",
                    "is_basic",
                    "image",
                    "description",
                    "recommended_materials",
                    "purchase_url",
                    "ahd_wp_product_id",
                    "ahd_wp_variation_id",
                )
            },
        ),
        (
            "Design elements",
            {
                "fields": (
                    "circumference",
                    "height",
                    "edging_stitch",
                    "edging_stitch_height",
                    "cast_on_x_mod",
                    "cast_on_mod_y",
                    "main_stitch",
                    "cable_stitch",
                    "extra_cable_stitches",
                    "extra_cable_stitches_are_main_pattern_only",
                    "panel_stitch",
                    "horizontal_panel_rounds",
                    "first_edging_template",
                    "main_section_template",
                    "final_edging_template",
                )
            },
        ),
        (
            "Design extras",
            {
                "fields": (
                    "pattern_credits",
                    "cover_sheet",
                    "notions",
                ),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(CowlDesign, CowlDesignAdmin)
admin.site.register(FirstEdgingTemplate)
admin.site.register(MainSectionTemplate)
admin.site.register(FinalEdgingTemplate)
