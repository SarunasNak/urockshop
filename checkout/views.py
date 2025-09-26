# checkout/views.py
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

import stripe

from cart.services import Cart, CART_SESSION_KEY, COUPON_SESSION_KEY
from catalog.models import Variant
from .forms import CheckoutForm
from .models import Order, OrderItem

from paysera.utils import parse_callback
from paysera.views import _mark_paid_and_decrease_stock
from stripe_payments.views import _ensure_pi_for_order

logger = logging.getLogger(__name__)

FLAT_SHIPPING = Decimal("4.99")


@require_http_methods(["GET", "POST"])
def checkout_view(request):
    cart = Cart(request)
    s = cart.summary()             # {items, subtotal, discount, total, coupon_code, coupon_error}
    items = list(s["items"])       # materializuojam

    if request.method == "GET":
        if not items:
            messages.info(request, "Krepšelis tuščias.")
            return redirect("cart:cart_view")

        ctx = {
            "form": CheckoutForm(),
            "items": items,
            "subtotal": s["subtotal"],
            "discount": s["discount"],
            "shipping": FLAT_SHIPPING,
            "total": s["total"] + FLAT_SHIPPING,
            # SEO
            "meta_title": "Apmokėjimas – Urock",
            "meta_description": "Užsakymo apmokėjimo žingsnis.",
            "meta_robots": "noindex,follow",
            "canonical_url": request.build_absolute_uri(request.path),
        }
        return render(request, "checkout/checkout.html", ctx)

    # POST
    form = CheckoutForm(request.POST)
    if not form.is_valid():
        ctx = {
            "form": form,
            "items": items,
            "subtotal": s["subtotal"],
            "discount": s["discount"],
            "shipping": FLAT_SHIPPING,
            "total": s["total"] + FLAT_SHIPPING,
            # SEO
            "meta_title": "Apmokėjimas – Urock",
            "meta_description": "Užsakymo apmokėjimo žingsnis.",
            "meta_robots": "noindex,follow",
            "canonical_url": request.build_absolute_uri(request.path),
        }
        return render(request, "checkout/checkout.html", ctx)

    # Pasirinktas apmokėjimo būdas
    payment_method = request.POST.get("payment_method", "cod").strip().lower()
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

        # 2) Pradinis statusas pagal PM
        initial_status = (
            "cod_placed" if payment_method == "cod"
            else "paysera_pending" if payment_method == "paysera"
            else "pending"   # stripe
        )

        # 3) Užsakymas (įrašom kuponą ir nuolaidą)
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
            coupon_code=(s.get("coupon_code") or ""),
            discount_amount=(s.get("discount") or Decimal("0")),
        )

        # 4) Eilutės (stock mažinsim tik kai apmokėta)
        for line in items:
            v = line.variant
            OrderItem.objects.create(
                order=order,
                variant=v,
                product_name=v.product.name,
                variant_sku=v.sku,
                qty=line.qty,
                price=v.price,
                line_total=(v.price * line.qty),
            )

        # 5) Bendra suma PO kupono + pristatymas
        order.total = s["total"] + FLAT_SHIPPING
        order.save(update_fields=["total"])

    # 6) Krepšelio išvalymas
    if payment_method != "stripe":
        request.session.pop(CART_SESSION_KEY, None)
        request.session.pop(COUPON_SESSION_KEY, None)
        request.session.modified = True

    # 7) Nukreipimas pagal apmokėjimo būdą
    if payment_method == "paysera":
        return redirect(reverse("paysera_redirect", kwargs={"order_id": order.id}))

    if payment_method == "stripe":
        # sugrąžinam tą patį šabloną – FE pradės Stripe apmokėjimą
        ctx = {
            "form": form,
            "items": items,
            "subtotal": s["subtotal"],
            "discount": s["discount"],
            "shipping": FLAT_SHIPPING,
            "total": order.total,
            "order": order,
            # SEO
            "meta_title": "Apmokėjimas – Urock",
            "meta_description": "Užsakymo apmokėjimo žingsnis.",
            "meta_robots": "noindex,follow",
            "canonical_url": request.build_absolute_uri(request.path),
        }
        return render(request, "checkout/checkout.html", ctx)

    # COD
    messages.success(request, "Užsakymas priimtas! Apmokėsite kurjeriui pristatymo metu.")
    return redirect(reverse("checkout_success", kwargs={"order_id": order.id}))


