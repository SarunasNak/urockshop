# catalog/admin.py
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.urls import reverse
from django.utils.http import urlencode
from django.db.models import Sum, Max
from django.utils.html import format_html
from decimal import Decimal
from adminsortable2.admin import SortableAdminMixin

from .models import Category, Product, ProductImage, Variant, Size

# ---------- Multi-upload widget + field ----------
class MultiFileInput(forms.ClearableFileInput):
    """ClearableFileInput, kuris leidžia pasirinkti kelis failus."""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """FileField, priimantis 0..N failų sąrašą iš MultiFileInput."""
    def to_python(self, data):
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return list(data)
        return [data]

    def validate(self, data):
        if self.required and not data:
            raise forms.ValidationError(self.error_messages["required"], code="required")
        for f in data:
            super().validate(f)

    def run_validators(self, data):
        for f in data:
            super().run_validators(f)

# ---------- Drag&drop palaikymas (adminsortable2) su fallback ----------
try:
    from adminsortable2.admin import SortableInlineAdminMixin, SortableAdminBase

    class _BaseImageInline(SortableInlineAdminMixin, admin.TabularInline):
        pass

    class _BaseProductAdmin(SortableAdminBase, admin.ModelAdmin):
        """Reikia, kai inline paveldi SortableInlineAdminMixin."""
        pass

    _HAS_SORTABLE = True
except Exception:
    class _BaseImageInline(admin.TabularInline):
        pass

    class _BaseProductAdmin(admin.ModelAdmin):
        pass

    _HAS_SORTABLE = False


# ================= Inlines =================
class ProductImageInline(_BaseImageInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)
    fields = ("preview", "image", "alt", "sort")
    if _HAS_SORTABLE:
        sortable_field_name = "sort"
    verbose_name = "Drabužio kortelės nuotrauka"
    verbose_name_plural = "Drabužio kortelės nuotraukos"


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    min_num = 0
    max_num = 1
    can_delete = False
    fields = ("sku", "stock", "is_active")     # rodome tik tai, ko reikia taisyti
    readonly_fields = ("sku",)                 # SKU generuojamas automatiškai
    verbose_name = "Drabužio kiekis"
    verbose_name_plural = "Drabužio kiekiai"

