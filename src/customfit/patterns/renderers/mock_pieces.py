import abc
import logging
import os.path

from customfit.patterns.renderers import InformationSection, SubSection

from .base import BASE_TEMPLATE_DIR

logger = logging.getLogger(__name__)


MOCK_PIECES = os.path.join(BASE_TEMPLATE_DIR, "mock_pieces")


class DesignerNotesRenderer(InformationSection):

    piece_name = "Design Notes"

    def __bool__(self):
        """
        Returns True if the design has notes. This is a magic method
        that gets called in truth-testing. This will simplify
        higher-level code by allowing:

        dnr = DesignerNotesRenderer(...)
        ...
        if dnr:
            dnr.render()

        Note that the default for a Python object is to evaluate to True,
        so this method need only be defined for renderers that might
        be empty (like this one).
        """
        spec_source = self.piece.get_spec_source()
        if any([spec_source.description, spec_source.pattern_credits]):
            return True
        else:
            return False

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        spec_source = self.piece.get_spec_source()
        additional_context["designer_notes"] = spec_source.description
        additional_context["credits"] = spec_source.pattern_credits
        self.add_template_file(MOCK_PIECES, "designer_notes", additional_context)


class StitchesSectionRenderer(InformationSection):

    piece_name = "Stitches"

    def _get_stitches_with_notes(self):
        stitches_used = self.piece.get_spec_source().stitches_used()
        stitches_with_notes = [s for s in stitches_used if s.notes]
        return stitches_with_notes

    def __bool__(self):
        """
        Returns True if the design has stitches with notes. This is a magic
        method that gets called in truth-testing. This will
        simplify higher-level code by allowing:

        ssr = StitchesSectionRenderer(...)
        ...
        if ssr:
            ssr.render()

        Note that the default for a Python object is to evaluate to True,
        so this method need only be defined for renderers that might
        be empty (like this one).
        """
        if self._get_stitches_with_notes():
            return True
        else:
            return False

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        additional_context["stitches_with_notes"] = self._get_stitches_with_notes()
        self.add_template_file(MOCK_PIECES, "stitches_section", additional_context)


class PersonalNotesRendererBase(InformationSection):

    piece_name = "Your Notes"
    template_name = None  # Must be defined by subclasses.

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        self.add_template_file(MOCK_PIECES, self.template_name, additional_context)


class WebPersonalNotesRenderer(PersonalNotesRendererBase):

    template_name = "personal_notes"


class PdfPersonalNotesRenderer(PersonalNotesRendererBase):

    template_name = "personal_notes_pdf"

    def __bool__(self):
        """
        On PDFs, suppress display of personal notes section if there aren't any.
        (In the web version, we always show something in this section, because
        we can provide the option to add notes; we can't provide any such option
        for PDFs, so there's no point in showing anything here.)
        """
        return bool(self.piece.notes)


class AboutDesignerRenderer(InformationSection):

    def _get_designer(self):
        spec_source = self.piece.get_spec_source()
        if spec_source.design_origin:
            return spec_source.design_origin.designer
        else:
            return None

    @property
    def piece_name(self):
        designer = self._get_designer()
        # If designer is None, then __nonzero__ will return False and
        # we won't get here. So, we can assume designer is not None
        assert designer is not None
        return "About %s" % designer.short_name

    def __bool__(self):
        """
        Returns True if the original design has a designer and the designer
        has a non-None value in either the `about_designer_long` or
        'about_designer_short' field. This is a magic
        method that gets called in truth-testing. This will
        simplify higher-level code by allowing:

        adr = AboutDesignerRenderer(...)
        ...
        if adr:
            adr.render()

        Thus, we only render the About Designer section if we have text
        to put in that section.

        Note that the default for a Python object is to evaluate to True,
        so this method need only be defined for renderers that might
        be empty (like this one).
        """
        designer = self._get_designer()
        if designer is None:
            return False
        else:
            return any(
                [
                    designer.about_designer_long is not None,
                    designer.about_designer_short is not None,
                ]
            )

    def _gather_text(self, additional_context):
        if additional_context is None:
            additional_context = {}

        additional_context["designer"] = self._get_designer()

        self.add_template_file(MOCK_PIECES, "about_designer", additional_context)


