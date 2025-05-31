from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User

from .models import UserProfile


# From the Django docs: to add the UserProfile fields to the User admin
# Define an inline admin descriptor for UserProfile model
# which acts a bit like a singleton
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "profile"
    fields = ("user", "display_imperial")
    raw_id_fields = ("user",)


# Define and register new User admin
class CustomfitUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ("username", "first_name", "last_name", "id")

    def mass_activate(self, request, queryset):
        """
        The usual django action handling uses queryset.update, but it
        doesn't emit save signals, which are needed to trigger activation
        emails.  If we do queryset.update() now and save() later, we won't
        have the mismatch between instance and in-db status that we need
        to trigger those emails.
        """
        for user in queryset:
            user.is_active = True
            user.save()

    mass_activate.short_description = "Mark selected users as active"

    actions = [mass_activate]


admin.site.unregister(User)
admin.site.register(User, CustomfitUserAdmin)


class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ("user__username",)
    list_display = ("user", "display_imperial")
    list_filter = ("display_imperial",)
    raw_id_fields = ("user",)


admin.site.register(UserProfile, UserProfileAdmin)
