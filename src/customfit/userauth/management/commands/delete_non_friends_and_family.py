import psycopg2
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from customfit.bodies.models import Body
from customfit.cowls.models import (
    CowlGarmentSchematic,
    CowlIndividualGarmentParameters,
    CowlPattern,
    CowlPatternPieces,
    CowlPatternSpec,
    CowlRedo,
)
from customfit.design_wizard.models import Transaction
from customfit.designs.models import Design
from customfit.patterns.models import GradedPattern, IndividualPattern
from customfit.swatches.models import Swatch
from customfit.sweaters.models import SweaterPatternSpec


class Command(BaseCommand):
    help = "Delete all users who are not staff, or in the friend-and-family group"

    def add_arguments(self, parser):

        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            default=False,
            help="Dry run (prints users who will be *kept*)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        to_delete = []
        to_keep = []
        self.stdout.write("Scanning %d users" % User.objects.count())
        num_scanned = 0
        for user in User.objects.all():
            if self.keep_user(user):
                to_keep.append(user)
            else:
                to_delete.append(user)
            num_scanned += 1
            if num_scanned % 1000 == 0:
                self.stdout.write("  %d scanned" % num_scanned)

        num_to_delete = len(to_delete)

        if dry_run:
            self.stdout.write("Will keep the following users:")
            to_keep.sort(key=lambda user: user.username.lower())
            for user in to_keep:
                self.stdout.write("   %s" % user.username)
            self.stdout.write("Will delete %d others" % num_to_delete)
        else:
            self.stdout.write("Deleting %d users:" % num_to_delete)
            self.print_model_counts(0, num_to_delete, None)

            # Clear out orphaned tables
            with connection.cursor() as cursor:
                for table_name in [
                    "change_email_emailchange",
                    "registration_registrationprofile",
                    "cms_usersettings",
                    "announcements_dismissal",
                    "oidc_provider_token",
                    "cms_pageuser",
                ]:
                    try:
                        cursor.execute("DROP TABLE %s CASCADE;" % table_name)
                    except psycopg2.ProgrammingError:
                        pass

            num_done = 0
            start_time = timezone.now()
            for user in to_delete:
                self.delete_user(user)
                num_done += 1
                if num_done % 50 == 0:
                    self.print_model_counts(num_done, num_to_delete, start_time)
            self.print_model_counts(num_done, num_to_delete, start_time)

    def keep_user(self, user):
        return any(
            [
                user.profile.is_friend_or_family,
                user.is_staff,
            ]
        )

    def print_model_counts(self, num_deleted, num_to_delete, start_time):
        if start_time is None or num_deleted <= 0:
            time_left = "unknown"
        else:
            now = timezone.now()
            elapsed = now - start_time
            time_per_user = elapsed / num_deleted
            time_left = time_per_user * (num_to_delete - num_deleted)
        self.stdout.write(
            "%d deleted; %d remaining. Left in DB: %d users, %d individual patterns, %d bodies, %d swatches, %d transactions, %d designs, %d graded patterns. Time left: %s"
            % (
                num_deleted,
                num_to_delete - num_deleted,
                User.objects.count(),
                IndividualPattern.objects.count(),
                Body.objects.count(),
                Swatch.objects.count(),
                Transaction.objects.count(),
                Design.objects.count(),
                GradedPattern.objects.count(),
                time_left,
            )
        )

    def delete_user(self, user):
        try:

            # If we don't do these deletions first, we get errors where Django tries to delete the polymorphic base
            # model before deleting the sub-class model.
            for cps in CowlPatternSpec.objects.filter(user=user):
                cps.delete()

            for sps in SweaterPatternSpec.objects.filter(user=user):
                sps.delete()

            user.delete()

        except Exception as e:
            self.stdout.write(str(e))
