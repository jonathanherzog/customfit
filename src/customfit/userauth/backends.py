# Taken from: http://www.shopfiber.com/case-insensitive-username-login-in-django/

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class CaseInsensitiveModelBackend(ModelBackend):
    """
    By default ModelBackend does case _sensitive_ username authentication,
    which isn't what is generally expected.  This backend supports case
    insensitive username authentication.
    """

    def authenticate(self, request, username=None, password=None):
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password):
                return user
            else:
                return None
        except User.DoesNotExist:
            return None
