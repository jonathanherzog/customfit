import functools
import itertools
import logging
import mimetypes
import os
import random
from io import BytesIO
from urllib.parse import urlparse

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse, HttpResponseServerError
from django.template import loader
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views.generic.base import RedirectView, TemplateView
from PyPDF2 import PdfReader, PdfWriter
from weasyprint import HTML, default_url_fetcher

from customfit.bodies.models import Body
from customfit.designs.models import Collection, Design
from customfit.swatches.models import Swatch

logger = logging.getLogger(__name__)


def _get_designs(return_count):
    """
    Gets `return_count` random designs to feature on the front page.
    We choose designs in the following way:

    * We first get the currently-promoted.
    * If we need more, we keep adding Collections in reverse chronological order.
    * If we ever get enough to satisfy return_count, choose without replacement
      from the ones we have.
    * If we never get enough, shuffle the ones we eventually get and repeat
      that random sequence over and over again as many times as we need.
    * If we never get *any* designs at all, return None.

    Should be replaced when proper photo management exists.
    """

    curr_design_set = list(Design.currently_promoted.all())
    # Note: Collections is currently ordered by '-creation_date' by default, but
    # no harm in enforcing it again here, where we really need it.
    displayable_collections_by_date = Collection.displayable.order_by(
        "-creation_date"
    ).iterator()

    # Note: the latest collection is automatically included in Designs.currently_promoted, so
    # we pop it off before adding collections by date
    try:
        next(displayable_collections_by_date)
    except StopIteration:
        pass

    while len(curr_design_set) < return_count:
        try:
            next_collection = next(displayable_collections_by_date)
        except StopIteration:
            break
        else:
            new_designs = next_collection.visible_designs
            curr_design_set += list(new_designs)  #

    # At this point, we either have enough designs to draw without replacement
    # or we've run out of Collections and need to shuffle and repeat. First,
    # take care of a corner case

    if len(curr_design_set) == 0:
        return None
    elif len(curr_design_set) >= return_count:
        return random.sample(curr_design_set, return_count)
    else:
        available_designs = curr_design_set
        random.shuffle(available_designs)  # shuffles in place
        repeated_sequence = itertools.cycle(available_designs)
        return_me = list(itertools.islice(repeated_sequence, return_count))
        return return_me


class AboutPageView(TemplateView):
    template_name = "about.html"

    def get_context_data(self, **kwargs):
        context = super(AboutPageView, self).get_context_data(**kwargs)
        context["designs"] = _get_designs(10)
        return context


class HomeView(TemplateView):
    template_name = "knitter_home.html"

    def get_context_data(self, **kwargs):
        context = super(HomeView, self).get_context_data(**kwargs)

        user = self.request.user

        # Design browse
        context["designs"] = _get_designs(10)

        # 'Measure' box
        if Body.objects.filter(user=user).exists():
            context["measure_url"] = reverse("bodies:body_list_view")
        else:
            context["measure_url"] = reverse("bodies:body_create_view")

        # 'Swatch' box
        if Swatch.objects.filter(user=user).exists():
            context["swatch_url"] = reverse("swatches:swatch_list_view")
        else:
            context["swatch_url"] = reverse("swatches:swatch_create_view")

        # 'knit' box
        context["knit_url"] = reverse("patterns:individualpattern_list_view")

        return context


class UniversalHomeView(RedirectView):
    url = reverse_lazy("home_view")
    permanent = False


# Weasyprint's use of url_fetcher involves pickling it, which means that it cannot
# be the method of a bound instance. The easiest way to enforce this is to make it
# a function rather than the instance of an object.


