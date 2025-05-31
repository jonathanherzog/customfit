from django.contrib.admin.views.decorators import staff_member_required
from django.urls import re_path

from customfit.designs import views

app_name = "designs"
urlpatterns = [
    re_path(r"^$", views.AllDesignsView.as_view(), name="all_designs"),
    re_path(
        r"^collections/$", views.AllCollectionsView.as_view(), name="all_collections"
    ),
    re_path(
        r"^create_collection/",
        staff_member_required(views.CreateCollectionView.as_view()),
        name="create_collection",
    ),
]
