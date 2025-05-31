"""
Created on Jun 22, 2012
"""

import copy
import logging
from os.path import join

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import model_to_dict
from django.urls import reverse

from customfit.fields import (
    GramsField,
    LongLengthField,
    NonNegSmallIntegerField,
    PositiveFloatField,
    PositiveLengthField,
    StrictPositiveSmallIntegerField,
)
from customfit.helpers.magic_constants import CM_PER_INCHES
from customfit.helpers.math_helpers import ROUND_ANY_DIRECTION, round
from customfit.patterns.templatetags.pattern_conventions import (
    length_fmt,
    length_long_fmt,
)
from customfit.stitches.models import UNKNOWN_STITCH_TYPE, Stitch

from .helpers import area_to_yards_of_yarn_estimate

logger = logging.getLogger(__name__)


class UnarchivedSwatchManager(models.Manager):
    """
    This class will act as the default manager for the Swatch model. If differs
    from the standard manager only in that its initial query set filters out
    archived swatches and returns only unarchived ones.
    """

    def get_queryset(self):
        return (
            super(UnarchivedSwatchManager, self).get_queryset().filter(archived=False)
        )


FOUR_INCHES = 4.0


class Swatch(models.Model):
    """
    Notes:

    * Due to changing needs of the UI, we have added human-readable names
    that get automatically transferred to labels in the ModelForm.

    * The `objects` manager has been modified to act 'safely' and return only unarchived swatches.
    If you really need access to all swatches, even unarchived ones, use the `even_archived`
    manager.

    """

    user = models.ForeignKey(
        User, db_index=True, related_name="swatches", on_delete=models.CASCADE
    )
    creation_date = models.DateTimeField(auto_now_add=True)
    name = models.CharField("name your gauge", max_length=50)
    notes = models.TextField("notes on swatch", blank=True)
    archived = models.BooleanField(default=False)

    stitches_number = PositiveFloatField(
        "stitch gauge",
        help_text="Number of stitches in swatch, along 'stitches' " "side of swatch",
    )

    stitches_length = PositiveLengthField(
        help_text="Precise length of the 'stitches' side of your swatch, " "in inches"
    )

    rows_length = PositiveLengthField(
        "row gauge", help_text="Precise length of the 'rows' side of swatch, in inches"
    )
    rows_number = PositiveFloatField(
        help_text="Number of rows in swatch, along 'rows' side of swatch"
    )

    use_repeats = models.BooleanField(
        help_text="If true, swatch was made using repeats", default=False
    )
    stitches_per_repeat = StrictPositiveSmallIntegerField(
        help_text="Number of stitches in a single repeat", null=True, blank=True
    )
    additional_stitches = NonNegSmallIntegerField(
        help_text="Number of stitches in addition to the repeated stitches (both before and after, combined)",
        null=True,
        blank=True,
    )

    yarn_name = models.CharField(max_length=100, null=True, blank=True)
    yarn_maker = models.CharField("yarn company", max_length=100, null=True, blank=True)

    length_per_hank = LongLengthField(
        "length per skein",
        help_text="How much yarn (in yards) in a hank?",
        null=True,
        blank=True,
    )

    weight_per_hank = GramsField(
        "weight per skein",
        help_text="How much does a hank weigh (in grams)?",
        null=True,
        blank=True,
    )

    full_swatch_height = PositiveLengthField(
        "full height of swatch",
        null=True,
        blank=True,
        help_text="How long (in inches) is the full swatch along " "the row edge?",
    )

    full_swatch_width = PositiveLengthField(
        "full width of swatch",
        null=True,
        blank=True,
        help_text="How long (in inches) is the full swatch along " "the stitch edge?",
    )

    full_swatch_weight = GramsField(
        "weight of swatch (in grams)",
        null=True,
        blank=True,
        help_text="How much does the full swatch weigh, in grams?",
    )

    needle_size = models.CharField(
        "needle info",
        max_length=100,
        help_text="This will be treated as text, so please describe your needles however it makes sense to you.",
        null=True,
        blank=True,
    )

    # The on_delete parameter ensures that, if the SwatchPicture is deleted,
    # there is NOT a cascade which also deletes the Swatch.
    # We're referencing by label rather than importing SwatchPicture directly to
    # avoid circular import hell: https://docs.djangoproject.com/en/1.5/ref/models/fields/#foreignkey
    # save() ensures that the featured_pic's swatch is THIS swatch.
    featured_pic = models.ForeignKey(
        "uploads.SwatchPicture", blank=True, null=True, on_delete=models.SET_NULL
    )

    @property
    def patterns(self):
        # putting this import at the top level was throwing ImportErrors
        # The simplest way to do this is
        #   patterns = [pattern for pattern in IP.objects.all() if pattern.get_spec_source().swatch == self]
        # But this is way too slow. So we need to push this to the database and get those patterns where
        #
        # 1) self is the swatch in the patterns original patternspec and it hasn't been redone, or
        # 2) the pattern has been redone and self is the swatch of the redo
        from django.db.models import Q

        from customfit.patterns.models import IndividualPattern as IP

        # self is the swatch of the pattern's current spec_source and it hasnt been redone
        q_pspec = Q(
            pieces__schematic__individual_garment_parameters__pattern_spec__swatch=self
        )

        # self is the swatch of the pattern's current spec_source and it has been redone
        q_redo = Q(pieces__schematic__individual_garment_parameters__redo__swatch=self)

        patterns = IP.objects.filter(q_pspec | q_redo).all()

        return patterns

    @property
    def details(self):
        details = []
        details.append(
            {
                "name": "Stitches",
                "field_key": "stitches",
                "value": str(self.stitches_number)
                + " in "
                + length_fmt(
                    self.stitches_length,
                    precision_imperial=1.0 / 8,
                    precision_metric=0.1,
                ),
            }
        )
        details.append(
            {
                "name": "Rows",
                "field_key": "rows",
                "value": str(self.rows_number)
                + " in "
                + length_fmt(
                    self.rows_length, precision_imperial=1.0 / 8, precision_metric=0.1
                ),
            }
        )
        details.append(
            {
                "name": "Needle size",
                "field_key": "needle_size",
                "value": self.needle_size,
            }
        )

        if self.use_repeats:
            if self.additional_stitches == 1:
                additional = "stitch"
            else:
                additional = "stitches"
            # No need to deal with pluralization of stitches_per_repeat
            # because a 1-stitch repeat is meaningless.
            details.append(
                {
                    "name": "Repeats",
                    "field_key": "repeats",
                    "value": str(self.stitches_per_repeat)
                    + " stitches per repeat; "
                    + str(self.additional_stitches)
                    + " additional %s" % additional,
                }
            )
        else:
            details.append(
                {"name": "Repeats", "field_key": "repeats", "value": "No repeats"}
            )

        if self.yarn_name:
            details.append(
                {"name": "Yarn", "field_key": "yarn_name", "value": self.yarn_name}
            )
        if self.yarn_maker:
            details.append(
                {"name": "Maker", "field_key": "yarn_maker", "value": self.yarn_maker}
            )
        if self.length_per_hank:
            details.append(
                {
                    "name": "Length per hank",
                    "field_key": "length_per_hank",
                    "value": length_long_fmt(self.length_per_hank),
                }
            )
        if self.weight_per_hank:
            details.append(
                {
                    "name": "Weight per hank",
                    "field_key": "weight_per_hank",
                    "value": str(self.weight_per_hank) + " g",
                }
            )
        if self.full_swatch_weight:
            details.append(
                {
                    "name": "Weight of swatch",
                    "field_key": "full_swatch_weight",
                    "value": str(self.full_swatch_weight) + " g",
                }
            )
        if self.full_swatch_height:
            details.append(
                {
                    "name": "Height of full swatch",
                    "field_key": "full_swatch_height",
                    "value": length_fmt(
                        self.full_swatch_height,
                        precision_imperial=1.0 / 8,
                        precision_metric=0.1,
                    ),
                }
            )
        if self.full_swatch_width:
            details.append(
                {
                    "name": "Width of full swatch",
                    "field_key": "full_swatch_width",
                    "value": length_fmt(
                        self.full_swatch_width,
                        precision_imperial=1.0 / 8,
                        precision_metric=0.1,
                    ),
                }
            )

        return details

    @property  # used in design_choices_base.html
    def stitches_in_four_inches(self):
        gauge = self.get_gauge()
        exact_answer = FOUR_INCHES * gauge.stitches
        return self._round_to_one_fourth(exact_answer)

    @property  # used in design_choices_base.html
    def rows_in_four_inches(self):
        gauge = self.get_gauge()
        exact_answer = FOUR_INCHES * gauge.rows
        return self._round_to_one_fourth(exact_answer)

    @property  # used in design_choices_base.html
    def stitches_in_ten_cm(self):
        gauge = self.get_gauge()
        exact_answer = gauge.stitches * 10 / CM_PER_INCHES
        return self._round_to_one_fourth(exact_answer)

    @property  # used in design_choices_base.html
    def rows_in_ten_cm(self):
        gauge = self.get_gauge()
        exact_answer = gauge.rows * 10 / CM_PER_INCHES
        return self._round_to_one_fourth(exact_answer)

    def area_to_weight(self, square_inches):
        """
        Convert a square-inch count (of a garment, say) to
        the weight of that fabric if knit in this swatch.
        Returns None is this instance does not have the needed
        information. Note: not rounded.
        """
        if all(
            [self.full_swatch_height, self.full_swatch_width, self.full_swatch_weight]
        ):

            swatch_area = self.full_swatch_height * self.full_swatch_width

            grams_per_square_inch = self.full_swatch_weight / swatch_area

            return square_inches * grams_per_square_inch

        else:
            return None

    def area_to_hanks(self, square_inches):
        """
        Convert a given amount of fabric, knit similar to this swatch, into
        a number of hanks. Returns None if this instance does not have the
        needed values. Note: not rounded.
        """
        weight = self.area_to_weight(square_inches)
        if all([weight, self.weight_per_hank]):
            return weight / self.weight_per_hank
        else:
            return None

    def area_to_yards_of_yarn(self, square_inches):
        """
        Convert a given area of fabric, in square-inches, to yards of
        yarn required to knit it in the same fabric as this swatch. Actually
        returns a tuple: (yardage, precise). If the swatch has the values needed
        to make a precise estimate, it will do so and the second return value
        will be True. Otherwise, a crude approximation will be used and the
        second return value will be False. Note: not rounded.
        """
        hanks = self.area_to_hanks(square_inches)
        if all([hanks is not None, self.length_per_hank]):
            yards_needed = hanks * self.length_per_hank
            return (yards_needed, True)
        else:
            # Get range-bounds (lower) from the magic constants.
            # Use binary search to find the range we're in.
            # Make a crude estimate
            gauge = self.get_gauge()
            yards_needed = area_to_yards_of_yarn_estimate(square_inches, gauge)
            return (yards_needed, False)

    def _round_to_one_fourth(self, val):
        return_me = round(val, ROUND_ANY_DIRECTION, 0.25)
        if return_me == int(return_me):
            return int(return_me)
        else:
            return return_me

    def get_stitch(self):
        """
        Returns the allover-stitch of this swatch in s StitchSpec
        """
        if self.use_repeats:
            return Stitch(
                is_allover_stitch=True,
                stitch_type=UNKNOWN_STITCH_TYPE,
                repeats_x_mod=self.additional_stitches,
                repeats_mod_y=self.stitches_per_repeat,
            )
        else:
            return Stitch(is_allover_stitch=True, stitch_type=UNKNOWN_STITCH_TYPE)

    def clean(self):
        errors = []
        # Test 1: if they use repeats, make sure necessary values are present
        if self.use_repeats:
            if self.stitches_per_repeat == None:
                errors.append(ValidationError("Value needed for stitches-per-repeat"))
            if self.additional_stitches == None:
                errors.append(
                    ValidationError("Value needed for non-repeated additional stitches")
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.featured_pic:
            # Make sure that any featured pic is actually of THIS swatch.
            if self.featured_pic.object != self:
                self.featured_pic = None
        super(Swatch, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        We used to go through some rigamarole to detect if the swatch was 'safe' to delete (meaning: not
        used in any patterns) but that turned out to age badly. It needed to hard-code in the internal
        structure of patterns, which meant that our rigamarole became unsafe when we changed that internal
        structure. So, we just always archive instead.

        _Note that this method is not called when deleting querysets in
        bulk_: https://docs.djangoproject.com/en/1.6/topics/db/queries/#topics-db-queries-delete

        If you are deleting swatch querysets in bulk, you may inadvertently
        delete swatches with associated patterns. Don't do that.
        """
        logger.info("Archiving swatch %s.", self.pk)
        self.archived = True
        self.save()

    def __str__(self):
        return "%s" % self.name

    def to_dict(self):
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, to_dict, user):
        to_dict = copy.copy(to_dict)
        to_dict["user"] = user
        if "id" in to_dict:
            del to_dict["id"]
        return cls(**to_dict)

    def get_gauge(self):
        gauge = Gauge.make_from_swatch(self)
        return gauge

    def get_absolute_url(self):
        return reverse("swatches:swatch_detail_view", kwargs={"pk": self.id})

    @property
    def preferred_picture_url(self):
        if self.featured_pic:
            return self.featured_pic.picture.url
        try:
            picture = self.pictures.all()[0].picture.url
        except IndexError:
            picture = join(settings.STATIC_URL, "img/My_Gauge.png")
        return picture

    @property
    def preferred_picture_file(self):
        """
        Returns the file of the preferred pic if available (otherwise None).
        This allows thumbnail_url to operate on the preferred pic in templates.
        """
        if self.featured_pic:
            return self.featured_pic.picture
        try:
            picture = self.pictures.all()[0].picture
        except IndexError:
            picture = None
        return picture

    # THE NEXT TWO LINES ARE A LANDMINE WAITING FOR US TO TRIP ON IT
    #
    # To keep things 'safe', we decided to set 'objects' to a custom manager that would exclude archived
    # bodies and to create a specia manager 'even_archived' that would return all bodies. And then we set
    # 'objects' to be defined first, and thus be the default manager. This will break certain kinds of Django
    # magic. ForeignKey fields that point at Body, for example, will be fragile and will break when Django
    # tries to perform automatic verification. Take BodyLinkage, which has a ForeignKey that points at Body.
    # If we ever try to create a BodyLinkage that points to an archived body, it will probably break during
    # model validation. (And if we tried to create that BodyLinkage through a ModelForm, as we would in the
    # admin interface, it will break in the ModelForm as well.) Why? Becuase Django will want to confirm that
    # the ForeignKey field points at a real Body, try to find it through the default manager, and fail.
    #
    # We could simply re-order the two managers and make `even_unarchived` the default manager. This has
    # a different set of risks. In particular, backwards relations. If we ever try to go 'backwards' from a
    # ForeignKey field to Body (e.g., User.body_set) then Django uses the default manager-- and we would get all
    # Bodies associated with that user, not just the unarchived ones. To really fix this, we would need to
    # find all instances of these backwards relations in our code and force them to use the `objects` manager
    # (e.g., User.body_set(manager = 'objects')). And then we would need to figure out how to remember that
    # we need to do this when writing code in the future.
    #
    # For the moment, we're going to live with this the way it is now. Why? A few reasons. First, things seem to
    # work. Second, it kind of makes sense that we would not want to create new model-instances that link to
    # archived bodies. Maybe this is the right behavior after all. And third, future versions of Django might
    # present us with with more elegant ways of solving this problem than we have now.
    #
    # See BodyLinkage, PatternLinkage, Body, and SwatchLinkage for other instances of this situation.
    #
    # See https://docs.djangoproject.com/en/1.8/topics/db/managers/#default-managers for more information
    objects = UnarchivedSwatchManager()
    even_archived = models.Manager()

    class Meta:
        app_label = "swatches"
        verbose_name_plural = "swatches"
        ordering = ["creation_date"]


class UnarchivedSwatchLinkageManager(models.Manager):
    """
    This class will act as the default manager for the SwatchLinkage model. If differs
    from the standard manager only in that its initial query set filters out (eliminates)
    linkages that point to archived bodies.
    """

    def get_queryset(self):
        return (
            super(UnarchivedSwatchLinkageManager, self)
            .get_queryset()
            .filter(swatch__archived=False)
        )


class Gauge(object):

    def __init__(self, stitches, rows, use_repeats=False, x_mod=None, mod_y=None):
        super(Gauge, self).__init__()
        self.stitches = stitches
        self.rows = rows
        self.use_repeats = use_repeats
        self.x_mod = x_mod
        self.mod_y = mod_y

    @classmethod
    def make_from_swatch(cls, swatch):
        """
        Makes, validates, and returns a Gauge object from a Swatch object.

        :type swatch: Swatch
        :rtype: Gauge
        """

        stitches = swatch.stitches_number / swatch.stitches_length
        rows = swatch.rows_number / swatch.rows_length

        user = swatch.user
        name = swatch.name
        use_repeats = swatch.use_repeats
        if use_repeats:
            x_mod = swatch.additional_stitches
            mod_y = swatch.stitches_per_repeat
        else:
            x_mod = None
            mod_y = None

        return cls(stitches, rows, use_repeats, x_mod, mod_y)
