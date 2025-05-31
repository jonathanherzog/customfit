# -*- coding: utf-8 -*-


from django.contrib import admin
from django.contrib.auth.models import Group

from .models import IndividualPattern

# For use in 'garment' apps


class ApprovedPatternFilter(admin.SimpleListFilter):
    title = "Approved"
    parameter_name = "approved"

    def lookups(self, request, model_admin):
        return (("yes", "Only approved"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(transactions__approved=True)


class UserGroupFilter(admin.SimpleListFilter):
    title = "Groups"
    parameter_name = "group"

    def lookups(self, request, model_admin):
        lookups_tuple = ()
        for group in Group.objects.all():
            local_tuple = (group.id, group.name)
            lookups_tuple = (local_tuple,) + lookups_tuple
        return lookups_tuple

    def queryset(self, request, queryset):
        if self.value() == None:
            return queryset.all()
        else:
            localgroup = Group.objects.get(id=self.value())
            groupusers = localgroup.user_set.all()
            return queryset.filter(user__in=groupusers)
