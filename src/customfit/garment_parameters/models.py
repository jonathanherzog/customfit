import logging

import reversion
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from polymorphic.models import PolymorphicModel

from customfit.pattern_spec.models import GradedPatternSpec, PatternSpec

logger = logging.getLogger(__name__)


class IncompatibleDesignInputs(Exception):
    """
    We raise this custom exception when the Body and PatternSpec are
    individually valid, but their combination is not (e.g. a short-sleeve length
    too short to accommodate a desired edging height).

    Separating this from ValidationError allows us to handle this case
    separately from other sources of invalidity, e.g. patterns that can't be
    made by the engine. This is important because it lets us signal to the user
    where and how *they* can fix the problem in a way they're happy with.

    In particular, this error is most likely to crop up when users add
    missing measurements, and thereby end up with a pattern that can't be
    created even though previous steps were valid. They can fix this by
    changing design inputs (e.g. elbow-length sleeve or shorter sleeve edging).
    Letting them fix it on their own is preferable to generating customer
    service queries.
    """

    pass


class MissingMeasurement(ValidationError):
    """
    The engine requires a body-measurement that is not present in the Body
    object. The attribute `missing_measurement` will contain the name of
    the missing attribute.
    """

    def __init__(self, missing_measurement):
        message = "missing measurement: %s" % missing_measurement
        super(MissingMeasurement, self).__init__(message)
        self.missing_measurement = missing_measurement


@reversion.register()
class BaseGarmentParameters(PolymorphicModel):
    # Subclasses must implement:
    #
    # * get_spec_source

    ############################################################################
    #
    # Informational / source fields
    #
    ############################################################################

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)

    creation_date = models.DateTimeField(auto_now_add=True)

    ############################################################################
    #
    # Exceptions and other constants
    #
    ############################################################################

    # Why do we have this next line? It's by analogy with how Django itself
    # handles errors thrown by model instances, and it allows us to look for
    # exceptions like "IndividualGarmentParameters.IncompatibleDesignInputs",
    # in exactly the same way we would expect to be able to look for
    # "Body.DoesNotExist" or "Swatch.MultipleInstancesReturned".
    IncompatibleDesignInputs = IncompatibleDesignInputs

    @classmethod
    def missing_body_fields(cls, patternspec):
        """
        Given a PatternSpec return
        an iterable of all 'missing' Bodies fields with respect to that spec (i.e.,
        fields that are currently None or blank that must be non-None in order
        to make that spec for that Body.) If no fields are missing, an empty
        list will be returned. Note that there is no guarantee made about the
        order of entries in the returned iterable. Note that the iterable
        will be one of Field objects and not their names.
        """

        # Why is this here instead of in Design or Body? Two reasons: First, in order
        # to avoid unnecessary dependencies between the Design and Body model. Both
        # of those models are conceptually valid in the absence of the other, and so
        # it's probably a good idea to keep their code separate, too. Second, this
        # model is already where the Body is compared to the needs of a Design. The
        # correctness of this method is relative to the rest of the code in *this*
        # file. By putting this method here, it becomes more likely that it will
        # be updated and maintained in sync with the rest of this file. If we put it
        # in Design or Body, on the other hand, it can more easily diverge from
        # the rest of the code in this model. (Out of sight, out of mind.)

        # Note that it's necessary to replicate some of this logic in the javascript
        # powering individualdesign_crete_form.html (the custom design form), in
        # order to communicate with users about which designs they can make with
        # which bodies. If our concepts about which fields are required for which
        # design parameters changes, that JS will also need to change.

        # Another note: the IGP engine will sometimes use a body-field if it is present,
        # but can also handle its absence. Examples: cross-chest width, or the hip-circs
        # above the cast-on length specified in the design. (See _get_hip_circ().) At
        # one point, we discussed the idea of having this method return two
        # lists: one need-to-have fields and one nice-to-have fields. This idea was
        # rejected, for the moment, as we worried that it would lead to user-confusion
        # during the purchase process: the nice-to-have fields are only really needed
        # for certain body-shapes, and we don't want to show them to all users all the
        # time since most of them won't benefit from their presence. And since this
        # is really an issue about bodies and not designs, we decided that the Right
        # Place to prompt users for nice-to-have measurements is during the BodyCreateViews,
        # when the focus is on the body and not the design.

        # Last note: This method is deliberately written in a redundant fashion.
        # Why? So that its internal structure mimics the code of _inner_make
        # and its sub-methods. That way, it's easier to update this method
        # when the more-complex logic of the _inner_make_* methods changes

        # To be shadowed by subclasses that might need specific fields from the body
        return set()

    @property
    def name(self):
        spec_source = self.get_spec_source()
        return spec_source.name

    @property
    def swatch(self):
        spec_source = self.get_spec_source()
        swatch = spec_source.swatch
        return swatch

    def __str__(self):
        return "%s %s/%s (%s)" % (self.__class__, self.name, self.user, self.id)

    class Meta:
        # Note: if this class is not abstract, we get additional complexity
        # with django-reversion interacting with multi-table inheritance
        abstract = True


