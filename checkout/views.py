# checkout/views.py
from decimal import Decimal, ROUND_HALF_UP
import logging
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt

import stripe

from cart.services import Cart
from catalog.models import Variant
from .forms import CheckoutForm
from .models import Order, OrderItem

# Palikta, jei kur nors naudojate PI srautui
from stripe_payments.views import _ensure_pi_for_order  # noqa: F401
from paysera.utils import parse_callback
from checkout.utils import mark_paid_and_decrease_stock

# DPD helperiai
from .services import get_all_dpd_points

logger = logging.getLogger(__name__)

# Siuntimas visada 0 €
FLAT_SHIPPING = Decimal("0.00")

# Stripe raktas
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)


def build_success_url(request, order):
    # Pridedame {CHECKOUT_SESSION_ID}, kad success puslapis galėtų patikimai „užbaigti“
    return request.build_absolute_uri(
        reverse("checkout:checkout_success", kwargs={"order_id": order.id})
    )


def build_cancel_url(request):
    # grįžimo adresas, jei pirkėjas nutraukia apmokėjimą
    try:
        return request.build_absolute_uri(reverse("cart:cart_view"))
    except Exception:
        return request.build_absolute_uri("/")


def _finalize_stripe_if_paid(order, session_id: str) -> None:
    """Pagal Stripe Checkout Session būseną pažymi užsakymą kaip apmokėtą arba nepavykusį."""
    if not session_id:
        return
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        # Expandinam PI jei reikėtų papildomos info ateityje
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        payment_status = getattr(session, "payment_status", "")
        if payment_status == "paid" and order.status != "paid":
            mark_paid_and_decrease_stock(order)
        elif payment_status == "unpaid" and order.status != "paid":
            order.status = "failed"
            order.save(update_fields=["status"])
        # "no_payment_required" – jei naudosite vėliau, čia galima tvarkyti kitaip
    except Exception:
        logger.exception("Stripe success finalize failed (session_id=%s)", session_id)


