from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User

UserAdmin.fieldsets += (("Role", {"fields": ("role",)}),)
UserAdmin.list_display += ("role",)

admin.site.register(User, UserAdmin)
