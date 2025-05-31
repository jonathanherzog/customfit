# -*- coding: utf-8 -*-

import logging

from django.core.exceptions import ValidationError
from django.db import models
from polymorphic.models import PolymorphicModel

from customfit.helpers.math_helpers import ROUND_UP, CompoundResult, round
from customfit.schematics.models import (
    ConstructionSchematic,
    GradedConstructionSchematic,
)
from customfit.swatches.helpers import area_to_yards_of_yarn_estimate

logger = logging.getLogger(__name__)

# Create your models here.


class AreaMixin(object):
    # A mixin-class for things that have area-- either an individual pattern pieces, or
    # a grade of a graded pattern pieces. Subclasses must implement
    #
    # sub_pieces()
    # _trim_area()

    def area(self):
        def f(piece):
            return piece.area()

        piece_areas = list(map(f, self.sub_pieces()))
        trim_area = self._trim_area()
        total_area = sum(piece_areas) + trim_area
        return total_area


class _BasePatternPieces(PolymorphicModel):
    # Subclasses need to implement
    #
    # * schematic (field)
    # * sub_pieces
    # * make_from_schematic

    class Meta:
        abstract = True

    def get_spec_source(self):
        return self.schematic.get_spec_source()


class PatternPieces(AreaMixin, _BasePatternPieces):
    # Subclasses need to implement
    #
    # * sub_pieces
    # * make_from_schematic
    # * _trim_area

    schematic = models.ForeignKey(
        ConstructionSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    def _map_over_pieces(self, f):
        for piece in self.sub_pieces():
            f(piece)

    def save(self, *args, **kwargs):
        def f(piece):
            piece.save()
            # This next line is a kludge, but after saving the piece, we
            # need to re-assign the piece to the pattern field or the
            # call to super().save() won't work right. See Django ticket
            # 8892
            piece.add_self_to_piece_list(self)

        self._map_over_pieces(f)
        super(PatternPieces, self).save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        def f(piece):
            piece.clean_fields(exclude)

        self._map_over_pieces(f)
        super(PatternPieces, self).clean_fields(exclude)

    def clean(self):
        def f(piece):
            piece.clean()

        self._map_over_pieces(f)
        super(PatternPieces, self).clean()

    def full_clean(self, *args, **kwargs):
        errors = []
        for piece in self.sub_pieces():
            try:
                piece.full_clean(*args, **kwargs)
            except ValidationError as e:
                errors.append(e)
        try:
            super(PatternPieces, self).full_clean(*args, **kwargs)
        except ValidationError as ve:
            errors.append(ve)

        if errors:
            raise ValidationError(errors)

    def delete(self):
        def f(piece):
            piece.delete()

        self._map_over_pieces(f)
        try:
            super(PatternPieces, self).delete()
        except PatternPieces.DoesNotExist:
            # If the ConstructionSchematic points to any pieces through ForeignKey or
            # OneToOne fields with on_delete of CASCADE, then deleting the piece will delete the
            # schematic. Which is fine-- that's what we wanted in the first place.
            pass

    def weight(self):
        swatch = self.get_spec_source().swatch
        square_inches = self.area()
        weight_float = swatch.area_to_weight(square_inches)
        if weight_float is None:
            return None
        else:
            return int(round(weight_float, ROUND_UP))

    def hanks(self):
        swatch = self.get_spec_source().swatch
        square_inches = self.area()
        hanks_float = swatch.area_to_hanks(square_inches)
        if hanks_float is None:
            return None
        else:
            return int(round(hanks_float, ROUND_UP))

    def yardage_is_precise(self):
        swatch = self.get_spec_source().swatch
        square_inches = self.area()
        return swatch.area_to_yards_of_yarn(square_inches)[1]

    def yards(self):
        swatch = self.get_spec_source().swatch
        square_inches = self.area()
        yards_float = swatch.area_to_yards_of_yarn(square_inches)[0]
        return int(round(yards_float, ROUND_UP))


class GradedPatternPieces(_BasePatternPieces):
    # Subclasses need to implement
    #
    # * sub_pieces
    # * make_from_schematic
    # * get_pattern_class
    # * area_list()

    schematic = models.ForeignKey(
        GradedConstructionSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    @property
    def all_pieces(self):
        return self.gradedpatternpiece_set.all()

    class Meta:
        pass

    def yards(self):
        # Make a temporary swatch for the purpose of computing yardage
        gauge = self.get_spec_source().gauge
        yard_list = [
            area_to_yards_of_yarn_estimate(square_inch, gauge)
            for square_inch in self.area_list()
        ]
        rounded_yard_list = [round(yards, ROUND_UP) for yards in yard_list]

        return CompoundResult(rounded_yard_list)


class BasePatternPiece(PolymorphicModel):
    #
    # Subclasses should implement:
    #
    # * schematic (property)
    # * get_pattern(self) -- returning the pattern it belongs to or None
    # * add_self_to_piece_list
    class Meta:
        abstract = True


class PatternPiece(BasePatternPiece):
    #
    # Subclasses should implement:
    #
    # * schematic (property)
    # * get_pattern(self) -- returning the pattern it belongs to or None
    # * area
    # * _pattern_field_name

    # subclasses should override this. It is used by add_self_to_piece_list.
    # The reference to 'pattern' is historical-- pieces used to be in IndividualPattern
    # directly.
    _pattern_field_name = None

    def add_self_to_piece_list(self, piece_list):
        """
        Needed by Pattern.save().
        """
        setattr(piece_list, self._pattern_field_name, self)

    @property
    def gauge(self):
        return self.schematic.get_spec_source().gauge

    @property
    def design(self):
        return self.schematic.get_spec_source().get_original_patternspec()

    def __str__(self):
        return "%s %s" % (self.__class__.__name__, self.id)


class GradedPatternPiece(BasePatternPiece):
    #
    # Subclasses should implement:
    #
    # * schematic (property)
    # * get_pattern(self) -- returning the pattern it belongs to or None
    # * graded_pattern_pieces (field)

    # Why, oh why isn't this inherited?
    class Meta:
        ordering = ["sort_key"]

    graded_pattern_pieces = models.ForeignKey(
        GradedPatternPieces,
        on_delete=models.CASCADE,
        related_name="gradedpatternpiece_set",
    )

    sort_key = models.FloatField()

    @property
    def gauge(self):
        return self.graded_pattern_pieces.get_spec_source().gauge

    @property
    def design(self):
        return self.graded_pattern_pieces.get_spec_source().get_original_patternspec()

    def validate_unique(self, exclude=None):
        super(GradedPatternPiece, self).validate_unique(exclude=exclude)

        # Check that no other piece of the same class shares the graded_pattern_peices and
        # sort_key

        if (
            GradedPatternPiece.objects.instance_of(self.__class__)
            .filter(
                sort_key=self.sort_key, graded_pattern_pieces=self.graded_pattern_pieces
            )
            .exists()
        ):
            msg = (
                "Another %s with this sort_key and graded_garment_parameters exists"
                % self.__class__
            )
            raise ValidationError("msg", code="sort_key_conflict")

    def add_self_to_piece_list(self, graded_pattern_pieces):
        """
        Needed by Pattern.save().
        """
        self.graded_pattern_pieces = graded_pattern_pieces
        self.save()
