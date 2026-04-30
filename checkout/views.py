from decimal import Decimal, ROUND_HALF_UP
import logging
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, Http404, HttpResponse
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.http import url_has_allowed_host_and_scheme

import stripe

from cart.services import Cart
from catalog.models import Variant
from .forms import CheckoutForm
from .models import Order, OrderItem

from paysera.utils import parse_callback
from checkout.utils import mark_paid_and_decrease_stock
from .services import get_all_dpd_points
from newsletter.models import Subscriber
from checkout.emails import send_order_emails


logger = logging.getLogger(__name__)

FLAT_SHIPPING = Decimal("0.00")
stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)


def build_success_url(request, order):
    return request.build_absolute_uri(
        reverse("checkout:checkout_success", kwargs={"order_id": order.id})
    )


def build_cancel_url(request):
    try:
        return request.build_absolute_uri(reverse("cart:cart_view"))
    except Exception:
        return request.build_absolute_uri("/")


def _finalize_stripe_if_paid(order, session_id: str) -> None:
    if not session_id:
        return
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.retrieve(session_id, expand=["payment_intent"])
        payment_status = getattr(session, "payment_status", "")
        if payment_status == "paid" and order.status != "paid":
            mark_paid_and_decrease_stock(order)
        elif payment_status == "unpaid" and order.status != "paid":
            order.status = "failed"
            order.save(update_fields=["status"])
    except Exception:
        logger.exception("Stripe success finalize failed (session_id=%s)", session_id)


@require_POST
def checkout_view(request):
    cart = Cart(request)
    items = list(cart.items())
    if not items:
        messages.info(request, "Krepšelis tuščias.")
        return redirect("cart:cart_view")

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        context = {"form": form, "cart": cart, "items": items}
        return render(request, "cart/view.html", context, status=400)

    cd = form.cleaned_data
    payment_method = cd["payment_method"].lower()
    shipping_method = cd["shipping_method"]

    with transaction.atomic():
        for line in items:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                form.add_error(None, f"Prekei „{v.product.name} {v.color} {v.size}“ trūksta likučio.")
                context = {"form": form, "cart": cart, "items": items}
                return render(request, "cart/view.html", context, status=400)

        if payment_method == "cod":
            initial_status = "cod_placed"
        elif payment_method == "paysera":
            initial_status = "paysera_pending"
        else:
            initial_status = "pending"

        order = Order.objects.create(
            first_name=cd["first_name"],
            last_name=cd["last_name"],
            email=cd["email"],
            phone=cd.get("phone", ""),
            address=cd["address"],
            city=cd["city"],
            postal_code=cd["postal_code"],
            shipping_cost=FLAT_SHIPPING,
            shipping_method=shipping_method,
            dpd_pickup_id=cd.get("dpd_pickup_id") or None,
            dpd_pickup_name=cd.get("dpd_pickup_name") or "",
            dpd_pickup_addr=cd.get("dpd_pickup_addr") or "",
            payment_method=payment_method,
            status=initial_status,
            needs_invoice=bool(cd.get("needs_invoice")),
            company_name=cd.get("company_name", "") or "",
            company_code=cd.get("company_code", "") or "",
        )
        # Newsletter opt-in (jei pažymėta)
        transaction.on_commit(
            lambda email=cd.get("email"),
                   o=order,
                   opted=bool(cd.get("marketing_consent")):
                _subscribe_if_opted_in(email, o, opted)
        )

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

        order.recalc_total()
        order.save(update_fields=[
            "total", "shipping_method", "dpd_pickup_id",
            "dpd_pickup_name", "dpd_pickup_addr"
        ])

    request.session.pop("cart", None)
    request.session.modified = True

    if payment_method == "paysera":
        return redirect(reverse("paysera:paysera_redirect", kwargs={"order_id": order.id}))

    if payment_method == "stripe":
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
            logger.exception("Stripe Checkout session create failed: %s", e)
            messages.error(request, f"Nepavyko inicijuoti Stripe apmokėjimo: {e}")
            return redirect("cart:cart_view")

    messages.success(request, "Užsakymas priimtas! Apmokėsite kurjeriui pristatymo metu.")
    return redirect(reverse("checkout:checkout_success", kwargs={"order_id": order.id}))

