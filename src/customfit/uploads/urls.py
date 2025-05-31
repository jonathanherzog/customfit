from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.decorators.cache import never_cache

from customfit.uploads import views

# Note that we use individual_pattern rather than individualpattern in names
# here so that the replace(' ', '_') in PictureDeleteView will work. (The
# verbose name of IndividualPattern has spaces in it.)
app_name = "uploads"
urlpatterns = [
    # uploading pictures
    re_path(
        r"^body/(?P<pk>\d+)/$",
        login_required(views.BodyPictureUploadView.as_view()),
        name="body_picture_upload",
    ),
    re_path(
        r"^swatch/(?P<pk>\d+)/$",
        login_required(views.SwatchPictureUploadView.as_view()),
        name="swatch_picture_upload",
    ),
    re_path(
        r"^pattern/(?P<pk>\d+)/$",
        login_required(views.IndividualPatternPictureUploadView.as_view()),
        name="individual_pattern_picture_upload",
    ),
    # editing pictures associated with a given object
    # We don't cache these because if we do, uploads and deletions appear to
    # the user not to have actually happened - they're not reflected when
    # they go back to the page after editing their pics, even though they exis
    # in the database.
    re_path(
        r"^gallery/body/(?P<pk>\d+)/$",
        login_required(never_cache(views.BodyPictureEditView.as_view())),
        name="body_picture_edit",
    ),
    re_path(
        r"^gallery/swatch/(?P<pk>\d+)/$",
        login_required(never_cache(views.SwatchPictureEditView.as_view())),
        name="swatch_picture_edit",
    ),
    re_path(
        r"^gallery/pattern/(?P<pk>\d+)/$",
        login_required(never_cache(views.IndividualPatternPictureEditView.as_view())),
        name="individual_pattern_picture_edit",
    ),
    # deleting pictures
    re_path(
        r"^delete/body_picture/(?P<pk>\d+)/$",
        login_required(views.BodyPictureDeleteView.as_view()),
        name="body_picture_delete",
    ),
    re_path(
        r"^delete/swatch_picture/(?P<pk>\d+)/$",
        login_required(views.SwatchPictureDeleteView.as_view()),
        name="swatch_picture_delete",
    ),
    re_path(
        r"^delete/pattern_picture/(?P<pk>\d+)/$",
        login_required(views.IndividualPatternPictureDeleteView.as_view()),
        name="individual_pattern_picture_delete",
    ),
    # featuring pictures
    re_path(
        r"^feature/body_picture/(?P<pk>\d+)/$",
        login_required(views.BodyPictureFeatureView.as_view()),
        name="body_picture_feature",
    ),
    re_path(
        r"^feature/swatch_picture/(?P<pk>\d+)/$",
        login_required(views.SwatchPictureFeatureView.as_view()),
        name="swatch_picture_feature",
    ),
    re_path(
        r"^feature/pattern_picture/(?P<pk>\d+)/$",
        login_required(views.IndividualPatternPictureFeatureView.as_view()),
        name="individual_pattern_picture_feature",
    ),
]
