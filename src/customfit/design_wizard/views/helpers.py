import logging

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.templatetags.static import static
from django.urls import reverse

from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.pattern_spec.models import PatternSpec
from customfit.patterns.models import IndividualPattern
from customfit.pieces.models import PatternPieces
from customfit.schematics.models import ConstructionSchematic

from ..constants import REDIRECT_TWEAK, REDO_AND_APPROVE, REDO_AND_TWEAK
from ..exceptions import OwnershipInconsistency

logger = logging.getLogger(__name__)


#
# Helper functions
# -----------------------------------------------------------------------------


def _make_IPS_from_IGP(user, igp):
    ips = ConstructionSchematic.make_from_garment_parameters(user, igp)
    ips.clean()
    ips.save()
    return ips


def _make_IPP_from_IPS(ips):
    ipp = PatternPieces.make_from_individual_pieced_schematic(ips)
    ipp.full_clean()
    ipp.save()
    return ipp


def _make_pattern_from_IPP(user, ipp):
    pattern = IndividualPattern.make_from_individual_pattern_pieces(user, ipp)
    pattern.clean()
    pattern.save()
    return pattern


def _send_to_tweak_or_approve_patternspec(request, igp):
    # Send the user to the tweak or the approval page, as requested.
    if REDIRECT_TWEAK in request.POST:
        logger.info(
            "Sending user %s to the tweak page for IGP %s", request.user, igp.id
        )
        return reverse("design_wizard:tweak", args=(igp.id,))
    else:
        logger.warning(
            "Can't figure out what action user %s wanted "
            "for IGP %s. Sending to approval page.",
            request.user,
            igp.id,
        )
        return reverse("design_wizard:summary", args=(igp.id,))


def _send_to_tweak_or_approval_redo(request, igp):
    # Send the user to the tweak or the approval page, as requested.
    if REDO_AND_TWEAK in request.POST:
        logger.info(
            "Sending user %s to the redo-tweak page for IGP %s", request.user, igp.id
        )
        return reverse("design_wizard:redo_tweak", args=(igp.id,))

    elif REDO_AND_APPROVE in request.POST:
        logger.info(
            "Sending user %s to the redo-approval page for IGP %s", request.user, igp.id
        )
        return reverse("design_wizard:redo_approve", args=(igp.id,))
    else:
        logger.warning(
            "Can't figure out what action user %s wanted "
            "for IGP %s. Sending to redo-approve page.",
            request.user,
            igp.id,
        )
        return reverse("design_wizard:redo_approve", args=(igp.id,))


def _get_featured_image_url(igp):
    """
    Given an IGP, returns the URL of an image suitable for representing it
    (e.g. on the tweak or summary pages), or None if it can't come up with a
    suitable image.
    """
    if igp.pattern_spec is not None:
        design = igp.pattern_spec.design_origin
    else:
        assert igp.redo is not None
        design = igp.redo.pattern.get_spec_source().design_origin

    # TODO: change this when there are more shape options

    # Set a default image url; change it if we have a better option
    featured_image_url = static("img/CF_Icon_Straight_Sweater-JP-Custom.gif")
    if hasattr(design, "image"):
        try:
            featured_image_url = design.image.url
        except ValueError:
            pass

    return featured_image_url


