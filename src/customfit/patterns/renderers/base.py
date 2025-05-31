import abc
import copy
import logging
import os.path
from functools import total_ordering
from itertools import chain, combinations, product

import django.template
import django.utils
from django.db.models import Model

from customfit.helpers.math_helpers import CallableCompoundResult, CompoundResult

logger = logging.getLogger(__name__)


# This file contains the base classes used to create patterntext. Although patterntext is just a giant
# HTML string, we construct it with, and to have, the following internal structure:
#
# * Sections: Patterntext is a sequence of sections. Each piece has its own section, and there are
#   sections for things like pattern notes, 'about the author', etc. A section is both a logical and
#   typographic entity: we will represent the patterntext as a sequence of `Section` objects (below),
#   and each section will begin with the section's title in H2 tags.
#
#   Right now, Sections fall neatly into two categories: those containing knitting instructions, and
#   those that don't. 'Non-instruction' sections, are generally informational ('About the desginer, etc.)
#   and do not have any internal structure we need to care about here. (Often, they can be
#   implemented with a single template.) 'Instruction' sections often have a highly-dynamic internal structure
#   composed of SubSections (below) derived from Elements (also below).
#
# * Subsections: Although many sections are simple enough to have no internal structure, some are
#   composed of internal subsections. Body-piece sections, for example, will have subsections for
#   cast-on, neckline & shoulder shaping, armhole shaping, etc. It is important to note that subsections
#   are purely internal concepts: they do not necessarily correspond one-to-one with a chunk of knitting
#   that would be meaningful to the knitter (see Elements, next). Also, they do not receive any special
#   typographic treatment, such as a starting header. (In fact, many subsections actually have normal-
#   looking text at the beginning and a header-like entity in the middle!) Subsections simply hold a sequence
#   of instructions that are intended to be printed or moved around as a unit.
#
# * An Element is a chunk of sweater-construction that is thought of as a single unit by the knitter. For
#   example, 'the neckline' is an Element, as is 'the cast-on and hem' and 'the armholes.' We separate Elements
#   from Subsections because an Element might actually produce more than one Subsection. If the neckline extends
#   below the armholes, for example, then the armhole instructions actually get broken into two chunks: one for
#   the armhole on one side, and one for the armhole on the otherside. These chunks get separated in the pattern
#   so that the knitter receives all of one side's instructions (neck, armhole and shoulder) before any instructions
#   for the other side (neck, armhole, and shoulder). So in this case, the armhole Element produces two Subsections
#   (one for each side).
#
# Why do we need all of this internal structure? First, we need to be able to add Elements to a Section dynamically.
# If a body-piece is straight, for example, then the 'waist/bust shaping' Element will be skipped. Likewise, if a
# Design wishes to add design-specific instructions to occur at specific locations (to change the all-over stitch at
# a certain height, for example) then those will be represented using dynamically-added Elements. Also, we need to
# be able to warn the reader that Elements will overlap, in the sense that their instructions are to be followed
# simultaneously. If the neck-shaping should begin before or during the armhole shaping, for example, then those two
# Elements 'overlap' and we should tell the reader this at the beginning of the section.
#
# Okay, but why do we then need Subsections? Because Element do *not* necessarily correspond to a single continuous
# set of instructions. Consider, for example, a front sweater-piece with Elements:
#
# * Cast-on and Hem
# * Shaping
# * Neckline
# * Armholes
# * Shoulders
#
# If the neckline starts below the armholes, though, we may need to order the instructions as follows:
#
# * Cast-on and hem
# * Shaping
# * Neckline start
# * "Side 1" side of neckline
# * "Side 1" armhole
# * "Side 1" shoulder
# * "Side 2" neckline
# * "Side 2" armhole
# * "Side 2" shoulder
#
# (Sometimes "Side 1/Side 2" means "left/right", sometimes "right/left". It depends on front vs. back.) If the piece
# is a cardigan side, on the other hand, then we need to order the instructions as:
#
#  * Cast-on and hem
# * Shaping
# * Neckline start
# * side of neckline
# * armhole
# * shoulder
#
#  So what do we do?
#
# 1) We first generate the Elements of a section, where each Element has a start row and an end row. These are actually
#    lists. For a single-grade pattern, it's a list of one element. In a graded pattern, it's a list of one element
#    per grade. These allows us to sort them and detect overlaps (so that we can warn the reader).
#
# 2) We then ask each Element for its set of Subsections. We can then sort the Subsections and order their
#    instructions accordingly.
#
# Note, however, that the ordering of Subsections is tricky: it is not always as simple as sorting by start-row.
# Above, for example, 'side 1' shoulders come before 'side 2' armholes. Also, we *sometimes* need to warn the
# reader of overlaps before individual subsections. If the 'side 1' neck is not finished before the 'side 1' armhole
# begin, for example, we need to tell the reader this by inserting "At the same time:" before the start of
# the 'side 1' armhole instructions. But sometimes we don't: we would never say 'At the same time:' before the
# start of the 'side 2' neckline. It gets complicated. But the important point here is that we need to be able
# to sort Subsections in piece-specific ways, and be able to detect/signal overlap in ways that change from
# Subsection to SubSection.
#
#
# Based on all this, we define a few base classes-- none of which are meant to be used directly:
#
# * The TextBuilder contains helper methods for building the text of a section/subsection. Specifically,
#   it contains methods for adding text-chunks to the text directly, or to add text by rendering a
#   template file.
#
# * The SubSection class extends TextBuilder, and contains a number of methods/attributes needed to
#   represent a subsection. (For example, methods to sort Subsections and detect overlap.)
#
# * The Element section holds a set of SubSections, and holds information about the element itself.
#   (for example, its name and start/end rows).
#
# * The Section abstract base class defines the interface that all 'section' objects must provide.
#
# * The InformSection class is for non-instruction sections. It does not use internal subsections.
#   It extends TextBuilder and implements Section.
#
# * The InstructionSection class is for sections that contain knitting instructions. It implements Section,
#   but does not extend TextBuilder. Instead, it contains methods for handling sets of Elements and
#   their SubSections.
#
# The actual patterntext will be built using section-specific classes that extend either InformSection
# or InstructionSection.
#
# (Note: we considered the idea of defining structure within TextBuilder, such as Paragraph, but decided
# that this was not worth it yet. It may be in the future. But for the moment, TextBuilder works on
# dumb strings.)


