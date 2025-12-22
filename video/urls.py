from django.urls import path
from .views import video_page

app_name = "video"

urlpatterns = [
    path("", video_page, name="index"),
]