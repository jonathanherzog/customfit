import logging
import os.path
import urllib.parse
import uuid

import django.template
from dbtemplates.models import Template
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.text import slugify
from polymorphic.models import PolymorphicManager, PolymorphicModel

import customfit.designs.helpers.design_choices as DC
import customfit.stitches.models as stitches
from customfit.fields import LowerLimitValidator
from customfit.helpers.math_helpers import round

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_designer_image_path(instance, filename):
    designer_slug = slugify(instance.full_name)
    unique_filename = "%s%s" % (uuid.uuid4(), filename)
    return os.path.join("designer_images", designer_slug, unique_filename)


def get_image_path(instance, filename):
    unique_filename = "%s%s" % (uuid.uuid4(), filename)
    return os.path.join("classic_images", unique_filename)


class RavelryUrlValidator(URLValidator):
    """
    Check that a value is both a syntactically-valid URL *and* points at
    ravelry.com. No attempt is made to ensure that it is a valid page,
    a public page, or a page that belongs to any given designer.
    """

    message = "Enter a valid URL for ravelry.com."
    rav_domain = "ravelry.com"

    def __call__(self, value):
        super(RavelryUrlValidator, self).__call__(value)
        # If the above did not raise a ValidatorError, then
        # we know that value matches Django's URL regex.
        try:
            parse_result = urllib.parse.urlparse(value)
            assert parse_result.netloc.lower().endswith(self.rav_domain)
        except:
            raise ValidationError("%s does not parse as a Raverly URL" % value)


