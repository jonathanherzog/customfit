import sys
from collections import defaultdict

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Find all usernames that would collide should case be ignored"

    def find_collisions(self):
        lowercased_usernames = defaultdict(list)
        for user in User.objects.all():
            username = user.username
            lc_username = username.lower()
            email = user.email
            user_tuple = (username, email)
            lowercased_usernames[lc_username].append(user_tuple)

        collisions = []
        for user_tuple_list in list(lowercased_usernames.values()):
            if len(user_tuple_list) > 1:
                collisions.append(user_tuple_list)
        return collisions

    def make_output_message(self, collisions):
        collisions = self.find_collisions()
        print(collisions)
        if collisions:
            if len(collisions) > 1:
                return_me = "Found %s collisions:\n" % len(collisions)
            else:
                return_me = "Found %s collision:\n" % len(collisions)
            for user_tuple_list in collisions:
                tuple_strings = [
                    "(%s: %s)" % user_tuple for user_tuple in user_tuple_list
                ]
                return_me += ", ".join(tuple_strings)
                return_me += "\n"
            return return_me
        else:
            return "No collisions found"

    def handle(self, *args, **options):
        collisions = self.find_collisions()
        msg = self.make_output_message(collisions)
        if "stdout" in options:
            output_stream = options["stdout"]
        else:
            output_stream = sys.stdout
        output_stream.write(msg)
