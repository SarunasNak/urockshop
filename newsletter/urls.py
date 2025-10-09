from django.urls import path
from .views import subscribe

app_name = "newsletter"   # svarbu, kad galėtume naudoti namespace

urlpatterns = [
    path("subscribe/", subscribe, name="subscribe"),
]