class StitchChartsRenderer(InformationSection):

    piece_name = "Stitch Charts"

    def get_section_css_class(self):
        return "stitch-chart-section"

    def _stitches_with_charts(self):
        stitches_used = self.piece.get_spec_source().stitches_used()
        return [stitch for stitch in stitches_used if stitch.chart]

    def __bool__(self):
        """
        Returns True if any stitches have charts. This is a magic method
        that gets called in truth-testing. This will simplify
        higher-level code by allowing:

        scr = StitchCartsRenderer(...)
        ...
        if scr:
            scr.render()

        Note that the default for a Python object is to evaluate to True,
        so this method need only be defined for renderers that might
        be empty (like this one).
        """
        return len(self._stitches_with_charts()) > 0

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        additional_context["stitches"] = self._stitches_with_charts()

        self.add_template_file(MOCK_PIECES, "stitch_charts", additional_context)


class PatternNotesRenderer(InformationSection):

    piece_name = "Pattern Notes"

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        self.add_template_file(MOCK_PIECES, "pattern_notes", additional_context)


class FinishingSubSection(SubSection):

    # We leave the sort-order completely arbitrary until we actually have more than one
    # possible subsection to talk about.

    @property
    def display_name(self):
        return "Finishing"

    def __init__(self):
        super(FinishingSubSection, self).__init__()
        self.sort_order = None

    def __eq__(self, other):
        # We don't currently use this, but we need to define it or python will
        # use the default instead. So we should define it so as to not leave a time-bomb
        # for our future selves.
        assert isinstance(other, FinishingSubSection)
        return self.sort_order == other.sort_order

    def __lt__(self, other):
        # We don't currently use this, but we need to define it or python will
        # use the default instead. So we should define it so as to not leave a time-bomb
        # for our future selves.
        assert isinstance(other, FinishingSubSection)
        return self.sort_order < other.sort_order

    def starts_during(self, other):
        return False

    def starts_during_all_grades(self, other):
        return False

    @property
    def start_rows(self):
        return None

    @property
    def end_rows(self):
        return None

    @property
    def warn_if_interrupted(self):
        return True

    @property
    def interrupts_others(self):
        return True


class SchematicRendererBase(InformationSection, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def _get_template_name(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _get_template_dir(self):
        raise NotImplementedError()

    piece_name = "Pattern Schematic"

    def get_section_css_class(self):
        return "schematic-section"

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        schematic_context = self._make_context()
        schematic_context.update(additional_context)

        self.add_template_file(
            self._get_template_dir(), self._get_template_name(), schematic_context
        )

    def _make_context(self):

        context = self.piece.get_schematic_display_context()

        return context


class PreambleRendererBase(InformationSection):

    piece_name = "Pattern Information"

    # Note: subclasses should define the property/attribute template_name. template_dir, _make_design_choices_text
    # example: 'design_choices_web', 'design_choices_pdf'
    #
    # Should also define _base_notions or shadow _make_notion_text

    def _make_notion_text(self):
        """
        Figure out what to include under 'Notions' entry.
        """
        notions_text = ""
        notions_text += self._base_notions
        spec_source = self.piece.get_spec_source()

        if spec_source.notions:
            notions_text += ", "
            notions_text += spec_source.notions

        for stitch in spec_source.stitches_used():
            if stitch.extra_notions_text:
                notions_text += ", "
                notions_text += stitch.extra_notions_text

        return notions_text

    def _make_needle_text(self):
        """
        Figure out what to put under the 'Needles' entry.
        """
        needles_text = ""

        spec_source = self.piece.get_spec_source()
        try:
            swatch_text = spec_source.swatch.needle_size
        except AttributeError:
            # spec_source is graded and doesn't have a swatch, probably
            swatch_text = ""

        if swatch_text:
            if not swatch_text.endswith("."):
                # If they specified a needle size, we want to separate it
                # from other text by a period. But if they didn't,
                # having a period after blank text would look dumb.
                # So we add it here if needed rather than in the return.
                swatch_text += ". "
                needles_text += swatch_text

        design_text = spec_source.needles
        if design_text is not None:
            needles_text += design_text

        return needles_text

    def _get_context(self, additional_context=None):
        context = additional_context
        if context is None:
            context = {}

        context["notions"] = self._make_notion_text()
        context["needles"] = self._make_needle_text()
        context["design_choices"] = self._make_design_choices_text()

        return context

    def _gather_text(self, additional_context=None):

        context = self._get_context(additional_context)
        self.add_template_file(self.template_dir, self.template_name, context)
