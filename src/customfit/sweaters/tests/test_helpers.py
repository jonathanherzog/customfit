import itertools

from django.contrib.staticfiles import finders
from django.test import TestCase

from ..helpers import sweater_design_choices as SDC
from ..helpers.schematic_images import (
    get_back_schematic_url,
    get_front_schematic_url,
    get_sleeve_schematic_url,
)
from ..helpers.secret_sauce import get_eases


class SchematicImagesTests(TestCase):

    def test_get_back_schematic_image_files(self):
        for silhouette in [
            SDC.SILHOUETTE_HOURGLASS,
            SDC.SILHOUETTE_TAPERED,
            SDC.SILHOUETTE_ALINE,
            SDC.SILHOUETTE_STRAIGHT,
        ]:
            for construction, _ in SDC.CONSTRUCTION_CHOICES:
                url = get_back_schematic_url(silhouette, construction)
                file = finders.find(url)
                self.assertIsNotNone(file)

    def test_get_sleeve_schematic_image_files(self):
        for length, _ in SDC.SLEEVE_LENGTH_CHOICES:
            for construction, _ in SDC.CONSTRUCTION_CHOICES:
                url = get_sleeve_schematic_url(length, construction)
                file = finders.find(url)
                self.assertIsNotNone(file)

    def test_get_front_schematic_image_files(self):
        silhouettes = [
            SDC.SILHOUETTE_HOURGLASS,
            SDC.SILHOUETTE_TAPERED,
            SDC.SILHOUETTE_ALINE,
            SDC.SILHOUETTE_STRAIGHT,
        ]
        for sil, (constr, _), (neck, _), cardi, empty in itertools.product(
            silhouettes,
            SDC.CONSTRUCTION_CHOICES,
            SDC.NECKLINE_STYLE_CHOICES,
            [True, False],
            [True, False],
        ):
            if neck == SDC.NECK_TURKS_AND_CAICOS and cardi:
                continue
            url = get_front_schematic_url(
                sil, neck, constr, cardigan=cardi, empty=empty
            )
            file = finders.find(url)
            self.assertIsNotNone(file, url)


class SecretSauceTests(TestCase):

    def test_hourglass_eases(self):
        for fit, _ in SDC.GARMENT_FIT_CHOICES_HOURGLASS:
            for construction, _ in SDC.SUPPORTED_CONSTRUCTIONS:
                for silhouette in [
                    SDC.SILHOUETTE_HOURGLASS,
                    SDC.SILHOUETTE_HALF_HOURGLASS,
                ]:

                    # No case
                    eases = get_eases(fit, silhouette, construction, case=None)
                    for k in [
                        "armhole_depth",
                        SDC.SLEEVE_SHORT,
                        SDC.SLEEVE_ELBOW,
                        SDC.SLEEVE_THREEQUARTER,
                        SDC.SLEEVE_FULL,
                    ]:
                        self.assertIn(k, eases)

                    if construction == SDC.CONSTRUCTION_SET_IN_SLEEVE:
                        for k in ["bicep", "cross_chest"]:
                            self.assertIn(k, eases)

                        # cases
                    for case_index in range(10):
                        case = "case" + str(case_index)
                        eases = get_eases(fit, silhouette, construction, case)
                        for k in [
                            "bust",
                            "waist",
                            SDC.HIGH_HIP_LENGTH,
                            SDC.MED_HIP_LENGTH,
                            SDC.LOW_HIP_LENGTH,
                            SDC.TUNIC_LENGTH,
                            "upper_torso",
                        ]:
                            self.assertIn(k, eases)

    def test_non_hourglass_eases(self):
        for fit, _ in SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS:
            for construction, _ in SDC.SUPPORTED_CONSTRUCTIONS:
                for silhouette in [
                    SDC.SILHOUETTE_STRAIGHT,
                    SDC.SILHOUETTE_TAPERED,
                    SDC.SILHOUETTE_ALINE,
                ]:

                    eases = get_eases(fit, silhouette, construction, case=None)
                    for k in [
                        "upper_torso",
                        "bust",
                        "armhole_depth",
                        SDC.SLEEVE_SHORT,
                        SDC.SLEEVE_ELBOW,
                        SDC.SLEEVE_THREEQUARTER,
                        SDC.SLEEVE_FULL,
                        "cast_on",
                        "waist",
                    ]:
                        self.assertIn(k, eases)

                    if construction == SDC.CONSTRUCTION_SET_IN_SLEEVE:
                        for k in ["bicep", "cross_chest"]:
                            self.assertIn(k, eases)
