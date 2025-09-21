from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget

from .models import BlogSettings, BrandItem, Post

# ── Brand ticker inline ────────────────────────────────────────────────────────
# Jei nori „drag & drop“ rikiavimo, gali naudoti:
# from adminsortable2.admin import SortableInlineAdminMixin
# class BrandItemInline(SortableInlineAdminMixin, admin.TabularInline):
class BrandItemInline(admin.TabularInline):
    model = BrandItem
    extra = 0
    fields = ("order", "title", "url", "is_active")
    ordering = ("order",)

# ── Blog settings ─────────────────────────────────────────────────────────────
@admin.register(BlogSettings)
class BlogSettingsAdmin(admin.ModelAdmin):
    save_on_top = True
    inlines = [BrandItemInline]

    fieldsets = (
        ("Hero", {"fields": ("hero_title",)}),
        ("Brand items (bėganti juosta)", {
            "fields": ("ticker_enabled", "ticker_speed", "ticker_separator"),
            "description": "Čia nustatai juostos elgseną. Patys brandai pildomi žemiau – inline’e."
        }),
        ("Blogo pavadinimas", {"fields": ("must_read_title",)}),
    )

    # leidžiam turėti tik vieną įrašą
    def has_add_permission(self, request):
        return not BlogSettings.objects.exists()

# ── Post + CKEditor5 ──────────────────────────────────────────────────────────
class PostAdminForm(forms.ModelForm):
    body = forms.CharField(required=False, widget=CKEditor5Widget(config_name="default"))
    class Meta:
        model = Post
        fields = "__all__"
    class Media:
        css = {"all": ("ckeditor.css",)}

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    save_on_top = True

    list_display = ("title", "published_at", "is_published", "card_variant", "thumb")
    list_editable = ("is_published",)
    list_filter = ("is_published", "card_variant")
    search_fields = ("title", "body")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"

    fieldsets = (
        (None, {"fields": ("title", "slug", "body", "is_published")}),
        ("Vaizdai", {"fields": ("cover", "card_image")}),
        ("Kortelės išvaizda", {"fields": ("card_variant",)}),
    )

    def thumb(self, obj):
        img = obj.card_image or obj.cover
        if img:
            return format_html('<img src="{}" style="height:48px;border-radius:6px;">', img.url)
        return "—"
    thumb.short_description = "Peržiūra"
