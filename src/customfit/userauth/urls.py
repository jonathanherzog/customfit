import django.contrib.auth.views
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.generic.base import TemplateView

from customfit.userauth import views

from .forms import CustomMessageAuthenticationForm

app_name = "userauth"

urlpatterns = [
    # Overwrite default view so that we can use a custom form
    re_path(
        r"^login/$",
        django.contrib.auth.views.LoginView.as_view(),
        {"authentication_form": CustomMessageAuthenticationForm},
        name="login",
    ),
    # Overwrite default so that we can force logout-then-login
    re_path(
        r"^logout/$",
        login_required(django.contrib.auth.views.LogoutView.as_view()),
        name="logout",
    ),
    re_path(
        r"^manage/$",
        login_required(views.ManageAccountView.as_view()),
        name="manage_account",
    ),
    re_path(
        r"^account_inactive/$",
        TemplateView.as_view(template_name="userauth/account_inactive.html"),
        name="account_inactive",
    ),
]
