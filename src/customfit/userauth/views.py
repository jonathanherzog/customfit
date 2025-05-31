import logging

from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.views.generic import FormView, RedirectView, UpdateView

from .forms import UserManagementForm

logger = logging.getLogger(__name__)


class ManageAccountView(UpdateView):
    """
    Allows the user to update their account settings. This is a base view
    (that gets subclassed) for historical reasons.
    """

    model = User
    success_url = reverse_lazy("userauth:manage_account")
    template_name = "userauth/manage_account.html"
    form_class = UserManagementForm

    def get_context_data(self, **kwargs):
        context = super(ManageAccountView, self).get_context_data(**kwargs)

        context["userform_url"] = reverse_lazy("userauth:manage_account")

        return context

    def get_object(self, queryset=None):
        return self.request.user
