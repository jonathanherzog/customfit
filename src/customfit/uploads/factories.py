import os.path

from django.core.files.uploadedfile import SimpleUploadedFile

from .models import BodyPicture, IndividualPatternPicture, SwatchPicture

path = os.path.dirname(os.path.abspath(__file__))


def create_picture(second_pic):
    current_directory = os.path.dirname(os.path.realpath(__file__))
    if second_pic:
        test_file_path = current_directory + "/test_assets/boy-elf-small.png"
    else:
        test_file_path = current_directory + "/test_assets/cutout.png"
    imagefile = SimpleUploadedFile(
        "cutout.png", open(test_file_path, "rb").read(), content_type="image/png"
    )
    return imagefile


def create_body_picture(body, second_pic=False):
    bp = BodyPicture()
    bp.object = body
    bp.picture = create_picture(second_pic)
    bp.save()
    return bp


def create_swatch_picture(swatch, second_pic=False):
    sp = SwatchPicture()
    sp.object = swatch
    sp.picture = create_picture(second_pic)
    sp.save()
    return sp


def create_individual_pattern_picture(pattern, second_pic=False):
    ipp = IndividualPatternPicture()
    ipp.object = pattern
    ipp.picture = create_picture(second_pic)
    ipp.save()
    return ipp
