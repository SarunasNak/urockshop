# catalog/urls.py
from django.urls import path
from .views import ProductListView, ProductDetailView

app_name = "catalog"  # <- BŪTINA, kad veiktų namespace

urlpatterns = [
    path("", ProductListView.as_view(), name="list"),
    path("<slug:slug>/", ProductDetailView.as_view(), name="detail"),
]
