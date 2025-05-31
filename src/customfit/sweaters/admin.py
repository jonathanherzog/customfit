import reversion
from django.contrib import admin
from django.forms import ModelForm
from django.urls import reverse

from customfit.designs.admin import AdditionalElementInlineBase
from customfit.helpers.admin_helpers import make_link_function
from customfit.patterns.admin import ApprovedPatternFilter, UserGroupFilter

from .models import (
    AdditionalBackElement,
    AdditionalFrontElement,
    AdditionalFullTorsoElement,
    AdditionalSleeveElement,
    BackNeckline,
    BoatNeck,
    CardiganSleeved,
    CardiganSleevedSchematic,
    CardiganVest,
    CardiganVestSchematic,
    CrewNeck,
    ScoopNeck,
    Sleeve,
    SleeveSchematic,
    SweaterBack,
    SweaterBackSchematic,
    SweaterDesign,
    SweaterFront,
    SweaterFrontSchematic,
    SweaterIndividualGarmentParameters,
    SweaterPattern,
    SweaterPatternPieces,
    SweaterPatternSpec,
    SweaterRedo,
    SweaterSchematic,
    TurksAndCaicosNeck,
    VeeNeck,
    VestBack,
    VestBackSchematic,
    VestFront,
    VestFrontSchematic,
)

# designs


# Register your models here.


class AdditionalFrontElementInline(AdditionalElementInlineBase):
    model = AdditionalFrontElement


class AdditionalBackElementInline(AdditionalElementInlineBase):
    model = AdditionalBackElement


class AdditionalFullTorsoElementInline(AdditionalElementInlineBase):
    model = AdditionalFullTorsoElement


class AdditionalSleeveElementInline(AdditionalElementInlineBase):
    model = AdditionalSleeveElement


class SweaterDesignAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "id", "visibility", "designer")
    list_filter = (
        "visibility",
        "designer",
        "is_basic",
        "silhouette_hourglass_allowed",
        "silhouette_aline_allowed",
        "silhouette_straight_allowed",
        "silhouette_tapered_allowed",
        "silhouette_half_hourglass_allowed",
    )
    inlines = [
        AdditionalFrontElementInline,
        AdditionalBackElementInline,
        AdditionalFullTorsoElementInline,
        AdditionalSleeveElementInline,
    ]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "designer",
                    "collection",
                    "garment_type",
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
            "Construction",
            {
                "fields": (
                    "primary_construction",
                    "construction_set_in_sleeve_allowed",
                    "construction_drop_shoulder_allowed",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Torso",
            {
                "fields": (
                    "primary_silhouette",
                    "silhouette_aline_allowed",
                    "silhouette_hourglass_allowed",
                    "silhouette_half_hourglass_allowed",
                    "silhouette_straight_allowed",
                    "silhouette_tapered_allowed",
                    "torso_length",
                    "hip_edging_stitch",
                    "hip_edging_height",
                    "back_allover_stitch",
                    "back_cable_stitch",
                    "back_cable_extra_stitches",
                    "front_allover_stitch",
                    "front_cable_stitch",
                    "front_cable_extra_stitches",
                    "waist_hem_template",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Neckline",
            {
                "fields": (
                    "neckline_style",
                    "neckline_width",
                    "neckline_other_val_percentage",
                    "neckline_depth",
                    "neckline_depth_orientation",
                    "neck_edging_stitch",
                    "neck_edging_height",
                    "trim_neckline_template",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Sleeve",
            {
                "fields": (
                    "sleeve_length",
                    "sleeve_shape",
                    "bell_type",
                    "sleeve_edging_height",
                    "sleeve_edging_stitch",
                    "sleeve_allover_stitch",
                    "sleeve_cable_stitch",
                    "sleeve_cable_extra_stitches",
                    "sleeve_cable_extra_stitches_caston_only",
                    "sleeve_hem_template",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Armhole",
            {
                "fields": (
                    "armhole_edging_height",
                    "armhole_edging_stitch",
                    "trim_armhole_template",
                    "drop_shoulder_additional_armhole_depth",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Buttonband",
            {
                "fields": (
                    "button_band_allowance",
                    "button_band_allowance_percentage",
                    "number_of_buttons",
                    "button_band_edging_stitch",
                    "button_band_edging_height",
                    "button_band_template",
                    "button_band_veeneck_template",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Design extras",
            {
                "fields": (
                    "panel_stitch",
                    "pattern_credits",
                    "cover_sheet",
                    "extra_finishing_template",
                    "notions",
                ),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(SweaterDesign, SweaterDesignAdmin)


# Patternspec


class SweaterPatternSpecAdmin(admin.ModelAdmin):
    search_fields = ("user__username",)
    list_display = ("name", "user", "swatch", "body", "garment_type", "id")
    raw_id_fields = (
        "user",
        #'design_origin', # TODO: uncomment
        "swatch",
        "body",
    )
    ordering = ("user", "name", "id")

    # Deliberately choosing not to 'exclude' body and swatch just in case
    # there is a real use-case for changing these values through the admin
    # interface
    body_link = make_link_function("body")
    swatch_link = make_link_function("swatch")

    readonly_fields = ["body_link", "swatch_link"]


admin.site.register(SweaterPatternSpec, SweaterPatternSpecAdmin)


# Garment parameters


class SweaterGarmentParametersAdmin(reversion.admin.VersionAdmin):
    search_fields = ("pattern_spec__user__username", "pattern_spec__name")
    list_display = ("name", "user", "id")
    raw_id_fields = ("user",)
    exclude = ("body", "swatch", "pattern_spec", "redo")

    body_link = make_link_function("body")
    swatch_link = make_link_function("swatch")
    pspec_link = make_link_function("pattern_spec")
    redo_link = make_link_function("redo")

    readonly_fields = ["body_link", "swatch_link", "pspec_link", "redo_link"]


admin.site.register(SweaterIndividualGarmentParameters, SweaterGarmentParametersAdmin)


# Schematics


class SweaterSchematicAdmin(admin.ModelAdmin):
    search_fields = (
        "individual_garment_parameters__pattern_spec__user__username",
        "individual_garment_parameters__pattern_spec__name",
    )
    list_display = ("name", "user", "id")
    #    raw_id_fields = ('user', )

    exclude = (
        "individual_garment_parameters",
        "sweater_back",
        "sweater_front",
        "vest_back",
        "vest_front",
        "sleeve",
        "cardigan_vest",
        "cardigan_sleeved",
    )

    igp_link = make_link_function("individual_garment_parameters", "Garment params")
    sweater_back_link = make_link_function("sweater_back")
    sweater_front_link = make_link_function("sweater_front")
    vest_back_link = make_link_function("vest_back")
    vest_front_link = make_link_function("vest_front")
    sleeve_link = make_link_function("sleeve")
    cardigan_vest_link = make_link_function("cardigan_vest")
    cardigan_sleeved_link = make_link_function("cardigan_sleeved")

    readonly_fields = (
        "igp_link",
        "sweater_back_link",
        "sweater_front_link",
        "vest_back_link",
        "vest_front_link",
        "sleeve_link",
        "cardigan_vest_link",
        "cardigan_sleeved_link",
    )


admin.site.register(SweaterSchematic, SweaterSchematicAdmin)


class SweaterPieceSchematicAdmin(admin.ModelAdmin):

    exclude = ["pattern_spec"]
    schematic_link = make_link_function("sweaterschematic", "SweaterSchematic")
    readonly_fields = ["schematic_link"]


admin.site.register(CardiganVestSchematic, SweaterPieceSchematicAdmin)
admin.site.register(CardiganSleevedSchematic, SweaterPieceSchematicAdmin)


class NonCardiganSchematicAdmin(SweaterPieceSchematicAdmin):
    search_fields = (
        "schematic__individual_garment_parameters__pattern_spec__user__username",
        "schematic__individual_garment_parameters__pattern_spec__name",
    )


#    list_display = ('schematic',)

admin.site.register(SleeveSchematic, NonCardiganSchematicAdmin)
admin.site.register(SweaterBackSchematic, NonCardiganSchematicAdmin)
admin.site.register(SweaterFrontSchematic, NonCardiganSchematicAdmin)
admin.site.register(VestBackSchematic, NonCardiganSchematicAdmin)
admin.site.register(VestFrontSchematic, NonCardiganSchematicAdmin)


# Pieces


class SweaterPatternPiecesAdmin(admin.ModelAdmin):
    exclude = [
        "sweater_back",
        "sweater_front",
        "vest_back",
        "vest_front",
        "sleeve",
        "cardigan_vest",
        "cardigan_sleeved",
        "schematic",
    ]

    sweater_back_link = make_link_function("sweater_back")
    sweater_front_link = make_link_function("sweater_front")
    vest_back_link = make_link_function("vest_back")
    vest_front_link = make_link_function("vest_front")
    sleeve_link = make_link_function("sleeve")
    cardigan_vest_link = make_link_function("cardigan_vest")
    cardigan_sleeved_link = make_link_function("cardigan_sleeved")
    schematic_link = make_link_function("schematic", "Schematic")

    readonly_fields = [
        "schematic_link",
        "sweater_back_link",
        "sweater_front_link",
        "vest_back_link",
        "vest_front_link",
        "sleeve_link",
        "cardigan_vest_link",
        "cardigan_sleeved_link",
    ]


admin.site.register(SweaterPatternPieces, SweaterPatternPiecesAdmin)


class PieceAdmin(admin.ModelAdmin):
    search_fields = ("individualpattern__user__username", "individualpattern__name")

    exclude = ["swatch", "schematic"]
    swatch_link = make_link_function("swatch")
    schematic_link = make_link_function("schematic")
    readonly_fields = ["swatch_link", "schematic_link"]


admin.site.register(Sleeve, PieceAdmin)


class PieceWithNecklineAdmin(PieceAdmin):
    exclude = PieceAdmin.exclude + ["neckline_content_type", "neckline_object_id"]
    neckline_link = make_link_function("neckline")
    readonly_fields = PieceAdmin.readonly_fields + ["neckline_link"]


admin.site.register(SweaterBack, PieceWithNecklineAdmin)
admin.site.register(VestBack, PieceAdmin)
admin.site.register(SweaterFront, PieceAdmin)
admin.site.register(VestFront, PieceAdmin)
admin.site.register(CardiganVest, PieceAdmin)
admin.site.register(CardiganSleeved, PieceAdmin)


class NecklineAdmin(admin.ModelAdmin):
    pass


admin.site.register(BackNeckline, NecklineAdmin)
admin.site.register(VeeNeck, NecklineAdmin)
admin.site.register(CrewNeck, NecklineAdmin)
admin.site.register(ScoopNeck, NecklineAdmin)
admin.site.register(BoatNeck, NecklineAdmin)
admin.site.register(TurksAndCaicosNeck, NecklineAdmin)


# Pattern


class SweaterPatternAdmin(admin.ModelAdmin):
    search_fields = ("user__username", "name")
    list_display = ("name", "user", "user_view", "approved", "id")
    ordering = ("user", "name")
    raw_id_fields = ("user",)
    list_filter = (ApprovedPatternFilter, UserGroupFilter)

    def get_queryset(self, request):
        qs = SweaterPattern.even_unapproved
        return qs

    def user_view(self, instance):
        url = reverse("patterns:individualpattern_detail_view", args=(instance.id,))
        response = """<a href="{0}">{0}</a>""".format(url)
        return response

    user_view.short_description = "See the pattern page"
    user_view.allow_tags = True

    def approved(self, instance):
        return bool(instance.transactions.filter(approved=True))

    approved.short_description = "Approved"

    exclude = ["pieces", "original_pieces"]

    pieces_link = make_link_function("pieces")
    original_pieces_link = make_link_function("original_pieces")

    readonly_fields = ["pieces_link", "original_pieces_link"]

    actions = ["approve_patterns"]

    def approve_patterns(self, request, queryset):
        # Import here, so as to avoid pesky circular imports
        from customfit.design_wizard.models import Transaction

        num_force_approved = 0
        num_already_approved = 0
        errors = []

        for pattern in queryset:
            if pattern.approved:
                num_already_approved += 1
            else:
                try:
                    tr = Transaction()
                    tr.user = pattern.user
                    tr.pattern = pattern
                    tr.amount = 0.00
                    tr.why_free = Transaction.UNKNOWN_REASON
                    tr.full_clean()
                    tr.save()
                    num_force_approved += 1
                except:
                    errors.append(pattern)

        message_string = ""
        if num_already_approved:
            message_string += (
                "%d pattern(s) were already approved\n" % num_already_approved
            )
        if num_force_approved:
            message_string += (
                "%d pattern(s) approved by admin fiat\n" % num_force_approved
            )
        if errors:
            message_string += "Errors encountered for the following pattern(s): %s" % [
                p.id for p in errors
            ]
        self.message_user(request, message_string)

    approved.short_description = "Approve"


admin.site.register(SweaterPattern, SweaterPatternAdmin)


# Redos


class SweaterRedoForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SweaterRedoForm, self).__init__(*args, **kwargs)
        user = self.instance.user
        self.fields["body"].queryset = self.fields["body"].queryset.filter(user=user)
        self.fields["swatch"].queryset = self.fields["swatch"].queryset.filter(
            user=user
        )


class SweaterRedoAdmin(admin.ModelAdmin):

    form = SweaterRedoForm
    exclude = ["pattern"]
    readonly_fields = ["pattern_link"]

    pattern_link = make_link_function("pattern")


admin.site.register(SweaterRedo, SweaterRedoAdmin)
