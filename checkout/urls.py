# checkout/urls.py
from django.urls import path
from .views import checkout_view, checkout_success

urlpatterns = [
    path("", checkout_view, name="checkout"),
    path("success/<int:order_id>/", checkout_success, name="checkout_success"),
]
