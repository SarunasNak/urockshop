# shop/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse, NoReverseMatch
from catalog.models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        try:
            return Product.objects.filter(is_active=True).order_by("pk")
        except Exception:
            return Product.objects.all().order_by("pk")

    def lastmod(self, obj):
        return getattr(obj, "updated_at", None) or getattr(obj, "created_at", None)

    def location(self, obj):
        for name in ("product_detail", "catalog_product_detail"):
            try:
                return reverse(name, kwargs={"slug": obj.slug})
            except NoReverseMatch:
                pass
        try:
            return obj.get_absolute_url()
        except Exception:
            return f"/shop/{obj.slug}/"


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all().order_by("pk")

    def location(self, obj):
        for name in ("category_detail", "catalog_category"):
            try:
                return reverse(name, kwargs={"slug": obj.slug})
            except NoReverseMatch:
                pass
        try:
            return obj.get_absolute_url()
        except Exception:
            return f"/shop/{obj.slug}/"


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        # Tik indeksuotini statiniai puslapiai. NEįtraukiam cart/checkout/success.
        return ["home", "about"]  # pridėk kitus indeksuotinus pvz. "blog_list" jei yra

    def location(self, name):
        return reverse(name)
