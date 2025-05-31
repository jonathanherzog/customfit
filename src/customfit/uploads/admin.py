from django.contrib import admin
from django.urls import reverse

from .models import AwesomePicture, BodyPicture, IndividualPatternPicture, SwatchPicture


class UploadedPictureAdmin(admin.ModelAdmin):
    search_fields = ("object__user__username", "object__name")
    list_display = ("object", "pic_link", "featured")
    raw_id_fields = ("object",)

    def pic_link(self, instance):
        url = instance.picture.url
        response = """<a href="{0}">{0}</a>""".format(url)
        return response

    pic_link.allow_tags = True


class AwesomePictureAdmin(admin.ModelAdmin):
    search_fields = ("user__username",)
    list_display = ("user", "quote", "pic_link", "user_view")
    raw_id_fields = ("user", "pattern", "design")

    def pic_link(self, instance):
        url = instance.picture.url
        response = """<a href="{0}">{0}</a>""".format(url)
        return response

    pic_link.allow_tags = True

    def user_view(self, instance):
        if instance.pattern:
            url = reverse(
                "patterns:individualpattern_detail_view", args=(instance.pattern.id,)
            )
            response = """<a href="{0}">{0}</a>""".format(url)
        else:
            response = ""
        return response

    user_view.short_description = "Pattern"
    user_view.allow_tags = True


admin.site.register(BodyPicture, UploadedPictureAdmin)
admin.site.register(SwatchPicture, UploadedPictureAdmin)
admin.site.register(IndividualPatternPicture, UploadedPictureAdmin)
admin.site.register(AwesomePicture, AwesomePictureAdmin)
