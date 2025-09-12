from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_sku", "qty", "price", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "status", "total", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("email", "id", "first_name", "last_name")
    inlines = [OrderItemInline]
    readonly_fields = ("created_at", "updated_at", "total")
