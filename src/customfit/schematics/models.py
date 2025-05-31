# -*- coding: utf-8 -*-
"""

This module holds schematics models: models for holding the
lengths and heights of a piece. These models do not hold any stitch- or
row-counts, as those belong in Piece models.

Schematics models come in two flavors:

* Those describing one particular piece, and
* Those describing all the pieces in one particular garment.

Generally, models of the second kind don't have any values of their own, but
exist merely to contain the piece-schematics of one particular garment.
"""


import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from polymorphic.models import PolymorphicModel

from customfit.garment_parameters.models import (
    GradedGarmentParameters,
    IndividualGarmentParameters,
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your models here.


class _BasePieceSchematic(PolymorphicModel):
    # Subclasses need to implement:
    #
    # * _get_values_from_gp
    # * get_spec_source
    # * add_self_to_schematic
    #
    # Sub-classes should NOT customize:
    #
    # full_clean()
    class Meta:
        abstract = True


class PieceSchematic(_BasePieceSchematic):

    # Subclasses need to implement:
    #
    # * schematic_field_name
    # * _get_values_from_gp
    # * get_spec_source
    #
    # Sub-classes should NOT customize:
    #
    # full_clean()

    # Subclasses should override this with the real name of the attribute in
    # ConstructionSchematic to which this piece should be assigned. It is
    # used in add_self_to_schematic (which it itself used in
    # Construction.save()) to provide a unique
    # prefix to piece-schematic forms.
    schematic_field_name = None

    def add_self_to_schematic(self, schematic):
        """
        Needed by the pattern wizard and by self.save().
        """
        setattr(schematic, self.schematic_field_name, self)

    @classmethod
    def make_from_gp_and_container(cls, gp):
        """
        Given a IndividualGarmentParameters instance from which to draw
        dimensions, and a ConstructionSchematic class to contain the
        new Schematic object, make the new PieceSchematic object and put it
        in the containing class. This exists so that there is a uniform
        way to create schematics.
        """
        return_me = cls()
        return_me._get_values_from_gp(gp)
        return return_me

    class Meta:
        abstract = True


class _BaseConstructionSchematic(PolymorphicModel):
    # subclasses need to implement:
    #
    # * sub_pieces
    # * get_gp()

    creation_date = models.DateTimeField(default=timezone.now)

    @property
    def name(self):
        return self.get_gp().name

    @property
    def user(self):
        return self.get_gp().user

    def get_spec_source(self):
        return self.get_gp().get_spec_source()

    def __str__(self):
        return "%s/%s/%s" % (self.__class__.__name__, self.name, self.user)

    class Meta:
        abstract = True


class ConstructionSchematic(_BaseConstructionSchematic):
    """
    Superclass for container models that hold the pieces of a given construction. Note: misnamed--
    should be GarmentSchematic, but it's too hard to change it.
    """

    # Subclasses need to implement
    #
    # * make_from_garment_parameters
    # * sub_pieces

    individual_garment_parameters = models.ForeignKey(
        IndividualGarmentParameters, on_delete=models.CASCADE
    )

    customized = models.BooleanField(
        help_text="If true, the user has tweaked the values in this model. "
        "If false, everything was derived.",
        default=False,
    )

    def get_gp(self):
        return self.individual_garment_parameters

    def _map_over_pieces(self, f):
        """
        A helper function to map a function f (over piece-schematics) over those
        piece-schematics actually contained in this container. Used in methods
        like save(), delete(), etc.
        """
        return [f(piece) for piece in self.sub_pieces()]

    def save(self, *args, **kwargs):
        def f(piece):
            piece.save()
            # This next line is a kludge, but after saving the piece, we
            # need to re-assign the piece to the schematic field or the
            # call to super().save() won't work right. See Django ticket
            # 8892
            piece.add_self_to_schematic(self)

        self._map_over_pieces(f)
        super(_BaseConstructionSchematic, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        def f(piece):
            piece.delete()

        self._map_over_pieces(f)
        try:
            super(_BaseConstructionSchematic, self).delete(*args, **kwargs)
        except ConstructionSchematic.DoesNotExist:
            # If the ConstructionSchematic points to any pieces through ForeignKey or
            # OneToOne fields with on_delete of CASCADE, then deleting the piece will delete the
            # schematic. Which is fine-- that's what we wanted in the first place.
            pass

    def clean_fields(self, exclude=None):

        # Note: we don't attempt to aggregate errors together.
        # Why? clean_fields() returns an error-dict mapping field-names to errors.
        # It's not clear how to aggregate the dicts from sub-pieces with those of
        # the garment, so we don't try.

        super(_BaseConstructionSchematic, self).clean_fields(exclude)

        def f(piece):
            piece.clean_fields(exclude)

        self._map_over_pieces(f)

    def validate_unique(self, exclude=None):

        # Note: we don't attempt to aggregate errors together.
        # Why? validate_unique() returns an error-dict mapping field-names to errors.
        # It's not clear how to aggregate the dicts from sub-pieces with those of
        # the garment, so we don't try.

        super(_BaseConstructionSchematic, self).clean_fields(exclude)

        def f(piece):
            piece.validate_unique(exclude)

        self._map_over_pieces(f)

    def clean(self):
        errors = []

        for piece in self.sub_pieces():
            try:
                piece.clean()
            except ValidationError as ve:
                errors.append(ve)

        try:
            super(_BaseConstructionSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if errors:
            raise ValidationError(errors)

    # Note: no need to write a recursive version of full_clean()-- full_clean() in the garment
    # will call clean(), clean_fields(), and validate_unique(), all of which are recursive.
    # The only gotcha to be aware of is that we shouldn't customize full_clean() in the pieces.


class GradedConstructionSchematic(_BaseConstructionSchematic):
    # Subclasses need to implement
    #
    # * make_from_garment_parameters
    # * get_pieces_class

    graded_garment_parameters = models.ForeignKey(
        GradedGarmentParameters, on_delete=models.CASCADE
    )

    @property
    def all_grades(self):
        return self.gradedpieceschematic_set.all()

    def get_gp(self):
        return self.graded_garment_parameters

    class Meta:
        pass


class GradedPieceSchematic(_BasePieceSchematic):
    # Subclasses need to implement:
    #
    # * _get_values_from_gp_and_grade

    construction_schematic = models.ForeignKey(
        GradedConstructionSchematic,
        on_delete=models.CASCADE,
        related_name="gradedpieceschematic_set",  # not sure why this is necessary
    )

    def add_self_to_schematic(self, schematic):
        """
        Needed by the pattern wizard and by self.save().
        """
        self.construction_schematic = schematic

    def get_spec_source(self):
        return self.construction_schematic.get_spec_source()

    @classmethod
    def make_from_gp_grade_and_container(
        cls, graded_garment_parameters, gp_grade, graded_construction_schematic
    ):
        return_me = cls()
        return_me._get_values_from_gp_and_grade(graded_garment_parameters, gp_grade)
        return_me.add_self_to_schematic(graded_construction_schematic)
        return_me.save()
        return return_me

    class Meta:
        pass
