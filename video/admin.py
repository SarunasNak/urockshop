from django.contrib import admin
from django.utils.html import format_html
from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "cover_preview")
    list_filter = ("category",)
    search_fields = ("title", "cloudflare_id")

    fieldsets = (
        ("Pagrindinė informacija", {
            "fields": ("title", "title_url", "category", "label")
        }),
        ("Cloudflare video", {
            "fields": ("cloudflare_id",)
        }),
        ("Viršeliai", {
            "fields": ("cover_desktop", "cover_mobile")
        }),
    )

    def cover_preview(self, obj):
        if obj.cover_desktop:
            try:
                return format_html(
                    '<img src="{}" width="80" style="border-radius:4px;" />',
                    obj.cover_desktop.url
                )
            except:
                return "—"
        return "—"

    cover_preview.short_description = "Viršelis"
