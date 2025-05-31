import logging

import django.template
import django.utils
from django.core.cache import cache

PREAMBLE_CHUNK_NAME = "preamble"
INSTRUCTIONS_CHUNK_NAME = "instructions"
POSTAMBLE_CHUNK_NAME = "postamble"
CHARTS_CHUNK_NAME = "charts"
PATTERN_CHUNK_NAME = "pattern"
COMPOUND_CHUNK_NAMES = [
    PREAMBLE_CHUNK_NAME,
    INSTRUCTIONS_CHUNK_NAME,
    POSTAMBLE_CHUNK_NAME,
    CHARTS_CHUNK_NAME,
    PATTERN_CHUNK_NAME,
]


logger = logging.getLogger(__name__)


class PatternRendererBase(object):
    """
    When initialized on a IndividualPattern object, will return the
    pattern instructions in HTML-- either in pieces or as a whole.

    Note: sub-classes need to define four additional methods:

    * self._make_preamble_piece_list(pattern)
    * self._make_instruction_piece_list(pattern)
    * self._make_postamble_piece_list(pattern)
    * selt._make_chart_piece_list(pattern)

    All four methods should return a list of (piece, renderer_class) tuples
    (where the piece can actually be any object, such as an IndividualPattern
    instance).
    """

    # Note: not a PieceRenderer, as it doesn't use any of those methods

    def __init__(self, pattern):
        self.pattern = pattern
        self.preamble_pieces = self._make_preamble_piece_list(pattern)
        self.instruction_pieces = self._make_instruction_piece_list(pattern)
        self.postamble_pieces = self._make_postamble_piece_list(pattern)
        self.chart_pieces = self._make_chart_piece_list(pattern)
        self.pieces = sum(
            [
                self.preamble_pieces,
                self.instruction_pieces,
                self.postamble_pieces,
                self.chart_pieces,
            ],
            [],
        )

    @staticmethod
    def _make_cache_key(renderer, chunk_name, ids):
        key = "patterntext:%s:%s:%s" % (renderer.__class__.__name__, chunk_name, ids)
        key = key.replace(" ", "_")  # Memcached doesn't like spaces
        return key

    def _piece_cache_key(self, renderer):
        try:
            exemplar = renderer.exemplar
            ids = renderer.piece_list.id
        except AttributeError:
            exemplar = renderer.piece
            ids = [renderer.piece.id]
        assert exemplar.__class__.__name__ not in COMPOUND_CHUNK_NAMES

        return self._make_cache_key(renderer, exemplar.__class__.__name__, ids)

    def prefill_cache(self):
        self.render_pattern()

    def flush_cache(self):
        for piece_list in [
            self.preamble_pieces,
            self.instruction_pieces,
            self.postamble_pieces,
            self.chart_pieces,
        ]:
            renderers = self._filter_renderers(piece_list)
            cache_keys = [self._piece_cache_key(renderer) for renderer in renderers]
            cache.delete_many(cache_keys)
        chunk_keys = [
            self._make_cache_key(self, chunk_name, [self.pattern.id])
            for chunk_name in COMPOUND_CHUNK_NAMES
        ]
        cache.delete_many(chunk_keys)

    def _filter_renderers(self, piece_list):
        """
        Take a list of (piece_object, PieceRendererClass) pairs, returns a list of those
        PieceRendererClass(piece_object) objects where
        * piece_object is not None, and
        * PieceRendererClass(piece_object) does not evaluate to False
        """
        l1 = [
            renderer_class(piece)
            for (piece, renderer_class) in piece_list
            if piece is not None
        ]
        l2 = [renderer for renderer in l1 if renderer]
        return l2

    def _render_piece_list(self, piece_list):
        """
        Take a list of (piece_object, PieceRendererClass) pairs,
        filter out the entries where piece_object is not None,
        render the remaining pieces using their respective
        PieceRendererClasses, and combine/return the resulting strings
        as a single safestring.
        """

        # Skip:
        #
        # 1) Those pieces that do not actually exist. Cardigans do not have
        # sleeves, for example, so we are going to skip any attempt to
        # render sleeve patterntext for non-existent sleeves. Note that
        # this is a 'structural' test: this first test is only testing
        # whether or not the piece exists to be rendered in the first
        # place.
        #
        # Those pieces that don't generate patterntest. Many of our 'pieces'
        # are 'mock pieces', representing information about the
        # pattern other than the instructions for a piece. For example,
        # the 'Pattern Notes' section is a mock piece, as is the
        # 'Schematic' section. There are some mock pieces that might be
        # 'empty' in the sense of not having any information to
        # display. For example, not all stitches have charts. Thus, the
        # 'Stitch Charts' section might not have any charts to display.
        # Note that this is different than the case above-- that test
        # was for pieces that do not exist and this is about pieces
        # that exist but are empty.

        renderers = self._filter_renderers(piece_list)

        # Now get (cached?) patterntext for each renderer
        return_strings = []

        for renderer in renderers:

            # Let's first check to see if we have that
            # patterntext in the cache. (We can't do this within the renderer's 'render()' method
            # because we only know out here what the 'additional context' will be.)

            cache_key = self._piece_cache_key(renderer)
            logger.info("Looking in cache for %s", cache_key)
            piece_text = cache.get(cache_key)

            if piece_text is None:
                # cache miss! Generate the text and store it
                logger.info("%s not found in cache-- generating and storing", cache_key)
                additional_context = {"pattern": self.pattern}
                piece_text = renderer.render(additional_context)
                cache.set(cache_key, piece_text)
            else:
                logger.info("%s found in cache", cache_key)

            return_strings.append(piece_text)

        html = "".join(return_strings)
        safe_html = django.utils.safestring.mark_safe(html)
        return safe_html

    def render_pattern(self):
        """
        Will return the HTML for patterntext as a safestring.
        """
        cache_key = self._make_cache_key(self, PATTERN_CHUNK_NAME, [self.pattern.id])
        chunk_text = cache.get(cache_key)
        if chunk_text is None:
            sub_htmls = [
                self.render_preamble(),
                self.render_instructions(),
                self.render_postamble(),
                self.render_charts(),
            ]
            html = "".join(sub_htmls)
            chunk_text = django.utils.safestring.mark_safe(html)
            cache.set(cache_key, chunk_text)
        return chunk_text

    def _render_text_chunk(self, piece_list, chunk_name):
        cache_key = self._make_cache_key(self, chunk_name, [self.pattern.id])
        text_chunk = cache.get(cache_key)
        if text_chunk is None:
            text_chunk = self._render_piece_list(piece_list)
            cache.set(cache_key, text_chunk)
        return text_chunk

    def render_preamble(self):
        """
        Will return the HTML for preamble pieces as a safestring.
        """
        return self._render_text_chunk(self.preamble_pieces, PREAMBLE_CHUNK_NAME)

    def render_instructions(self):
        """
        Will return the HTML for instruction pieces as a safestring.
        """
        return self._render_text_chunk(self.instruction_pieces, INSTRUCTIONS_CHUNK_NAME)

    def render_postamble(self):
        """
        Will return the HTML for postamble pieces as a safestring.
        """
        return self._render_text_chunk(self.postamble_pieces, POSTAMBLE_CHUNK_NAME)

    def render_charts(self):
        return self._render_text_chunk(self.chart_pieces, CHARTS_CHUNK_NAME)


# And now a whole bunch of PatternRendererBase subclasses. Each one selects
# a seperate set of sections to include. General rules of thumb:
#
#  * The Abridged child (PatternRendererPdfAbridged) contains just those
#    sections that we expect most kntters to need on a day-to-day basis
#    and/or those that really should be part of every pattern (About Designer,
#    stitch charts, etc).
#
#  * The 'Full' classes (PatternRendererWebFull, PatternRendererPdfFull) hold
#    everything that even a beginner knitter might need (Pattern notes).
#
#  * PDF versions and HTML versions need slightly different renderers in some
#    parts (WebPreambleRenderer vs  PdfPreambleRenderer, specifically).
#
#  * There is no need for an Abridged Web version.
#
# Thus, we have a single Abridged version for PDF, and two Full versions:
# one for HTML and for PDF. They are very very similar, though, so we define
# a PatternRendererFullBase superclass to hold their common code.
