"""
This module holds the classes/models for body measurements. It
contains only a single model, Body, which holds the core measurements
for one single body. 

If/when we decide to support graded patterns for
designers, we will want to add a Grade model.
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

from customfit.fields import LengthField, PositiveLengthField

logger = logging.getLogger(__name__)


# Body type: adult man, adult woman, child, unstated.
#
# Our code was written under the assumption that all bodies belong to adult
# women. body_type_unstated is frequently handled as if it were
# body_type_adult_woman, but is not guaranteed to be.


class _HasBodyType(models.Model):
    BODY_TYPE_ADULT_MAN = "body_type_adult_man"
    BODY_TYPE_ADULT_WOMAN = "body_type_adult_woman"
    BODY_TYPE_CHILD = "body_type_child"
    BODY_TYPE_UNSTATED = "body_type_unstated"
    BODY_TYPE_CHOICES = [
        (BODY_TYPE_ADULT_WOMAN, "Adult woman"),
        (BODY_TYPE_ADULT_MAN, "Adult man"),
        (BODY_TYPE_CHILD, "Child"),
        (BODY_TYPE_UNSTATED, "I'd prefer not to say"),
    ]

    body_type = models.CharField(
        choices=BODY_TYPE_CHOICES, max_length=25, default=BODY_TYPE_UNSTATED
    )

    @property
    def is_man(self):
        return self.body_type == self.BODY_TYPE_ADULT_MAN

    @property
    def is_woman(self):
        return self.body_type == self.BODY_TYPE_ADULT_WOMAN

    @property
    def is_child(self):
        return self.body_type == self.BODY_TYPE_CHILD

    @property
    def is_unstated_type(self):
        return self.body_type == self.BODY_TYPE_UNSTATED

    class Meta:
        abstract = True


class MeasurementSet(models.Model):
    """
    Model for just the measurements of a body. Abastract, and will be
    instantiated/extended by Body and Grade
    """

    waist_circ = LengthField(
        "waist circumference", help_text="Full circumference, in inches"
    )

    bust_circ = LengthField(
        "full bust/chest", help_text="Full circumference, in inches"
    )

    upper_torso_circ = LengthField(
        "upper torso circumference",
        blank=True,
        null=True,
        help_text="Full circumference, in inches",
    )

    wrist_circ = LengthField(
        "wrist circumference", help_text="Full circumference, in inches"
    )

    forearm_circ = LengthField(
        "forearm circumference",
        blank=True,
        null=True,
        help_text="Full circumference, in inches",
    )

    bicep_circ = LengthField(
        "bicep circumference", help_text="Full circumference, in inches"
    )

    elbow_circ = LengthField(
        "elbow circumference",
        blank=True,
        null=True,
        help_text="Full circumference, in inches",
    )

    armpit_to_short_sleeve = LengthField(
        "short sleeve to armhole",
        blank=True,
        null=True,
        help_text="Distance, in inches, from armhole shaping down to "
        "the bottom of a short sleeve",
    )

    armpit_to_elbow_sleeve = LengthField(
        "elbow sleeve to armhole",
        blank=True,
        null=True,
        help_text="Distance, in inches, from the armhole shaping down to "
        "the bottom of an elbow sleeve",
    )

    armpit_to_three_quarter_sleeve = LengthField(
        "3/4 sleeve to armhole",
        blank=True,
        null=True,
        help_text="Distance, in inches, from armhole shaping down to "
        "the bottom of a three-quarter sleeve",
    )

    armpit_to_full_sleeve = LengthField(
        "long sleeve length (from armhole to cuff)",
        help_text="Distance, in inches, from armhole shaping down to "
        "the bottom of a full sleeve",
    )

    inter_nipple_distance = LengthField(
        "inter-nipple distance", blank=True, null=True, help_text="In inches"
    )

    armpit_to_waist = LengthField(
        "waist (up) to armhole shaping",
        blank=True,
        null=True,
        help_text="Length (in inches), from armhole-shaping to waist",
    )

    armhole_depth = PositiveLengthField(
        "armhole depth",
        help_text="In inches, from shoulder going straight down to armhole height",
    )

    armpit_to_high_hip = LengthField(
        "short sweater length from armhole to hem",
        blank=True,
        null=True,
        help_text="Length (in inches) from armhole-shaping to high-hip",
    )

    high_hip_circ = PositiveLengthField(
        "body circumference at short sweater hem",
        blank=True,
        null=True,
        help_text="Circumference (in inches) around body at high-hip",
    )

    armpit_to_med_hip = LengthField(
        "average sweater length from armhole to hem",
        help_text="Length (in inches) from armhole-shaping to medium-hip",
    )

    med_hip_circ = PositiveLengthField(
        "body circumference at average sweater hem",
        help_text="Circumference (in inches) around body at medium-hip",
    )

    armpit_to_low_hip = LengthField(
        "long sweater length from armhole to hem",
        blank=True,
        null=True,
        help_text="Length (in inches) from armhole-shaping to low-hip",
    )

    low_hip_circ = PositiveLengthField(
        "body circumference at long sweater hem",
        blank=True,
        null=True,
        help_text="Circumference (in inches) around body at low-hip",
    )

    armpit_to_tunic = LengthField(
        "tunic sweater length from armhole to hem",
        blank=True,
        null=True,
        help_text="Length (in inches) from armhole-shaping to tunic-length",
    )

    tunic_circ = PositiveLengthField(
        "body circumference at tunic sweater hem",
        blank=True,
        null=True,
        help_text="Circumference (in inches) around body at tunic-hem height",
    )

    cross_chest_distance = PositiveLengthField(
        "cross-chest distance",
        blank=True,
        null=True,
        help_text='Optional. (If left blank, subsequent models will compute " \
            "a default value where needed.',
    )

    def clean(self):

        super(MeasurementSet, self).clean()

        validation_errors = []

        # Test 1: Do the sleeve-lengths make sense?
        if all(
            [
                self.armpit_to_elbow_sleeve is not None,
                self.armpit_to_short_sleeve is not None,
            ]
        ):
            if self.armpit_to_elbow_sleeve < self.armpit_to_short_sleeve:
                validation_errors.append(
                    ValidationError(
                        "Shoulder-to-elbow-sleeve "
                        "measurement must be longer than shoulder-to-short-sleeve."
                    )
                )

        if all(
            [
                self.armpit_to_three_quarter_sleeve is not None,
                self.armpit_to_elbow_sleeve is not None,
            ]
        ):
            if self.armpit_to_three_quarter_sleeve < self.armpit_to_elbow_sleeve:
                validation_errors.append(
                    ValidationError(
                        "Shoulder-to-three-quarter-sleeve "
                        "measurement must be longer than shoulder-to-elbow-sleeve."
                    )
                )

        if self.armpit_to_three_quarter_sleeve is not None:
            if self.armpit_to_full_sleeve < self.armpit_to_three_quarter_sleeve:
                validation_errors.append(
                    ValidationError(
                        "Shoulder-to-full-sleeve "
                        "measurement must be longer than shoulder-to-three-quarter-sleeve."
                    )
                )

        if self.armpit_to_high_hip is not None:
            if self.armpit_to_med_hip < self.armpit_to_high_hip:
                validation_errors.append(
                    ValidationError(
                        "Short sweater length must be "
                        "shorter than average sweater length."
                    )
                )

        if self.armpit_to_low_hip is not None:
            if self.armpit_to_low_hip < self.armpit_to_med_hip:
                validation_errors.append(
                    ValidationError(
                        "Average sweater length must be "
                        "shorter than long sweater length."
                    )
                )

        if all([self.armpit_to_tunic is not None, self.armpit_to_low_hip is not None]):
            if self.armpit_to_tunic < self.armpit_to_low_hip:
                validation_errors.append(
                    ValidationError(
                        "Long sweater length must be "
                        "shorter than tunic sweater length."
                    )
                )

        # TODO: Add tests: bicep must be bigger than wrist
        if all([self.bicep_circ is not None, self.wrist_circ is not None]):
            if self.bicep_circ < self.wrist_circ:
                validation_errors.append(
                    ValidationError(
                        "Wrist-circumference "
                        "measurement must be smaller than bicep circumference."
                    )
                )

        # We append validation errors to this list so we can raise them all
        # at once, rather than returning a form to a user with only one
        # error when in fact multiple things might need to be corrected.
        # https://docs.djangoproject.com/en/1.8/ref/forms/validation/#raising-multiple-errors
        if validation_errors:
            raise ValidationError(validation_errors)

    class Meta:
        abstract = True
        ordering = ["bust_circ"]


class UnarchivedBodyManager(models.Manager):
    """
    This class will act as the default manager for the Body model. If differs
    from the standard manager only in that its initial query set filters out
    archived bodies and returns only unarchived ones.
    """

    def get_queryset(self):
        return super(UnarchivedBodyManager, self).get_queryset().filter(archived=False)


# Developer's note: There are currently three kinds of fields:
#
# * Essential fields are required for all bodies. This is enforced by
#   setting 'blank' and 'null' to False (or omitting them entirely, which has
#   the same effect).
#
# * Extra fields are optional and allow for more customization options. Users
#   may enter as many or as few as they like. However, they must enter all
#   hourglass fields to make hourglass sweaters. During pattern creation,
#   they will be blocked from making hourglass sweaters for non-hourglass
#   bodies. If they try to make a sweater for a body that is missing
#   required non-hourglass measurements, they will be prompted to enter
#   the missing measurements or use defaults. (The logic here is that they
#   should only need to enter one or two additional measurements for
#   non-hourglass sweaters - e.g. a sleeve length and arm circ - but they
#   might potentially need to enter all the hourglass measurements to make
#   an hourglass sweater for a non-hourglass body. The former isn't too much
#   of a speedbump; the latter is.)
#
# * Optional fields are never needed. If provided, we will use them. But if
#   they are not provided, we will approximate them from other (essential)
#   fields.

# If you change the order of fields in these lists, please also change the
# order of ESSENTIAL_FIELDS, etc., in bodies/forms.py to match;
# this isn't functionally important, but it allows us to present
# measurements to users in the same order on the measurement entry
# and measurement detail pages.

ESSENTIAL_FIELDS = [
    "name",
    "bust_circ",
    "waist_circ",
    "med_hip_circ",
    "armhole_depth",
    "armpit_to_med_hip",
    "armpit_to_full_sleeve",
    "bicep_circ",
    "wrist_circ",
    "body_type",
]


EXTRA_SLEEVE_FIELDS = [
    "elbow_circ",
    "forearm_circ",
    "armpit_to_short_sleeve",
    "armpit_to_elbow_sleeve",
    "armpit_to_three_quarter_sleeve",
]

EXTRA_HOURGLASS_FIELDS = [
    "upper_torso_circ",
    "armpit_to_waist",
    "armpit_to_high_hip",
    "high_hip_circ",
    "armpit_to_low_hip",
    "low_hip_circ",
    "armpit_to_tunic",
    "tunic_circ",
]

EXTRA_FIELDS = EXTRA_SLEEVE_FIELDS + EXTRA_HOURGLASS_FIELDS

OPTIONAL_FIELDS = ["cross_chest_distance", "inter_nipple_distance"]


class Body(MeasurementSet, _HasBodyType):
    """
    User measurement sets.

    By default, the 'objects' manager only unarchived bodies. Use the
    `even_archived` manager in lieu of `objects` if it is important
    to consider archived bodies.
    """

    user = models.ForeignKey(
        User, db_index=True, related_name="bodies", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=50)
    creation_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    archived = models.BooleanField(default=False)

    # The on_delete parameter ensures that, if the BodyPicture is deleted,
    # there is NOT a cascade which also deletes the Body.
    # We're referencing by label rather than importing BodyPicture directly to
    # avoid circular import hell: https://docs.djangoproject.com/en/1.5/ref/models/fields/#foreignkey
    # save() ensures that the featured_pic's body is THIS body.
    featured_pic = models.ForeignKey(
        "uploads.BodyPicture", blank=True, null=True, on_delete=models.SET_NULL
    )

    def _measurement_sublist(self, my_list=None):
        def verbosify(field_name):
            return {
                "name": self._meta.get_field(field_name).verbose_name,
                "value": self.__dict__[field_name],
            }

        return list(map(verbosify, my_list))

    @property
    def essential_measurement_values(self):
        """
        This returns a list of name/value dicts of essential measurements,
        in the same order as on the measurement entry page.
        """
        measurements = [
            "bust_circ",
            "waist_circ",
            "med_hip_circ",
            "armhole_depth",
            "armpit_to_med_hip",
            "armpit_to_full_sleeve",
            "wrist_circ",
            "bicep_circ",
        ]
        return self._measurement_sublist(measurements)

    @property
    def extra_measurement_values(self):
        """
        This returns a list of name/value dicts of essential measurements,
        in the same order as on the measurement entry page.
        """
        measurements = [
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
        return self._measurement_sublist(measurements)

    @property
    def optional_measurement_values(self):
        measurements = ["cross_chest_distance", "inter_nipple_distance"]
        return self._measurement_sublist(measurements)

    @property
    def has_any_extra_measurements(self):
        """
        Returns a boolean indicating whether this body has any of the extra
        measurements.
        """
        return any([getattr(self, field) is not None for field in EXTRA_FIELDS])

    @property
    def has_all_extra_measurements(self):
        """
        Returns a boolean indicating whether this body has all of the extra
        measurements.
        """
        return all([getattr(self, field) is not None for field in EXTRA_FIELDS])

    @property
    def has_any_optional_measurements(self):
        """
        Returns a boolean indicating whether this body has any of the optional
        measurements.
        """
        return any([getattr(self, field) is not None for field in OPTIONAL_FIELDS])

    @property
    def patterns(self):
        # putting this import at the top level was throwing ImportErrors
        # The simplest way to do this is
        #   patterns = [pattern for pattern in IP.objects.all() if pattern.get_spec_source().body == self]
        # But this is way too slow. So we need to push this to the database and get those patterns where
        #
        # 1) self is the body in the patterns original patternspec and it hasn't been redone, or
        # 2) the pattern has been redone and self is the body of the redo
        from django.db.models import Q

        from customfit.pattern_spec.models import PatternSpec
        from customfit.patterns.models import IndividualPattern as IP
        from customfit.patterns.models import Redo

        # self is the swatch of the pattern's current spec_source and it hasnt been redone
        pspecs = PatternSpec.objects.filter(SweaterPatternSpec___body=self)
        q_pspec = Q(
            pieces__schematic__individual_garment_parameters__pattern_spec__in=pspecs
        )

        test_pspecs = PatternSpec.objects.filter(TestPatternSpecWithBody___body=self)
        q_test_pspec = Q(
            pieces__schematic__individual_garment_parameters__pattern_spec__in=test_pspecs
        )

        # self is the swatch of the pattern's current spec_source and it has been redone
        redos = Redo.objects.filter(SweaterRedo___body=self)
        q_redo = Q(pieces__schematic__individual_garment_parameters__redo__in=redos)

        test_redos = Redo.objects.filter(TestRedoWithBody___body=self)
        q_test_redo = Q(
            pieces__schematic__individual_garment_parameters__redo__in=test_redos
        )

        patterns = IP.approved_patterns.filter(
            q_pspec | q_redo | q_test_pspec | q_test_redo
        ).all()

        return patterns

    @property
    def is_updateable(self):
        """
        Bodies can be updated if they are missing any extra fields.
        Existing field values cannot be changed(*), but new ones can be added.

        (*) It would actually be perfectly reasonable to change fields if there
        are no patterns made from the body, but this would mean *even
        unapproved* patterns; those could become broken if existing measurements
        were changed. However, the user can't tell by looking at a body whether
        it has unapproved patterns, but CAN tell if it has incomplete
        measurements. Therefore having an if condition on pattern existence
        would create arbitrary results for the user, whereas letting them add
        (but not change) measurements yields a consistent experience.
        """
        extras = [getattr(self, field) for field in EXTRA_FIELDS]

        return None in extras

    def __str__(self):
        return "%s" % self.name

    def to_dict(self):
        """
        Produce a dictionary which can be used in a unit test to
        re-create the values of this object.
        """
        return model_to_dict(self)

    @classmethod
    def from_dict(cls, to_dict, user):
        new_dict = copy.copy(to_dict)
        if "id" in new_dict:
            del new_dict["id"]
        new_dict["user"] = user
        return cls(**new_dict)

    def get_absolute_url(self):
        return reverse("bodies:body_detail_view", kwargs={"pk": self.id})

    @property
    def preferred_picture_url(self):
        """
        Returns URL of preferred pic.
        """
        if self.featured_pic:
            return self.featured_pic.picture.url
        try:
            picture = self.pictures.all()[0].picture.url
        except IndexError:
            picture = join(settings.STATIC_URL, "img/My_Measurements.png")
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

    def save(self, *args, **kwargs):
        if self.featured_pic:
            # Make sure that any featured pic is actually of THIS body.
            if self.featured_pic.object != self:
                self.featured_pic = None
        super(Body, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """

        We used to go through some rigamarole to detect if the body was 'safe' to delete (meaning: not
        used in any patterns) but that turned out to age badly. It needed to hard-code in the internal
        structure of patterns, which meant that our rigamarole became unsafe when we changed that internal
        structure. So, we just always archive instead.

        _Note that this method is not called when deleting querysets in
        bulk_: https://docs.djangoproject.com/en/1.6/topics/db/queries/#topics-db-queries-delete

        If you are deleting body querysets in bulk, you may inadvertently
        delete bodies with associated patterns. Don't do that.
        """

        logger.info("Archiving body %s", self.pk)
        self.archived = True
        self.save()

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
    # See BodyLinkage, Swatch, SwatchLinkage, and PatternLinkage for other instances of this situation.
    #
    # See https://docs.djangoproject.com/en/1.8/topics/db/managers/#default-managers for more information
    objects = UnarchivedBodyManager()
    even_archived = models.Manager()

    class Meta:
        app_label = "bodies"
        verbose_name_plural = "bodies"
        ordering = ["creation_date"]


class UnarchivedBodyLinkageManager(models.Manager):
    """
    This class will act as the default manager for the BodyLinkage model. If differs
    from the standard manager only in that its initial query set filters out (eliminates)
    linkages that point to archived bodies.
    """

    def get_queryset(self):
        return (
            super(UnarchivedBodyLinkageManager, self)
            .get_queryset()
            .filter(body__archived=False)
        )


class GradeSet(_HasBodyType):

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    creation_date = models.DateTimeField(auto_now_add=True)
    # Inherits body_tupe from _HasBodyType

    @property
    def grades(self):
        return self.grade_set.all()

    def __str__(self):
        return "%s (%s)" % (self.name, self.user.username)

    class Meta:
        unique_together = [["user", "name"]]


class Grade(MeasurementSet):

    grade_set = models.ForeignKey(
        GradeSet, db_index=True, related_name="grade_set", on_delete=models.CASCADE
    )

    @property
    def body_type(self):
        return self.grade_set.body_type

    class Meta:
        ordering = ["bust_circ"]
        unique_together = [["bust_circ", "grade_set"]]
