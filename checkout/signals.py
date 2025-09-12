# checkout/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction

from .models import Order

def _send_emails(order: Order):
    ctx = {
        "order": order,
        "ORDER_ADMIN_EMAIL": settings.ORDER_ADMIN_EMAIL,
        "SITE_HOST": getattr(settings, "SITE_HOST", ""),
        "SITE": None,
        # request stub nebūtinas jei šablonai nepasikliauja request; paliekam jei naudojai:
        # "request": SimpleNamespace(get_host=lambda: getattr(settings, "SITE_HOST", "sarunasnakvosas.pythonanywhere.com"), scheme="https"),
    }

    # Klientui
    subject_c = f"Užsakymo #{order.id} patvirtinimas"
    txt_c = render_to_string("emails/order_confirmation.txt", ctx)
    html_c = render_to_string("emails/order_confirmation.html", ctx)
    msg_c = EmailMultiAlternatives(subject_c, txt_c, settings.DEFAULT_FROM_EMAIL, [order.email])
    msg_c.attach_alternative(html_c, "text/html")
    msg_c.send(fail_silently=False)

    # Adminui
    subject_a = f"Naujas užsakymas #{order.id}"
    txt_a = render_to_string("emails/order_notify_admin.txt", ctx)
    html_a = render_to_string("emails/order_notify_admin.html", ctx)
    msg_a = EmailMultiAlternatives(subject_a, txt_a, settings.DEFAULT_FROM_EMAIL, [settings.ORDER_ADMIN_EMAIL])
    msg_a.attach_alternative(html_a, "text/html")
    msg_a.send(fail_silently=False)

@receiver(post_save, sender=Order)
def send_order_emails(sender, instance: Order, created, **kwargs):
    if not created:
        return

    # Siųsk tik kai užsakymas tikrai „pateiktas“ (o ne kokie tarpiniai draft’ai)
    if instance.status not in ("cod_placed", "pending", "paid"):
        return

    # Labai svarbu: siųsti po commit, ir pasikrauti Order iš DB, kad turėtų eilutes/total
    def _after_commit():
        try:
            order = Order.objects.select_related().prefetch_related("items").get(pk=instance.pk)
        except Order.DoesNotExist:
            return
        _send_emails(order)

    transaction.on_commit(_after_commit)
