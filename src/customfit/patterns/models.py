# -*- coding: utf-8 -*-


import datetime
import logging
import urllib.parse

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from django.utils import timezone
from polymorphic.models import PolymorphicManager, PolymorphicModel

from customfit.pieces.models import GradedPatternPieces, PatternPieces
from customfit.swatches.models import Swatch

from .helpers import REDO_DEADLINE_IN_DAYS, REDO_DEADLINE_START

LOGGER = logging.getLogger(__name__)

# Create your models here.


class ApprovedPatternManager(PolymorphicManager):
    """
    This returns all approved patterns, whether archived or not.
    """

    def get_queryset(self):
        return (
            super(ApprovedPatternManager, self)
            .get_queryset()
            .filter(transactions__approved=True)
        )


class LivePatternManager(ApprovedPatternManager):
    """
    This class differs from the standard manager in that its initial
    query set:
        * filters out unapproved patterns, returning only approved ones.
        * filters out archived patterns, returning only unarchived ones.
    Here "approved" means "associated with an approved transaction".
    """

    def get_queryset(self):
        return super(LivePatternManager, self).get_queryset().filter(archived=False)


class ArchivedPatternManager(ApprovedPatternManager):
    """
    This class differs from the standard manager in that its initial
    query set:
        * filters out unapproved patterns, returning only approved ones.
        * filters out unarchived patterns, returning only archived ones.
    Here "approved" means "associated with an approved transaction".
    """

    def get_queryset(self):
        return super(ArchivedPatternManager, self).get_queryset().filter(archived=True)


