from django.urls import path
from .views import subscribe
from .views_unsubscribe import unsubscribe_view

app_name = "newsletter"   # svarbu, kad galėtume naudoti namespace

urlpatterns = [
    path("subscribe/", subscribe, name="subscribe"),
    path("unsubscribe/", unsubscribe_view, name="unsubscribe"),
]