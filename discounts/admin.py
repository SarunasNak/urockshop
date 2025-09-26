# discounts/admin.py
from django.contrib import admin
from .models import Coupon, CouponRedemption

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "type", "value", "is_active", "starts_at", "ends_at")
    list_filter = ("is_active", "type")
    search_fields = ("code",)
    filter_horizontal = ("products", "categories")
    fieldsets = (
        (None, {
            "fields": ("code", "type", "value", "is_active", "stackable")
        }),
        ("Taikymo ribos", {
            "fields": ("applies_to_all", "products", "categories")
        }),
        ("Galiojimas", {
            "fields": ("starts_at", "ends_at", "min_order_total",
                       "usage_limit_total", "usage_limit_per_user")
        }),
        ("Asmeniniai ribojimai", {
            "fields": ("assigned_user", "allowed_emails")
        }),
    )

@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("coupon", "email", "user", "order_id", "created_at")
    search_fields = ("coupon__code", "email", "order_id")
    autocomplete_fields = ("coupon", "user")
    ordering = ("-created_at",)

