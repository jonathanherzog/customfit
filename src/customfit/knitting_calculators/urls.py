from django.contrib.auth.decorators import login_required
from django.urls import re_path

from . import views

app_name = "calculators"
urlpatterns = [
    re_path(r"^$", views.CalculatorListView.as_view(), name="tool_list"),
    re_path(
        r"^shaping$",
        login_required(views.ShapingPlacerCalculatorView.as_view()),
        name="shaping_calculator",
    ),
    re_path(
        r"^buttonhole_spacing$",
        login_required(views.ButtonSpacingCalculator.as_view()),
        name="buttonhole_calculator",
    ),
    re_path(
        r"^armcap$",
        login_required(views.ArmcapShapingCalculatorView.as_view()),
        name="armcap_shaping",
    ),
    re_path(
        r"^pickup",
        login_required(views.PickupCalculatorView.as_view()),
        name="pickup_calculator",
    ),
    re_path(
        r"^gauge",
        login_required(views.GaugeCalculatorView.as_view()),
        name="gauge_calculator",
    ),
]