def pdf_url_fetcher(url):
    """
    To style the PDF, we need access to images and fonts. The generated
    HTML will have paths to those assets-- but in the form of URLs to
    our asset server (S3). WeasyPrint allows us to define our own function
    for retrieving those assets, and we're going to take advantage of
    that opportunity.

    1) First, it attempts to find the file locally. That is, it turns
    STATIC_URL and MEDIA_URL into paths into the relevant directory in
    static. This bypasses the collectstatic mechanism.

    2) If the relevant file is not there, however (as would be the
    case for images uploaded through the admin interface, or
    thumbnails created by easy-thumbnails) then this function will
    call _get_data_url to get it from the cache (possibly fetching
    it first).
    """

    # If is a local file? This is trickier than it seems, since we need to determine
    # it just from the URL provided-- and the URL provided can differ significantly
    # between local dev environments and Heroku.
    #
    # Example: the file webfonts/NexaLight.ttf (which we don't use anymore, but we're keeping the example)
    #
    # Local dev environment:
    # * URL passed in: http://127.0.0.1:8000/static/webfonts/NexaLight.ttf
    # * STATIC_URL: /static/
    #
    # Heroku:
    # * URL passed in: https://some_bucket.s3.us-east-1.amazonaws.com/webfonts/NexaLight.ttf
    # * STATIC_URL: https://some_bucket.s3.us-east-1.amazonaws.com/
    #
    # So in this next bit, we try to figure out if the URL falls into either of the above cases and
    # (if so) if the file can be found locally.

    logger.info("pdf_url_fetcher called on url %s", url)

    url_parts = urlparse(url)
    url_netloc = url_parts.netloc
    url_path = url_parts.path
    sUrl = settings.STATIC_URL
    dev_local_file_test = url_netloc.startswith("127.0.0.1") and url_path.startswith(
        sUrl
    )
    heroku_local_file_test = url.startswith(sUrl)

    if dev_local_file_test or heroku_local_file_test:

        # Try to find it locally
        if dev_local_file_test:
            local_rel_path = url_path.replace(sUrl, "")
            logger.debug(
                "Looks like a loopback url. Stripping off STATIC_URL of %s to find %s",
                sUrl,
                local_rel_path,
            )
        else:
            assert heroku_local_file_test
            local_rel_path = url.replace(sUrl, "")
            logger.debug(
                "Looks like a url for our static server. Stripping off STATIC_URL of %s to find %s",
                sUrl,
                local_rel_path,
            )

        # Get the path to the static directory.
        project_root = os.path.dirname(os.path.realpath(__file__))
        project_static_root = os.path.join(project_root, "static")

        # Try to find the file
        local_path = os.path.join(project_static_root, local_rel_path)
        logger.debug(
            "Adding a basepath of %s, and looking locally for %s",
            project_static_root,
            local_path,
        )
        if os.path.isfile(local_path):
            logger.info("%s found locally. Returning it.", local_rel_path)
            f = open(local_path, "rb")
            # For questions about the format/structure of the
            # dict being returned, see WeasyPrint documentation
            # http://weasyprint.readthedocs.io/en/latest/api.html#weasyprint.default_url_fetcher
            return_me = {"file_obj": f}
            (mime_type, encoding) = mimetypes.guess_type(local_path)
            return_me["mime_type"] = mime_type
            return_me["encoding"] = encoding
            return return_me
        else:
            logger.info("%s not found locally.", local_path)

            # No 'return' needed. If the file is not there, then we just proceed as if the URL
            # was not to our static files in the first place

    # URL either not recognized as possibly a static asset, or not found. In either
    # case, look in the cache for it. If not there, fetch it and put it there.

    return_me = cache.get(url)
    if return_me is None:
        logger.info("URL not in cache, fetching.")
        return_me = default_url_fetcher(url)
        # If the default fetcher returns a dict with the 'file_obj' key (and not the
        # 'string' key) the caching will mess it up somehow. So let's convert it to the
        # 'string' key and cache/return that. See the WeasyPrint documentation
        # http://weasyprint.readthedocs.io/en/latest/api.html#weasyprint.default_url_fetcher

        f = return_me.pop("file_obj")
        if f is not None:
            if "string" not in return_me:
                return_me["string"] = f.read()
            f.close()
        logger.debug("Caching the value %s", return_me)
        cache.set(url, return_me)
    else:
        logger.info("URL found in cache.")

    return return_me