class PieceList(object):

    def __init__(self, piece_iter):
        super(PieceList, self).__init__()
        self._piece_list = [p for p in piece_iter]

        # prohibit corner case: empty list
        assert self._piece_list, self._piece_list

    def _postprocess(self, result_list):
        # If the results are itself a list of Models, assume they are pieces and return a PieceList
        if all(isinstance(x, Model) for x in result_list):
            return PieceList(result_list)

        # Else, check on the callability
        return self._branch_on_callable(result_list)

    @staticmethod
    def _branch_on_callable(list_to_call):
        are_callable = [callable(x) for x in list_to_call]
        # case 1: they are all callable
        if all(are_callable):
            return CallableCompoundResult(list_to_call)

        # case 2: none are callable
        elif not any(are_callable):
            return CompoundResult(list_to_call)

        # case 3: fail loudly:
        else:
            raise RuntimeError("Some but not all items are callable")

    def __getitem__(self, key):
        sub_results = [d[key] for d in self._piece_list]
        return self._postprocess(sub_results)

    def __getattr__(self, item):
        sub_results = [getattr(p, item) for p in self._piece_list]
        return self._postprocess(sub_results)

    def get_first(self):
        return self._piece_list[0]

    def __len__(self):
        return len(self._piece_list)


#####################################################################
# Base classes
#####################################################################


BASE_TEMPLATE_DIR = os.path.join("patterns", "renderer_templates")
STITCH_TEMPLATES = os.path.join(BASE_TEMPLATE_DIR, "stitch_templates")
TEMPLATE_SUFFIX = ".html"


#
# Helper functions
#


def make_template_path(template_dir, template_name):
    """
    Makes a path to the template, suitable for giving to
    `django.template.loader.get_template`. Argument
    `template_name` should be the basename of the template, without
    the suffix. This method will automatically add the `TEMPLATE_SUFFIX`
    value.
    """
    return os.path.join(template_dir, template_name + TEMPLATE_SUFFIX)


