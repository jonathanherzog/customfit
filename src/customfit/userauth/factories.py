import factory
from django.contrib.auth.models import Group, User
from django.db.models import signals

from . import models


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.UserProfile
        django_get_or_create = ("user",)

    # We pass in profile=None to prevent UserFactory from creating another profile
    # (this disables the RelatedFactory)
    user = factory.SubFactory("customfit.userauth.factories.UserFactory", profile=None)
    display_imperial = True


class MetricUserProfileFactory(UserProfileFactory):
    display_imperial = False


@factory.django.mute_signals(signals.pre_save, signals.post_save)
class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        strategy = factory.CREATE_STRATEGY
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: "user_%d" % n)
    password = factory.PostGenerationMethodCall("set_password", "alice")
    email = factory.Sequence(lambda n: "%d@example.com" % n)
    is_active = True
    is_staff = False
    is_superuser = False

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call UserProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(UserProfileFactory, "user")


class MetricUserFactory(UserFactory):

    # We pass in 'user' to link the generated Profile to our just-generated User
    # This will call UserProfileFactory(user=our_new_user), thus skipping the SubFactory.
    profile = factory.RelatedFactory(MetricUserProfileFactory, "user")


class FriendAndFamilyFactory(UserFactory):

    @factory.post_generation
    def add_to_beta_tester_group(self, create, extracted, **kwargs):
        (group, _) = Group.objects.get_or_create(name="Friends And Family")
        self.groups.add(group)


class StaffFactory(UserFactory):
    is_staff = True
    is_superuser = True
