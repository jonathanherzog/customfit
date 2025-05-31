"""
Created on Jun 23, 2012
"""

import logging

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

from customfit.helpers.user_constants import MAX_BODIES
from customfit.patterns.models import IndividualPattern

logger = logging.getLogger(__name__)


class UserProfile(models.Model):

    user = models.OneToOneField(User, related_name="profile", on_delete=models.CASCADE)

    display_imperial = models.BooleanField(
        help_text="If checked, measurements are in "
        "inches/yards/oz. Otherwise, in "
        "centimeters/meters/grams.",
        default=True,
    )

    @property
    def can_create_new_bodies(self):
        if self.user.is_staff or self.user.bodies.count() < MAX_BODIES:
            return True
        return False

    @property
    def is_friend_or_family(self):
        return self.user.groups.filter(name="Friends And Family").exists()

    # Why override save()? When we add a user in the admin site, Django
    # creates a User, which means that a post-save signal is sent to
    # create_user_profile, below, which makes a UserProfile object and
    # saves it. But then the Admin site takes the inline UserProfile *form*
    # and tries to save it-- causing an IntegrityError because UserProfile
    # is supposed to be OneToOne with User and the second save violates that.
    # To fix this, we use the solution suggested in:
    #
    # http://stackoverflow.com/questions/6117373/django-userprofile-m2m-field-in-admin-error/6117457#6117457
    #
    # and override save()

    @property
    def has_archived_patterns(self):
        return IndividualPattern.approved_patterns.filter(
            user=self.user, archived=True
        ).exists()

    def save(self, *args, **kwargs):
        if not self.pk:
            try:
                p = UserProfile.objects.get(user=self.user)
                self.pk = p.pk
            except UserProfile.DoesNotExist:
                pass

        super(UserProfile, self).save(*args, **kwargs)

    class Meta:
        app_label = "userauth"


def create_user_profile(sender, **kwargs):
    """
    Creates a new profile for a user. Meant to be handle a signal when
    a User model is created.
    """
    created = kwargs["created"]
    instance = kwargs["instance"]
    if created and not kwargs.get("raw", False):
        UserProfile.objects.get_or_create(user=instance)


# register the previous function to receive post-save signals from User models
post_save.connect(create_user_profile, sender=User)
