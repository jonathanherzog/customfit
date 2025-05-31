import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe

from customfit.helpers.user_constants import MAX_BODIES

logger = logging.getLogger(__name__)


def can_make_body(wrapped_view):
    """
    Redirects the user back to home (with a message) if they cannot make
    more Body objects. Expects that the user be logged in.
    """

    def view(request, *args, **kwargs):
        if not request.user.profile.can_create_new_bodies:
            logger.info(
                "User %s was blocked from making a new body, redirected to body-list page",
                request.user.id,
            )
            message = "".join(
                [
                    "Whoops! You can&#39;t have more than %s measurement sets at a time. You may delete "
                    "existing measurement sets as long as you haven't created any patterns for them. "
                    "There&#39;s a link at the bottom of each details page."
                ]
            )
            message = message % MAX_BODIES
            messages.add_message(request, messages.WARNING, mark_safe(message))
            return HttpResponseRedirect(reverse_lazy("bodies:body_list_view"))
        else:
            return wrapped_view(request, *args, **kwargs)

    return view
