from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum
from .models import Category, Product, Variant, ProductImage
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)
    fields = ("preview", "image", "alt", "sort")

class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    min_num = 1
    max_num = 1
    can_delete = False
    fields = ("sku", "price", "stock", "color", "size", "compare_at_price")

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "category", "price_col", "stock_col", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VariantInline, ProductImageInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category").prefetch_related("images", "variants")

    @admin.display(description="Preview")
    def thumbnail(self, obj):
        img = obj.images.order_by("sort", "id").first()
        if img and img.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', img.image.url)
        return "—"

    @admin.display(description="Price", ordering="variants__price")
    def price_col(self, obj):
        v = obj.variants.order_by("price").first()
        return v.price if v else None

    @admin.display(description="Stock", ordering="variants__stock")
    def stock_col(self, obj):
        return obj.variants.aggregate(s=Sum("stock"))["s"] or 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",        # 👈 miniatiūra
        "sku",
        "product",
        "color",
        "size",
        "price",
        "compare_at_price",
        "discount_pct", # 👈 rodomas % nuolaidos dydis
        "stock",
        "is_active",
    )
    list_editable = ("price", "compare_at_price", "stock", "is_active")
    list_filter = ("is_active", "product__category", "color", "size")
    search_fields = ("sku", "product__name")
    list_select_related = ("product",)

    actions = ["discount_10", "discount_20", "clear_discount"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # mažiau užklausų ir greitesnės miniatiūros
        return qs.select_related("product").prefetch_related("product__images")

    @admin.display(description="Preview")
    def thumb(self, obj):
        img = obj.product.images.order_by("sort", "id").first()
        if img and img.image:
            return format_html('<img src="{}" style="height:48px;border-radius:6px;" />', img.image.url)
        return "—"

    @admin.display(description="Discount %")
    def discount_pct(self, obj):
        """
        Rodo nuolaidos dydį procentais, jei compare_at_price > price.
        Pvz.: compare 100.00, price 80.00 → 20 (%)
        """
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            pct = (obj.compare_at_price - obj.price) / obj.compare_at_price * Decimal("100")
            return f"{pct.quantize(Decimal('1'))}%"
        return "—"

    # ---------- Admin actions ----------
    def _apply_percent(self, queryset, percent: int):
        """
        Sumažina kainą procentais. Jei compare_at_price tuščias, užpildo jį sena kaina.
        """
        factor = (Decimal("100") - Decimal(percent)) / Decimal("100")
        for v in queryset:
            if not v.compare_at_price or v.compare_at_price < v.price:
                v.compare_at_price = v.price  # prisimename „seną“ kainą
            v.price = (v.price * factor).quantize(Decimal("0.01"))
            v.save(update_fields=["price", "compare_at_price"])

    @admin.action(description="Taikyti −10%%")
    def discount_10(self, request, queryset):
        self._apply_percent(queryset, 10)
        self.message_user(request, "Pritaikyta −10% pasirinktiems variantams.")

    @admin.action(description="Taikyti −20%%")
    def discount_20(self, request, queryset):
        self._apply_percent(queryset, 20)
        self.message_user(request, "Pritaikyta −20% pasirinktiems variantams.")

    @admin.action(description="Nuimti nuolaidą (atstatyti kainą)")
    def clear_discount(self, request, queryset):
        """
        Grąžina price = compare_at_price, jei compare_at_price nustatytas.
        """
        for v in queryset:
            if v.compare_at_price and v.compare_at_price > 0:
                v.price = v.compare_at_price
                v.save(update_fields=["price"])
        self.message_user(request, "Nuolaidos nuimtos (kainos atstatytos).")