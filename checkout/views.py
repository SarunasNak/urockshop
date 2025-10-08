# checkout/views.py
from decimal import Decimal
import logging
from types import SimpleNamespace

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

import stripe

from cart.services import Cart
from catalog.models import Variant
from .forms import CheckoutForm
from .models import Order, OrderItem

from stripe_payments.views import _ensure_pi_for_order
from paysera.utils import parse_callback
from paysera.views import _mark_paid_and_decrease_stock

logger = logging.getLogger(__name__)

FLAT_SHIPPING = Decimal("4.99")


@require_http_methods(["GET", "POST"])
def checkout_view(request):
    cart = Cart(request)
    items = list(cart.items())            # materializuojam
    subtotal_before = cart.total          # fiksuojam prieš galimą krepšelio išvalymą

    if request.method == "GET":
        if not items:
            messages.info(request, "Krepšelis tuščias.")
            return redirect("cart_view")

        form = CheckoutForm()
        ctx = {
            "form": form,
            "items": items,
            "subtotal": cart.total,
            "shipping": FLAT_SHIPPING,
            "total": cart.total + FLAT_SHIPPING,

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
            "subtotal": cart.total,
            "shipping": FLAT_SHIPPING,
            "total": cart.total + FLAT_SHIPPING,

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
                return redirect("cart_view")

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

        # 3) eilučių kūrimas (stock mažinsime tik kai apmokėta)
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

        # 4) suma
        order.recalc_total()
        order.save(update_fields=["total"])

    # 5) išvalom krepšelį (visais atvejais)
    request.session.pop("cart", None)
    request.session.modified = True

    # 6) nukreipimas pagal apmokėjimo būdą
    if payment_method == "paysera":
        return redirect(reverse("paysera_redirect", kwargs={"order_id": order.id}))

    if payment_method == "stripe":
        # Grąžinam tą patį checkout šabloną su 'order' – FE atliks Stripe apmokėjimą
        ctx = {
            "form": form,
            "items": items,
            "subtotal": subtotal_before,   # <<< naudok fiksuotą sumą, nes krepšelis jau išvalytas
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
                        _mark_paid_and_decrease_stock(order)

                elif status in ("0", "failed", "cancelled", "canceled"):
                    if order.status != "paid":
                        order.status = "failed"
                        order.save(update_fields=["status"])
    # --- /Paysera fallback ---

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
                # 'processing' ir pan. – paliekame 'pending'
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
    lines = list(cart.items())  # viena materializacija
    if not lines:
        return JsonResponse({"error": "Krepšelis tuščias."}, status=400)

    form = CheckoutForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "Patikrinkite formos laukus."}, status=400)

    with transaction.atomic():
        # 1) likučiai
        for line in lines:
            v = Variant.objects.select_for_update().get(pk=line.variant.pk)
            if line.qty > v.stock:
                return JsonResponse(
                    {"error": f"Likutis nepakankamas: {v.product.name} {v.color} {v.size}."},
                    status=400,
                )

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
        order.save(update_fields=["total"])

    # 3) suformuojam PaymentIntent ir gaunam clientSecret
    client_secret = _ensure_pi_for_order(order)

    # (pasirinktinai) krepšelį išvalyk po sėkmės FE pusėje
    return JsonResponse({"order_id": order.id, "clientSecret": client_secret})


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
