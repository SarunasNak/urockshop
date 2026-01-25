from django.urls import path
from . import views

app_name = "marketing"

urlpatterns = [
    path("popup-submit/", views.popup_submit, name="popup_submit"),
]
