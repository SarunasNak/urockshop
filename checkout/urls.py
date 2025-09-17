# checkout/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # pagrindinis checkout puslapis
    path("", views.checkout_view, name="checkout"),
    # (nebūtina, bet galima palikti alias’ą, jei kur nors buvai panaudojęs 'checkout_view')
    path("", views.checkout_view, name="checkout_view"),

    path("success/<int:order_id>/", views.checkout_success, name="checkout_success"),

    # API kelias naujam 1-žingsnio Stripe flow’ui
    # galutinis URL bus /checkout/api/create/
    path("api/create/", views.checkout_create_order_api, name="checkout_create_order_api"),
]

