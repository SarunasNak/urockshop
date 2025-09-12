from django.contrib import admin
from .models import SiteSettings, StaticPage


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_name", "email", "phone")

    # leidžiam turėti tik vieną įrašą
    def has_add_permission(self, request):
        if SiteSettings.objects.exists():
            return False
        return super().has_add_permission(request)


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "is_published")
    list_editable = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