# TODO: Move this into the sweaters app once we refactor AddMissingMeasurementsView,
# CustomDesignCreateView, CustomDesignUpdateView, and RedoView
def _return_post_design_redirect_url(request, spec_source):
    """
    This function takes a user's design parameters and returns an HttpResponse
    with the appropriate next step in their design process.

    If we don't have enough measurements to make an IGP: solicit them via
    AddMissingMeasurementsView.

    If we do have enough measurements, is the IGP valid?
        If so, continue to tweak or approve, per the user's request.
        If not, go back to the design step (Personalize or Custom) to get
        design changes that do work.
    """
    igp_class = spec_source.get_igp_class()

    if igp_class.missing_body_fields(spec_source):
        # We can't make the IGP without additional data. Let's harvest the data.

        if isinstance(spec_source, PatternSpec):
            logger.info(
                "PatternSpec #{pspec} for user {user} requires more "
                "measurements (missing {missing}); redirecting to missing "
                "measurements view".format(
                    pspec=spec_source.pk,
                    user=request.user,
                    missing=igp_class.missing_body_fields(spec_source),
                )
            )
            if REDIRECT_TWEAK in request.POST:
                action = "tweak"
            else:
                # Default to the approve-right-away view.
                action = "summary"

            return_url = reverse(
                "design_wizard:missing", kwargs={"pk": spec_source.pk, "action": action}
            )
            return return_url

        else:
            logger.info(
                "Redo #{redo} for user {user} requires more "
                "measurements (missing {missing}); redirecting to missing "
                "measurements view".format(
                    redo=spec_source.pk,
                    user=request.user,
                    missing=igp_class.missing_body_fields(spec_source),
                )
            )
            if REDO_AND_TWEAK in request.POST:
                action = "tweak"
            else:
                assert REDO_AND_APPROVE in request.POST
                # Default to the approve-right-away view.
                action = "summary"

            return_url = reverse(
                "design_wizard:missing_redo",
                kwargs={"pk": spec_source.pk, "action": action},
            )

            return return_url

    else:
        if isinstance(spec_source, PatternSpec):

            logger.info(
                "User {user} has appropriate measurements for patternspec "
                "#{pspec}; making IGP".format(user=request.user, pspec=spec_source.pk)
            )
            # We can make the IGP; let's see if it's also valid.

            try:
                igp = igp_class.make_from_patternspec(request.user, spec_source)

                # It is valid! Let them continue forward.
                logger.info(
                    "Successfully made IGP #{igp} for user {user}. "
                    "Continuing to tweak or approval.".format(
                        igp=igp.id, user=request.user
                    )
                )
                return_url = _send_to_tweak_or_approve_patternspec(request, igp)
                return return_url

            except IndividualGarmentParameters.IncompatibleDesignInputs as e:
                # Sadface: we can't make the IGP because the body and design are
                # incompatible. Let them go back to edit their design parameters.
                logger.exception(
                    "Could not make IGP for user {spec.user} with body "
                    "#{spec.body.id} ({spec.body}) and patternspec "
                    "#{spec.id} due to incompatible inputs".format(spec=spec_source)
                )

                for error in e.args:
                    messages.warning(request, error)

                if spec_source.design_origin:
                    logger.info(
                        "Returning {user} to personalize-design "
                        "page for patternspec #{spec}".format(
                            user=request.user, spec=spec_source.pk
                        )
                    )
                    return_url = reverse(
                        "design_wizard:personalize_plus_missing",
                        kwargs={
                            "design_slug": spec_source.design_origin.slug,
                            "pk": spec_source.pk,
                        },
                    )
                else:
                    # It was a custom design.
                    logger.info(
                        "Returning {user} to custom-design "
                        "page for patternspec #{spec}".format(
                            user=request.user, spec=spec_source.pk
                        )
                    )
                    return_url = reverse(
                        "design_wizard:custom_design_plus_missing_garment",
                        kwargs={
                            "pk": spec_source.pk,
                            "garment": spec_source.get_garment(),
                        },
                    )

                return return_url
        else:

            logger.info(
                "User {user} has appropriate measurements for redo "
                "#{pspec}; making IGP".format(user=request.user, pspec=spec_source.pk)
            )
            # We can make the IGP; let's see if it's also valid.

            try:
                igp = igp_class.make_from_redo(request.user, spec_source)

                # It is valid! Let them continue forward.
                logger.info(
                    "Successfully made IGP #{igp} for user {user}. "
                    "Continuing to redo-tweak or redo-approval.".format(
                        igp=igp.id, user=request.user
                    )
                )
                return_url = _send_to_tweak_or_approval_redo(request, igp)
                return return_url

            except IndividualGarmentParameters.IncompatibleDesignInputs as e:
                # Sadface: we can't make the IGP because the body and design are
                # incompatible. Let them go back to edit their design parameters.
                logger.exception(
                    "Could not make IGP for user {spec.user} with body "
                    "#{spec.body.id} ({spec.body}) and redo "
                    "#{spec.id} due to incompatible inputs".format(spec=spec_source)
                )

                for error in e.args:
                    messages.warning(request, error)

                logger.info(
                    "Returning {user} to redo page for redo #{spec}".format(
                        user=request.user, spec=spec_source.pk
                    )
                )
                return_url = reverse(
                    "design_wizard:redo_plus_missing", kwargs={"pk": spec_source.pk}
                )

                return return_url


