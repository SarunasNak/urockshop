from django.urls import path
from .views import ProductListView, ProductDetailView, category_redirect, private_collection_view
from .views import private_product_detail_view


app_name = "catalog"

urlpatterns = [
    # 1. /shop/ -> visos prekės
    path("", ProductListView.as_view(), name="product_list"),

    # 2. PRODUKTAI (turi būti PRIEŠ kategorijas!)
    path("preke/<slug:slug>/", ProductDetailView.as_view(), name="product_detail"),

    # 3. private catalog
    path("private/<slug:slug>/", private_collection_view, name="private_collection"),

    # 4. private product
    path("private/preke/<slug:slug>/", private_product_detail_view, name="private_product_detail"),

    # 5. kategorijų redirect
    path("<slug:slug>/", category_redirect, name="category_redirect"),
]

