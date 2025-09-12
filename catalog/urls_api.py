from django.urls import path
from .views_api import ProductListView, ProductDetailView

urlpatterns = [
    path("products/", ProductListView.as_view(), name="api-product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="api-product-detail"),
]