class _BasePattern(PolymorphicModel):
    #
    # Subclasses must implement:
    #
    # * user (field/property)
    # * get_schematic_display_context(self)
    # * make_from_individual_pattern_pieces(cls, user, ipp)
    #
    # And either
    #
    # * self.abridged_pdf_renderer_class
    # * self.full_pdf_renderer_class
    # * self.web_renderer_class
    #
    # or they can override:
    #
    # * render_preamble(self, abridged=False)
    # * render_instructions(self, abridged=False)
    # * render_postamble(self, abridged=False)
    # * render_charts(self, abridged=False)
    # * render_pattern(self, abridged=False)

    class Meta:
        abstract = True

    creation_date = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100)
    notes = models.TextField(blank=True)
    archived = models.BooleanField(default=False)

    # The on_delete parameter ensures that, if the IPPicture is deleted, there
    # is NOT a cascade which also deletes the IP.
    # We're referencing by label rather than importing IPPicture directly to
    # avoid circular import hell: https://docs.djangoproject.com/en/1.5/ref/models/fields/#foreignkey
    # save() ensures that the featured_pic's IP is THIS IP.
    # Why are we preventing the creation of backwards relation? See the comment below on the managers.
    featured_pic = models.ForeignKey(
        "uploads.IndividualPatternPicture",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    #
    # Overrides to Django built-in functions.
    #
    def save(self, *args, **kwargs):
        self.pieces.save()
        self.pieces = self.pieces
        if self.featured_pic:
            # Make sure that any featured pic is actually of THIS pattern.
            if self.featured_pic.object != self:
                self.featured_pic = None
        super(_BasePattern, self).save(*args, **kwargs)

    def __str__(self):
        return "%s" % self.name

    #
    # Ways to get associated objects.
    #

    def get_spec_source(self):
        return self.pieces.get_spec_source()

    def get_design(self):
        """
        Returns the original PatternSpec from the beginning of the process. DO NOT USE.
        Use get_spec_source instead. Present only to maintain backwards compatibility with
        templates in the database.
        """
        spec_source = self.get_spec_source()
        original_pspec = spec_source.get_original_patternspec()
        return original_pspec

    def get_schematic(self):
        return self.pieces.schematic

    @property
    def design(self):
        return self.get_spec_source().get_original_patternspec()

    # Subclasses can override this if applicable
    @property
    def body(self):
        return None

    def yards(self):
        return self.pieces.yards()

    #
    # Images.
    #

    @property
    def preferred_picture_url(self):
        if self.featured_pic:
            return self.featured_pic.picture.url
        try:
            picture_base_url = self.pictures.all()[0].picture.url
        except IndexError:
            spec_source = self.get_spec_source()
            if spec_source.design_origin is not None:
                picture_base_url = spec_source.design_origin.image.url
            else:
                picture_base_url = "img/Build-Your-Own-Photo-Card.png"

        picture_url = urllib.parse.urljoin(settings.STATIC_URL, picture_base_url)
        return picture_url

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
            spec_source = self.get_spec_source()
            if spec_source.design_origin is not None:
                picture = spec_source.design_origin.image
            else:
                picture = None
        return picture

    @property
    def main_stitch(self):
        # subclasses should override
        raise NotImplemented()

    #
    # Patterntext renderers
    #

    def prefill_patterntext_cache(self):
        """
        Called by views to pre-fill the cache with patterntext. Default implementation does nothing,
        but subclasses can use this to do work on spec. It is important that this return quickly, and
        sends all 'real' work to celery.
        """
        self.web_renderer_class(self).prefill_cache()
        self.full_pdf_renderer_class(self).prefill_cache()
        self.abridged_pdf_renderer_class(self).prefill_cache()

    def flush_patterntext_cache(self):
        """
        Called by views to invalidate cached patterntext. Default implementation does nothing,
        but subclasses can use this to do work on spec.
        """
        self.web_renderer_class(self).flush_cache()
        self.full_pdf_renderer_class(self).flush_cache()
        self.abridged_pdf_renderer_class(self).flush_cache()

    def _get_renderer(self, abridged, for_pdf):
        if for_pdf:
            if abridged:
                return self.abridged_pdf_renderer_class(self)
            else:
                return self.full_pdf_renderer_class(self)
        else:
            assert not for_pdf
            return self.web_renderer_class(self)

    def render_preamble(self, abridged=False, for_pdf=False):
        renderer = self._get_renderer(abridged, for_pdf)
        preamble = renderer.render_preamble()
        return preamble

    def render_instructions(self, abridged=False, for_pdf=False):
        renderer = self._get_renderer(abridged, for_pdf)
        instructions = renderer.render_instructions()
        return instructions

    def render_postamble(self, abridged=False, for_pdf=False):
        renderer = self._get_renderer(abridged, for_pdf)
        postamble = renderer.render_postamble()
        return postamble

    def render_charts(self, abridged=False, for_pdf=False):
        renderer = self._get_renderer(abridged, for_pdf)
        charts = renderer.render_charts()
        return charts

    def render_pattern(self, abridged=False, for_pdf=False):
        renderer = self._get_renderer(abridged, for_pdf)
        patterntext = renderer.render_pattern()
        return patterntext

    #
    # Misc.
    #

    @property
    def approved(self):
        return bool(self.transactions.filter(approved=True))

    def delete(self):
        super(_BasePattern, self).delete()


class IndividualPattern(_BasePattern):

    #
    # Subclasses must implement:
    #
    # * get_schematic_display_context(self)
    # * make_from_individual_pattern_pieces(cls, user, ipp)
    #
    # And either
    #
    # * self.abridged_pdf_renderer_class
    # * self.full_pdf_renderer_class
    # * self.web_renderer_class
    #
    # or they can override:
    #
    # * render_preamble(self, abridged=False)
    # * render_instructions(self, abridged=False)
    # * render_postamble(self, abridged=False)
    # * render_charts(self, abridged=False)
    # * render_pattern(self, abridged=False)

    user = models.ForeignKey(User, db_index=True, on_delete=models.CASCADE)

    pieces = models.OneToOneField(PatternPieces, on_delete=models.CASCADE)

    original_pieces = models.OneToOneField(
        PatternPieces,
        on_delete=models.CASCADE,
        # Can be blank if the pattern has not been redone
        blank=True,
        null=True,
        # Unlikely we'll need to follow this relation backwards often
        related_name="+",
    )

    objects = PolymorphicManager()
    approved_patterns = ApprovedPatternManager()
    live_patterns = LivePatternManager()
    archived_patterns = ArchivedPatternManager()
    even_unapproved = PolymorphicManager()  # Here for historical reasons

    def save(self, *args, **kwargs):
        self.pieces = self.pieces
        if self.original_pieces:
            self.original_pieces.save()
            self.original_pieces = self.original_pieces
        self.user = self.user
        super(IndividualPattern, self).save(*args, **kwargs)

    def clean_fields(self, exclude=None):
        if self.original_pieces:
            self.original_pieces.clean_fields(exclude)
        super(IndividualPattern, self).clean_fields(exclude)

    def clean(self):
        if self.original_pieces:
            self.original_pieces.clean()
        super(IndividualPattern, self).clean()

    def full_clean(self, *args, **kwargs):
        if self.original_pieces:
            self.original_pieces.full_clean()
        super(IndividualPattern, self).full_clean(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("patterns:individualpattern_detail_view", kwargs={"pk": self.id})

    @property
    def swatch(self):
        return self.get_spec_source().swatch

    @property
    def gauge(self):
        return self.swatch.get_gauge()

    #
    # Garment properties.
    #

    def area(self):
        return self.pieces.area()

    def weight(self):
        return self.pieces.weight()

    def hanks(self):
        return self.pieces.hanks()

    def yardage_is_precise(self):
        return self.pieces.yardage_is_precise()

    #
    # Redo-related
    #

    def redo_deadline(self):
        # return datetime at which point redos stop being possible. Note that even though
        # this might be in the future, a redo may not be possible for other reasons.
        # Always check with redo_possible().
        redo_window = datetime.timedelta(REDO_DEADLINE_IN_DAYS)

        from_deadline_start = REDO_DEADLINE_START + redo_window
        from_creation = self.creation_date + redo_window

        deadline = max([from_creation, from_deadline_start])

        return deadline

    def redo_days_left(self):
        # Return days left until redo expires, in integer, rounded down.
        # Return None instead of negative number
        time_left = self.redo_deadline() - timezone.now()
        if time_left > datetime.timedelta(0):
            return time_left.days
        else:
            return None

    def redo_possible(self):
        # Returns True iff the user should be allowed to redo this pattern
        already_redone = self.original_pieces is not None
        deadline_in_future = timezone.now() < self.redo_deadline()

        redo_possible = (not already_redone) and deadline_in_future

        return redo_possible

    def update_with_new_pieces(self, ipp):
        assert self.original_pieces is None
        self.original_pieces = self.pieces
        self.pieces = ipp
        self.save()

    def full_clean(self, *args, **kwargs):
        self.pieces.full_clean()
        if self.original_pieces:
            self.original_pieces.full_clean()
        super(IndividualPattern, self).full_clean(*args, **kwargs)

    def clean_fields(self, exclude=None):
        if self.original_pieces:
            self.original_pieces.clean_fields(exclude)
        super(IndividualPattern, self).clean_fields(exclude)

    def clean(self):
        self.pieces.clean()
        if self.original_pieces:
            self.original_pieces.clean()
        super(IndividualPattern, self).clean()


class GradedPattern(_BasePattern):

    #
    # Subclasses must implement:
    #
    # * get_schematic_display_context(self)
    # * make_from_individual_pattern_pieces(cls, user, ipp)
    #
    # And either
    #
    # * self.abridged_pdf_renderer_class
    # * self.full_pdf_renderer_class
    # * self.web_renderer_class
    #
    # or they can override:
    #
    # * render_preamble(self, abridged=False)
    # * render_instructions(self, abridged=False)
    # * render_postamble(self, abridged=False)
    # * render_charts(self, abridged=False)
    # * render_pattern(self, abridged=False)

    class Meta:
        pass

    pieces = models.OneToOneField(GradedPatternPieces, on_delete=models.CASCADE)

    @property
    def user(self):
        return self.get_spec_source().user

    @property
    def row_gauge_four_inches(self):
        spec_source = self.get_spec_source()
        return spec_source.row_gauge

    @property
    def stitch_gauge_four_inches(self):
        spec_source = self.get_spec_source()
        return spec_source.stitch_gauge

    @property
    def gauge(self):
        return self.get_spec_source().gauge

    def get_absolute_url(self):
        return reverse("patterns:gradedpattern_detail_view", kwargs={"pk": self.id})

    def full_clean(self, *args, **kwargs):
        self.pieces.full_clean()
        super(_BasePattern, self).full_clean(*args, **kwargs)

    def clean(self):
        self.pieces.clean()
        super(GradedPattern, self).clean()


class ApprovedPatternLinkageManager(models.Manager):
    def get_queryset(self):
        qs = super(ApprovedPatternLinkageManager, self).get_queryset()
        return qs.filter(pattern__transactions__approved=True)


class LivePatternLinkageManager(ApprovedPatternLinkageManager):
    def get_queryset(self):
        qs = super(LivePatternLinkageManager, self).get_queryset()
        return qs.filter(pattern__archived=False)


class ArchivedPatternLinkageManager(ApprovedPatternLinkageManager):
    def get_queryset(self):
        qs = super(ArchivedPatternLinkageManager, self).get_queryset()
        return qs.filter(pattern__archived=True)


class Redo(PolymorphicModel):

    # Subclasses need to implement:
    #
    # * get_igp_class()

    pattern = models.ForeignKey(IndividualPattern, on_delete=models.CASCADE)
    swatch = models.ForeignKey(Swatch, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "%s (redo)" % self.pattern.name

    # List of attribute names for which Redo should NOT just reach back through to the underlying PatternSpec.
    pspec_property_blacklist = [
        "_pattern_cache",
        "_prefetched_objects_cache",
        "pattern",
    ]

    def __getattr__(self, item):
        if item not in self.pspec_property_blacklist:
            underlying_pspec = self.get_original_patternspec()
            return getattr(underlying_pspec, item)
        else:
            raise AttributeError(item)

    def get_original_patternspec(self):
        # return the PatternSpec at the beginning of the pattern being redone.
        # DO NOT USE IF YOU CAN HELP IT. Much better to give Redo and PatternSpec
        # the same interface. But we need to expose it for __getattr__ above and
        # IndividualPattern.get_design, which is used by templates in the database
        from customfit.pattern_spec.models import PatternSpec

        pattern = self.pattern
        schematic = (
            pattern.original_pieces.schematic
            if pattern.original_pieces
            else pattern.pieces.schematic
        )
        pattern_spec = schematic.individual_garment_parameters.get_spec_source()
        assert isinstance(pattern_spec, PatternSpec)
        return pattern_spec


#
# Models for testing
#