class _ErrorCheckerMixin(object):
    """
    Provides methods to check for common errors (e.g., mismatches between the
    current user / current knitter on the one hand and object-owners and
    customer-linkages on the other).

    This is meant to be used as mix-in by other design-wizard view classes.

    Subclasses can override:
    * _check_consistency(self, request)

    This class will call _check_consistency() in dispatch().

    """

    def _check_consistency(self, request):
        pass

    def dispatch(self, request, *args, **kwargs):
        self._check_consistency(request)
        return super(_ErrorCheckerMixin, self).dispatch(request, *args, **kwargs)

    # TODO: MAke this handle patternspecs without bodies
    def _check_patternspec_consistency_base(self, request, patternspec):
        # Before we work with a patternspec, we want to check the following:
        #
        # That the patternspec is owned by the same user as this request (often redundant with dispatch(), but why not)
        # That the patternspec has a body
        # That the patternspec's body has the same owner as this request
        # That the patternspec has a swatch
        # That the patternspec's swatch has the same owner as this request

        # That the patternspec is owned by the same user as this request
        if request.user != patternspec.user:
            msg = "User {0} attempting to work with PatternSpec {1}".format(
                request.user.id, patternspec.id
            )
            logger.error(msg)
            raise PermissionDenied(msg)

        try:
            body = patternspec.body
        except AttributeError:
            # Guess there's no body defined for this model.
            pass
        else:
            if patternspec.body is None:
                msg = "PatternSpec {0} does not have a body".format(patternspec.id)
                logger.error(msg)
                raise ObjectDoesNotExist(msg)
            body = patternspec.body

            # That the patternspec's body has the same owner as this request
            if body.user != request.user:
                msg = "User {0} attempting to use body {1}".format(
                    request.user.id, body.id
                )
                logger.error(msg)
                raise OwnershipInconsistency(msg)

        # That the patternspec has a swatch
        if patternspec.swatch is None:
            msg = "PatternSpec {0} does not have a swatch".format(patternspec.id)
            logger.error(msg)
            raise ObjectDoesNotExist(msg)
        swatch = patternspec.swatch

        # That the patternspec's swatch has the same owner as this request
        if swatch.user != request.user:
            msg = "User {0} attempting to use swatch {1}".format(
                request.user.id, swatch.id
            )
            logger.error(msg)
            raise OwnershipInconsistency(msg)

    # TODO: MAke this handle IGPs/spec-sources without bodies
    def _check_igp_consistency_base(self, request, igp):
        # Before we work with an IGP, we need to check the following:
        #
        # That the IGP is owned by the same user as this request (often redundant with dispatch(), but why not)
        # If the IGP has a body, then the IGP's body has the same owner as this request
        # That the IGP has a swatch
        # That the IGP's swatch has the same owner as this request
        # That the IGP has a PatternSpec or Redo
        # That the PatternSpec or Redo is owned by the same user as this request
        # That the IGP is not already part of an approved pattern
        #
        # Any violation should raise an exception

        # That the IGP is owned by the same user as this request
        if request.user != igp.user:
            msg = "User {0} attempting to work with IGP {1}".format(
                request.user.id, igp.id
            )
            logger.error(msg)
            raise PermissionDenied(msg)

        # That the IGP's body has the same owner as this request
        # Note-- not all IGPs have a body, but enough do/will that it makes sense to try to test it here
        # (and gracefully handle it when they don't)
        try:
            body = igp.body
        except AttributeError:
            # No body, so nothing to do here
            pass
        else:
            if body.user != request.user:
                msg = "User {0} attempting to use body {1}".format(
                    request.user.id, body.id
                )
                logger.error(msg)
                raise OwnershipInconsistency(msg)

        # That the IGP's swatch has the same owner as this request
        swatch = igp.swatch
        if swatch.user != request.user:
            msg = "User {0} attempting to use swatch {1}".format(
                request.user.id, swatch.id
            )
            logger.error(msg)
            raise OwnershipInconsistency(msg)

        # That the PatternSpec or Redo is owned by the same user as this request
        if igp.pattern_spec is not None:
            if igp.pattern_spec.user != request.user:
                msg = "User {0} attempting to use patternspec {1}".format(
                    request.user.id, igp.pattern_spec.id
                )
                logger.error(msg)
                raise OwnershipInconsistency(msg)
        else:
            assert igp.redo is not None
            # Redo doesn't have an owner, but it has a pattern
            if igp.redo.pattern.user != request.user:
                msg = "User {0} attempting to use Redo {1}".format(
                    request.user.id, igp.redo.id
                )
                logger.error(msg)
                raise OwnershipInconsistency(msg)

        # That the IGP is not already part of an approved pattern
        if IndividualPattern.approved_patterns.filter(
            pieces__schematic__individual_garment_parameters=igp
        ).exists():
            raise PermissionDenied()

        # TODO: DO we recurse down and check the PatternSpec for consistency, too?

    def _check_pattern_consistency_base(self, request, pattern):
        # Before we work with a pattern (e.g., to redo) we should check that
        # * The pattern is approved,
        # * The pattern belongs to the user in question
        if request.user != pattern.user:
            msg = "User {0} attempting to work with IndivdiualPattern {1}".format(
                request.user.id, pattern.id
            )
            logger.error(msg)
            raise PermissionDenied(msg)

        if not pattern.approved:
            msg = "User {0} attempting to work with unapproved IndivdiualPattern {1}".format(
                request.user.id, pattern.id
            )
            logger.error(msg)
            raise PermissionDenied(msg)

    def _check_redo_consistency_base(self, request, redo):
        self._check_patternspec_consistency_base(request, redo)
        self._check_pattern_consistency_base(request, redo.pattern)
