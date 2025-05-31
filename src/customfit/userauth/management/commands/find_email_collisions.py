import pprint
import sys
from collections import defaultdict

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Find all duplicate email addresses in our database (and who has them)"

    def add_arguments(self, parser):

        parser.add_argument(
            "--just-count",
            action="store_true",
            dest="just_count",
            default=False,
            help="Output count of collisions found instead of list",
        )

        parser.add_argument(
            "--include-staff",
            action="store_true",
            dest="include_staff",
            default=False,
            help="Include 'staff' users in output",
        )

        parser.add_argument(
            "--include-deactivated",
            action="store_true",
            dest="include_deactivated",
            default=False,
            help="Include users without 'is_active' in output",
        )

    def find_collisions(self, include_staff=False, include_deactivated=False):
        usernames_of_email = defaultdict(list)
        user_queryset = User.objects

        if not include_staff:
            user_queryset = user_queryset.filter(is_staff=False)

        if not include_deactivated:
            user_queryset = user_queryset.filter(is_active=True)

        users = user_queryset.all()

        for user in users:
            email = user.email
            username = user.username
            usernames_of_email[email].append(username)

        collisions = []
        for email, usernamelist in list(usernames_of_email.items()):
            if len(usernamelist) > 1:
                collisions.append((email, usernamelist))

        return collisions

    def make_output_message(self, collisions, just_count=False):
        if just_count:
            return_me = str(len(collisions)) + "\n"
        else:
            return_me = ""

            collisions.sort(key=lambda tup: tup[0])
            for email, usernames in collisions:
                return_me += email
                return_me += ": "
                username_str = ", ".join(usernames)
                return_me += username_str
                return_me += "\n"

        return return_me

    def handle(self, *args, **options):
        include_staff = options["include_staff"]
        include_deactivated = options["include_deactivated"]
        just_count = options["just_count"]

        collisions = self.find_collisions(
            include_staff=include_staff, include_deactivated=include_deactivated
        )
        msg = self.make_output_message(collisions, just_count=just_count)

        output_stream = sys.stdout
        output_stream.write(msg)