class Designer(models.Model):
    """
    Represents an individual designer. These designers might not be users,
    and this model is not associated with User accounts.

    Both about_designer_short and about_designer_long are optional.

    * If present, we will use about_designer_long in the About Designer
    section of a pattern.

    * If not, we use about_designer_short.

    * If neither about_designer_long and about_designer_short are present,
    we omit the section entirely (header and text).
    """

    # Let's try to handle a wider variety of human naming schemes.

    full_name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Examples: Taylor Swift, Bjork Gudmundsdottir, "
        "Maria-Jose Carreno Quinones. (ASCII characters only)",
    )

    short_name = models.CharField(
        max_length=50,
        help_text="Examples: Taylor, Mrs. Swift, Bjork, Maria-Jose. "
        "(ASCII characters only)",
    )

    primary_sort_name = models.CharField(
        max_length=150,
        help_text="Examples: Swift, Bjork, Carreno Quinones or "
        "Quinones (depending on her origin and preference). "
        "(ASCII characters only). For internal use only; not "
        "for display.",
    )

    secondary_sort_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Examples: Taylor, Gundmundsdottir, Maria-Jose. "
        "(ASCII characters only). For internal use only; not "
        "for display.",
    )

    primary_home_page = models.URLField(
        blank=True,
        null=True,
        help_text="Home page used when we want to make the designer's "
        "name into a link.",
    )

    secondary_home_page = models.URLField(
        blank=True,
        null=True,
        help_text="Listed after primary home page when explicitly " "listed in text",
    )

    business_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Name of associated business. Example: Taylor Nation, The Sugarcubes. (ASCII characters only.)",
    )

    ravelry_link = models.URLField(
        blank=True,
        null=True,
        validators=[RavelryUrlValidator()],
        help_text="A full URL to the designer's page in Ravelry.",
    )

    about_designer_long = models.TextField(
        blank=True,
        null=True,
        max_length=2000,
        verbose_name="long 'about designer'",
        help_text="1-2 paragraph version of 'About Designer'. Enter " "in markdown",
    )

    about_designer_short = models.TextField(
        blank=True,
        null=True,
        max_length=500,
        verbose_name="short 'about designer'",
        help_text="1-2 sentence version of 'About Designer'. Enter " "in markdown",
    )

    picture = models.ImageField(
        blank=True,
        null=True,
        upload_to=get_designer_image_path,
        help_text="Head shot preferable",
    )

    date_added = models.DateTimeField(auto_now_add=True)

    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    def clean(self):
        errors = []
        try:
            super(Designer, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        # Check-- if we have a secondary home page, do we have a primary?
        if self.secondary_home_page and not self.primary_home_page:
            errors.append(
                ValidationError(
                    "Cannot have secondary home page without primary home page"
                )
            )

        if errors:
            raise ValidationError(errors)

    class Meta:
        get_latest_by = "date_added"
        ordering = ["primary_sort_name", "secondary_sort_name"]


class ExtraFinishingTemplate(Template):
    """
    Extra finishing instructions associated with the design.
    """

    pass


class DisplayableCollectionsManager(models.Manager):
    """
    Custom manager for Collections that only returns collections with
    at least one publicly-visible design in it. We will often want
    to limit our attention to these Collections in our views
    """

    def get_queryset(self):
        all_collections = super(DisplayableCollectionsManager, self).get_queryset()
        displayable_collections = all_collections.filter(
            designs__visibility__in=[DC.PUBLIC, DC.FEATURED]
        )
        return_me = displayable_collections.distinct()
        return return_me


class Collection(models.Model):
    """
    Collections let us feature designs in groups. There is a ForeignKey field
    on Design which points to Collection, allowing for the grouping.
    """

    name = models.CharField(max_length=50, unique=True)
    creation_date = models.DateField(auto_now_add=True)

    # Managers
    #
    # THE ORDER OF MANAGER-DECLARATION IS FRAGILE AND IMPORTANT.
    # If you define any custom managers, Django will interepret the first defined manager
    # to be the default manager. Since Django uses the default manager in
    # model/form validation, it is important that the default manager return
    # all objects. Therefore, it is crucial that we define 'objects' manually
    # and that it appear *first* in the list of managers.
    #
    # See https://docs.djangoproject.com/en/1.8/topics/db/managers/#default-managers for more information
    #
    objects = models.Manager()
    displayable = DisplayableCollectionsManager()

    @property
    def visible_designs(self):
        """
        Return the designs in this collection that are visible to the public
        """
        return [
            design for design in self.designs.all() if design.is_visible_to_public()
        ]

    def __str__(self):
        return self.name

    class Meta:
        get_latest_by = "creation_date"
        ordering = ["-creation_date"]


###############################################################################
#
#  Managers for the Design model
#
###############################################################################

# First, some common queries
publicly_visible = ~Q(visibility=DC.PRIVATE)
featured = Q(visibility=DC.FEATURED)
is_basic = Q(is_basic=True)
# Note that becuase image is a file-field, we need to be careful about
# specifying that the image field have an actual value. Note:
# Q(image__is_null = False) will not actually eliminate designs without images
has_image = ~Q(image="")


class ListableDesignManager(PolymorphicManager):
    """
    Custom manager that returns all the designs that can go in a public list
    of designs:

    * Visibility is not private
    * Has an image

    """

    def get_queryset(self):
        base_queryset = super(ListableDesignManager, self).get_queryset()
        listable_designs = base_queryset.filter(publicly_visible & has_image)
        return listable_designs


class BasicDesignManager(ListableDesignManager):
    """
    A custom manager that limits the initial queryset to listable designs
    that are basics.
    """

    def get_queryset(self):
        base_queryset = super(BasicDesignManager, self).get_queryset()
        return base_queryset.filter(is_basic)


class NonbasicDesignManager(ListableDesignManager):
    """
    A custom manager that limits the initial queryset to listable designs
    that are *not* basic.
    """

    def get_queryset(self):
        base_queryset = super(NonbasicDesignManager, self).get_queryset()
        designed_designs = base_queryset.filter(~is_basic)
        return designed_designs


class FeaturedDesignManager(ListableDesignManager):
    """
    A custom manager that limits the initial queryset to listable designs
    that are featured.
    """

    def get_queryset(self):
        base_queryset = super(FeaturedDesignManager, self).get_queryset()
        return base_queryset.filter(featured)


class CurrentlyPromotedManager(ListableDesignManager):
    """
    Custom manager that limits the Designs to those which are currently
    promoted: those that

    * Are listable, and
    * Are either in the latest collection (if one exists) or are featured.
    """

    # Currently used in customfit.views._get_designs

    def get_queryset(self):
        # Note that due to inheritance, base_queryset will be limited
        # to listable designs: publicly visible, and with pictures
        base_queryset = super(CurrentlyPromotedManager, self).get_queryset()
        try:
            latest_collection = Collection.displayable.latest()
            # No need to filter out those design in the collection that are not
            # visible-- base_queryset has already done this for us.
            in_latest_collection = Q(collection=latest_collection)
            query_filter = featured | in_latest_collection
        except Collection.DoesNotExist:
            query_filter = featured

        return base_queryset.filter(query_filter)


class NegativeRegexValidator(RegexValidator):
    """
    Validates that the field does NOT match the regex. Note: not needed
    once we update to Django 1.7+ which provides this built-in to
    RegexValidator.
    """

    def __call__(self, value):
        # cut-and-copied from Django 1.6 source, with small modification.
        # Note: does NOT call super() on purpose
        if self.regex.search(force_str(value)):
            raise ValidationError(self.message, code=self.code)


class Design(PolymorphicModel):

    # Subclasses must implement:
    #
    # *     def compatible_swatch(self, swatch):
    #         """
    #         Return True iff the swatch is compatible with this design
    #         """
    # * def uses_stitch(self, stitch):
    #     # Returns True if the Design uses the Stitch in any way. To be implemented
    #     # by subclasses
    # * isotope_classes(self):
    #       returns space-separated list of classes to use in all-designs page for Isotope filtering

    name = models.CharField(max_length=100)

    pattern_credits = models.CharField(
        max_length=100,
        blank=True,
        help_text="For any non-authorship and non-photography credits. "
        "Example: 'Technical editing: Jane Doe.'",
    )

    slug = models.SlugField(
        unique=True,
        # Note: we used to embed a design's pk in URLs, but have switched to
        # using slugs instead. But we want to gracefully handle the old URLs
        # still, and so we have a special url pattern for all-digit design-
        # identifiers. Thus, these slugs cannot be all-digits. Note that
        # The slug field already tests that the slug is not empty.
        validators=[
            NegativeRegexValidator(
                regex="^[0-9]+$", message="slug cannot be just digits"
            )
        ],
        help_text="A URL-friendly form of the design's name. Since this is used in "
        "URLs, it should not be changed from its initial value. Valid "
        "characters include: numbers, letters, hypens, and underscores. "
        "(We recommend that you replace spaces with hyphens, for "
        "consistent stlying.) Do not use an all-number value, however, as "
        "this would conflict with our special handling of old-style design "
        "URLs.",
    )

    designer = models.ForeignKey(
        Designer, related_name="designs", on_delete=models.CASCADE, help_text="Required"
    )

    collection = models.ForeignKey(
        Collection,
        related_name="designs",
        null=True,
        on_delete=models.CASCADE,
        blank=True,
    )

    visibility = models.CharField(
        max_length=7, choices=DC.VISIBILITY_CHOICES, default=DC.PRIVATE
    )

    purchase_url = models.CharField(
        max_length=100,
        help_text="Relative URL where credits for this design can be purchased. "
        "If the URL is 'http://example.com/design_foo', for example, put 'design_foo' "
        "here. The base URL is taken from the AHD_WC_PRODUCTS_BASE_URL setting/env. "
        "NOTE: If you enter a path here with a leading slash ('/design_foo') it will "
        "override any path in AHD_WC_PRODUCTS_BASE_URL. Don't do this unless you really "
        "want to hard-code the entire path here for some reason.",
    )

    ahd_wp_product_id = models.IntegerField(
        help_text="The product ID (not variation ID) of this design in WooCommerce"
    )

    ahd_wp_variation_id = models.IntegerField(
        blank=True,
        null=True,
        help_text="The variation ID (not product ID) of this design in WooCommerce",
    )

    # Note: the difficulty rating and the is_basic flags
    # will be correlated in practice, but the code should allow them to
    # vary independently.
    difficulty = models.IntegerField(
        help_text="Difficulty rating for this design",
        choices=DC.DESIGN_DIFFICULTY_CHOICES,
    )

    # What is a 'basic' sweater? I'm told that
    # is a term that has meaning to knitters, and will *correlate* with
    # low difficulty ratings, few-to-none custom templates, well-known
    # stitches, etc. Having said that, also tells me that there is no crisp
    # definition for this term that we can or should enforce in clean().
    # So rather than trying to derive this property from anything else in the
    # model, we should let the humans decide
    # and simply tag Designs as 'basic' using a boolean flag.
    is_basic = models.BooleanField(
        help_text="Is this a 'basic' sweater?", default=False
    )
    image = models.FileField(upload_to=get_image_path, blank=True, null=True)

    cover_sheet = models.FileField(
        upload_to=get_image_path,
        blank=True,
        null=True,
        help_text="A one- or two-page PDF file to be the first pages of "
        "all PDFs for patterns made from this design. Make it "
        "pretty! Also, make sure that it's letter-page sized, "
        "because it will be added to PDF versions of patterns "
        "even it it's not.",
    )

    description = models.TextField(
        blank=True,
        help_text="Short description of the design to be displayed to "
        "users when they click on it.",
    )

    # Though we provide perfectly good defaults for the following, desginers
    # may want to write their own copy

    recommended_gauge = models.CharField(
        max_length=200,
        blank=True,
        help_text="Text to go under the 'Recommended Gauge' heading. "
        "Will be skipped if absent.",
    )

    notions = models.CharField(max_length=200,
         blank=True,
         help_text="Text to add under the 'Notions' heading. "
                   "Will be 'Stitch markers, stitch holder, darning needle' if blank.")

    recommended_materials = models.TextField(
        blank=True,
        help_text="Text to go under the 'Recommended Materials' heading. "
        "Will be skipped if absent. Enter in markdown. Largest"
        "header size should be h3.",
    )

    needles = models.CharField(
        max_length=200,
        blank=True,
        help_text="Text to go under the 'Needles' heading. "
        "Will be skipped if absent.",
    )

    yarn_notes = models.TextField(
        blank=True,
        help_text="1 to 2 paragraphs recommended. Follows " "description in pattern.",
    )

    style_notes = models.TextField(
        blank=True, help_text="Example: 'style adjustment for different bodies'"
    )

    # Managers
    #
    # THE ORDER OF MANAGER-DECLARATION IS FRAGILE AND IMPORTANT.
    # If you define any custom managers, Django will interepret the first defined manager
    # to be the default manager. Since Django uses the default manager in
    # model/form validation, it is important that the default manager return
    # all objects. Therefore, it is crucial that we define 'objects' manually
    # and that it appear *first* in the list of managers.
    #
    # See https://docs.djangoproject.com/en/1.8/topics/db/managers/#default-managers for more information
    #
    objects = PolymorphicManager()
    listable = ListableDesignManager()
    designed = NonbasicDesignManager()
    basic = BasicDesignManager()
    currently_promoted = CurrentlyPromotedManager()
    featured = FeaturedDesignManager()

    def get_absolute_url(self):
        return reverse("design_wizard:personalize", kwargs={"design_slug": self.slug})

    def get_full_purchase_url(self):
        base_url = settings.AHD_WC_PRODUCTS_BASE_URL
        full_url = urllib.parse.urljoin(base_url, self.purchase_url)
        return full_url

    def is_visible_to_public(self):
        """
        Return true iff this Design is visible to the public
        """
        return self.visibility in [DC.PUBLIC, DC.FEATURED]

    def is_visible_to_user(self, user):
        """
        Takes a user; tells you if that user can see this design.
        Used in making designs visible (they're invisible by default) and
        limiting designs to subscribers.
        """
        # Everyone can see public and featured
        if self.visibility in [DC.FEATURED, DC.PUBLIC]:
            return True
        # Anonymous users should not be able to see
        # anything else. Put this here so we can assume the user
        # is authenticated from here on out
        elif not user.is_authenticated:
            return False

        # Corner cases for staff
        elif self.visibility == DC.LIMITED:
            return user.is_staff
        else:
            assert self.visibility == DC.PRIVATE
            return user.is_staff

    def __str__(self):
        return "%s" % self.name

    class Meta:
        ordering = ["name"]


class DesignAlternatePicture(models.Model):
    """
    For the gallery of alternate images that can appear thumbnailed under
    the main image on the personalize-design page. Or, I suppose, for wherever
    else you might want alternate images.
    """

    design = models.ForeignKey(
        Design, related_name="alternate_images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to=get_image_path)

    def __str__(self):
        return "Alternate pic for %s" % self.design

    class Meta:
        abstract = False


class AdditionalDesignElementTemplate(Template):
    """
    Instructions associated with an AdditionalDesignElement.
    """

    # Note: we add help-text to this model in the admin interface. See admin.py
    pass


class AdditionalDesignElement(models.Model):
    # A place to define the idea of an Additional Element: a set of instructions that are one-off
    # for a particular design. They should have:
    # * A name,
    # * A link to the relevant design,
    # * A start location,
    # * A height,
    # * A template,
    # * An optional link to a stitch pattern
    # * A flag indicating it's 'overlap' behavor. (See below)
    #
    # The 'start location' gets tricky, though, as designers would like to say
    # things like "3 inches before neckline" and "5 inches after sleeve cast-on". Therefore, we
    # declare this to be an abstract base model, to hold common fields and methods, but declare
    # 'real' models for the following situations:
    #
    # * 'Sleeve' elements,
    # * 'Back-only' elements,
    # * 'Front-only' elements (will be included in pullover-fronts once, and once in *each* cardigan side), and
    # * 'Full-torso' elements (those which *must* match, row-for-row, on front and back).
    #
    # Note: the assumption is that any change to an additional element *must* propogate to all patterns
    # made from the associated design. Therefore, pattern-text generation must go through Designs--
    # AdditionalDesignElements should not be copied to PatternSpecs. Therefore, we link AdditionalDesignElements
    # directly to Designs. (No, they should not be shared by multiple designs.)

    design = models.ForeignKey(
        Design,
        db_index=True,
        on_delete=models.CASCADE,
        help_text="The design that should include this additional element",
    )

    name = models.CharField(max_length=100, help_text="Note: will be visible to users")

    template = models.ForeignKey(
        AdditionalDesignElementTemplate,
        related_name="+",  # We don't need a backwards relation
        on_delete=models.CASCADE,
        help_text="Template for this additional-element. Note: Template should start with "
        "{% load pattern_conventions %} and be 'complete' "
        "HTML (include liminal p or h3 tags). The associated piece will be available"
        "under the name 'piece'.",
    )

    stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_stitch",
        limit_choices_to=Q(is_panel_stitch=True) | Q(is_allover_stitch=True),
    )

    # Heights are expressed as a tuple:
    #  * A non-negative float value, and
    #  * A choice-parameter indicating whether it's in inches or rows -- or 'no end', meaning that it goes to
    #    the end of the piece.
    # (If the choice is 'no end', the the value is ignored.)
    # If it's a row-valued height, we validate the float to ensure that it represents an integer value.
    # If an element has 'no' height-- meaning it occurs / starts and ends entirely in 1 row, then the
    # user should say that its height is 1 row.

    HEIGHT_IN_INCHES = "height_in_inches"
    HEIGHT_IN_ROWS = "height_in_rows"
    HEIGHT_NO_END = "height_no_end"
    HEIGHT_TYPE_CHOICES = [
        (HEIGHT_IN_INCHES, "inches"),
        (HEIGHT_IN_ROWS, "rows"),
        (HEIGHT_NO_END, "no end"),
    ]

    height_value = models.FloatField(
        validators=[LowerLimitValidator(0)],  # Validation fails if value is 0 or less
        help_text="If height is row-valued, the row-count should be an integer that includes start *and* end row. "
        "Elements with 'no' height should be entered as having height of 1 row. "
        "Note: this value is ignored if the element's height is 'no end'.",
    )
    height_type = models.CharField(
        max_length=20,
        help_text="Elements with 'no' height should be entered as having height of 1 row.",
        choices=HEIGHT_TYPE_CHOICES,
        default=HEIGHT_IN_INCHES,
    )

    # When we turn these additional elements into patterntext, we will need to know the intended
    # 'overlap' behavior. Suppose that the element starts during bust shaping, but the neckline
    # starts during the element. Which overlaps do we want in the patternttext? This depends
    # on the element in question. IN theory, there are four possibilities-- but we use only three:
    #
    # 'purely informational': neither warning is appropriate
    # 'standard instruction': both warnings are appropriate
    # 'start only': Warn that the element starts during shaping, but not that the neckline starts during the element
    #
    # (The fourth option-- neckline but not shaping-- is never needed, apparently).
    # This next field allows the designer to specify the behavior they want for the element
    OVERLAP_PURELY_INFORMATIONAL = "overlap_inform"
    OVERLAP_INSTRUCTIONS = "overlap_instruct"
    OVERLAP_START_ONLY = "overlap_start"
    OVERLAP_CHOICES = [
        (OVERLAP_PURELY_INFORMATIONAL, "purely informational"),
        (OVERLAP_INSTRUCTIONS, "instructions"),
        (OVERLAP_START_ONLY, "start only"),
    ]

    overlap_behavior = models.CharField(max_length=20, choices=OVERLAP_CHOICES)

    def clean(self):
        super(AdditionalDesignElement, self).clean()

        # If the height is row-valued, then the height's numeric-value must encode an integer
        if self.height_type == self.HEIGHT_IN_ROWS:
            # Note that the following test agrees that 3, 3.0, 0, 0.0, -3 and -3.0 are all int-valued
            height_is_int_valued = int(self.height_value) == self.height_value
            if not height_is_int_valued:
                raise ValidationError(
                    {
                        "height_value": "Row-valued heights must be integers, like 3, 4.0, -3.0, 0, or 0.0"
                    }
                )

    def get_template(self):
        return django.template.Template(
            self.template.content,
            # Why do we add the name?
            # For unit testing
            name=self.name,
        )

    def height_in_rows(self, gauge):
        """
        Returns the height of this element, in rows. Will include both the start row and end row. Will never be
        less than 1. If the height is inch-valued, then this will always return an even number of rows
        """
        if self.height_type == self.HEIGHT_NO_END:
            return float("inf")
        elif self.height_type == self.HEIGHT_IN_ROWS:
            assert self.height_value >= 1
            return self.height_value
        else:
            assert self.height_type == self.HEIGHT_IN_INCHES
            # Need to convert using gauge
            rows_float = self.height_value * gauge.rows
            rows_int = round(rows_float, multiple=2, mod=0)
            if rows_int < 2:
                return 2
            else:
                return int(rows_int)

    def interrupts_others(self):
        return self.overlap_behavior in [
            self.OVERLAP_INSTRUCTIONS,
            self.OVERLAP_START_ONLY,
        ]

    def warn_if_interrupted(self):
        return self.overlap_behavior == self.OVERLAP_INSTRUCTIONS

    class Meta:
        abstract = True