def render_template(template, additional_context_data=None):
    """
    Helper funtion to render a Template object and perform necessary
    postprocessing.
    """
    if additional_context_data is None:
        additional_context_data = {}

    final_context = additional_context_data

    context = django.template.Context(final_context)

    # For simplicity, assume/enforce that template is a 'real' template (django.template.base.Template)
    # and not the top-level django.template.backends.django.Template by 'wrapping' it if it is.
    if isinstance(template, django.template.backends.django.Template):
        template = template.template

    try:
        html = template.render(context)
        safe_html = django.utils.safestring.mark_safe(html)
        return safe_html
    except:
        logger.exception("%s called with context %s", template.name, context)
        raise


def render_template_path(template_path, additional_context_data=None):
    """
    Helper function to get a template from a given path,
    render it in the given context, and return a safe string. Note:
    does not use any internal values from the object: all context
    must be passed in explicitly.
    """

    if additional_context_data is None:
        additional_context_data = {}
    template = django.template.loader.get_template(template_path)
    try:
        return render_template(template, additional_context_data)
    except:
        logger.exception(
            "%s called with context %s", template_path, additional_context_data
        )
        raise


def _render_template_dir_name(template_dir, template_name, additional_context=None):
    """
    Take a template dir, a template in that dir, and context data and
    return the rendered template as a safe string.
    """
    if additional_context is None:
        additional_context = {}
    template_path = make_template_path(template_dir, template_name)
    return render_template_path(template_path, additional_context)


def _make_stitch_transition_text(old_stitch, new_stitch):
    """
        Add the text for changing from a hem stitch to an allover stitch.
        Note: switching to/from None gets special handling. t breaks down like
        this--

                new stitch
        old     None                 not None
              --------------------------------------------------------
        None  | switch to whatever   switch to new stitch
    not None  | switch to whatever   pass or switch to new stitch

    """

    if new_stitch is None:
        return _render_template_dir_name(
            STITCH_TEMPLATES, "switch_stitches_to_whatever"
        )
    elif (old_stitch is None) or (old_stitch != new_stitch):
        additional_context = {"stitch_name": new_stitch.patterntext}
        return _render_template_dir_name(
            STITCH_TEMPLATES, "switch_stitches", additional_context
        )

    else:
        # Only case left: new_stitch == old_stitch != None
        return ""


class TextBuilder(object):
    """
    Base class for classes that build text from text-chunks or template files.
    """

    def __init__(self):
        self._text_chunks = []

    def _render_text(self):
        return "".join(self._text_chunks)

    def _add_text_chunk(self, text):
        """
        Adds a string to the list of patterntext strings (`self._text_chunks`).
        """
        self._text_chunks += [text]

    def add_template_object(self, template, context_data=None):
        """
        Take a Template object, render it using context_data, and add the
        resulting text to self._text_chunks. As opposed to _add_template_file,
        expects to be given a django.template.Template rather than a file-name.
        """
        if context_data is None:
            context_data = {}

        text_chunk = render_template(template, context_data)
        self._add_text_chunk(text_chunk)

    def add_template_file(self, template_dir, template_name, context_data=None):
        """
        Get a template with basename `template_name` from directory
        `template_dir`, render it in the context `context_data`, and add
        the resulting text to `self._text_chunks`. Note: the context will
        map `'piece'` to the object provided to `__init__` unless that mapping
        is overwritten by `context_data`. As opposed to _add_template_object,
        expects to be given a file dir/name combination for a template file
        instead of a live Template object.
        """
        if context_data is None:
            context_data = {}

        text_chunk = _render_template_dir_name(
            template_dir, template_name, context_data
        )
        self._add_text_chunk(text_chunk)