# ============= Product form (4 SKU + masinis įkėlimas) =============
class ProductAdminForm(forms.ModelForm):
    # 4 SKU laukai „panašioms“
    related_sku_1 = forms.CharField(label="Susijusi prekė #1 (SKU)", required=False)
    related_sku_2 = forms.CharField(label="Susijusi prekė #2 (SKU)", required=False)
    related_sku_3 = forms.CharField(label="Susijusi prekė #3 (SKU)", required=False)
    related_sku_4 = forms.CharField(label="Susijusi prekė #4 (SKU)", required=False)

    # masinis galerinų nuotraukų įkėlimas
    bulk_images = MultipleFileField(
        label="Įkelti kelias detalės nuotraukas",
        required=False,
        widget=MultiFileInput(attrs={"multiple": True}),
        help_text="Pasirink kelis failus – po išsaugojimo jie atsiras žemiau „Drabužio kortelės nuotraukos“ sąraše.",
    )

    # >>> nauji laukai (vienas varianto rinkinys viršuje, po Slug):
    v_size  = forms.CharField(label="Dydis", required=False)
    v_price = forms.DecimalField(label="Kaina", max_digits=10, decimal_places=2)
    v_stock = forms.IntegerField(label="Kiekis", min_value=0, initial=0)

    # papildomi (nerodomi pirmoje eilėje, bet palikti patogumui)
    v_color = forms.CharField(label="Spalva", required=False)
    v_sku   = forms.CharField(label="Varianto SKU (nebūtina)", required=False)
    v_compare_at_price = forms.DecimalField(
        label="Kaina be nuolaidos", max_digits=10, decimal_places=2, required=False
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # pradinės reikšmės 4 SKU
        if self.instance and self.instance.pk:
            skus = list(self.instance.related_products.values_list("sku", flat=True)[:4])
            for i, sku in enumerate(skus, start=1):
                self.fields[f"related_sku_{i}"].initial = sku

        # help text kortelės nuotraukoms
        if "main_image" in self.fields:
            self.fields["main_image"].help_text = "Kortelės nuotrauka /shop/ sąraše (pagrindinė)."
        if "hover_image" in self.fields:
            self.fields["hover_image"].help_text = "Kortelės nuotrauka /shop/ sąraše (rodoma ant „hover“)."

        # užpildom viršutinius varianto laukus, jei toks jau yra
        v = self.instance.variants.first() if (self.instance and self.instance.pk) else None
        if v:
            self.fields["v_size"].initial  = v.size
            self.fields["v_price"].initial = v.price
            self.fields["v_stock"].initial = v.stock
            self.fields["v_color"].initial = v.color
            self.fields["v_sku"].initial   = v.sku
            self.fields["v_compare_at_price"].initial = v.compare_at_price
        else:
            # siūlom varianto SKU = produkto SKU
            self.fields["v_sku"].initial = getattr(self.instance, "sku", "")

    def clean(self):
        cleaned = super().clean()
        # validuojam 4 SKU
        raw = [
            cleaned.get("related_sku_1") or "",
            cleaned.get("related_sku_2") or "",
            cleaned.get("related_sku_3") or "",
            cleaned.get("related_sku_4") or "",
        ]
        skus = [s.strip() for s in raw if s.strip()]
        if len(skus) != len(set(skus)):
            raise ValidationError("Susijusių prekių SKU negali dubliuotis.")
        qs = Product.objects.filter(sku__in=skus)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        found = list(qs)
        not_found = set(skus) - set(p.sku for p in found)
        if not_found:
            raise ValidationError(f"Nerastos prekės pagal SKU: {', '.join(sorted(not_found))}")
        self._resolved_related = found[:4]
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=commit)

        # priskiriam „panašias“
        def apply_m2m():
            instance.related_products.set(getattr(self, "_resolved_related", []))
        if commit:
            apply_m2m()
        else:
            self.save_m2m = apply_m2m  # type: ignore

        # masinis ProductImage sukūrimas
        files = self.cleaned_data.get("bulk_images", []) or []
        if files:
            start = instance.images.aggregate(m=Max("sort"))["m"] or 0
            for i, f in enumerate(files, start=1):
                ProductImage.objects.create(product=instance, image=f, sort=start + i)

        # >>> išsaugom / atnaujinam VIENĄ varianto įrašą (viršutiniai laukai)
        v = instance.variants.first()
        if not v:
            v = Variant(product=instance)
        v.size  = self.cleaned_data.get("v_size") or ""
        v.price = self.cleaned_data["v_price"]
        v.stock = self.cleaned_data["v_stock"]
        v.color = self.cleaned_data.get("v_color") or ""
        v.sku   = (self.cleaned_data.get("v_sku") or instance.sku or "").strip() or None
        v.compare_at_price = self.cleaned_data.get("v_compare_at_price") or None
        v.is_active = True
        v.save()

        return instance

