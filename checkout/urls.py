# checkout/urls.py
from django.urls import path
from . import views

app_name = "checkout"

urlpatterns = [
    path("", views.checkout_view, name="checkout"),
    path("dpd/points/", views.dpd_points, name="dpd_points"),
    path("success/<int:order_id>/", views.checkout_success, name="checkout_success"),
    path("api/create/", views.checkout_create_order_api, name="checkout_create_order_api"),
]
