# cart/views.py

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from catalog.models import Variant
from .services import Cart


# ───────────────────────────────── helpers ───────────────────────────────── #

def _is_ajax(request):
    """Ar užklausa siųsta per fetch/XHR?"""
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _cart_counts_payload(cart):
    """Bendras JSON atsakas AJAX atvejams (header badge, sumos ir t. t.)."""
    lines = cart.items()
    order_items = [l for l in lines if l.intent == "purchase"]
    try_on_items = [l for l in lines if l.intent == "try_on"]

    cart_count   = sum(l.qty for l in lines)
    order_count  = sum(l.qty for l in order_items)
    try_on_count = sum(l.qty for l in try_on_items)
    total_sum    = sum(l.line_total for l in order_items)

    return {
        "ok": True,
        "cart_count": cart_count,          # naudok header'io skaičiukui
        "order_count": order_count,
        "try_on_count": try_on_count,
        "total": float(total_sum),         # bendra pirkinių suma
    }


# ─────────────────────────────────  views  ───────────────────────────────── #

def cart_view(request):
    cart = Cart(request)
    lines = cart.items()

    order_items = [l for l in lines if l.intent == "purchase"]
    try_on_items = [l for l in lines if l.intent == "try_on"]

    ctx = {
        # „Noriu pasimatuoti“ blokui (tavo šablonas naudoja kintamąjį `items`)
        "items": try_on_items,
        "fit_total": sum(l.qty for l in try_on_items),

        # „Jūsų užsakymas“ sumoms
        "total": sum(l.line_total for l in order_items),
        "order_items": order_items,
        "order_items_len": len(order_items),
    }
    return render(request, "cart/view.html", ctx)


@require_POST
def cart_add(request):
    mode = (request.POST.get("mode") or "buy").lower()
    intent = "try_on" if mode == "fit" else "purchase"

    # variant_id
    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkamas prekės ID."}, status=400)
        messages.error(request, "Netinkamas prekės ID.")
        return redirect("cart:cart_view")

    v = get_object_or_404(
        Variant.objects.select_related("product"),
        pk=variant_id, is_active=True, product__is_active=True
    )

    if intent == "purchase" and v.stock <= 0:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Šio varianto nebėra sandėlyje."}, status=400)
        messages.error(request, "Šis variantas šiuo metu neturi atsargų.")
        return redirect(reverse("catalog:detail", kwargs={"slug": v.product.slug}))

    cart = Cart(request)
    cart.add(variant_id=v.id, qty=1, intent=intent)

    # AJAX – jokio Django messages, tik JSON
    if _is_ajax(request):
        return JsonResponse(_cart_counts_payload(cart))

    # Ne-AJAX – seno stiliaus pranešimas + redirect
    messages.success(
        request,
        "Prekė pridėta į krepšelį." if intent == "purchase" else "Prekė pridėta į matavimosi krepšelį."
    )
    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER") or "cart:cart_view")


@require_POST
def cart_update(request):
    try:
        variant_id = int(request.POST.get("variant_id", 0))
        qty = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkami duomenys."}, status=400)
        messages.error(request, "Netinkami duomenys.")
        return redirect("cart:cart_view")

    cart = Cart(request)
    cart.set(variant_id, 1 if qty > 0 else 0)

    if _is_ajax(request):
        return JsonResponse(_cart_counts_payload(cart))

    messages.success(request, "Krepšelis atnaujintas.")
    return redirect("cart:cart_view")

@require_POST
def cart_remove(request):
    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkamas prekės ID."}, status=400)
        messages.error(request, "Netinkamas prekės ID.")
        return redirect("cart:cart_view")  # ← ČIA svarbu

    cart = Cart(request)
    cart.remove(variant_id)

    if _is_ajax(request):
        data = _cart_counts_payload(cart)   # {ok, cart_count, order_count, try_on_count, total}
        data["removed_id"] = variant_id     # patogu DOM'ui
        return JsonResponse(data)

    messages.info(request, "Prekė pašalinta.")
    return redirect("cart:cart_view")       # ← ČIA svarbu
