# cart/urls.py
from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("", views.cart_view, name="view"),  # alias 'cart:view'

    path("add/", views.cart_add, name="cart_add"),
    path("add/", views.cart_add, name="add"),  # alias 'cart:add'

    path("update/", views.cart_update, name="cart_update"),
    path("update/", views.cart_update, name="update"),  # alias 'cart:update'

    path("remove/", views.cart_remove, name="cart_remove"),
    path("remove/", views.cart_remove, name="remove"),  # alias 'cart:remove'

    # Kuponai
    path("coupon/apply/", views.cart_apply_coupon, name="cart_apply_coupon"),
    path("coupon/apply/", views.cart_apply_coupon, name="apply_coupon"),  # alias 'cart:apply_coupon'

    path("coupon/remove/", views.cart_remove_coupon, name="cart_remove_coupon"),
    path("coupon/remove/", views.cart_remove_coupon, name="remove_coupon"),  # alias 'cart:remove_coupon'
]
