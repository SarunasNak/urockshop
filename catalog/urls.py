from django.urls import path
from .views import ProductListView, ProductDetailView, category_redirect

app_name = "catalog"

urlpatterns = [
    # 1. /shop/ -> visos prekės
    path("", ProductListView.as_view(), name="product_list"),

    # 2. PRODUKTAI (turi būti PRIEŠ kategorijas!)
    path("preke/<slug:slug>/", ProductDetailView.as_view(), name="product_detail"),

    # 3. kategorijų redirect 
    path("<slug:slug>/", category_redirect, name="category_redirect"),
]

