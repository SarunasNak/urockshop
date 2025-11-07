from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import PageView, Event
from . import admin_dashboard
from django.urls import path
from django.shortcuts import redirect
from . import views


# ==========================
# 📊 PAGE VIEW ADMIN
# ==========================
@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ("session_id", "path", "source", "device", "duration", "created_at")
    list_filter = ("source", "device")
    search_fields = ("session_id", "path")
    readonly_fields = (
        "session_id", "path", "ip_hash", "user_agent",
        "referer", "source", "device", "duration", "created_at"
    )

    ordering = ("-created_at",)

    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        filters.append(DurationRangeFilter)
        return filters


class DurationRangeFilter(admin.SimpleListFilter):
    title = "Trukmės diapazonas"
    parameter_name = "duration_range"

    def lookups(self, request, model_admin):
        return [
            ("short", "Iki 15 s"),
            ("medium", "15–60 s"),
            ("long", "Daugiau nei 60 s"),
        ]

    def queryset(self, request, queryset):
        value = self.value()
        if value == "short":
            return queryset.filter(duration__lt=15)
        elif value == "medium":
            return queryset.filter(duration__gte=15, duration__lte=60)
        elif value == "long":
            return queryset.filter(duration__gt=60)
        return queryset


# ==========================
# 🛍️ EVENT ADMIN
# ==========================
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("pageview", "name", "created_at")
    list_filter = ("name",)
    search_fields = ("pageview__path", "name")
    readonly_fields = ("pageview", "name", "data", "created_at")

    # 🔹 2. Custom URL admin'e
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "events_overview/",
                self.admin_site.admin_view(views.events_overview),
                name="analytics_events_overview_admin",
            ),
        ]
        return custom_urls + urls
