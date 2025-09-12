from django.core.management.base import BaseCommand
from catalog.models import Category, Product, Variant

class Command(BaseCommand):
    help = "Seed demo categories/products/variants"

    def handle(self, *args, **options):
        self.stdout.write("Seeding catalog...")

        hoodies, _ = Category.objects.get_or_create(name="Hoodies", slug="hoodies")
        tees, _ = Category.objects.get_or_create(name="T-Shirts", slug="t-shirts")

        hoodie, _ = Product.objects.get_or_create(
            name="Unisex Hoodie",
            slug="unisex-hoodie",
            category=hoodies,
            defaults={"description": "Minkštas, šiltas, 80% medvilnės.", "is_active": True},
        )
        Variant.objects.get_or_create(product=hoodie, sku="HOOD-BLK-M",
                                      defaults={"color": "black", "size": "M", "price": 39.99, "stock": 8})
        Variant.objects.get_or_create(product=hoodie, sku="HOOD-GRY-L",
                                      defaults={"color": "gray", "size": "L", "price": 44.99, "stock": 2})

        tee, _ = Product.objects.get_or_create(
            name="Classic T-Shirt",
            slug="classic-t-shirt",
            category=tees,
            defaults={"description": "100% medvilnė.", "is_active": True},
        )
        Variant.objects.get_or_create(product=tee, sku="TEE-WHT-M",
                                      defaults={"color": "white", "size": "M", "price": 14.99, "stock": 20})
        Variant.objects.get_or_create(product=tee, sku="TEE-NVY-L",
                                      defaults={"color": "navy", "size": "L", "price": 19.99, "stock": 10})

        self.stdout.write(self.style.SUCCESS("Catalog seeded."))
