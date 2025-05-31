import uuid
from os.path import join

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete

from customfit.bodies.models import Body
from customfit.designs.models import Design
from customfit.patterns.models import IndividualPattern
from customfit.swatches.models import Swatch


def get_image_path(instance, filename):
    # Tempting as it would be to urlencode/escape the following line, we really shouldn't.
    # It will get encoded *again* by django, and then Amazon doesn't understand us any more.
    user_directory = instance.object.user.username

    object_type_subdirectory = instance.object._meta.verbose_name
    # If a user uploads multiple files with the same name, the last uploaded
    # overres the previous and can appear in unintended contexts. Therefore
    # we uniquify the filename.
    unique_filename = "%s%s" % (uuid.uuid4(), filename)
    return join(user_directory, object_type_subdirectory, unique_filename)


# The XPictures (except Awesome) really should inherit from an abstract base
# class, but making sure that migration survives south with data intact will take
# some thought.
class BodyPicture(models.Model):
    object = models.ForeignKey(
        Body, verbose_name="Body", related_name="pictures", on_delete=models.CASCADE
    )
    picture = models.ImageField(upload_to=get_image_path, max_length=150)

    @property
    def featured(self):
        return self.object.featured_pic == self

    class Meta:
        app_label = "uploads"


class IndividualPatternPicture(models.Model):
    object = models.ForeignKey(
        IndividualPattern,
        verbose_name="Pattern",
        related_name="pictures",
        on_delete=models.CASCADE,
    )
    picture = models.ImageField(upload_to=get_image_path, max_length=150)

    @property
    def featured(self):
        return self.object.featured_pic == self

    class Meta:
        app_label = "uploads"


class SwatchPicture(models.Model):
    object = models.ForeignKey(
        Swatch, verbose_name="Swatch", related_name="pictures", on_delete=models.CASCADE
    )
    picture = models.ImageField(upload_to=get_image_path, max_length=150)

    @property
    def featured(self):
        return self.object.featured_pic == self

    class Meta:
        app_label = "uploads"


class AwesomePicture(models.Model):
    quote = models.TextField(blank=False)
    picture = models.ImageField(upload_to="awesome", blank=False, max_length=150)
    user = models.ForeignKey(
        User, related_name="awesome_pictures", blank=False, on_delete=models.CASCADE
    )
    pattern = models.ForeignKey(
        IndividualPattern,
        related_name="awesome_pictures",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    design = models.ForeignKey(
        Design,
        related_name="awesome_pictures",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        app_label = "uploads"


# Django does NOT automatically delete image files when model instances
# referencing theirs are edited or deleted, because this leads to data loss
# problems if you're using transaction rollbacks.
# We're not, and we do incur costs (however small) from S3 storage, so let's
# clean up files when users delete pics.


def picture_post_delete_handler(sender, **kwargs):
    pic_instance = kwargs["instance"]
    storage, name = pic_instance.picture.storage, pic_instance.picture.name
    storage.delete(name)


post_delete.connect(picture_post_delete_handler, sender=BodyPicture)
post_delete.connect(picture_post_delete_handler, sender=IndividualPatternPicture)
post_delete.connect(picture_post_delete_handler, sender=SwatchPicture)
post_delete.connect(picture_post_delete_handler, sender=AwesomePicture)
