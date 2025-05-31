import io

import factory
import PIL
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import slugify

import customfit.designs.helpers.design_choices as DC

from .models import (
    AdditionalDesignElement,
    AdditionalDesignElementTemplate,
    Design,
    Designer,
)


class DesignerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Designer
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("full_name",)

    full_name = factory.Sequence(lambda n: "Designer fullname %s" % n)
    short_name = factory.Sequence(lambda n: "Designer shortname %s" % n)
    primary_sort_name = factory.Sequence(lambda n: "Designer primarysort name %s" % n)
    secondary_sort_name = factory.Sequence(
        lambda n: "Designer secondarysortname %s" % n
    )
    business_name = factory.Sequence(lambda n: "Designer business_name %s" % n)
    primary_home_page = "http://www.examplehome.com/"
    secondary_home_page = "http://www.examplesecondhome.com"
    ravelry_link = "http://www.ravelry.com/"
    about_designer_long = factory.Sequence(
        lambda n: "About designer (long) lorem ipsem %s" % n
    )
    about_designer_short = factory.Sequence(
        lambda n: "About designer (short) lorem ipsem %s" % n
    )
    picture = None


def make_jpeg_bytes():
    buffer = io.BytesIO()
    image = PIL.Image.new("RGB", (100, 100), color="white")
    image.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.read()


class DesignFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Design
        django_get_or_create = ("name",)

    # Design fields
    name = factory.Sequence(lambda n: "factory-made design %s" % n)
    pattern_credits = ""
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    designer = factory.SubFactory(DesignerFactory)
    collection = None
    visibility = DC.PUBLIC
    purchase_url = factory.LazyAttribute(lambda o: "http://example.com/%s" % o.slug)
    # Some tests need product IDs guaranteed not to be associated with a design, so the following Sequence
    # was written so as to never assign an ID below 100
    ahd_wp_product_id = factory.Sequence(lambda n: n + 100)
    ahd_wp_variation_id = None
    difficulty = 3
    is_basic = False
    image = SimpleUploadedFile(
        name="image.jpg", content=make_jpeg_bytes(), content_type="image/jpeg"
    )
    cover_sheet = None
    description = ""
    recommended_gauge = ""
    notions = ""
    recommended_materials = ""
    needles = ""
    yarn_notes = ""
    style_notes = ""


###################################################################################
#
# Additional design elements
#
####################################################################################


class AdditionalDesignElementTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdditionalDesignElementTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
        {% load pattern_conventions %}
        <p>
        When piece measures {{start_height | length_fmt}} ({{start_row}} rows from beginning)
        on RS row
        switch to secondary color. Continue as written for {{ height_in_rows }} rows, then
        switch back to primary color.
        </p>
        <p>
        Note: There were {{ piece.cast_ons | count_fmt}} stitches at cast-on.
        </p>
        """


class _AdditionalDesignElementFactoryBase(factory.django.DjangoModelFactory):

    design = factory.SubFactory(DesignFactory)
    name = "Additional design element"
    overlap_behavior = AdditionalDesignElement.OVERLAP_INSTRUCTIONS
    template = factory.SubFactory(AdditionalDesignElementTemplateFactory)
    height_value = 1.0
    height_type = AdditionalDesignElement.HEIGHT_IN_INCHES
    stitch = None