# === PAGRINDINIS: tik POST (UI – iš cart/view.html) ===
@require_POST
def checkout_view(request):
    cart = Cart(request)
    items = list(cart.items())
    if not items:
        messages.info(request, "Krepšelis tuščias.")
        return redirect("cart:cart_view")

    # Tik POST – jokio checkout.html renderinimo
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect("cart:cart_view")

    # Pasirinktas apmokėjimo būdas
    payment_method = (request.POST.get("payment_method") or "cod").strip().lower()
    if payment_method not in ("cod", "paysera", "stripe"):
        payment_method = "cod"

    with transaction.atomic():
        # 1) atsargų patikra (be mažinimo)
        for line in items:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                messages.error(
                    request,
                    f"Prekei „{v.product.name} {v.color} {v.size}“ trūksta likučio."
                )
                return redirect("cart:cart_view")

        # 2) užsakymo būsena pagal PM
        if payment_method == "cod":
            initial_status = "cod_placed"
        elif payment_method == "paysera":
            initial_status = "paysera_pending"
        else:  # stripe
            initial_status = "pending"

        order = Order.objects.create(
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            address=form.cleaned_data["address"],
            city=form.cleaned_data["city"],
            postal_code=form.cleaned_data["postal_code"],
            shipping_cost=FLAT_SHIPPING,
            payment_method=payment_method,
            status=initial_status,
        )

        # 3) pristatymo pasirinkimas iš FE ('delivery': kurjeris|pastomatas)
        delivery = (request.POST.get("delivery") or "").strip().lower()
        if delivery == "pastomatas":
            order.shipping_method = "dpd_pickup"

            pick_id   = (request.POST.get("dpd_pickup_id") or "").strip()
            pick_name = (request.POST.get("dpd_pickup_name") or "").strip()
            pick_addr = (request.POST.get("dpd_pickup_addr") or "").strip()

            if not pick_id:
                messages.error(request, "Pasirinkite DPD paštomatą.")
                order.delete()  # neliktų tuščio orderio
                return redirect("cart:cart_view")

            order.dpd_pickup_id   = pick_id
            order.dpd_pickup_name = pick_name
            order.dpd_pickup_addr = pick_addr
        else:
            order.shipping_method = "dpd_courier"

        # 4) eilučių kūrimas (stock mažinsime tik kai apmokėta)
        for line in items:
            v = line.variant
            OrderItem.objects.create(
                order=order,
                variant=v,
                product_name=v.product.name,
                variant_sku=v.sku,
                qty=line.qty,
                price=v.price,
                line_total=v.price * line.qty,
            )

        # 5) suma
        order.recalc_total()
        order.save(update_fields=[
            "total",
            "shipping_method", "dpd_pickup_id", "dpd_pickup_name", "dpd_pickup_addr"
        ])

    # 6) išvalom krepšelį (visais atvejais)
    request.session.pop("cart", None)
    request.session.modified = True

    # 7) nukreipimas pagal apmokėjimo būdą
    if payment_method == "paysera":
        return redirect(reverse("paysera:paysera_redirect", kwargs={"order_id": order.id}))

    if payment_method == "stripe":
        # Stripe Checkout (hosted)
        try:
            # Pridedame session_id vietą success URL'e
            success_url = (
                build_success_url(request, order)
                + "?paid=stripe&session_id={CHECKOUT_SESSION_ID}"
            )
            cancel_url = build_cancel_url(request)

            line_items = []
            for it in OrderItem.objects.filter(order=order):
                # centai su saugiu apvalinimu
                unit_amount = int((Decimal(it.price) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                # Stripe riboja pavadinimo ilgį
                name = (it.product_name or f"Item {it.id}")[:120]
                qty = int(it.qty or 1)
                line_items.append({
                    "price_data": {
                        "currency": getattr(settings, "STRIPE_CURRENCY", "eur"),
                        "product_data": {"name": name},
                        "unit_amount": unit_amount,
                    },
                    "quantity": qty,
                })

            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=order.email,
                locale="lt",
                metadata={"order_id": str(order.id)},
            )

            # Išsaugome session id jei toks laukas yra (nekeičiant modelio)
            if hasattr(order, "stripe_session_id"):
                order.stripe_session_id = session.id
                order.save(update_fields=["stripe_session_id"])

            return redirect(session.url)
        except Exception as e:
            logger.exception("Stripe Checkout session create failed: %s", e)
            messages.error(request, f"Nepavyko inicijuoti Stripe apmokėjimo: {e}")
            return redirect("cart:cart_view")

    # COD
    messages.success(request, "Užsakymas priimtas! Apmokėsite kurjeriui pristatymo metu.")
    return redirect(reverse("checkout:checkout_success", kwargs={"order_id": order.id}))


def checkout_success(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)

    # --- Paysera SS1 fallback ---
    if order.payment_method == "paysera" and order.status in ("paysera_pending", "failed"):
        data, sign = request.GET.get("data"), request.GET.get("sign")
        if data and sign:
            try:
                parsed = parse_callback(request.GET)  # meta ValueError, jei blogas sign
            except Exception:
                parsed = None
                logger.exception("SS1 parse failed on success page")

            if parsed and str(parsed.get("orderid")) == str(order.id):
                status = (parsed.get("status") or "").lower()
                amount_ct = parsed.get("amount", "")
                currency = (parsed.get("currency") or "").upper()

                if status in ("1", "success"):
                    # (pasirinktinai) patikrinam sumą/valiutą
                    try:
                        expected_ct = int((order.total * Decimal("100")).quantize(Decimal("1")))
                    except Exception:
                        expected_ct = None

                    ok_amount = (not amount_ct.isdigit()) or (expected_ct is None) or (int(amount_ct) == expected_ct)
                    ok_curr = (not currency) or (currency == "EUR")

                    if ok_amount and ok_curr and order.status != "paid":
                        mark_paid_and_decrease_stock(order)

                elif status in ("0", "failed", "cancelled", "canceled"):
                    if order.status != "paid":
                        order.status = "failed"
                        order.save(update_fields=["status"])
    # --- /Paysera fallback ---

    # --- Stripe finalize per Checkout Session ---
    if order.payment_method == "stripe" and order.status != "paid":
        # Iš URL arba iš orderio, jei laukas egzistuoja
        session_id = request.GET.get("session_id") or getattr(order, "stripe_session_id", None)
        _finalize_stripe_if_paid(order, session_id)
    # --- /Stripe finalize ---

    ctx = {
        "order": order,

        # SEO
        "meta_title": "Užsakymas priimtas – Urock",
        "meta_description": f"Užsakymas #{order.id} priimtas. Ačiū!",
        "meta_robots": "noindex,follow",
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "checkout/success.html", ctx)


# === NAUJAS: PRG API (palikta, jei ateityje prireiks) ===
@require_POST
def checkout_create_order_api(request):
    cart = Cart(request)
    lines = list(cart.items())
    if not lines:
        messages.error(request, "Krepšelis tuščias.")
        return redirect("cart:cart_view")

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        messages.error(request, form.errors.as_text())
        return redirect("cart:cart_view")

    cd = form.cleaned_data
    payment_method_lower = cd["payment_method"].lower()  # 'cod' | 'paysera' | 'stripe'

    with transaction.atomic():
        # 1) likučiai (lock)
        for line in lines:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                messages.error(request, f"Likutis nepakankamas: {v.product.name} {v.color} {v.size}.")
                return redirect("cart:cart_view")

        # 2) pradinė būsena
        if payment_method_lower == "cod":
            initial_status = "cod_placed"
        elif payment_method_lower == "paysera":
            initial_status = "paysera_pending"
        else:
            initial_status = "pending"

        # 3) orderis
        order = Order.objects.create(
            first_name=cd["first_name"],
            last_name=cd["last_name"],
            email=cd["email"],
            address=cd["address"],
            city=cd["city"],
            postal_code=cd["postal_code"],
            shipping_cost=FLAT_SHIPPING,
            payment_method=payment_method_lower,
            status=initial_status,
            shipping_method=cd["shipping_method"],
            dpd_pickup_id=cd.get("dpd_pickup_id") or None,
            dpd_pickup_name=cd.get("dpd_pickup_name") or "",
            dpd_pickup_addr=cd.get("dpd_pickup_addr") or "",
        )

        # 4) eilutės
        for line in lines:
            v = line.variant
            OrderItem.objects.create(
                order=order,
                variant=v,
                product_name=v.product.name,
                variant_sku=v.sku,
                qty=line.qty,
                price=v.price,
                line_total=v.price * line.qty,
            )

        # 5) suma
        order.recalc_total()
        order.save(update_fields=[
            "total", "shipping_method", "dpd_pickup_id", "dpd_pickup_name", "dpd_pickup_addr"
        ])

    # 6) tuštinam krepšelį
    request.session.pop("cart", None)
    request.session.modified = True

    # 7) redirect pagal apmokėjimą
    if payment_method_lower == "cod":
        messages.success(request, "Užsakymas priimtas. Mokėsite atsiimdami.")
        return redirect("checkout:checkout_success", order_id=order.id)

    if payment_method_lower == "paysera":
        try:
            return redirect(reverse("paysera:paysera_redirect", kwargs={"order_id": order.id}))
        except Exception:
            messages.error(request, "Paysera redirect nėra sukonfigūruotas.")
            return redirect("cart:cart_view")

    if payment_method_lower == "stripe":
        try:
            success_url = (
                build_success_url(request, order)
                + "?paid=stripe&session_id={CHECKOUT_SESSION_ID}"
            )
            cancel_url = build_cancel_url(request)
            line_items = []
            for it in OrderItem.objects.filter(order=order):
                unit_amount = int((Decimal(it.price) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                name = (it.product_name or f"Item {it.id}")[:120]
                qty = int(it.qty or 1)
                line_items.append({
                    "price_data": {
                        "currency": getattr(settings, "STRIPE_CURRENCY", "eur"),
                        "product_data": {"name": name},
                        "unit_amount": unit_amount,
                    },
                    "quantity": qty,
                })
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=order.email,
                locale="lt",
                metadata={"order_id": str(order.id)},
            )
            if hasattr(order, "stripe_session_id"):
                order.stripe_session_id = session.id
                order.save(update_fields=["stripe_session_id"])
            return redirect(session.url)
        except Exception as e:
            logger.exception("Stripe Checkout session create failed (API): %s", e)
            messages.error(request, f"Nepavyko inicijuoti Stripe apmokėjimo: {e}")
            return redirect("cart:cart_view")

    # Fallback
    return redirect("checkout:checkout_success", order_id=order.id)


def success_preview(request):
    # Veikia tik DEBUG režime arba staff vartotojams
    if not settings.DEBUG and not (request.user.is_authenticated and request.user.is_staff):
        raise Http404()

    method = request.GET.get("method", "cod")      # cod | stripe | paysera
    status = request.GET.get("status", "paid")     # paid | pending | paysera_pending | failed
    email = request.GET.get("email", "demo@urock.lt")
    oid = int(request.GET.get("id", "123456"))

    # Minimalus "order" objektas šablonui
    order = SimpleNamespace(
        id=oid,
        email=email,
        payment_method=method,
        status=status,
    )

    return render(request, "checkout/success.html", {"order": order})


# ---------- JSON endpointas FE modalui ----------
@require_GET
def dpd_points(request):
    """Grąžina visus LT DPD paštomatus JSON formatu FE modalui."""
    return JsonResponse(get_all_dpd_points(), safe=False)


# ---------- STRIPE WEBHOOK ----------
@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Minimalus Stripe webhook, kuris pažymi užsakymą kaip apmokėtą,
    kai gaunamas 'checkout.session.completed'.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    if not endpoint_secret:
        # Jei secret nėra – geriau aiškiai log'inti, bet vis tiek gražinti 400
        logger.error("STRIPE_WEBHOOK_SECRET not set")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return HttpResponse(status=400)

    try:
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = (session.get("metadata") or {}).get("order_id")
            if order_id:
                try:
                    order = Order.objects.get(pk=order_id)
                except Order.DoesNotExist:
                    order = None
                if order and session.get("payment_status") == "paid" and order.status != "paid":
                    mark_paid_and_decrease_stock(order)
        # Pagal poreikį galima pridėti ir kitų event'ų (payment_intent.succeeded ir pan.)
    except Exception:
        logger.exception("Webhook handler failed")

    return HttpResponse(status=200)
