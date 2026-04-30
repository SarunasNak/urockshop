from django.urls import path
from . import views

app_name = "marketing"

urlpatterns = [
    path("popup-submit/", views.popup_submit, name="popup_submit"),
    path("private-presentation/thanks/", views.presentation_thanks, name="presentation_thanks"),
    path("private/", views.private_presentation, name="private"),
]