# ================= Product =================
@admin.register(Product)
class ProductAdmin(_BaseProductAdmin):
    form = ProductAdminForm
    list_display = ("thumb", "sku", "brand", "category", "price_col", "stock_col", "is_active", "created_at")
    list_filter = ("category",)
    search_fields = ("sku", "name", "brand", "description")
    prepopulated_fields = {"slug": ("name",)}
    # variantų inline nebėra – naudojam viršuje esančius laukus
    inlines = [ProductImageInline]
    readonly_fields = ("related_preview", "main_image_preview", "hover_image_preview")

    fieldsets = (
        # 1) Viskas pagrindiniame bloke: po Slug – Kaina, Dydis, Kiekis
        ("Naujas katalogo drabužis", {
            "fields": (
                "sku", "brand", "category",
                "name", "slug",
                ("v_price", "v_size", "v_stock"),   # <<< čia perkelta
                "description", "is_active",
            )
        }),
        # (nebūtina, bet palieku papildomus varianto laukus atskirai, suskleidžiamus)
        ("Papildoma varianto informacija", {
            "fields": (("v_color", "v_sku", "v_compare_at_price"),),
            "classes": ("collapse",),
        }),
        ("Katalogo nuotraukos", {
            "fields": (
                ("main_image", "main_image_preview"),
                ("hover_image", "hover_image_preview"),
            ),
            "description": "Šios dvi nuotraukos rodomos produktų sąraše (/shop/): pagrindinė ir „hover“."
        }),
        ("Drabužio nuotraukų įkėlimas", {
            "fields": ("bulk_images",),
            "description": "Pasirink kelis failus – po išsaugojimo jie atsiras žemiau „Drabužio kortelės nuotraukos“ sąraše.",
        }),
        ("Panašios prekės (įvesti SKU)", {
            "fields": ("related_sku_1", "related_sku_2", "related_sku_3", "related_sku_4"),
            "description": "Įrašykite iki 4 kitų produktų SKU. Dubliuoti ar nurodyti paties produkto SKU negalima."
        }),
        ("Panašių prekių peržiūra", {
            "fields": ("related_preview",),
        }),
    )

    # --- likusi klasė be pokyčių ---

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None and "sku" in form.base_fields:
            try:
                form.base_fields["sku"].initial = Product.next_sku()
            except Exception:
                pass
        return form

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj:
            ro.append("sku")
        return ro

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("category").prefetch_related("images", "variants", "related_products__images")

    @admin.display(description="Preview")
    def thumb(self, obj):
        if getattr(obj, "main_image", None):
            try:
                return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', obj.main_image.url)
            except Exception:
                pass
        img = obj.images.order_by("sort", "id").first()
        if img and img.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', img.image.url)
        return "—"

    @admin.display(description="Price")
    def price_col(self, obj):
        if hasattr(obj, "price"):
            return obj.price
        v = obj.variants.order_by("price").first()
        return v.price if v else None

    @admin.display(description="Stock")
    def stock_col(self, obj):
        if hasattr(obj, "stock"):
            return obj.stock
        return obj.variants.aggregate(s=Sum("stock"))["s"] or 0

    @admin.display(description="Panašių peržiūra")
    def related_preview(self, obj):
        if not obj or not getattr(obj, "pk", None):
            return "—"
        items = obj.related_products.all()[:4]
        if not items:
            return "—"
        blocks = []
        for p in items:
            url = ""
            if getattr(p, "main_image", None):
                try:
                    url = p.main_image.url
                except Exception:
                    url = ""
            if not url:
                im = p.images.order_by("sort", "id").first()
                if im and im.image:
                    url = im.image.url
            thumb = format_html('<img src="{}" style="height:48px;border-radius:6px;" />', url) if url else "—"
            blocks.append(format_html(
                '<div style="display:inline-block;margin-right:8px;text-align:center;">{}'
                '<div style="font-size:11px;color:#666;">{}</div></div>',
                thumb, p.sku
            ))
        return format_html("".join(blocks))

    @admin.display(description="Peržiūra")
    def main_image_preview(self, obj):
        if obj and getattr(obj, "main_image", None):
            try:
                return format_html('<img src="{}" style="height:80px;border-radius:6px;" />', obj.main_image.url)
            except Exception:
                pass
        return "—"

    @admin.display(description="Peržiūra")
    def hover_image_preview(self, obj):
        if obj and getattr(obj, "hover_image", None):
            try:
                return format_html('<img src="{}" style="height:80px;border-radius:6px;" />', obj.hover_image.url)
            except Exception:
                pass
        return "—"


