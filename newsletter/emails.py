from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def send_welcome_email(email):
    """Pirmas, trumpas pasveikinimo laiškas iškart po prenumeratos"""
    subject = "Sveiki! Ačiū, kad prisijungėte prie UROCK naujienų"
    context = {}

    html_message = render_to_string("emails/subscription_welcome_simple.html", context)
    plain_message = render_to_string("emails/subscription_welcome_simple.txt", context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_message,
    )


def send_personalized_email(email):
    """Antras, suasmenintas laiškas po 24 val."""
    subject = "Ačiū, kad prisijungėte prie UROCK prenumeratorių!"
    context = {}

    html_message = render_to_string("emails/subscription_welcome.html", context)
    plain_message = render_to_string("emails/subscription_welcome.txt", context)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        html_message=html_message,
    )


#def schedule_personalized_email(email):
    """Suplanuoja antro laiško siuntimą po 24 val."""
#    schedule(
#        func='newsletter.emails.send_personalized_email',
#        args=[email],
#        next_run=timezone.now() + timedelta(hours=24),
#    )
