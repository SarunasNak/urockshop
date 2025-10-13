# catalog/urls.py
from django.urls import path
from .views import ProductListView, ProductDetailView

app_name = "catalog"  # <— svarbu, nes šablone naudoji 'catalog:list'

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("", ProductListView.as_view(), name="list"),  # ← alias senam pavadinimui

    path("<slug:slug>/", ProductDetailView.as_view(), name="product_detail"),
]