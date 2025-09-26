# catalog/models.py
from django.db import models, transaction, IntegrityError
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.html import format_html
from django.apps import apps

# ---- helper upload kelias: products/<SKU>/filename ----
def product_upload_to(instance, filename):
    """
    Failų saugojimo kelias pagal SKU:
    - Product: products/<product.sku>/<filename>
    - ProductImage: products/<product.sku>/<filename>
    """
    sku = None
    # jei keliame Product nuotraukas
    if hasattr(instance, "sku") and instance.sku:
        sku = instance.sku
    # jei keliame ProductImage nuotraukas
    if not sku and hasattr(instance, "product") and instance.product:
        sku = getattr(instance.product, "sku", None)

    sku = sku or "no-sku"
    return f"products/{sku}/{filename}"


class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    # NEW
    order = models.PositiveSmallIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Size(models.Model):
    slug  = models.SlugField(max_length=40, unique=True)   # "s", "m", "l", "xl", "xxl", "xxxl"
    label = models.CharField(max_length=40)                # "S", "M", "L", "XL", "XXL", "XXXL"
    order = models.PositiveSmallIntegerField(default=0)    # rikiavimui (S=1, M=2, ...)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "label"]

    def __str__(self):
        return self.label


class Product(models.Model):
    sku = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r"^UR\d{4}$", "SKU formatas: UR0001–UR9999")],
        help_text="Sugeneruojamas automatiškai",
    )
    brand = models.CharField(max_length=120, blank=True, default="")
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )

    # >>> nauji laukai, kuriuos pildai Product formoje
    size = models.ForeignKey(
    "Size",                 # string – veiks nepriklausomai nuo klasės vietos faile
    null=True, blank=True,
    on_delete=models.PROTECT,
    related_name="products",
    db_index=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=1, help_text="Pradinė atsarga")

    description = models.TextField(blank=True)

    # --- 2 kortelės nuotraukos (listingo) ---
    main_image = models.ImageField(upload_to=product_upload_to, blank=True, null=True)
    hover_image = models.ImageField(upload_to=product_upload_to, blank=True, null=True)

    # --- galerija detalei tvarkoma ProductImage modelyje ---

    related_products = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="related_to",
        help_text="Iki 4 susijusių prekių",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Product {self.pk}"

    # ---- sekantis SKU iš esamų URxxxx
    @classmethod
    def next_sku(cls) -> str:
        last = cls.objects.filter(sku__regex=r"^UR\d{4}$").order_by("-sku").first()
        n = int(last.sku[2:]) if last and last.sku else 0
        if n >= 9999:
            raise ValueError("Pasiektas maksimalus SKU (UR9999).")
        return f"UR{n+1:04d}"

    def _ensure_slug(self):
        if not self.slug:
            base = f"{self.brand}-{self.name}"
            if self.sku:
                base = f"{base}-{self.sku}"
            self.slug = slugify(base)

    def save(self, *args, **kwargs):
        # 1) užtikrinam SKU ir slug
        if not self.sku:
            for _ in range(5):
                self.sku = Product.next_sku()
                self._ensure_slug()
                try:
                    with transaction.atomic():
                        super().save(*args, **kwargs)
                    break
                except IntegrityError:
                    self.sku = None
            else:
                raise
        else:
            self._ensure_slug()
            super().save(*args, **kwargs)

        # 2) po išsaugojimo – sukurti/atnaujinti vienintelį variantą pagal Product laukus
        Variant = apps.get_model("catalog", "Variant")

        # paimam Size label kaip string (jei dydis neparinktas – tuščia)
        size_label = self.size.label if self.size_id else ""

        v, created = Variant.objects.get_or_create(
            product=self,
            defaults={
                "price": self.price,
                "size": size_label,       # ← buvo: self.size
                "stock": self.stock,
                "is_active": self.is_active,
            },
        )

        if not created:
            fields_to_update = []

            if v.price != self.price:
                v.price = self.price
                fields_to_update.append("price")

            target_size = size_label     # ← palyginam su stringu
            if v.size != target_size:
                v.size = target_size
                fields_to_update.append("size")

            if v.is_active != self.is_active:
                v.is_active = self.is_active
                fields_to_update.append("is_active")

            if v.stock != self.stock:
                v.stock = self.stock
                fields_to_update.append("stock")

            if fields_to_update:
                v.save(update_fields=fields_to_update)


class ProductImage(models.Model):
    """Papildomos nuotraukos produkto detalei (kortelei atidarius)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=product_upload_to)
    alt = models.CharField(max_length=160, blank=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

    def preview(self):
        if self.image:
            return format_html('<img src="{}" style="height:80px; border-radius:6px;" />', self.image.url)
        return "—"
    preview.short_description = "Preview"


class Variant(models.Model):
    """Vienetinė atmaina; SKU generuojamas pagal Product SKU + (COLOR/SIZE)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=50, unique=True, null=True, blank=True)
    color = models.CharField(max_length=40, blank=True)
    size = models.CharField(max_length=20, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "color", "size")

    def _generate_sku(self):
        base = (self.product.sku or "UR0000").upper()
        parts = [p for p in [self.color, self.size] if p]
        tail = "-".join(slugify(p).upper().replace("-", "") for p in parts)
        candidate = base if not tail else f"{base}-{tail}"

        sku = candidate
        i = 1
        # naudokime type(self) vietoj importo, kad neatsirastų „Model already registered“
        while type(self).objects.filter(sku=sku).exclude(pk=self.pk).exists():
            i += 1
            sku = f"{candidate}-{i}"
        return sku

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generate_sku()
        super().save(*args, **kwargs)

    def __str__(self):
        base = f"{self.product.name} [{self.sku}]"
        opts = " ".join([self.color or "", self.size or ""]).strip()
        return f"{base} {opts}" if opts else base




