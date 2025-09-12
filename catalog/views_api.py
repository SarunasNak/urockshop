from rest_framework import generics, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductListSerializer, ProductDetailSerializer

class ProductListView(generics.ListAPIView):
    queryset = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images","variants")
        .order_by("-created_at")
    )
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # /api/products/?category=hoodies
    filterset_fields = {"category__slug": ["exact"]}
    # /api/products/?search=hoodie
    search_fields = ["name", "description"]
    # /api/products/?ordering=name  (arba -created_at)
    ordering_fields = ["id", "name", "created_at"]

class ProductDetailView(generics.RetrieveAPIView):
    lookup_field = "slug"
    queryset = (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("images","variants")
    )
    serializer_class = ProductDetailSerializer
