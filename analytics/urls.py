# analytics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("track/", views.track_event, name="analytics_track"),
    path("events_overview/", views.events_overview, name="events_overview"),
]

