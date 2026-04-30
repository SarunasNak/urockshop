# catalog/models.py
from django.db import models, transaction, IntegrityError
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.utils.html import format_html
from django.apps import apps
from django.urls import reverse
import os
from django_ckeditor_5.fields import CKEditor5Field
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings

# ---- helper upload kelias: products/<SKU>/filename ----
def product_upload_to(instance, filename):
    """
    Stabilus kelias į media:
    - products/<product_pk>/<filename>, jei turim tėvo PK
    - products/tmp/<filename>, jei PK dar nėra (labai retas atvejis)
    """
    # Jei pats Product (turi main_image/hover_image) – tėvas = instance
    product = instance if hasattr(instance, "sku") else getattr(instance, "product", None)
    pk = getattr(product, "pk", None)
    folder = f"products/{pk if pk else 'tmp'}"
    return os.path.join(folder, filename)

def resize_image(image_field, max_width=2000, quality=72):
    img = Image.open(image_field)

    if img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size

    if width > max_width:
        img.thumbnail((max_width, max_width*2), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)

    return ContentFile(buffer.getvalue())

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
        "Size",
        null=True, blank=True,
        on_delete=models.PROTECT,
        related_name="products",
        db_index=True,
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=1, help_text="Pradinė atsarga")

    description = CKEditor5Field('Aprašymas', config_name='products', blank=True)

    # --- 2 kortelės nuotraukos (listingo) ---
    main_image = models.ImageField(upload_to=product_upload_to, blank=True, null=True)
    hover_image = models.ImageField(upload_to=product_upload_to, blank=True, null=True)

    # --- ALT tekstai SEO tikslams ---
    main_image_alt = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Main image ALT",
        help_text="ALT tekstas pagrindinei produkto nuotraukai (SEO aprašymas)"
    )
    hover_image_alt = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Hover image ALT",
        help_text="ALT tekstas antroje produkto nuotraukai (rodoma ant hover)"
    )

    # --- galerija detalei tvarkoma ProductImage modelyje ---

    related_products = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
        related_name="related_to",
        help_text="Iki 4 susijusių prekių",
    )

    is_active = models.BooleanField(default=True)

    # ✅ NAUJAS LAUKAS
    on_model = models.BooleanField(
        default=False,
        verbose_name="Produktas ant modelio",
        help_text="Pažymėkite, jei pagrindinė produkto nuotrauka yra ant modelio (žmogaus)."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Product {self.pk}"

    # ---- URL į detalės puslapį (SU namespace)
    def get_absolute_url(self):
        return reverse("catalog:product_detail", kwargs={"slug": self.slug})

    # ---- Patogus tekstas „Dydis …“ vietoj None
    @property
    def size_display(self) -> str:
        return self.size.label if self.size_id else ""

    # ---- Pagrindinė nuotrauka kortelei: main_image -> pirmas iš galerijos -> None
    def primary_image_url(self) -> str | None:
        if self.main_image and getattr(self.main_image, "url", None):
            return self.main_image.url
        img = self.images.all().order_by("sort", "id").first() if hasattr(self, "images") else None
        if not img:
            return None
        if hasattr(img, "image") and getattr(img.image, "url", None):
            return img.image.url
        return getattr(img, "url", None)

    # ---- sekantis SKU iš esamų URxxxx
    @classmethod
    def next_sku(cls) -> str:
        last = cls.objects.filter(sku__regex=r"^UR\d{4}$").order_by("-sku").first()
        n = int(last.sku[2:]) if last and last.sku else 0
        if n >= 9999:
            raise ValueError("Pasiektas maksimalus SKU (UR9999).")
        return f"UR{n+1:04d}"

    def _ensure_slug(self):
        base = f"{self.brand} {self.name}"

        if self.sku:
            base = f"{base} {self.sku}"

        self.slug = slugify(base)

    def save(self, *args, **kwargs):

         # --- resize listing images only if new ---
        if self.main_image and not self.pk:
            resized = resize_image(self.main_image, 800)
            self.main_image.save(self.main_image.name, resized, save=False)

        if self.hover_image and not self.pk:
            resized = resize_image(self.hover_image, 800)
            self.hover_image.save(self.hover_image.name, resized, save=False)


        # --- ALT auto generation ---

        name = self.name or ""

        # jei name jau turi brand – nedubliuojam
        if self.brand and self.brand.lower() in name.lower():
            base_alt = name
        else:
            base_alt = f"{self.brand} {name}".strip()

        generated_main = f"{base_alt} vyrams".strip()
        generated_hover = f"{base_alt} detalė".strip()

        # visada perrašom ALT
        # generuojam tik jei ALT tuščias
        if not self.main_image_alt:
            self.main_image_alt = generated_main

        if not self.hover_image_alt:
            self.hover_image_alt = generated_hover

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
        size_label = self.size.label if self.size_id else ""

        v, created = Variant.objects.get_or_create(
            product=self,
            defaults={
                "price": self.price,
                "size": size_label,   # string, ne FK
                "stock": self.stock,
                "is_active": self.is_active,
            },
        )
        if not created:
            fields_to_update = []
            if v.price != self.price:
                v.price = self.price
                fields_to_update.append("price")
            if v.size != size_label:
                v.size = size_label
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
    zoom_image = models.ImageField(upload_to=product_upload_to, null=True, blank=True)
    mobile_image = models.ImageField(upload_to=product_upload_to, null=True, blank=True)

    alt = models.CharField(max_length=160, blank=True)
    sort = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]

    def preview(self):
        if self.image:
            return format_html('<img src="{}" style="height:80px; border-radius:6px;" />', self.image.url)
        return "—"
    preview.short_description = "Preview"

    def save(self, *args, **kwargs):

        # --- ALT auto generation (tik jei ALT tuščias) ---
        if not self.alt and self.product:
            parts = [self.product.brand, self.product.name]
            base_alt = " ".join([p for p in parts if p]).strip()

            if base_alt:
                self.alt = base_alt

        old_image = None
        if self.pk:
            try:
                old = ProductImage.objects.get(pk=self.pk)
                old_image = old.image
            except ProductImage.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        if self.image and (old_image != self.image):

            with Image.open(self.image) as img:

                if img.mode != "RGB":
                    img = img.convert("RGB")

                # ---- SLIDER IMAGE (1200px) ----
                slider = img.copy()

                if slider.width > 1200:
                    slider.thumbnail((1200, 2400), Image.LANCZOS)

                slider.save(
                    self.image.path,
                    format="JPEG",
                    quality=72,
                    optimize=True,
                    progressive=True,
                    subsampling=2
                )

                # ---- ZOOM IMAGE (1600px) ----
                zoom = img.copy()

                if zoom.width > 1600:
                    zoom.thumbnail((1600, 3200), Image.LANCZOS)

                base, ext = os.path.splitext(self.image.path)
                zoom_path = base + "_zoom.jpg"

                if os.path.exists(zoom_path):
                    os.remove(zoom_path)

                zoom.save(
                    zoom_path,
                    format="JPEG",
                    quality=78,
                    optimize=True,
                    progressive=True
                )

                self.zoom_image = zoom_path.replace(str(settings.MEDIA_ROOT) + "/", "")

                super().save(update_fields=["zoom_image"])

                # ---- MOBILE IMAGE (700px) ----
                mobile = img.copy()

                if mobile.width > 700:
                    mobile.thumbnail((700, 1400), Image.LANCZOS)

                mobile_path = base + "_mobile.jpg"

                if os.path.exists(mobile_path):
                    os.remove(mobile_path)

                mobile.save(
                    mobile_path,
                    format="JPEG",
                    quality=65,
                    optimize=True,
                    progressive=True
                )

                self.mobile_image = mobile_path.replace(str(settings.MEDIA_ROOT) + "/", "")
                super().save(update_fields=["mobile_image"])


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

    @property
    def discount_percent(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            return int((self.compare_at_price - self.price) / self.compare_at_price * 100)
        return 0

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generate_sku()
        super().save(*args, **kwargs)

    def __str__(self):
        base = f"{self.product.name} [{self.sku}]"
        opts = " ".join([self.color or "", self.size or ""]).strip()
        return f"{base} {opts}" if opts else base


class PrivateCollection(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class PrivateProduct(models.Model):
    collection = models.ForeignKey(
        PrivateCollection,
        on_delete=models.CASCADE,
        related_name="items"
    )

    is_sold = models.BooleanField(default=False)

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position"]
        unique_together = ("collection", "product")