@total_ordering
class SubSection(TextBuilder, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def display_name(self):
        pass

    # Different sections need to sort their sub-sections in different ways. Therefore,
    # we let each section define their own specific subclass of SubSection and define
    # a sorting method.
    @abc.abstractmethod
    def __eq__(self, other):
        pass

    @abc.abstractmethod
    def __lt__(self, other):
        pass

    # Likewise, each piece needs to define for its own subsections the manner in
    # which to detect overlaps. Specifically, we detect one specific kind of overlap:
    # when one section starts 'during' another section. There are two kinds of 'starts during'. They
    # act identically for single-grade patterns, but may differ for multi-grade patterns
    #
    # * starts_during(self, other) returns True if there is overlap in *any* grade
    #
    # * starts_during_all_grades(self, other) returns True if there is overlap in *all* grades
    @abc.abstractmethod
    def starts_during(self, other):
        """
        Return true iff self begins 'during' other (after other starts but before other ends) in any grade.
        """
        pass

    @abc.abstractmethod
    def starts_during_all_grades(self, other):
        """
        Return true iff self begins 'during' other (after other starts but before other ends) in all grades.
        """
        pass

    # We need all subsections to be able to provide their 'start' and 'end' rows
    # so that we can alert the reader to overlaps of Elements.
    @property
    @abc.abstractmethod
    def start_rows(self):
        # Note: should return CompoundResult or None
        pass

    @property
    def smallest_start_row(self):
        return None if self.start_rows is None else min(self.start_rows)

    @property
    @abc.abstractmethod
    def end_rows(self):
        # Note: should return CompoundResult or None
        pass

    @property
    @abc.abstractmethod
    def interrupts_others(self):
        # If this returns True, then it is possibly disruptive to other SubSections for this
        # Subsection to start during it-- and we may produce a warning to the user. See
        # warn_if_interrupted, below.
        pass

    @property
    @abc.abstractmethod
    def warn_if_interrupted(self):
        # If this returns True, then we need to warn the user when this SubSection is interrupted.
        pass

    # Lastly, different subsections may want to handle overlaps differently. We provide a common default here.
    def handle_overlap(self, overlap, overlap_is_partial=False):
        if overlap:
            if overlap_is_partial:
                self._text_chunks.insert(
                    0,
                    "<p><strong><em>At the same time (for some sizes):</em></strong></p>",
                )
                if getattr(self, "start_text_overlap_partial", None):
                    self._text_chunks.insert(1, self.start_text_overlap_partial)
            else:
                self._text_chunks.insert(
                    0, "<p><strong><em>At the same time:</em></strong></p>"
                )
                if getattr(self, "start_text_overlap", None):
                    self._text_chunks.insert(1, self.start_text_overlap)
        else:
            if getattr(self, "start_text_non_overlap", None):
                self._text_chunks.insert(0, self.start_text_non_overlap)

    def add_start_template_overlap(
        self, template_dir, template_name, context_data=None
    ):
        # Render the given template in the given context, and assign it to self.start_text_overlap.
        # Convenience method
        if context_data is None:
            context_data = {}

        text_chunk = _render_template_dir_name(
            template_dir, template_name, context_data
        )
        self.start_text_overlap = text_chunk

    def add_start_template_overlap_partial(
        self, template_dir, template_name, context_data=None
    ):
        # Render the given template in the given context, and assign it to self.start_text_overlap_partial.
        # Convenience method
        if context_data is None:
            context_data = {}

        text_chunk = _render_template_dir_name(
            template_dir, template_name, context_data
        )
        self.start_text_overlap_partial = text_chunk

    def add_start_template_non_overlap(
        self, template_dir, template_name, context_data=None
    ):
        # Render the given template in the given context, and assign it to self.start_text_non_overlap.
        # Convenience method
        if context_data is None:
            context_data = {}

        text_chunk = _render_template_dir_name(
            template_dir, template_name, context_data
        )
        self.start_text_non_overlap = text_chunk

    def render(self, overlap=False, overlap_is_partial=False):
        self.handle_overlap(overlap, overlap_is_partial)
        return_me = "".join(self._text_chunks)
        return return_me


class Element(object):

    def __init__(self, display_name, subsection=None):
        # An element with one subsection (a common theme) can be quickly made by passing
        # the subsection into the constructor. display_name should be singular, so as to fit
        # into the template "___ begins on row X and ends on row Y"
        self.display_name = display_name
        self.subsections = []
        if subsection:
            self.subsections.append(subsection)

    def warn_of_overlap_with(self, other):
        # Return True iff there is the need to warn the user of an overlap between other and self.
        # (Returns True if there is an overlap in *any* grade.)
        # Can assume that self starts before other
        for self_subsection, other_subsection in product(
            self.subsections, other.subsections
        ):
            if all(
                [
                    other_subsection.starts_during(self_subsection),
                    other_subsection.interrupts_others,
                    self_subsection.warn_if_interrupted,
                ]
            ):
                return True
        return False

    def warn_of_full_overlap_with(self, other):
        # Return True iff there is the need to warn the user of a full overlap between other and self.
        # (That is, returns True if there is an overlap in *all* grades.)
        # Can assume that self starts before other
        for self_subsection, other_subsection in product(
            self.subsections, other.subsections
        ):
            if all(
                [
                    other_subsection.starts_during_all_grades(self_subsection),
                    other_subsection.interrupts_others,
                    self_subsection.warn_if_interrupted,
                ]
            ):
                return True
        return False

    def add_subsection(self, new_subsection):
        self.subsections.append(new_subsection)

    def smallest_start_row(self):
        def _min_helper(l_or_none):
            if l_or_none is None:
                return None
            else:
                return min(l_or_none)

        if self.subsections:
            mins = [_min_helper(subsec.start_rows) for subsec in self.subsections]
            return min(mins)
        else:
            return None

    # used in templates
    def start_rows(self):
        if self.subsections:
            start_rows_list = [subsec.start_rows for subsec in self.subsections]
            min_count_list = [
                min(grade_counts) for grade_counts in zip(*start_rows_list)
            ]
            return CompoundResult(min_count_list)
        else:
            return None

    # used in templates
    def end_rows(self):
        if self.subsections:
            end_rows_list = [subsec.end_rows for subsec in self.subsections]
            max_count_list = CompoundResult(
                [max(grade_counts) for grade_counts in zip(*end_rows_list)]
            )
            return max_count_list

        else:
            return None


class Section(object, metaclass=abc.ABCMeta):
    """
    Builds the text of a section and returns it as a (safe) HTML string.

    Use: Sub-classes should implement at least three things:

    1) The abstract method _section_text.

    2) The abstract property piece_name.

    3) The abstract property top_level_template

    These are used in the (non-abstract) method render(), which will drop the
    section-text and piece-name into the top-level template and return the
    result as a (safe) HTML string.

    In addition, sub-classes may implement:

    3) The __nonzero__ method. This is a special Python method that is used
    to evaluate the object to True or False.

    Some Sections may be 'empty' in the sense that they will generate no actual
    patterntext. (For example, the StitchChartRenderer sub-class will be empty
    when no stitches in the pattern have charts.) These subclasses should
    implement __nonzero__() and evalaute to False when empty. This signals to
    higher-level code that the renderer should be skipped. Note that if an
    object implements neither __nonzero__() or __len__(), then it automatically
    evaluates to True. Thus, the __nonzero__() method need not be implemented by
    sub-classes that will always have patterntext to display.

    """

    @abc.abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @property
    @abc.abstractmethod
    def top_level_template(self):
        pass

    @property
    @abc.abstractmethod
    def piece_name(self):
        pass

    @abc.abstractmethod
    def _section_text(self, additional_context):
        pass

    def get_section_css_class(self):
        """
        Override for pieces that need custom top-level css class
        """
        return None

    @abc.abstractmethod
    def _get_piece_context(self):
        # return template context for 'piece', etc
        pass

    def render(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        piece_context = self._get_piece_context()
        additional_context.update(piece_context)

        # Get the patterntext proper
        section_text = self._section_text(additional_context)
        safe_text = django.utils.safestring.mark_safe(section_text)

        # Now, drop that in to a top-level template which combines that
        # with the name of the piece.
        toplevel_context = {}
        if "piece_name" in additional_context:
            toplevel_context["piece_name"] = additional_context["piece_name"]
        else:
            toplevel_context["piece_name"] = self.piece_name

        if "section_css_class" in additional_context:
            toplevel_context["section_css_class"] = additional_context[
                "section_css_class"
            ]
        else:
            toplevel_context["section_css_class"] = self.get_section_css_class()

        toplevel_context["pattern_text"] = safe_text

        template_path = make_template_path(BASE_TEMPLATE_DIR, self.top_level_template)
        final_html = render_template_path(template_path, toplevel_context)

        return final_html


class InformationSection(Section, TextBuilder, metaclass=abc.ABCMeta):

    def __init__(self, piece):
        Section.__init__(self, piece)
        TextBuilder.__init__(self)
        self.piece = piece

    # The template for a non-piece section is called 'mock_piece.html' for historical reasons.
    # (Originally, there were no non-piece sections, so when we added them we needed to
    # shoehorn them into the 'piece' paradigm.)
    @property
    def top_level_template(self):
        return "mock_piece"

    @abc.abstractmethod
    def _gather_text(self, additional_context):
        pass

    def _section_text(self, additional_context):
        self._gather_text(additional_context)
        return self._render_text()

    def _get_piece_context(self):
        # return template context for 'piece', etc
        return {"piece": self.piece}


class InstructionSection(Section, metaclass=abc.ABCMeta):

    def __init__(self, piece):
        super(InstructionSection, self).__init__()
        if isinstance(piece, PieceList):
            self.piece_list = piece
            self.exemplar = piece.get_first()
            self.is_graded = True
        else:
            self.piece_list = PieceList([piece])
            self.exemplar = piece
            self.is_graded = False

    # This template is called 'piece' for historical reasons, even though it is used by sections that
    # don't actually represent pieces. (Like 'finishing', for example.)
    @property
    def top_level_template(self):
        return "piece"

    @abc.abstractmethod
    def _make_elements(self, additional_context=None):
        # Should return a list of Element objects, ready to render
        pass

    def _get_piece_context(self):
        # return template context for 'piece', etc
        return {"piece": self.piece_list, "piece_is_graded": self.is_graded}

    ################################################################################################
    #
    # Methods and classes for uniform handling of 'additonal elements'
    #
    #################################################################################################

    class SectionStartsAfterPieceEnds(Exception):
        pass

    @abc.abstractmethod
    def _get_additional_elements_from_design(self, design):
        """
        Given a Design, retrieve the AdditonalDesignElements that are relevant for this section
        and return them as a list.
        """
        pass

    @abc.abstractmethod
    def _get_start_rows_from_additonal_element(self, additional_element):
        """
        Given a list of designs.models.AdditionalDesignElement instances, return the rows
        at which they should start. Note: this is mostly a thin wrapper around the
        methods of the AdditionalDesignElement itself, but those methods (and their arguments)
        will depend on whether this is for front, back, or sleeve.

        return an int or CompoundResult
        """
        pass

    @abc.abstractmethod
    def _make_subsections_for_additonal_element(
        self,
        title,
        start_rows,
        end_rows,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        """
        Return a list of bare-bones SubSection instances for an 'additional element'. Will be a thin
        wrapper around a SubSection class.
        """
        pass

    @abc.abstractmethod
    def get_piece_final_rows(self, additional_context):
        """
        return an int or CompoundResult
        """
        pass

    def _make_additional_elements(self, additional_context):
        """
        Get relevant 'additional design elements' from the original Design (if it exists)
        and return them as a list of Elements
        """
        pattern = self.exemplar.get_pattern()
        spec_source = pattern.get_spec_source()
        design = spec_source.design_origin
        if design is None:
            return []
        else:
            additional_design_elements = self._get_additional_elements_from_design(
                design
            )
            return_me = []
            for adl in additional_design_elements:
                pattern_element = self._make_pattern_element_from_design_element(
                    adl, additional_context
                )
                return_me.append(pattern_element)
            return return_me

    def _make_context_for_additional_element(self, start_rows, end_rows):
        # Note: if you change anything here, be sure to synchronize the help_text being displayed to the
        # admin in customfit.designs.admin:AdditionalDesignElementTemplateAdmin
        gauge = self.exemplar.gauge
        context = {}
        context["piece"] = self.piece_list
        context["start_row"] = start_rows
        context["final_row"] = end_rows
        context["start_height"] = start_rows / gauge.rows
        context["final_height"] = end_rows / gauge.rows
        context["height_in_rows"] = CompoundResult(
            [int(x) for x in (end_rows - start_rows + 1)]
        )
        context["height_in_inches"] = (end_rows - start_rows + 1) / gauge.rows
        return context

    def _make_pattern_element_from_design_element(self, adl, additional_context):
        """
        Given an designs.models.AdditionalDesignElement, turn it into an Element and return it.
        """
        return_element = Element(adl.name)

        title = adl.name
        gauge = self.exemplar.gauge
        start_rows = self._get_start_rows_from_additonal_element(adl)
        end_rows = start_rows + adl.height_in_rows(gauge) - 1

        # Catch a possibility-- the end_row is after the end of the piece. This can be the
        # case if the element has too much height, or if it has 'no end' (which translated into
        # an infinte height_in_rows
        final_rows = self.get_piece_final_rows(additional_context)
        new_end_rows = [min(x, y) for (x, y) in zip(end_rows, final_rows)]
        end_rows = CompoundResult(new_end_rows)

        # Determine warning behavior for this element
        interrupts_others = adl.interrupts_others()
        warn_if_interrupted = adl.warn_if_interrupted()

        subsections = self._make_subsections_for_additonal_element(
            title,
            start_rows,
            end_rows,
            interrupts_others,
            warn_if_interrupted,
            additional_context,
        )

        for subsection in subsections:
            context = copy.copy(additional_context)
            context.update(
                self._make_context_for_additional_element(start_rows, end_rows)
            )
            subsection.add_template_object(adl.get_template(), context)
            return_element.add_subsection(subsection)

        return return_element

    ######################################################################################################
    #
    # Building the patterntext
    #
    ######################################################################################################

    def render(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        if "gauge" not in additional_context:
            additional_context["gauge"] = self.exemplar.gauge
        if "design" not in additional_context:
            additional_context["design"] = self.exemplar.design

        return super(InstructionSection, self).render(additional_context)

    def _section_text(self, additional_context=None):
        return_me = ""

        # Gather elements, sort by smallest start row. (That is, smallest across all grades.)
        elements = sorted(
            self._make_elements(additional_context),
            key=lambda x: x.smallest_start_row(),
        )

        # Get subsections from elements
        subsections = chain.from_iterable([element.subsections for element in elements])

        # Remove empty subsections, sort the rest. Note that 'empty' is determined by the
        # __nonzero__ method on subsections, which will make a SubSection evaluate to 'False' if
        # it has no text to present. The sort-order is determined by Subsection's __cmp__ method.
        # (This allows subclasses of Subsection to specify their own sort-orders).
        subsections = sorted(filter(bool, subsections))

        # List element overlaps for the reader. Note that the list `elements` is sorted by this point,
        # and combinations() will preserve that order. So all pairs (a, b) will have a come before b
        # in elements.
        element_overlaps = [
            (a, b) for (a, b) in combinations(elements, 2) if a.warn_of_overlap_with(b)
        ]

        # Annotate with whether the overlaps are full or partial
        element_overlaps = [
            (a, b, a.warn_of_full_overlap_with(b)) for (a, b) in element_overlaps
        ]

        if element_overlaps:
            if len(element_overlaps) == 1:
                (first_element, second_element, full_overlap) = element_overlaps[0]
                return_me += _render_template_dir_name(
                    BASE_TEMPLATE_DIR,
                    "single_overlap_warning",
                    {
                        "first_element": first_element,
                        "second_element": second_element,
                        "overlap_is_full": full_overlap,
                    },
                )

            else:
                return_me += _render_template_dir_name(
                    BASE_TEMPLATE_DIR,
                    "multiple_overlap_warnings",
                    {"overlap_pairs": element_overlaps},
                )

        # The above was about *element* overlaps. Now we need to detect overlaps
        # at the subsection level. Why? So that the interruptING subsection can remind the user
        # that it is interrupting (via an "at the same time" at the beginning.) But we
        # only need to do that if some prior interrupted section would warn about the interruption
        prior_sections = []
        for subsection in subsections:
            if subsection.interrupts_others:
                interrupted_sections = [
                    s for s in prior_sections if subsection.starts_during(s)
                ]
                overlap_to_handle = any(
                    [s.warn_if_interrupted for s in interrupted_sections]
                )
                overlap_is_full = any(
                    [subsection.starts_during_all_grades(s) for s in prior_sections]
                )
                overlap_is_only_partial = not overlap_is_full
            else:
                overlap_to_handle = False
                overlap_is_only_partial = False
            return_me += subsection.render(
                overlap=overlap_to_handle, overlap_is_partial=overlap_is_only_partial
            )
            prior_sections.append(subsection)

        return return_me

    # Embed helper function in this class to simplify module API
    @staticmethod
    def make_stitch_transition_text(old_stitch, new_stitch):
        return _make_stitch_transition_text(old_stitch, new_stitch)