@require_POST
def checkout_create_order_api(request):
    cart = Cart(request)
    lines = list(cart.items())
    if not lines:
        messages.error(request, "Krepšelis tuščias.")
        return redirect("cart:cart_view")

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        errors = form.errors
        logger.warning(f"Checkout form validation failed: {errors}")
        cart = Cart(request)
        items = list(cart.items())
        context = {"form": form, "cart": cart, "items": items}
        return render(request, "cart/view.html", context, status=400)

    cd = form.cleaned_data
    payment_method_lower = cd["payment_method"].lower()

    with transaction.atomic():
        for line in lines:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                messages.error(request, f"Likutis nepakankamas: {v.product.name} {v.color} {v.size}.")
                return redirect("cart:cart_view")

        if payment_method_lower == "cod":
            initial_status = "cod_placed"
        elif payment_method_lower == "paysera":
            initial_status = "paysera_pending"
        else:
            initial_status = "pending"

        order = Order.objects.create(
            first_name=cd["first_name"],
            last_name=cd["last_name"],
            email=cd["email"],
            phone=cd.get("phone", ""),
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
            needs_invoice=bool(cd.get("needs_invoice")),
            company_name=cd.get("company_name", "") or "",
            company_code=cd.get("company_code", "") or "",
        )

        # Newsletter opt-in (jei pažymėta)
        transaction.on_commit(
            lambda email=cd.get("email"),
                   o=order,
                   opted=bool(cd.get("marketing_consent")):
                _subscribe_if_opted_in(email, o, opted)
        )

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

        order.recalc_total()
        order.save(update_fields=[
            "total", "shipping_method", "dpd_pickup_id",
            "dpd_pickup_name", "dpd_pickup_addr"
        ])

    request.session.pop("cart", None)
    request.session.modified = True

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

    return redirect("checkout:checkout_success", order_id=order.id)

@require_GET
def dpd_points(request):
    return JsonResponse(get_all_dpd_points(), safe=False)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", None)

    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not set")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
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
    except Exception:
        logger.exception("Webhook handler failed")

    return HttpResponse(status=200)

def checkout_success(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)

    if order.payment_method == "paysera" and order.status in ("paysera_pending", "failed"):
        data, sign = request.GET.get("data"), request.GET.get("sign")
        if data and sign:
            try:
                parsed = parse_callback(request.GET)
            except Exception:
                parsed = None
                logger.exception("SS1 parse failed on success page")

            if parsed and str(parsed.get("orderid")) == str(order.id):
                status = (parsed.get("status") or "").lower()
                amount_ct = parsed.get("amount", "")
                currency = (parsed.get("currency") or "").upper()

                if status in ("1", "success"):
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

    if order.payment_method == "stripe" and order.status != "paid":
        session_id = request.GET.get("session_id") or getattr(order, "stripe_session_id", None)
        _finalize_stripe_if_paid(order, session_id)

    # --- NAUJA: jei jau apmokėtas, išsiųsti laiškus (1 kartą) ---
    if order.status == "paid":
        cache_key = f"order-mails-sent:{order.pk}"
        if not cache.get(cache_key):
            try:
                send_order_emails(order)               # klientui + adminui
            except Exception:
                # nekertam success puslapio, tik loguojam
                logger.exception("Failed to send order emails (order #%s)", order.pk)
            else:
                cache.set(cache_key, 1, 60 * 60 * 24)  # 24 h – anti-dup

    return_url = request.session.pop("return_url", None)

    if return_url and url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}):
        safe_return_url = return_url
    else:
        safe_return_url = None

    ctx = {
        "order": order,
        "meta_title": "Užsakymas priimtas – Urock",
        "meta_description": f"Užsakymas #{order.id} priimtas. Ačiū!",
        "meta_robots": "noindex,follow",
        "canonical_url": request.build_absolute_uri(request.path),
        "return_url": safe_return_url,  # 👈 NAUJA
    }

    return render(request, "checkout/success.html", ctx)

# views.py
def _subscribe_if_opted_in(email: str, order, opt_in: bool) -> None:
    """
    Jei opt_in=True – sukuria/atnaujina Subscriber iš ORDER duomenų:
    email, phone (jei yra), source='order', (nebūtina) sizes.
    """
    if not opt_in or not email:
        return
    try:
        email = email.strip().lower()

        # ką paduodam kuriant naują
        defaults = {"is_active": True}
        # NUSTATOM SOURCE 'order' kuriant
        if hasattr(Subscriber, "source"):
            defaults["source"] = "order"
        if hasattr(Subscriber, "phone") and getattr(order, "phone", None):
            defaults["phone"] = order.phone

        sub, created = Subscriber.objects.get_or_create(email=email, defaults=defaults)

        updates = []

        # atnaujinam phone, jei atėjo iš orderio ir pasikeitė
        if hasattr(sub, "phone") and getattr(order, "phone", None) and sub.phone != order.phone:
            sub.phone = order.phone
            updates.append("phone")

        # priverstinai laikom source='order' (jei koks senas buvo 'footer' ir pan.)
        if hasattr(sub, "source") and sub.source != "order":
            sub.source = "order"
            updates.append("source")

        # (nebūtina) jei turit 'sizes'
        if hasattr(sub, "sizes"):
            sizes = set()
            try:
                items_qs = getattr(order, "items", None) or order.orderitem_set
                for it in items_qs.all():
                    v = getattr(it, "variant", None)
                    sv = getattr(v, "size_display", None) or getattr(v, "size", None)
                    if sv:
                        sizes.add(str(sv))
            except Exception:
                pass
            if sizes:
                sub.sizes = ",".join(sorted(sizes))
                updates.append("sizes")

        if updates:
            sub.save(update_fields=updates)
    except Exception:
        logger.exception("Subscriber opt-in failed (email=%s, order_id=%s)", email, getattr(order, "id", None))


