import codecs
import locale
import sys
from collections import Counter

import unicodecsv as csv
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

USERNAME = "Username"
EMAIL = "Email"
USER_PASS = "user_pass"
FIRST_NAME = "first_name"
LAST_NAME = "last_name"


class Command(BaseCommand):
    help = "Dump all users to a CSV (importable into Wordpress)"

    def add_arguments(self, parser):

        parser.add_argument(
            "--include-staff",
            action="store_true",
            dest="include_staff",
            default=False,
            help="Include 'staff' users in output",
        )

        parser.add_argument(
            "--include-inactive",
            action="store_true",
            dest="include_inactive",
            default=False,
            help="Include inactive users' in output",
        )

        parser.add_argument(
            "--exclude-email-duplicates",
            action="store_true",
            dest="exclude_email_dups",
            default=False,
            help="Exclude users that share an email address with another user",
        )

        parser.add_argument(
            "--suppress-header",
            action="store_true",
            dest="suppress_header",
            default=False,
            help="Suppress column-name header in CSV output",
        )

        parser.add_argument(
            "--just-count",
            action="store_true",
            dest="just_count",
            default=False,
            help="Print only number of users that would be returned",
        )

    def _make_row_from_user(self, user):
        d = {
            USERNAME: user.username,
            USER_PASS: user.password,
            FIRST_NAME: user.first_name,
            LAST_NAME: user.last_name,
            EMAIL: user.email,
        }
        return d

    def _get_users(
        self, include_staff=False, include_inactive=False, exclude_email_dups=False
    ):

        user_queryset = User.objects

        # exclude staff
        if not include_staff:
            user_queryset = user_queryset.filter(is_staff=False)

        # exclude inactive
        if not include_inactive:
            user_queryset = user_queryset.filter(is_active=True)

        users = user_queryset.all()

        if exclude_email_dups:
            # search for email duplicates
            addr_counter = Counter()
            for user in users:
                email = user.email
                addr_counter[email] += 1

            return [user for user in users if addr_counter[user.email] == 1]

        else:
            return users

    def handle(self, *args, **options):

        include_staff = options["include_staff"]
        include_inactive = options["include_inactive"]
        supress_header = options["suppress_header"]
        exclude_email_dups = options["exclude_email_dups"]
        just_count = options["just_count"]

        users = self._get_users(
            include_staff=include_staff,
            include_inactive=include_inactive,
            exclude_email_dups=exclude_email_dups,
        )
        if just_count:
            print((str(len(users)) + "\n"))

        else:
            rows = [self._make_row_from_user(user) for user in users]

            # Username and email must be first and second, respectively
            column_names = [USERNAME, EMAIL, FIRST_NAME, LAST_NAME, USER_PASS]
            writer = csv.DictWriter(sys.stdout, column_names)

            if not supress_header:
                writer.writeheader()

            writer.writerows(rows)
