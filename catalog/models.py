from django.db import models
from django.utils.text import slugify
from django.utils.html import format_html

class Category(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def admin_thumbnail(self):
        img = self.images.order_by("sort", "id").first()
        if img and img.image:
            return format_html('<img src="{}" style="height:60px; border-radius:6px;" />', img.image.url)
        return "—"
    admin_thumbnail.short_description = "Preview"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
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
    """Dydis/spalva su kaina ir atsarga per variantą."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=40, blank=True)
    size = models.CharField(max_length=20, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("product", "color", "size")

    def __str__(self):
        base = f"{self.product.name} [{self.sku}]"
        opts = " ".join([self.color or "", self.size or ""]).strip()
        return f"{base} {opts}" if opts else base
