from django.core.management.base import BaseCommand
from PIL import Image

from customfit.uploads.models import (
    AwesomePicture,
    BodyPicture,
    IndividualPatternPicture,
    SwatchPicture,
)

# PNG is lossless, JPEG is lossy. Let's do PNG.
FMT = "PNG"

# A little bigger than the biggest place we're displaying images.
MAX_WIDTH = 350
MAX_HEIGHT = 450


class Command(BaseCommand):
    help = (
        "Resizes uploaded images to a max of 300x300 (preserving aspect ratio."
        "Safe, though not performant, to run more than once."
    )

    def handle(self, *args, **options):
        # See http://djangosaur.tumblr.com/post/422589280/django-resize-thumbnail-image-pil
        # We skip the part about resize_path in that code because we are
        # overwriting the originals with the resized images - no point in keeping
        # giant images around that we're not going to serve.

        def resize_picture(modelpic):
            picture = modelpic.picture
            picture_file = Image.open(picture.path)
            if picture_file.mode != "RGB":
                picture_file = picture_file.convert("RGB")
            picture_file.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.ANTIALIAS)
            picture_file.save(picture.path, FMT)

        for pic in AwesomePicture.objects.all():
            resize_picture(pic)

        for pic in BodyPicture.objects.all():
            resize_picture(pic)

        for pic in IndividualPatternPicture.objects.all():
            resize_picture(pic)

        for pic in SwatchPicture.objects.all():
            resize_picture(pic)
