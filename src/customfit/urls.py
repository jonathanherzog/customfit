import django.views.defaults

# import admin_honeypot.urls
import impersonate.urls
from django.conf import settings
from django.conf.urls import include
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.generic.base import RedirectView, TemplateView

import customfit.bodies.urls
import customfit.design_wizard.urls
import customfit.designs.urls
import customfit.graded_wizard.urls
import customfit.knitting_calculators.urls
import customfit.patterns.urls
import customfit.stitches.urls
import customfit.swatches.urls
import customfit.sweaters.urls
import customfit.uploads.urls
import customfit.uploads.views
import customfit.userauth.urls

from . import views as toplevel_views

# Uncomment the next two lines to enable the admin:
# yes, even though we're overriding /admin, django-admin-honeypot expects this
admin.autodiscover()


top_level_pages = [
    re_path(
        r"^favicon\.png$",
        RedirectView.as_view(url="/static/img/favicon.png", permanent=True),
    ),
    re_path(r"^about/$", toplevel_views.AboutPageView.as_view(), name="about"),
    # We used to provide /customfit/about/ as the Rav link. Let's make
    # sure it still works.
    re_path(r"^customfit/about/$", RedirectView.as_view(url="/about/", permanent=True)),
    re_path(
        r"^awesome/$", customfit.uploads.views.AwesomeView.as_view(), name="awesome"
    ),
    re_path(
        r"^staff/$",
        staff_member_required(TemplateView.as_view(template_name="staff.html")),
        name="staff",
    ),
    re_path(
        r"^home/$", login_required(toplevel_views.HomeView.as_view()), name="home_view"
    ),
    re_path(
        r"^robots\.txt/?$", toplevel_views.RobotsTxtView.as_view(), name="robots.txt"
    ),
]


# Error-handling views and associated URLs for testing them.
handler500 = toplevel_views.server_error
error_testing_urls = [
    re_path(r"^400/$", staff_member_required(toplevel_views.force_400)),
    re_path(r"^403/$", staff_member_required(toplevel_views.force_403)),
    re_path(r"^404/$", staff_member_required(toplevel_views.force_404)),
    re_path(
        r"^500/$",
        staff_member_required(toplevel_views.force_error),
        name="force_error_page",
    ),
    re_path(r"^loop/$", staff_member_required(toplevel_views.infinite_loop_view)),
    re_path(
        r"^test_cache/$",
        staff_member_required(toplevel_views.cache_test_view),
        name="test_cache_view",
    ),
]


admin_site_re = r"^%s/" % settings.ADMIN_SITE_PATH
admin_doc_re = r"^%s/doc/" % settings.ADMIN_SITE_PATH

urlpatterns = [
    re_path(r"^measurement/", include(customfit.bodies.urls)),
    re_path(r"^swatch/", include(customfit.swatches.urls)),
    re_path(r"^pattern/", include(customfit.patterns.urls)),
    re_path(r"^design/", include(customfit.design_wizard.urls)),
    re_path(r"^graded/", include(customfit.graded_wizard.urls)),
    re_path(r"^uploads/", include(customfit.uploads.urls)),
    re_path(r"^calculators/", include(customfit.knitting_calculators.urls)),
    re_path(r"^stitches/", include(customfit.stitches.urls)),
    re_path(r"^designs/", include(customfit.designs.urls)),
    re_path(r"^sweaters/", include(customfit.sweaters.urls)),
    # Admin URLs. Note: actual admin moved to makewearsudo for security
    # as per Two Scoops of Django
    re_path(admin_site_re, admin.site.urls),
    #    re_path(r'^admin/', include(admin_honeypot.urls)),
    re_path(r"^impersonate/", include(impersonate.urls)),
    # Allow us devs to test our error-page templates
    re_path(r"", include(error_testing_urls)),
    re_path(r"^accounts/", include(customfit.userauth.urls)),
    re_path(r"", include(top_level_pages)),
    # Default URL
    re_path(
        r"^$",
        # Note: decorations should be added to the SortingHat. See declaration.
        toplevel_views.UniversalHomeView.as_view(),
        name="universal_home",
    ),
    # Knitters' Toolbox landing page
    re_path(r"^kt/$", TemplateView.as_view(template_name="kt.html"), name="kt"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        re_path(r"^__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns

if not settings.SERVER:
    urlpatterns += [
        re_path(
            r"^static/(?P<path>.*)$",
            django.views.static.serve,
            {"document_root": settings.STATIC_ROOT},
        ),
        re_path(
            r"^media/(?P<path>.*)$",
            django.views.static.serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