# ================= Variant =================
@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = (
        "thumb",
        "sku",
        "product",
        "color",
        "size",
        "price",
        "compare_at_price",
        "discount_pct",
        "stock",
        "is_active",
    )
    list_editable = ("price", "compare_at_price", "stock", "is_active")
    list_filter = ("size",)  # tik dydis
    search_fields = ("sku", "product__name")
    list_select_related = ("product",)

    actions = ["discount_10", "discount_20", "clear_discount"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("product").prefetch_related("product__images")

    @admin.display(description="Preview")
    def thumb(self, obj):
        if getattr(obj.product, "main_image", None):
            try:
                return format_html('<img src="{}" style="height:48px;border-radius:6px;" />', obj.product.main_image.url)
            except Exception:
                pass
        img = obj.product.images.order_by("sort", "id").first()
        if img and img.image:
            return format_html('<img src="{}" style="height:48px;border-radius:6px;" />', img.image.url)
        return "—"

    @admin.display(description="Discount %")
    def discount_pct(self, obj):
        if obj.compare_at_price and obj.compare_at_price > obj.price:
            pct = (obj.compare_at_price - obj.price) / obj.compare_at_price * Decimal("100")
            return f"{pct.quantize(Decimal('1'))}%"
        return "—"

    # ----- Actions -----
    def _apply_percent(self, queryset, percent: int):
        factor = (Decimal("100") - Decimal(percent)) / Decimal("100")
        for v in queryset:
            if not v.compare_at_price or v.compare_at_price < v.price:
                v.compare_at_price = v.price
            v.price = (v.price * factor).quantize(Decimal("0.01"))
            v.save(update_fields=["price", "compare_at_price"])

    @admin.action(description="Taikyti −10%%")  # svarbu: dvigubas %
    def discount_10(self, request, queryset):
        self._apply_percent(queryset, 10)
        self.message_user(request, "Pritaikyta −10% pasirinktiems variantams.")

    @admin.action(description="Taikyti −20%%")
    def discount_20(self, request, queryset):
        self._apply_percent(queryset, 20)
        self.message_user(request, "Pritaikyta −20% pasirinktiems variantams.")

    @admin.action(description="Nuimti nuolaidą (atstatyti kainą)")
    def clear_discount(self, request, queryset):
        for v in queryset:
            if v.compare_at_price and v.compare_at_price > 0:
                v.price = v.compare_at_price
                v.save(update_fields=["price"])
        self.message_user(request, "Nuolaidos nuimtos (kainos atstatytos).")

@admin.register(Category)
class CategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        "name", "parent", "order", "active_products_link", "all_products_link",
    )
    search_fields = ("name", "slug")
    list_filter = ("parent",)
    ordering = ("order", "name")
    prepopulated_fields = {"slug": ("name",)}  # jei nori – patogu kurti naujas

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # skaičiuojam prekių kiekius (aktyvias ir visas)
        return qs.annotate(
            all_products_count=Count("products", distinct=True),
            active_products_count=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True,
            ),
        )

    @admin.display(description="Akt. prekės", ordering="active_products_count")
    def active_products_link(self, obj):
        url = reverse("admin:catalog_product_changelist")
        params = urlencode({"category__id__exact": obj.id, "is_active__exact": "1"})
        return format_html('<a href="{}?{}">{}</a>', url, params, obj.active_products_count)

    @admin.display(description="Viso prekių", ordering="all_products_count")
    def all_products_link(self, obj):
        url = reverse("admin:catalog_product_changelist")
        params = urlencode({"category__id__exact": obj.id})
        return format_html('<a href="{}?{}">{}</a>', url, params, obj.all_products_count)

@admin.register(Size)
class SizeAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = (
        "label", "slug", "order", "is_active",
        "active_products_link", "all_products_link",
    )
    list_editable = ("is_active",)
    ordering = ("order", "label")
    search_fields = ("label", "slug")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # suskaičiuojam produktus (aktyvius ir visus)
        return qs.annotate(
            all_products_count=Count("products", distinct=True),
            active_products_count=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True,
            ),
        )

    @admin.display(description="Akt. prekės", ordering="active_products_count")
    def active_products_link(self, obj):
        url = reverse("admin:catalog_product_changelist")
        params = urlencode({"size__id__exact": obj.id, "is_active__exact": "1"})
        return format_html('<a href="{}?{}">{}</a>', url, params, obj.active_products_count)

    @admin.display(description="Viso prekių", ordering="all_products_count")
    def all_products_link(self, obj):
        url = reverse("admin:catalog_product_changelist")
        params = urlencode({"size__id__exact": obj.id})
        return format_html('<a href="{}?{}">{}</a>', url, params, obj.all_products_count)
