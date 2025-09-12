from rest_framework import serializers
from .models import Category, Product, Variant, ProductImage

class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("image", "alt")

class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = ("id", "sku", "color", "size", "price", "stock", "is_active")

class ProductListSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer()
    thumbnail = serializers.SerializerMethodField()
    min_price = serializers.SerializerMethodField()
    max_price = serializers.SerializerMethodField()
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ("id","name","slug","category","thumbnail","min_price","max_price","in_stock")

    def get_thumbnail(self, obj):
        img = obj.images.order_by("sort","id").first()
        return img.image.url if img else None

    def get_min_price(self, obj):
        v = obj.variants.order_by("price").first()
        return float(v.price) if v else None

    def get_max_price(self, obj):
        v = obj.variants.order_by("-price").first()
        return float(v.price) if v else None

    def get_in_stock(self, obj):
        return obj.variants.filter(stock__gt=0, is_active=True).exists()

class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategoryMiniSerializer()
    images = ProductImageSerializer(many=True, read_only=True)
    variants = VariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ("id","name","slug","description","category","images","variants","is_active","created_at")
