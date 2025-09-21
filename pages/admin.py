# pages/admin.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.forms import Textarea

# CKEditor (jau instaliavai)
from django_ckeditor_5.widgets import CKEditor5Widget  # ← NAUJAS widgetas

# Importuok VISUS realiai egzistuojančius modelius iš pages.models
from .models import (
    SiteSettings,
    StaticPage,
    HomePage,
    HomeTile,
    PageBanner,
)

# ── SiteSettings ───────────────────────────────────────────────────────────────

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_name", "company_name", "owner_email")
    save_on_top = True
    readonly_fields = ("logo_preview",)

    fieldsets = (
        ("Prekės ženklas", {"fields": ("site_name", "logo", "logo_preview")}),
        ("Įmonės kontaktai (kairė kolona)", {
            "fields": ("company_name", "company_code", "vat_code", "address", "city", "country")
        }),
        ("Savininko kontaktai (centras)", {"fields": ("owner_name", "owner_email", "owner_phone")}),
        ("Social (centrinės apačia)", {"fields": ("facebook", "instagram")}),  # tiktok išimtas – ok
        ("Naujienlaiškis (dešinė)", {"fields": ("newsletter_title", "newsletter_placeholder", "newsletter_button")}),
        ("Teisinės nuorodos (dešinės apačia)", {"fields": ("terms_url", "shipping_url", "returns_url", "privacy_url")}),
        ("Papildomas footer HTML (nebūtina)", {"fields": ("footer_html",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def logo_preview(self, obj):
        if obj and obj.logo:
            return format_html('<img src="{}" style="height:50px;border-radius:6px;">', obj.logo.url)
        return "—"
    logo_preview.short_description = "Peržiūra"


# ── Titulinis (palieku kaip turėjai) ───────────────────────────────────────────

class HomeTileInline(admin.TabularInline):
    model = HomeTile
    extra = 3
    fields = ("order", "title", "alt_text", "image_thumb", "image", "link_url", "variant", "label_pos", "is_active")
    readonly_fields = ("image_thumb",)
    ordering = ("order",)

    def image_thumb(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:50px;border-radius:6px;">', obj.image.url)
        return "—"
    image_thumb.short_description = "Peržiūra"


@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    save_on_top = True
    inlines = [HomeTileInline]
    fieldsets = (
        ("Hero", {"fields": ("hero_title", "hero_subtitle", "hero_note", "hero_cta_text", "hero_cta_url", "hero_image")}),
        ("SEO", {"fields": ("seo_title", "seo_description")}),
    )
    exclude = ("newsletter_title", "newsletter_subtitle", "newsletter_button")

    def has_add_permission(self, request):
        return not HomePage.objects.exists()


# ── „Apie mus“: inline'ai ─────────────────────────────────────────────────────

class PageBannerInline(admin.TabularInline):
    model = PageBanner
    extra = 0
    fields = ("order", "title", "image_thumb", "image", "link_url", "is_active")
    readonly_fields = ("image_thumb",)
    ordering = ("order",)

    def image_thumb(self, obj):
        if getattr(obj, "image", None):
            return format_html('<img src="{}" style="height:50px;border-radius:6px;">', obj.image.url)
        return "—"
    image_thumb.short_description = "Peržiūra"


# ── „Apie mus“: admin su CKEditor ─────────────────────────────────────────────

class StaticPageAdminForm(forms.ModelForm):
    body = forms.CharField(required=False, widget=CKEditor5Widget(config_name="default"))

    class Meta:
        model = StaticPage
        fields = "__all__"

    class Media:
        css = {"all": ("ckeditor.css",)}  # <- ne Meta, o Media


@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    form = StaticPageAdminForm  # CKEditor body'ui

    list_display = ("title", "slug", "is_published")
    list_editable = ("is_published",)
    search_fields = ("title", "slug", "body")
    list_filter = ("is_published",)
    prepopulated_fields = {"slug": ("title",)}
    save_on_top = True

    fieldsets = (
        ("Puslapio info", {"fields": ("title", "slug", "is_published")}),
        ("Baneris / Hero (viršuje)", {"fields": ("hero", "hero_alt")}),
        ("Straipsnis (body)", {"fields": ("body",)}),
        ("DEŠINĖ: Pagrindinis video (viršuje)", {
        "fields": ("sidebar_main_video_url", "sidebar_main_video_poster")
        }),
        ("DEŠINĖ: PAGE BANNERS (po video)", {"fields": ()}),  # inline čia
        ("SEO", {"fields": ("seo_title", "seo_description")}),
    )

    # Inline rodom TIK 'about' įrašui
    def get_inline_instances(self, request, obj=None):
        if obj and obj.slug == "about":
            return [PageBannerInline(self.model, self.admin_site)]
        return []