@reversion.register()
class IndividualGarmentParameters(BaseGarmentParameters):
    # Subclasses must implement:
    #
    # * make_from_patternspec
    # * make_from_redo

    pattern_spec = models.ForeignKey(
        PatternSpec,
        blank=True,
        null=True,
        help_text="Spec from which these parameters was derived",
        on_delete=models.CASCADE,
    )

    redo = models.ForeignKey(
        "patterns.Redo",
        blank=True,
        null=True,
        help_text="Spec from which these parameters was derived",
        on_delete=models.CASCADE,
    )

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        """
        Make, validate and return an instance of
        IndividualGarmentParameters from high-level inputs.
        Note: returned object will not have been saved.
        """
        raise NotImplementedError()

    @classmethod
    def make_from_redo(cls, user, redo):
        """
        Make, validate and return an instance of
        IndividualGarmentParameters from high-level inputs.
        Note: returned object will not have been saved.
        """
        raise NotImplementedError()

    def get_spec_source(self):
        assert (self.pattern_spec is not None) or (self.redo is not None)
        source = self.pattern_spec if self.pattern_spec else self.redo
        return source

    def clean(self):

        super(IndividualGarmentParameters, self).clean()

        if (self.pattern_spec is None) and (self.redo is None):
            raise ValidationError("Must have one of pattern_spec or redo")

        if (self.pattern_spec is not None) and (self.redo is not None):
            raise ValidationError("Must have only one of pattern_spec or redo")

    @reversion.create_revision()
    def save(self, *args, **kwargs):
        """
        save() exists solely so that it can be decorated to create the
        revision.

        We could create revisions in the TweakIndividualGarmentParameters
        form, but in that case the *first* version of the IGP (the pre-tweaking
        version) would not exist, and that is the one we most want to keep
        track of.
        """
        super(IndividualGarmentParameters, self).save(*args, **kwargs)

    class Meta:
        pass


class GradedGarmentParameters(BaseGarmentParameters):
    # Subclasses must implement:
    #
    # * make_from_patternspec
    # * get_schematic_class()

    pattern_spec = models.ForeignKey(
        GradedPatternSpec,
        help_text="Spec from which these parameters was derived",
        on_delete=models.CASCADE,
    )

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        """
        Make, validate and return an instance of
        GradedGarmentParameters from high-level inputs.
        Note: returned object will not have been saved.
        """
        raise NotImplementedError()

    def get_spec_source(self):
        return self.pattern_spec

    @property
    def all_grades(self):
        return self.gradedgarmentparametersgrade_set.all()

    class Meta:
        pass


class GradedGarmentParametersGrade(PolymorphicModel):

    graded_garment_parameters = models.ForeignKey(
        GradedGarmentParameters,
        on_delete=models.CASCADE,
        related_name="gradedgarmentparametersgrade_set",
    )

    class Meta:
        pass