class MakePdfMixin(object):
    """
    Mixin class with methods useful for turning HTML into a PDF and returning the PDF.
    Classes need to implement one of the following:

    * get_object_name()
    * make_file_name()

    Subclasses can also override:

    * make_html(context)
    * get_base_url()
    * get_cover_sheet()
    """

    def get_cover_sheet(self):
        return None

    def make_file_name(self):
        object_name = self.get_object_name()
        slug = slugify(object_name)
        filename = slug + ".pdf"
        return filename

    def make_html(self, context):
        """
        Go get the HTML that will go into the xhtml2pdf engine.
        Note: broken out into its own method so that it can
        be used by the make_sample_files management command.
        """
        template_name = self.get_template_names()[0]
        template = loader.get_template(template_name)
        html = template.render(context, self.request)
        return html

    def get_base_url(self):
        base_url = self.request.build_absolute_uri()
        return base_url

    def _make_cache_key(self):
        ids = [self.object.id]
        key = "pdf:%s:%s" % (self.__class__.__name__, ids)
        key = key.replace(" ", "_")  # Memcached doesn't like spaces
        return key

    def flush_cached_pdf(self):
        cache_key = self._make_cache_key()
        cache.delete(cache_key)

    def make_pdf(self):
        """
        Allow direct access to the xhtml2pdf engine using the callback method of
        this class. Note: broken out into its own method so that it can be used
        by the make_sample_files management command.
        """

        cache_key = self._make_cache_key()
        pdf = cache.get(cache_key)
        if pdf is None:

            context = self.get_context_data(object=self.object)
            html = self.make_html(context)

            pdf_buffer = BytesIO()
            HTML(string=html, url_fetcher=pdf_url_fetcher).write_pdf(target=pdf_buffer)
            pdf_buffer.seek(0)


            cache.set(cache_key, pdf_buffer.getvalue())
            pdf = pdf_buffer.getvalue()
            pdf_buffer.close()
        else:
            logger.info("PDF found in cache")

        cover_sheet = self.get_cover_sheet()

        if cover_sheet:
            # use pyPdf to stitch together the cover sheet and the PDF
            try:
                pdf_buffer = BytesIO(pdf)
                result = PdfFileWriter()
                for pdf_file in [cover_sheet, pdf_buffer]:
                    input = PdfFileReader(pdf_file)
                    for page_num in range(input.numPages):
                        result.addPage(input.getPage(page_num))
                combined_pdf_buffer = BytesIO()
                result.write(combined_pdf_buffer)
                pdf = combined_pdf_buffer.getvalue()
                pdf_buffer.close()
                combined_pdf_buffer.close()
            except:
                logger.exception("exception raised while trying to glue on cover sheet")
        else:
            logger.info("No coversheet to stitch on")

        return pdf

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponse(content_type="application/pdf")

        filename = self.make_file_name()
        disposition = 'attachment; filename="%s"' % filename

        response["Content-Disposition"] = disposition

        pdf = self.make_pdf()
        response.write(pdf)
        return response


def server_error(request, *args):
    """
    500 error handler which includes ``request`` in the context and then instantiates the
    template 500.html. Note that we do this so that the end-user sees a nice Sentry id-tag
    to report (provided by middleware and used in the template).
    """
    t = loader.get_template("500.html")
    context = {"request": request}
    return HttpResponseServerError(t.render(context, request))


def force_error(request, *args):
    """
    Allows staff to force an error (by going to /500) in order to observe
    error handling.

    NOTE:
    * If DEBUG = True, you will see a trace, not this page.
    * If DEBUG = False, you will see this page, but it will probably be styled
      incorrectly on localhost since runserver's staticfiles handling does not
      work with DEBUG = False. If you want to confirm that the styling looks
      correct, you will need to view it on a test server, or set up suitable
      static files handling on localhost.
    """
    1 / 0


def infinite_loop_view(request, *args):
    # Intentionally loop forever so that I can test timeout behaviors.
    while True:
        pass


def force_404(request, *args):
    # Intentionally raise 404 so that I can test 404 page
    raise Http404


def force_403(request, *args):
    # Intentionally raise 403 so that I can test 403 page
    raise PermissionDenied


def force_400(request, *args):
    # Intentionally raise 400 so that I can test 400 page
    raise SuspiciousOperation


#
# For testing that celery can write to cache
#


@shared_task
def put_time_in_cache(cache_key):
    import datetime

    cache_me = "The current time is %s" % datetime.datetime.now()
    cache.set(cache_key, cache_me)
    return True


def cache_test_view(request):
    cache_key = "customfit.tests.cache_test_view.cache_key"
    task_result = put_time_in_cache.delay(cache_key)
    return_value = task_result.get(timeout=10)
    assert return_value
    cached_value = cache.get(cache_key)
    assert cached_value is not None
    return HttpResponse(
        "<html><body><p>Success!</p><p>%s.</p></body></html>" % cached_value
    )


class RobotsTxtView(TemplateView):
    template_name = "robots.txt"
    content_type = "text/plain"
