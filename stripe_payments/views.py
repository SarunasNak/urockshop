# stripe_payments/views.py
from decimal import Decimal, ROUND_HALF_UP
import logging
import json

import stripe
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from checkout.models import Order
from paysera.views import _mark_paid_and_decrease_stock

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


def _amount_cents(order: Order) -> int:
    return int((Decimal(order.total) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _ensure_pi_for_order(order: Order) -> str:
    """Sukuria arba pernaudoja PaymentIntent. Leidžiam tik CARD."""
    amount = _amount_cents(order)

    # Jei turime esamą PI – pabandom pernaudoti
    if getattr(order, "stripe_pi_id", None):
        try:
            pi = stripe.PaymentIntent.retrieve(order.stripe_pi_id)

            # Užtikrinam, kad leidžiamas tik "card"
            if "card" not in (pi.payment_method_types or []):
                try:
                    stripe.PaymentIntent.modify(pi.id, payment_method_types=["card"])
                except stripe.error.InvalidRequestError:
                    pass

            # Jei PI dar gali būti naudojamas – grąžinam client_secret (jei reikia, pataisom sumą)
            if pi.status in {"requires_payment_method", "requires_confirmation", "requires_action", "processing"}:
                if pi.amount != amount and pi.status in {"requires_payment_method", "requires_confirmation"}:
                    try:
                        pi = stripe.PaymentIntent.modify(pi.id, amount=amount)
                    except stripe.error.InvalidRequestError:
                        pass
                return pi.client_secret
        except stripe.error.InvalidRequestError:
            # jeigu PI neberandamas – kursim naują
            pass

    # Kuriam naują PI – TIK kortelė
    pi = stripe.PaymentIntent.create(
        amount=amount,
        currency=getattr(settings, "STRIPE_CURRENCY", "eur"),
        payment_method_types=["card"],  # be Link ir t. t.
        metadata={"order_id": str(order.id), "email": order.email or ""},
        description=f"Order #{order.id} – urock.lt",
    )

    if hasattr(order, "stripe_pi_id") and order.stripe_pi_id != pi.id:
        order.stripe_pi_id = pi.id
        order.save(update_fields=["stripe_pi_id"])

    return pi.client_secret


@require_POST
def stripe_create_intent(request, order_id: int):
    try:
        order = get_object_or_404(Order, pk=order_id)
        if getattr(order, "payment_method", "") == "stripe" and order.status != "paid":
            if order.status != "pending":
                order.status = "pending"
                order.save(update_fields=["status"])

        client_secret = _ensure_pi_for_order(order)
        return JsonResponse({"clientSecret": client_secret})
    except Exception:
        logger.exception("stripe_create_intent failed")
        return JsonResponse({"error": "Nepavyko sukurti PaymentIntent."}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Stripe siųs RAW body + 'Stripe-Signature' header.
    Čia griežtai verifikuojam parašą ir loguojam, kad būtų lengva debuginti.
    """
    payload = request.body.decode("utf-8")
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    logger.info("Stripe webhook hit. Sig present: %s", bool(sig_header))

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,  # paduodam stringą
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        # Netinkamas JSON/payload (labai retai)
        logger.exception("Stripe webhook: invalid payload")
        return HttpResponse("invalid payload", status=400)
    except stripe.error.SignatureVerificationError:
        # Dažniausia priežastis – NETEISINGAS WHSEC secret
        logger.exception(
            "Stripe webhook: signature verification FAILED. "
            "Check STRIPE_WEBHOOK_SECRET and that it matches the Workbench endpoint secret."
        )
        return HttpResponse("invalid signature", status=400)
    except Exception:
        logger.exception("Stripe webhook: unexpected error while constructing event")
        return HttpResponse("error", status=400)

    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    # Surandam užsakymą iš metadata.order_id arba iš PI id (fallback)
    order = None
    meta = obj.get("metadata") or {}
    order_id = meta.get("order_id")
    if order_id:
        order = Order.objects.filter(pk=order_id).first()
    if order is None:
        pi_id = obj.get("id")
        if pi_id:
            order = Order.objects.filter(stripe_pi_id=pi_id).first()

    logger.info("Stripe webhook OK. type=%s order_id=%s pi=%s", etype, order_id, obj.get("id"))

    if etype == "payment_intent.succeeded" and order:
        if order.status != "paid":
            _mark_paid_and_decrease_stock(order)
        return HttpResponse(status=200)

    if etype == "payment_intent.payment_failed" and order:
        if order.status != "paid":
            order.status = "failed"
            order.save(update_fields=["status"])
        return HttpResponse(status=200)

    # kitus eventus laikom OK, kad Stripe jų nebebandytų resend'inti
    return HttpResponse(status=200)