def checkout_success(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)

    # --- SS1 fallback iš Payseros ---
    if order.payment_method == "paysera" and order.status in ("paysera_pending", "failed"):
        data, sign = request.GET.get("data"), request.GET.get("sign")
        if data and sign:
            try:
                parsed = parse_callback(request.GET)
            except Exception:
                parsed = None
                logger.exception("SS1 parse failed on success page")

            if parsed and str(parsed.get("orderid")) == str(order.id):
                status    = (parsed.get("status") or "").lower()
                amount_ct = parsed.get("amount", "")
                currency  = (parsed.get("currency") or "").upper()

                if status in ("1", "success"):
                    try:
                        expected_ct = int((order.total * Decimal("100")).quantize(Decimal("1")))
                    except Exception:
                        expected_ct = None

                    ok_amount = (not amount_ct.isdigit()) or (expected_ct is None) or (int(amount_ct) == expected_ct)
                    ok_curr   = (not currency) or (currency == "EUR")

                    if ok_amount and ok_curr and order.status != "paid":
                        _mark_paid_and_decrease_stock(order)

                elif status in ("0", "failed", "cancelled", "canceled"):
                    if order.status != "paid":
                        order.status = "failed"
                        order.save(update_fields=["status"])
    # --- /SS1 fallback ---

    # --- Stripe fallback (jei webhook dar nepažymėjo) ---
    if order.payment_method == "stripe" and order.status != "paid":
        pi_id = getattr(order, "stripe_pi_id", None)
        if pi_id:
            try:
                stripe.api_key = settings.STRIPE_SECRET_KEY
                pi = stripe.PaymentIntent.retrieve(pi_id)
                pi_status = getattr(pi, "status", "")

                if pi_status == "succeeded" and order.status != "paid":
                    _mark_paid_and_decrease_stock(order)
                elif pi_status in {"requires_payment_method", "canceled"} and order.status != "paid":
                    order.status = "failed"
                    order.save(update_fields=["status"])
            except Exception:
                logger.exception("Stripe fallback poll failed on success page")
    # --- /Stripe fallback ---

    ctx = {
        "order": order,
        # SEO
        "meta_title": "Užsakymas priimtas – Urock",
        "meta_description": f"Užsakymas #{order.id} priimtas. Ačiū!",
        "meta_robots": "noindex,follow",
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "checkout/success.html", ctx)


@require_POST
def checkout_create_order_api(request):
    cart = Cart(request)
    s = cart.summary()
    items = list(s["items"])
    if not items:
        return JsonResponse({"error": "Krepšelis tuščias."}, status=400)

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Patikrinkite formos laukus."}, status=400)

    with transaction.atomic():
        # 1) likučiai
        for line in items:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                return JsonResponse({"error": f"Likutis nepakankamas: {v.product.name} {v.color} {v.size}."}, status=400)

        # 2) orderis (Stripe flow)
        order = Order.objects.create(
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            email=form.cleaned_data["email"],
            address=form.cleaned_data["address"],
            city=form.cleaned_data["city"],
            postal_code=form.cleaned_data["postal_code"],
            shipping_cost=FLAT_SHIPPING,
            payment_method="stripe",
            status="pending",
            coupon_code=(s.get("coupon_code") or ""),
            discount_amount=(s.get("discount") or Decimal("0")),
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

        order.total = s["total"] + FLAT_SHIPPING
        order.save(update_fields=["total"])

    client_secret = _ensure_pi_for_order(order)
    return JsonResponse({"order_id": order.id, "clientSecret": client_secret})
