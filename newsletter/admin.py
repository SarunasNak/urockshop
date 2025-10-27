from django.contrib import admin
from django.http import HttpResponse
import csv

from .models import Subscriber


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "is_active",
        "source",
        "phone",
        "height_cm",
        "weight_kg",
        "created_at",
    )
    list_filter = ("is_active", "source", "created_at")
    search_fields = ("email", "phone")
    readonly_fields = ("created_at",)
    actions = ["export_csv", "deactivate", "activate"]
    list_per_page = 50

    @admin.action(description="Export selected to CSV")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = "attachment; filename=subscribers.csv"
        w = csv.writer(resp)
        w.writerow([
            "email",
            "is_active",
            "source",
            "phone",
            "height_cm",
            "weight_kg",
            "created_at",
        ])
        for s in queryset:
            w.writerow([
                s.email,
                "1" if s.is_active else "0",
                s.source or "",
                s.phone or "",
                s.height_cm if s.height_cm is not None else "",
                s.weight_kg if s.weight_kg is not None else "",
                s.created_at.isoformat(),
            ])
        return resp

    @admin.action(description="Mark as inactive")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Mark as active")
    def activate(self, request, queryset):
        queryset.update(is_active=True)
