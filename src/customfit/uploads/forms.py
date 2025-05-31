import logging
from io import BytesIO

from django import forms
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image

from .models import BodyPicture, IndividualPatternPicture, SwatchPicture

logger = logging.getLogger(__name__)

MAX_WIDTH = 350
MAX_HEIGHT = 450
MAX_SIZE = (MAX_WIDTH, MAX_HEIGHT)


class PictureUploadModelForm(forms.ModelForm):
    def __init__(self, pk, *args, **kwargs):
        """
        Extends the usual constructor so as to accept a `pk` argument.
        This keeps us from having to ask the user to re-enter info we already
        know when uploading a file.
        We verify that the object belongs to request.user in
        GenericPictureUploadView.
        Subclasses should define class Meta which specifies fields.
        """
        self.pk = pk
        super(PictureUploadModelForm, self).__init__(*args, **kwargs)
        self.fields["picture"].label = ""  # not needed in context

    def clean_picture(self):
        # Resizes uploaded pictures before writing them to disk so that
        # we're not serving ginormous images forever.
        picture = self.cleaned_data["picture"]
        content_type = picture.content_type

        image = Image.open(picture)
        image.thumbnail(MAX_SIZE)
        imageString = BytesIO()
        image.save(imageString, image.format)

        # InMemoryUploadedFile documentation is horrible and will make you sad.
        # Here, have source code: https://github.com/django/django/blob/stable/1.5.x/django/core/files/uploadedfile.py
        resized_pic = InMemoryUploadedFile(
            file=imageString,
            field_name=None,
            name=picture.name,
            content_type=content_type,
            size=len(imageString.getvalue()),
            charset=None,
        )
        logger.info(
            "%s resized for associated object with pk %s"
            % (self.instance.__class__.__name__, self.pk)
        )
        return resized_pic


class BodyPictureUploadForm(PictureUploadModelForm):
    class Meta:
        fields = ["picture"]
        model = BodyPicture


class SwatchPictureUploadForm(PictureUploadModelForm):
    class Meta:
        fields = ["picture"]
        model = SwatchPicture


class IndividualPatternPictureUploadForm(PictureUploadModelForm):
    class Meta:
        fields = ["picture"]
        model = IndividualPatternPicture
