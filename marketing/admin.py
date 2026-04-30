from django.contrib import admin
from .models import MarketingPopup, PopupLead
from .models import PrivatePresentationLead
from .models import PrivatePageVisit

@admin.register(MarketingPopup)
class MarketingPopupAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "active",
        "delay_seconds",
        "hide_after_seconds",
        "priority",
    )
    list_filter = ("active",)
    search_fields = ("name",)
    ordering = ("priority",)
    list_editable = ("priority", "active")


@admin.register(PopupLead)
class PopupLeadAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "name",
        "phone",
        "city",
        "source",
        "popup",
        "created_at",
    )
    list_filter = (
        "source",
        "popup",
        "created_at",
    )
    search_fields = (
        "email",
        "name",
        "phone",
        "city",
    )
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)

@admin.register(PrivatePresentationLead)
class PrivatePresentationLeadAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "city", "created_at")
    list_filter = ("city", "created_at")
    search_fields = ("name", "email")

@admin.register(PrivatePageVisit)
class PrivatePageVisitAdmin(admin.ModelAdmin):
    list_display = ("id", "created")
    ordering = ("-created",)



