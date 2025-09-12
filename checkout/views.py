from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from cart.services import Cart
from catalog.models import Variant
from .forms import CheckoutForm
from .models import Order, OrderItem
import logging

from paysera.utils import parse_callback
from paysera.views import _mark_paid_and_decrease_stock

logger = logging.getLogger(__name__)

FLAT_SHIPPING = Decimal("4.99")


@require_http_methods(["GET", "POST"])
def checkout_view(request):
    cart = Cart(request)
    items = list(cart.items())  # materializuojam

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

    # Pasirinktas apmokėjimo būdas (pagal formą; jei nesi panaudojęs radiobutton – pradiniam MVP naudok "cod")
    payment_method = request.POST.get("payment_method", "cod").strip().lower()
    if payment_method not in ("cod", "paysera"):
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

        # 2) Sukuriam užsakymą su teisingu statusu pagal PM
        initial_status = "cod_placed" if payment_method == "cod" else "paysera_pending"

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

        # 3) Eilutės (be stock mažinimo — darysime tik kai apmokėta)
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

        # 4) Suma
        order.recalc_total()
        order.save(update_fields=["total"])

    # 5) išvalom krepšelį
    request.session.pop("cart", None)
    request.session.modified = True

    # 6) Nukreipimas pagal apmokėjimo būdą
    if payment_method == "paysera":
        # Čia dabar keliausime į tarpinius „Paysera redirect“ view, kuris suformuos nukreipimą į Payserą
        return redirect(reverse("paysera_redirect", kwargs={"order_id": order.id}))
    else:
        messages.success(request, "Užsakymas priimtas! Apmokėsite kurjeriui pristatymo metu.")
        return redirect(reverse("checkout_success", kwargs={"order_id": order.id}))


def checkout_success(request, order_id: int):
    order = get_object_or_404(Order, pk=order_id)

    # --- SS1 fallback: jei grįžtam iš Payseros su ?data=...&sign=... ---
    # Tik 'paysera' užsakymams ir tik jei dar ne 'paid'
    if order.payment_method == "paysera" and order.status in ("paysera_pending", "failed"):
        data, sign = request.GET.get("data"), request.GET.get("sign")
        if data and sign:
            try:
                # Patikrina sign (md5) viduje; meta ValueError, jei blogas
                parsed = parse_callback(request.GET)
            except Exception:
                parsed = None
                logger.exception("SS1 parse failed on success page")

            if parsed and str(parsed.get("orderid")) == str(order.id):
                status    = (parsed.get("status") or "").lower()
                amount_ct = parsed.get("amount", "")
                currency  = (parsed.get("currency") or "").upper()

                if status in ("1", "success"):
                    # (pasirinktinai) tikrinam sumą/valiutą, jei Paysera atsiuntė
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

    ctx = {
        "order": order,

        # SEO
        "meta_title": "Užsakymas priimtas – Urock",
        "meta_description": f"Užsakymas #{order.id} priimtas. Ačiū!",
        "meta_robots": "noindex,follow",
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "checkout/success.html", ctx)
