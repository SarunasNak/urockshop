# paysera/views.py
from decimal import Decimal
import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from catalog.models import Variant
from checkout.models import Order
from .utils import make_payment_data, parse_callback, PAYMENT_URL

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def paysera_redirect(request, order_id: int):
    """
    SS1: suformuojam Paysera data+sign ir pateikiam auto-submit formą.
    Leidžiam 'retry' atvejį, jei buvo 'failed'.
    """
    order = get_object_or_404(Order, pk=order_id)

    # Jei ne Paysera – nieko nebedarom, grąžinam į success
    if order.payment_method != "paysera":
        return redirect(reverse("checkout_success", kwargs={"order_id": order.id}))

    # Jei buvo nepavykęs bandymas – leiskime bandyti iš naujo
    if order.status == "failed":
        order.status = "paysera_pending"
        order.save(update_fields=["status"])

    # Jei jau apmokėtas ar kitoks statusas nei pending – grąžinam į success
    if order.status != "paysera_pending":
        return redirect(reverse("checkout_success", kwargs={"order_id": order.id}))

    # Suma centais (EUR -> ct)
    total_cents = int((order.total * Decimal("100")).quantize(Decimal("1")))

    # Absoliutūs URL'ai, kuriuos Paysera naudos grąžinimams
    accept_url   = f"{settings.SITE_SCHEME}://{settings.SITE_HOST}{reverse('checkout_success', kwargs={'order_id': order.id})}"
    cancel_url   = f"{settings.SITE_SCHEME}://{settings.SITE_HOST}{reverse('paysera_cancel',   kwargs={'order_id': order.id})}"
    callback_url = f"{settings.SITE_SCHEME}://{settings.SITE_HOST}{reverse('paysera_callback')}"

    # Parametrai pagal Paysera specifikaciją
    params = {
        "projectid": settings.PAYSERA_PROJECT_ID,
        "orderid": str(order.id),
        "amount": str(total_cents),
        "currency": "EUR",
        "accepturl": accept_url,
        "cancelurl": cancel_url,
        "callbackurl": callback_url,
        "version": "1.6",               # ← PRIDĖTA (privaloma pagal spec)
        "test": "1" if settings.PAYSERA_TEST_MODE else "0",
        # nebūtina, bet gali būti patogu
        "lang": "LIT",                  # ← pasirinktina (LIT/RUS/ENG...)
        "p_firstname": order.first_name,
        "p_lastname": order.last_name,
        "p_email": order.email,
    }

    payload = make_payment_data(params)

    # Pateikiam auto-submit formą į Paysera
    return render(request, "paysera/auto_post.html", {
        "payment_url": PAYMENT_URL,
        "payload": payload,
    })


@require_http_methods(["GET"])
def paysera_cancel(request, order_id: int):
    """
    Vartotojas grįžo per cancelurl – statuso nekeičiam (lieka pending/failed).
    Leidžiam klientui bandyti apmokėti dar kartą iš success puslapio.
    """
    order = get_object_or_404(Order, pk=order_id)
    return redirect(reverse("checkout_success", kwargs={"order_id": order.id}))


@csrf_exempt
def paysera_callback(request):
    # --- tik derinimui: patikrinti pasiekiamumą ---
    if settings.DEBUG and request.method == "GET" and request.GET.get("ping") == "1":
        return render(request, "paysera/plain.txt", {"text": "OK"}, content_type="text/plain")
    # ----------------------------------------------

    if request.method != "POST":
        return render(request, "paysera/plain.txt", {"text": "ERROR"}, content_type="text/plain")

    try:
        parsed = parse_callback(request.POST)  # patikrina sign
    except Exception:
        logger.exception("Paysera callback: sign/parse error")
        return render(request, "paysera/plain.txt", {"text": "ERROR"}, content_type="text/plain")

    order_id = int(parsed.get("orderid", "0") or "0")
    status   = (parsed.get("status", "") or "").lower()
    amount_ct = parsed.get("amount", "")
    currency  = (parsed.get("currency", "") or "").upper()

    order = get_object_or_404(Order, pk=order_id)

    if order.payment_method != "paysera":
        return render(request, "paysera/plain.txt", {"text": "OK"}, content_type="text/plain")
    if order.status == "paid":
        return render(request, "paysera/plain.txt", {"text": "OK"}, content_type="text/plain")

    success = status in ("1", "success")

    # (pasirinktinai) sutikrinti sumą/valiutą
    try:
        expected_ct = int((order.total * Decimal("100")).quantize(Decimal("1")))
    except Exception:
        expected_ct = None
    if success and ((currency and currency != "EUR") or (amount_ct.isdigit() and expected_ct is not None and int(amount_ct) != expected_ct)):
        success = False

    if not success:
        order.status = "failed"
        order.save(update_fields=["status"])
        logger.warning("Paysera FAIL: order=%s status=%s", order.id, status)
        return render(request, "paysera/plain.txt", {"text": "OK"}, content_type="text/plain")

    # Sekmes kelias – sutvarkom per helperį
    _mark_paid_and_decrease_stock(order)

    logger.info("Paysera OK: order=%s status=%s", order.id, status)
    return render(request, "paysera/plain.txt", {"text": "OK"}, content_type="text/plain")

def _mark_paid_and_decrease_stock(order):
    with transaction.atomic():
        for item in order.items.select_related("variant").select_for_update():
            v: Variant = item.variant
            v.stock = max(0, v.stock - item.qty)
            v.save(update_fields=["stock"])
        order.status = "paid"
        order.save(update_fields=["status"])

