from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("add/", views.cart_add, name="add"),        # <- svarbu
    path("update/", views.cart_update, name="cart_update"),
    path("remove/", views.cart_remove, name="cart_remove"),
    path("tryon/submit/", views.tryon_submit, name="tryon_submit"),
]

