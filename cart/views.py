from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.http import require_POST
from django.urls import reverse
from catalog.models import Variant
from .services import Cart

def cart_view(request):
    cart = Cart(request)
    lines = cart.items()  # CartLine: variant, qty, intent, line_total

    order_items = [l for l in lines if l.intent == "purchase"]
    try_on_items = [l for l in lines if l.intent == "try_on"]

    # ⚠️ TAVO ŠABLONAS „Noriu pasimatuoti“ naudoja kintamąjį `items`
    # todėl čia paliekam TRY-ON eiles, kad nieko nelūžtų
    ctx = {
        "items": try_on_items,                           # try-on sąrašas su kaina
        "fit_total": sum(l.qty for l in try_on_items),   # jei kur rodysi skaitliuką

        # „Jūsų užsakymas“ sumoms (šitas blokas jau naudoja `total`)
        "total": sum(l.line_total for l in order_items),

        # + pirkimo eilutės, jei prireiks (nerodomos, bet bus kontekste)
        "order_items": order_items,
    }

    # (nebūtina) — jei norėsi turėti atskirai „pirkinio“ kiekį šablone
    ctx["order_items_len"] = len(order_items)

    return render(request, "cart/view.html", ctx)


@require_POST
def cart_add(request):
    mode = (request.POST.get("mode") or "buy").lower()
    intent = "try_on" if mode == "fit" else "purchase"

    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        messages.error(request, "Netinkamas prekės ID.")
        return redirect("cart:cart_view")

    # vienetinės prekės – qty visada 1
    v = get_object_or_404(
        Variant.objects.select_related("product"),
        pk=variant_id, is_active=True, product__is_active=True
    )

    if intent == "purchase" and v.stock <= 0:
        messages.error(request, "Šis variantas šiuo metu neturi atsargų.")
        return redirect(reverse("catalog:detail", kwargs={"slug": v.product.slug}))

    cart = Cart(request)
    cart.add(variant_id=v.id, qty=1, intent=intent)  # PASKUTINIS PASPAUDIMAS LAIMI

    messages.success(
        request,
        "Prekė pridėta į krepšelį." if intent == "purchase" else "Prekė pridėta į matavimosi krepšelį."
    )
    return redirect(request.POST.get("next") or request.META.get("HTTP_REFERER") or "cart:cart_view")


@require_POST
def cart_update(request):
    # jei leisite keisti kiekį – čia palikta; pagal nutylėjimą 1/0
    try:
        variant_id = int(request.POST.get("variant_id", 0))
        qty = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        messages.error(request, "Netinkami duomenys.")
        return redirect("cart:cart_view")

    cart = Cart(request)
    cart.set(variant_id, 1 if qty > 0 else 0)
    messages.success(request, "Krepšelis atnaujintas.")
    return redirect("cart:cart_view")


@require_POST
def cart_remove(request):
    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        messages.error(request, "Netinkamas prekės ID.")
        return redirect("cart:cart_view")

    cart = Cart(request)
    cart.remove(variant_id)  # pašalina nepriklausomai nuo intent
    messages.info(request, "Prekė pašalinta.")
    return redirect("cart:cart_view")
