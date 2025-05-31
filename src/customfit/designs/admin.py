from django.contrib import admin

from customfit.helpers.admin_helpers import make_link_function
from customfit.sweaters.models import (
    AdditionalBackElement,
    AdditionalFrontElement,
    AdditionalFullTorsoElement,
    AdditionalSleeveElement,
)

from .models import (
    AdditionalDesignElementTemplate,
    Collection,
    DesignAlternatePicture,
    Designer,
    ExtraFinishingTemplate,
)

admin.site.register(ExtraFinishingTemplate)
admin.site.register(Collection)
admin.site.register(Designer)

# Register the 'additonal elements' for direct listing/editing
admin.site.register(AdditionalFrontElement)
admin.site.register(AdditionalBackElement)
admin.site.register(AdditionalFullTorsoElement)
admin.site.register(AdditionalSleeveElement)


# add helpful text to the template interface


class AdditionalDesignElementTemplateAdmin(admin.ModelAdmin):

    fields = ["name", "content"]

    # If you change the help_text below, be sure to synchronize with
    # customfit/pattern/renderers/base:InstructionSection._make_context_for_additional_element

    def get_form(self, request, obj=None, **kwargs):
        form = super(AdditionalDesignElementTemplateAdmin, self).get_form(
            request, obj, **kwargs
        )
        form.base_fields[
            "content"
        ].help_text = """
        <p>Be sure to write complete HTML, and start with <code>{% load pattern_conventions %}</code> if you want
        the usual set of template filters.
        Also, the following context-variables will be available within the template:
        </p>
        <ul>
        <li><p><code>piece</code>: the piece to which this element is attached. Note that you should not
            use this directly, but as way of getting information about the piece. For example,
            <code>{{ piece.cast_ons}}</code> will give you the cast-on count (when the piece
            is a sleeve, front, back, etc.) and <code>{{ piece.actual_bicep }} will give the actual
            bicep, in inches, if the piece is a sleeve. What other kind of information is available?
            Unfortunately, the list is long, constantly changing, and piece-specific. You'll need
            to ask for what you need. Note that for graded patterns you'll gets lists of values, so
            always use the length_fmt or count_fmt filters. </p></li>
        <li><p><code>start_row</code>: the first row to be in this element. For graded patterns, this will be a list. Be sure to use the count_fmt filter.</p></li>
        <li><p><code>final_row</code>: the last row to be in this element. For graded patterns, this will be a list. Be sure to use the count_fmt filter.</p></li>
        <li><p><code>start_height</code>: height of <code>start_row</code> in inches. For graded patterns, this will be a list. Be sure to use the length_fmt filter.</p></li>
        <li><p><code>final_height</code>: height of <code>final_row</code> in inches. For graded patterns, this will be a list. Be sure to use the length_fmt filter.</p></li>
        <li><p><code>height_in_rows</code>: number of rows in the element (includes <code>start_row</code> and <code>end_row</code>). For graded patterns, this will be a list. Be sure to use the count_fmt filter. </p></li>
        <li><p><code>height_in_inches</code>: number of inches consumed between start of <code>start_row</code> and end of <code>end_row</code>. For graded patterns, this will be a list. Be sure to use the length_fmt filter.</p></li>
        </ul>
        """
        return form


admin.site.register(
    AdditionalDesignElementTemplate, AdditionalDesignElementTemplateAdmin
)

# Create inlines for editing through the design-detail page


class AdditionalElementInlineBase(admin.StackedInline):
    extra = 0
    fields = [
        "name",
        "start_location_value",
        "start_location_type",
        "height_value",
        "height_type",
        "template",
        "overlap_behavior",
        "stitch",
    ]


class DesignAlternatePictureAdmin(admin.ModelAdmin):
    search_fields = ("design",)
    list_display = (
        "design",
        "image",
    )

    body_link = make_link_function("design")

    def get_form(self, request, obj=None, **kwargs):
        """
        Limits drop-down in admin to designs that might actually appear
        on the personalize design page.
        """
        form = super(DesignAlternatePictureAdmin, self).get_form(request, obj, **kwargs)
        designs = form.base_fields["design"].queryset
        form.base_fields["design"].queryset = designs.extra(order_by=["name"])
        return form


admin.site.register(DesignAlternatePicture, DesignAlternatePictureAdmin)
