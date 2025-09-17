# checkout/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
import logging

from .models import Order

log = logging.getLogger(__name__)

def _send_emails(order: Order):
    # Ar naudojam "saugų" (negriaunantį) režimą?
    # Staging’e su console/filebased backend – visada tyliai.
    backend = getattr(settings, "EMAIL_BACKEND", "")
    silent_backend = backend.endswith("console.EmailBackend") or backend.endswith("filebased.EmailBackend")

    ctx = {
        "order": order,
        "ORDER_ADMIN_EMAIL": getattr(settings, "ORDER_ADMIN_EMAIL", None),
        "SITE_HOST": getattr(settings, "SITE_HOST", ""),
        "SITE": None,
    }

    # Klientui
    try:
        subject_c = f"Užsakymo #{order.id} patvirtinimas"
        txt_c = render_to_string("emails/order_confirmation.txt", ctx)
        html_c = render_to_string("emails/order_confirmation.html", ctx)
        msg_c = EmailMultiAlternatives(subject_c, txt_c, getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost"), [order.email])
        msg_c.attach_alternative(html_c, "text/html")
        msg_c.send(fail_silently=silent_backend)
    except Exception:
        log.exception("Nepavyko išsiųsti kliento laiško (order #%s)", order.id)

    # Adminui (siunčiam tik jei turim admin el. paštą)
    admin_email = getattr(settings, "ORDER_ADMIN_EMAIL", None)
    if admin_email:
        try:
            subject_a = f"Naujas užsakymas #{order.id}"
            txt_a = render_to_string("emails/order_notify_admin.txt", ctx)
            html_a = render_to_string("emails/order_notify_admin.html", ctx)
            msg_a = EmailMultiAlternatives(subject_a, txt_a, getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost"), [admin_email])
            msg_a.attach_alternative(html_a, "text/html")
            msg_a.send(fail_silently=silent_backend)
        except Exception:
            log.exception("Nepavyko išsiųsti administratoriaus laiško (order #%s)", order.id)
    else:
        log.warning("ORDER_ADMIN_EMAIL nenustatytas – praleidžiam admino pranešimą (order #%s)", order.id)

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
