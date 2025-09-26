# discounts/apps.py
from django.apps import AppConfig

class DiscountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "discounts"
    verbose_name = "Discounts"  # arba "Nuolaidos"

    def ready(self):
        # Vietinis importas, kad išvengtume ciklinių importų.
        # Čia užkrausite visus signalų registravimus (receiver’ius).
        import discounts.signals  # noqa: F401
