from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe


class UserManagementForm(forms.ModelForm):
    class Meta:
        model = User
        # We need *some* form here to maintain compatibility with _ManageAccountViewBase, but we don't really
        # want the user to change anything
        fields = ()


class CustomMessageAuthenticationForm(AuthenticationForm):
    """
    A custom version of the built-in
    django.contrib.auth.forms.AuthenticationForm that overwrites the standard
    error messages with custom ones.
    """

    invalid_login_message = mark_safe(
        "Your username and password didn't match. Please "
        "try again. Be sure to double-check capitalization! Some mobile "
        "devices auto-capitalize."
    )

    error_messages = {
        "invalid_login": invalid_login_message,
        "inactive": "This account is inactive.",
    }
