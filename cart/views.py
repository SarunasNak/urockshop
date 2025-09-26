# cart/views.py
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.models import Variant
from .services import Cart


def cart_view(request):
    cart = Cart(request)
    s = cart.summary()  # {items, subtotal, discount, total, coupon_code, coupon_error}

    ctx = {
        "items": s["items"],
        "subtotal": s["subtotal"],
        "discount": s["discount"],
        "total": s["total"],
        "coupon_code": s["coupon_code"],
        "coupon_error": s["coupon_error"],

        # SEO
        "meta_title": "Krepšelis – Urock",
        "meta_description": "Jūsų pirkinių krepšelis.",
        "meta_robots": "noindex,follow",
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "cart/view.html", ctx)


@require_POST
def cart_add(request):
    cart = Cart(request)
    variant_id = int(request.POST.get("variant_id", 0))
    qty = max(1, int(request.POST.get("qty", 1)))

    try:
        v = Variant.objects.select_related("product").get(
            id=variant_id, is_active=True, product__is_active=True
        )
    except Variant.DoesNotExist:
        messages.error(request, "Variantas nerastas arba neaktyvus.")
        return redirect("cart:cart_view")

    if v.stock <= 0:
        messages.error(request, "Šis variantas šiuo metu neturi atsargų.")
        return redirect(reverse("product_detail", kwargs={"slug": v.product.slug}))

    if qty > v.stock:
        messages.error(request, "Kiekis viršija likutį.")
        return redirect(reverse("product_detail", kwargs={"slug": v.product.slug}))

    cart.add(variant_id, qty)
    messages.success(request, "Prekė pridėta į krepšelį.")
    return redirect("cart:cart_view")


@require_POST
def cart_update(request):
    cart = Cart(request)
    variant_id = int(request.POST.get("variant_id", 0))
    qty = int(request.POST.get("qty", 0))

    try:
        v = Variant.objects.select_related("product").get(id=variant_id)
    except Variant.DoesNotExist:
        messages.error(request, "Variantas nerastas.")
        return redirect("cart:cart_view")

    if qty < 0:
        qty = 0

    if qty > v.stock:
        messages.error(request, "Kiekis viršija likutį.")
        return redirect("cart:cart_view")

    cart.set(variant_id, qty)
    messages.success(request, "Krepšelis atnaujintas.")
    return redirect("cart:cart_view")


@require_POST
def cart_remove(request):
    cart = Cart(request)
    variant_id = int(request.POST.get("variant_id", 0))
    cart.remove(variant_id)
    messages.info(request, "Prekė pašalinta.")
    return redirect("cart:cart_view")


@require_POST
def cart_apply_coupon(request):
    cart = Cart(request)
    code = (request.POST.get("coupon") or "").strip()
    cart.set_coupon(code or None)

    # Iškart patikrinam ir parodom žinutę
    s = cart.summary()
    if s["coupon_error"]:
        messages.error(request, s["coupon_error"])
    elif s["coupon_code"]:
        messages.success(request, f'Nuolaidos kodas „{s["coupon_code"]}“ pritaikytas.')

    return redirect("cart:cart_view")


@require_POST
def cart_remove_coupon(request):
    cart = Cart(request)
    cart.set_coupon(None)
    messages.info(request, "Nuolaidos kodas nuimtas.")
    return redirect("cart:cart_view")
