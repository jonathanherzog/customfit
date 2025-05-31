import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit
from django.contrib import messages
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect
from django.http.request import QueryDict
from django.shortcuts import get_object_or_404
from django.views.generic.edit import UpdateView

from customfit.bodies.models import Body
from customfit.helpers.form_helpers import wrap_with_units
from customfit.helpers.math_helpers import cm_to_inches
from customfit.pattern_spec.models import PatternSpec
from customfit.patterns.models import Redo

from ..constants import (
    REDIRECT_APPROVE,
    REDIRECT_TWEAK,
    REDO_AND_APPROVE,
    REDO_AND_TWEAK,
)
from .garment_registry import model_to_view
from .helpers import _ErrorCheckerMixin, _return_post_design_redirect_url

logger = logging.getLogger(__name__)


def get_view_for_spec_source(view_name, spec_source_class):

    def view(request, *args, **kwargs):

        pk = kwargs["pk"]
        igp = get_object_or_404(spec_source_class, pk=pk)
        inner_view = model_to_view(igp, view_name)
        return inner_view(request, *args, **kwargs)

    return view


#
# Views for adding missing measurements
# -----------------------------------------------------------------------------


class AddMissingMeasurementsViewBase(_ErrorCheckerMixin, UpdateView):

    model = Body
    template_name = "design_wizard/missing_measurements.html"

    # Local functions
    # --------------------------------------------------------------------------

    def _get_missing_body_field_names(self):
        # Note that the missing_body_fields function returns a set of items
        # whose type is *LengthField*, not a list, and not field names.
        # However, we happen to need a list of field names.
        patternspec = self.get_spec_source()
        body = patternspec.body
        igp_class = self.get_igp_class()
        missing_body_fields = igp_class.missing_body_fields(patternspec)
        field_names = [field.name for field in missing_body_fields]
        return field_names

    def get_form_class(self):
        """
        Dynamically construct the form class depending on which fields
        we happen to need. Thanks, modelform_factory!
        """
        fields = self._get_missing_body_field_names()
        form_class = modelform_factory(Body, fields=fields)
        return form_class

    def get_form(self, form_class=None):
        """
        Add layout to the form instance.
        """
        if not form_class:
            form_class = self.get_form_class()
        form = super(AddMissingMeasurementsViewBase, self).get_form(
            form_class=form_class
        )
        form.helper = FormHelper()

        form.helper.layout = Layout()
        for fieldname in list(form.fields.keys()):
            form.helper.layout.extend(Field(fieldname))

        wrap_with_units(form, self.request.user)

        action = self._get_action()

        form.helper.layout.extend(
            [
                Submit(
                    action,
                    "continue with these measurements",
                    css_class="btn-customfit",
                    css_id="continue",
                )
            ]
        )
        return form

    def get_object(self):
        """
        Returns the body to be updated by this view.

        This use of UpdateView is unusual in that the model it is updating is
        the *Body*, but the model associated with the primary key argument in
        the URL is *PatternSpec*.

        We need to have PS in the URL because at this point we need to maintain
        state information about both the Design and the Body that are inputs to
        the patternmaking process; the PS includes all the information from its
        base Design and references the relevant Body as a foreign key. PS is the
        farthest we have been able to get in the patternmaking process; we are
        blocked on creating the IGP because the Body doesn't have the right
        measurements. Therefore this view needs to update Body to proceed, and
        its logic is geared around doing so, even though the object whose state
        we are tracking is PatternSpec.
        """
        patternspec = self.get_spec_source()
        return patternspec.body

    def get_context_data(self, **kwargs):
        context = super(AddMissingMeasurementsViewBase, self).get_context_data(**kwargs)
        context["patternspec"] = self.get_spec_source()
        return context

    def form_valid(self, form):

        logger.info(
            "Adding new measurements for user %s and re-cleaning "
            "patternspec" % self.request.user
        )
        super(AddMissingMeasurementsViewBase, self).form_valid(form)

        # We need to re-clean the PatternSpec because we may not have
        # been able to confirm that the sleeve edging and sleeve length were
        # compatible earlier, if we were missing sleeve lengths.
        patternspec = self.get_spec_source()
        patternspec.full_clean()

        # And now we pick up the pattern-creation workflow where we
        # left it earlier. Woot!
        redirect_url = _return_post_design_redirect_url(self.request, patternspec)
        return HttpResponseRedirect(redirect_url)

    def form_invalid(self, form):
        messages.warning(self.request, "Please correct the errors below.")
        return super(AddMissingMeasurementsViewBase, self).form_invalid(form)

    def post(self, request, *args, **kwargs):
        """
        If the user is operating in metric, we need to convert that before
        perfoming any form validation.
        """
        if not request.user.profile.display_imperial:
            post_data = {}
            for key, value in list(request.POST.items()):
                if key in self._get_missing_body_field_names():
                    try:
                        # The value will be passed as a string, but we need to
                        # work with it as a number.
                        value = float(value)
                        post_data[key] = cm_to_inches(value)
                    except ValueError:
                        # This should not have happened since the front end
                        # should be validating the numeric-ness of the data.
                        # If it did happen, log it, though.
                        logger.exception(
                            "Found invalid data when attempting "
                            "to do metric conversion for user %s and "
                            "patternspec %s",
                            request.user,
                            self.get_spec_source(),
                        )
                        raise
                else:
                    post_data[key] = value

            updated_query = QueryDict(mutable=True)
            updated_query.update(post_data)
            request.POST = updated_query

        return super(AddMissingMeasurementsViewBase, self).post(
            request, *args, **kwargs
        )


class AddMissingMeasurementsViewPatternspecMixin(object):

    def _check_consistency(self, request):
        patternspec = self.get_spec_source()
        self._check_patternspec_consistency_base(request, patternspec)
        super(AddMissingMeasurementsViewPatternspecMixin, self)._check_consistency(
            request
        )

    def get_spec_source(self):
        patternspec = PatternSpec.objects.get(pk=self.kwargs["pk"])
        return patternspec

    def get_design(self):
        spec_source = self.get_spec_source()
        if spec_source.design_origin:
            return spec_source.design_origin
        else:
            return self.get_myo_design()

    # TODO: eventually remove
    def _get_design(self):
        return self.get_design()

    def _get_action(self):
        if "action" in self.kwargs:
            if self.kwargs["action"] == "tweak":
                action = REDIRECT_TWEAK
            else:
                action = REDIRECT_APPROVE
        else:
            action = REDIRECT_APPROVE

        return action


add_missing_measurements_patternspec_view = get_view_for_spec_source(
    "add_missing_measurements_patternspec_view", PatternSpec
)


class AddMissingMeasurementsViewRedoMixin(object):
    def get_spec_source(self):
        redo = Redo.objects.get(pk=self.kwargs["pk"])
        return redo

    def _get_action(self):
        if "action" in self.kwargs:
            if self.kwargs["action"] == "tweak":
                action = REDO_AND_TWEAK
            else:
                action = REDO_AND_APPROVE
        else:
            action = REDO_AND_APPROVE
        return action

    def _check_consistency(self, request):
        redo = self.get_spec_source()
        self._check_redo_consistency_base(request, redo)
        super(AddMissingMeasurementsViewRedoMixin, self)._check_consistency(request)


add_missing_measurements_redo_view = get_view_for_spec_source(
    "add_missing_measurements_redo_view", Redo
)
