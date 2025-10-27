from django.apps import AppConfig

class AnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "analytics"

    def ready(self):
        # Importuojame admin dashboard'us tik kai Django jau užkrautas
        from . import admin_dashboard
        from . import admin_events

