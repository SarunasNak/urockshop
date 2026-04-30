# cart/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import TryOnRequest
import json

@admin.register(TryOnRequest)
class TryOnRequestAdmin(admin.ModelAdmin):
    list_display  = ("created_at", "email", "phone",
                     "items_count", "marketing_consent")
    list_filter   = ("marketing_consent", "created_at")
    search_fields = ("email", "phone")

    # readonly – kad admin'e niekas nesugadintų momentinės kopijos
    readonly_fields = ("created_at", "items_pretty_html", "items_raw_json")

    fieldsets = (
        ("Kontaktai", {
            "fields": (
                "name", "email", "phone", "comment",
            )
        }),
        ("Sutikimai", {
            "fields": (
                ("terms_accepted", "marketing_consent"),
            )
        }),
        ("Prekės", {
            "fields": ("items_pretty_html",),
        }),
        ("Raw snapshot (debug)", {
            "classes": ("collapse",),
            "fields": ("items_raw_json",),
        }),
        ("Sistema", {
            "fields": ("created_at",),
        }),
    )

    # kiek prekių
    def items_count(self, obj):
        try:
            return len(obj.items_json or [])
        except Exception:
            return 0
    items_count.short_description = "Prekių kiekis"

    # žalias JSON (tik jei nori matyti raw)
    def items_raw_json(self, obj):
        try:
            return format_html(
                '<pre style="white-space:pre-wrap">{}</pre>',
                json.dumps(obj.items_json, ensure_ascii=False, indent=2)
            )
        except Exception:
            return "–"
    items_raw_json.short_description = "Krepšelio snapshot (raw)"

    # gražus blokas – tiesiog iš modelio metodo
    def items_pretty_html(self, obj):
        return obj.items_pretty_html()
    items_pretty_html.short_description = "Prekės (gražiai)"
