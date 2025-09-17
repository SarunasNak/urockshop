from django.conf import settings

def stripe_public_key(request):
    return {
        "STRIPE_PUBLISHABLE_KEY": getattr(settings, "STRIPE_PUBLISHABLE_KEY", ""),
        "STRIPE_CURRENCY": getattr(settings, "STRIPE_CURRENCY", "eur"),
    }
