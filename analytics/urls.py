# analytics/urls.py
from django.urls import path
from . import views
from .views import track_private

urlpatterns = [
    path("track/", views.track_event, name="analytics_track"),
    path("events_overview/", views.events_overview, name="analytics_events_overview"),
    path("track-private/", track_private, name="track_private"),
]

