import copy

import factory

from customfit.userauth.factories import UserFactory

from .models import Gauge, Swatch


# Note: see get_csv_swatch, below, if you want to access a variety of 'real' swatches
class SwatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Swatch

    user = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: "Swatch %d" % n)
    stitches_length = 1
    stitches_number = 5
    rows_length = 1
    rows_number = 7
    use_repeats = False
    stitches_per_repeat = None
    additional_stitches = None
    yarn_name = "Cascade"
    yarn_maker = factory.Sequence(lambda n: "Yarn maker %d" % n)
    length_per_hank = 220
    weight_per_hank = 100
    full_swatch_height = 7.75
    full_swatch_width = 5.25
    full_swatch_weight = 19
    needle_size = "My favorites!"


class GaugeFactory(factory.Factory):
    # Note: Yes, this will work. FactoryBoy can build any kind of python object, not just
    # Django models, so long as FactoryBoy can introspect the __init__ method
    class Meta:
        model = Gauge

    stitches = 5
    rows = 7
    use_repeats = False
    x_mod = None
    mod_y = None


# Hard-coded swatchs needed for tests. Note: called 'csv' swatches for historical
# reasons. (They used to be stored in CSV format.) We keep them around becuase
# (1) they are used in some regression tests, and (2) it's useful to have a set of
# real swatches around to make sure that our engine can handle them
# To access them, you *can* get a copy of the dict through `csv_swatches`, but we
# suggest that you get them through `get_csv_swatch` (which will use SwatchFactory)
# to give you a real Swatch instance instead of a dict).

_csv_swatches_dict = {
    "Aran St st": {
        "additional_stitches": None,
        "name": "Aran St st",
        "rows_length": 1.0,
        "rows_number": 6.0,
        "stitches_length": 1.0,
        "stitches_number": 4.0,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "Shelter",
    },
    "Bulky St st": {
        "additional_stitches": None,
        "name": "Bulky St st",
        "rows_length": 1.0,
        "rows_number": 5.0,
        "stitches_length": 1.0,
        "stitches_number": 3.0,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "Rhinebeck 12?",
    },
    "Cascade 220 St st": {
        "additional_stitches": None,
        "name": "Cascade 220 St st",
        "rows_length": 1.0,
        "rows_number": 7.0,
        "stitches_length": 1.0,
        "stitches_number": 5.0,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "Cascade",
    },
    "DK St st": {
        "additional_stitches": None,
        "name": "DK St st",
        "rows_length": 1.0,
        "rows_number": 7.5,
        "stitches_length": 1.0,
        "stitches_number": 5.5,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "MCFA Sweet",
    },
    "DK Stitch repeats": {
        "additional_stitches": 1.0,
        "name": "DK Stitch repeats",
        "rows_length": 1.0,
        "rows_number": 7.5,
        "stitches_length": 1.0,
        "stitches_number": 5.75,
        "stitches_per_repeat": 4.0,
        "use_repeats": True,
        "yarn_maker": None,
        "yarn_name": "Who knows",
    },
    "Fingering St st": {
        "additional_stitches": None,
        "name": "Fingering St st",
        "rows_length": 1.0,
        "rows_number": 12.0,
        "stitches_length": 1.0,
        "stitches_number": 8.0,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "Indigodragonfly MCS",
    },
    "Sport St st": {
        "additional_stitches": None,
        "name": "Sport St st",
        "rows_length": 1.0,
        "rows_number": 8.0,
        "stitches_length": 1.0,
        "stitches_number": 6.0,
        "stitches_per_repeat": None,
        "use_repeats": False,
        "yarn_maker": None,
        "yarn_name": "LL Sportmate",
    },
    "Sport stitch repeats": {
        "additional_stitches": 0.0,
        "name": "Sport stitch repeats",
        "rows_length": 1.0,
        "rows_number": 8.0,
        "stitches_length": 1.0,
        "stitches_number": 6.0,
        "stitches_per_repeat": 6.0,
        "use_repeats": True,
        "yarn_maker": None,
        "yarn_name": "Indigodragonfly MCS",
    },
}


def _create_csv_swatches():
    csv_swatches = copy.copy(_csv_swatches_dict)
    return csv_swatches


csv_swatches = _create_csv_swatches()


def get_csv_swatch(csv_swatch_name):
    sw_dict = csv_swatches[csv_swatch_name]
    return SwatchFactory(**sw_dict)
