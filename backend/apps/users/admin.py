from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "email_verified",
        "sso_subject",
        "nickname",
        "is_staff",
    )
    readonly_fields = ("sso_subject",)
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "추가 정보",
            {
                "fields": (
                    "nickname",
                    "home_location",
                    "preferred_themes",
                    "email_verified",
                    "sso_link_allowed",
                    "sso_subject",
                )
            },
        ),
    )
