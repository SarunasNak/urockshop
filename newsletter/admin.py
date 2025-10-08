from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Subscriber

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "is_active", "source", "created_at")
    list_filter = ("is_active", "source", "created_at")
    search_fields = ("email",)
    actions = ["export_csv", "deactivate", "activate"]

    @admin.action(description="Export selected to CSV")
    def export_csv(self, request, queryset):
        resp = HttpResponse(content_type="text/csv")
        resp["Content-Disposition"] = "attachment; filename=subscribers.csv"
        w = csv.writer(resp)
        w.writerow(["email", "is_active", "source", "created_at"])
        for s in queryset:
            w.writerow([s.email, s.is_active, s.source, s.created_at.isoformat()])
        return resp

    @admin.action(description="Mark as inactive")
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Mark as active")
    def activate(self, request, queryset):
        queryset.update(is_active=True)
