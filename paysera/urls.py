from django.urls import path
from .views import paysera_redirect, paysera_callback, paysera_cancel

urlpatterns = [
    path("redirect/<int:order_id>/", paysera_redirect, name="paysera_redirect"),
    path("callback/", paysera_callback, name="paysera_callback"),
    path("cancel/<int:order_id>/", paysera_cancel, name="paysera_cancel"),
]
