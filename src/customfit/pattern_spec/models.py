# -*- coding: utf-8 -*-
import logging
import os.path

import django.template
from django.contrib.auth.models import User
from django.db import models
from polymorphic.models import PolymorphicModel

from customfit.bodies.models import Body
from customfit.designs.models import Design
from customfit.stitches.models import Stitch
from customfit.swatches.models import Swatch

logger = logging.getLogger(__name__)


class BasePatternSpec(PolymorphicModel):
    # Base class for both PatternSpec (individual) and GradedPatternSpec

    name = models.CharField(max_length=100)

    pattern_credits = models.CharField(
        max_length=100,
        blank=True,
        help_text="For any non-authorship and non-photography credits. "
        "Example: 'Technical editing: Jane Doe.'",
    )

    creation_date = models.DateTimeField(auto_now_add=True)

    design_origin = models.ForeignKey(
        Design, on_delete=models.CASCADE, blank=True, null=True, related_name="+"
    )

    user = models.ForeignKey(
        User, blank=True, db_index=True, related_name="+", on_delete=models.CASCADE
    )

    def _get_from_origin(self, field_name):
        if self.design_origin is None:
            return None
        else:
            return getattr(self.design_origin, field_name)

    @property
    def notions(self):
        return self._get_from_origin("notions")

    @property
    def recommended_gauge(self):
        return self._get_from_origin("recommended_gauge")

    @property
    def recommended_materials(self):
        return self._get_from_origin("recommended_materials")

    @property
    def needles(self):
        return self._get_from_origin("needles")

    @property
    def yarn_notes(self):
        return self._get_from_origin("yarn_notes")

    @property
    def style_notes(self):
        return self._get_from_origin("style_notes")

    @property
    def description(self):
        return self._get_from_origin("description")

    def get_cover_sheet(self):
        return self._get_from_origin("cover_sheet")

    def get_original_patternspec(self):
        # A no-op here, but non-trivial in Redo
        return self

    def _stitch_or_design_template(
        self,
        design_field_name,
        stitch,
        use_stitch_bool,
        stitch_field_name,
        template_directory,
        no_stitch_template_name,
    ):
        """
        Get a template and return it, in this order:
        * From design_template:
        * If stitch is not none and the relevant hem-height is more than zero,
          stitch.stitch_field_name,
        * Load 'no_stitch_template_name' from the filesystem
        """
        if self.design_origin is not None:
            design_template = getattr(self.design_origin, design_field_name)
            if design_template is not None:
                return django.template.Template(
                    design_template.content,
                    # Why do we add the name?
                    # For unit testing
                    name=design_template.name,
                )
        if stitch is not None and use_stitch_bool:
            return getattr(stitch, stitch_field_name)
        else:
            # Get the no-stitch template from the filesystem
            template_path = os.path.join(template_directory, no_stitch_template_name)
            return django.template.loader.get_template(template_path)

    def __str__(self):
        return "%s/%s" % (self.name, self.user)

    class Meta:
        abstract = True


class PatternSpec(BasePatternSpec):
    # PatternSpec information for patterns that will be made in exactly one size (i.e., not graded).
    #
    # Should really be called IndividualPatternSpec, but named just PatternSpec for historical reasons.
    #
    # Subclasses need to implement:
    #
    # * stitches_used()
    # * get_igp_class()
    # * get_garment()

    swatch = models.ForeignKey(
        Swatch,
        help_text="Swatch for which this design is intended",
        related_name="+",
        on_delete=models.CASCADE,
    )


class GradedPatternSpec(BasePatternSpec):
    # PatternSpec information for patterns that will be made in graded. The specification of the grades will be
    # highly garment-specific. Sweaters will be graded according to a list of bodies (Grades, actually), while
    # cowls will be graded according to a list of (length, height) pairs. So we factor out this base class and
    # let garments implement it as they see fit.

    # Subclasses need to implement:
    #
    # * get_igp_class()

    pass
