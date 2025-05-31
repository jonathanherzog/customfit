import csv
import sys

from django.core.management.base import BaseCommand

from ...models import Body


class Command(BaseCommand):
    help = "Writes all bodies to stdout in CSV format"

    NON_VERBATIM_COLUMNS = [
        "body_id",
        "body_name",
        "user_id",
        "archived",
    ]
    VERBATIM_COLUMNS = [
        "waist_circ",
        "bust_circ",
        "upper_torso_circ",
        "wrist_circ",
        "forearm_circ",
        "bicep_circ",
        "elbow_circ",
        "armpit_to_short_sleeve",
        "armpit_to_elbow_sleeve",
        "armpit_to_three_quarter_sleeve",
        "armpit_to_full_sleeve",
        "inter_nipple_distance",
        "armpit_to_waist",
        "armhole_depth",
        "armpit_to_high_hip",
        "high_hip_circ",
        "armpit_to_med_hip",
        "med_hip_circ",
        "armpit_to_low_hip",
        "low_hip_circ",
        "armpit_to_tunic",
        "tunic_circ",
        "cross_chest_distance",
        "body_type",
    ]
    ALL_COLUMNS = NON_VERBATIM_COLUMNS + VERBATIM_COLUMNS

    def handle(self, *args, **options):
        writer = csv.DictWriter(sys.stdout, self.ALL_COLUMNS)
        writer.writeheader()
        for body in Body.even_archived.all():
            d = {
                "body_id": body.id,
                "body_name": body.name.encode("utf-8"),
                "user_id": body.user.id,
                "archived": body.archived,
            }
            for col_name in self.VERBATIM_COLUMNS:
                d[col_name] = getattr(body, col_name)

            writer.writerow(d)
