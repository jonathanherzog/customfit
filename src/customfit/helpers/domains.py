from django.conf import settings


def get_current_domain(request=None):
    """
    Get the current domain from the request, if provided, or from ALLOWED_HOSTS otherwise.
    """
    if request is not None:
        host = request.get_host()
    else:
        host = None

    if host:
        return host
    else:
        return settings.ALLOWED_HOSTS[0]
