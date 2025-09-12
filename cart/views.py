# cart/views.py
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.urls import reverse
from catalog.models import Variant
from .services import Cart

def cart_view(request):
    cart = Cart(request)
    ctx = {
        "items": cart.items(),
        "total": cart.total,

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
        v = Variant.objects.select_related("product").get(id=variant_id, is_active=True, product__is_active=True)
    except Variant.DoesNotExist:
        messages.error(request, "Variantas nerastas arba neaktyvus.")
        return redirect("cart_view")
    if v.stock <= 0:
        messages.error(request, "Šis variantas šiuo metu neturi atsargų.")
        return redirect(reverse("product_detail", kwargs={"slug": v.product.slug}))
    if qty > v.stock:
        messages.error(request, "Kiekis viršija likutį.")
        return redirect(reverse("product_detail", kwargs={"slug": v.product.slug}))
    cart.add(variant_id, qty)
    messages.success(request, "Prekė pridėta į krepšelį.")
    return redirect("cart_view")

@require_POST
def cart_update(request):
    cart = Cart(request)
    variant_id = int(request.POST.get("variant_id", 0))
    qty = int(request.POST.get("qty", 0))
    try:
        v = Variant.objects.select_related("product").get(id=variant_id)
    except Variant.DoesNotExist:
        messages.error(request, "Variantas nerastas.")
        return redirect("cart_view")
    if qty < 0: qty = 0
    if qty > v.stock:
        messages.error(request, "Kiekis viršija likutį.")
        return redirect("cart_view")
    cart.set(variant_id, qty)
    messages.success(request, "Krepšelis atnaujintas.")
    return redirect("cart_view")

@require_POST
def cart_remove(request):
    cart = Cart(request)
    variant_id = int(request.POST.get("variant_id", 0))
    cart.remove(variant_id)
    messages.info(request, "Prekė pašalinta.")
    return redirect("cart_view")
