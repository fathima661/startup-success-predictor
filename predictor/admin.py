from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import EvaluationRecord, CustomUser


# ================= EvaluationRecord Admin =================
@admin.register(EvaluationRecord)
class EvaluationRecordAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "country",
        "probability",
        "rating",
        "created_at"
    )
    list_filter = ("category", "country", "rating")
    search_fields = ("category", "country")


# ================= CustomUser Admin =================
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):

    model = CustomUser

    list_display = ("email", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Permissions", {
            "fields": (
                "is_staff",
                "is_active",
                "is_superuser",
                "groups",
                "user_permissions"
            )
        }),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active"),
        }),
    )

    search_fields = ("email",)
    ordering = ("email",)