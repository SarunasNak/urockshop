# cart/views.py
from time import time
import json
import logging

from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.core.cache import cache

from catalog.models import Variant
from .services import Cart
from .models import TryOnRequest

from django.core.mail import send_mail
from django.conf import settings

from catalog.models import PrivateProduct

from checkout.services import get_all_dpd_points

# <<< PAKAITALAS: griežtas importas (jei kas blogai – pamatysit klaidą loguose ir konsolėje)
from newsletter.models import Subscriber

logger = logging.getLogger(__name__)


# ───────────────────────── helpers ───────────────────────── #

def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"

def _client_ip(request):
    xfwd = request.META.get("HTTP_X_FORWARDED_FOR")
    if xfwd:
        return xfwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")

def _cart_counts_payload(cart):
    lines = cart.items()
    order_items = [l for l in lines if l.intent == "purchase"]
    try_on_items = [l for l in lines if l.intent == "try_on"]

    cart_count   = sum(l.qty for l in lines)
    order_count  = sum(l.qty for l in order_items)
    try_on_count = sum(l.qty for l in try_on_items)
    total_sum    = sum(l.line_total for l in order_items)

    return {
        "ok": True,
        "cart_count": cart_count,
        "order_count": order_count,
        "try_on_count": try_on_count,
        "total": float(total_sum),
    }


# ───────────────────────── views ───────────────────────── #

def cart_view(request):
    cart = Cart(request)

    lines = cart.items()

    order_items = [l for l in lines if l.intent == "purchase"]
    try_on_items = [l for l in lines if l.intent == "try_on"]

    is_private = request.session.get("is_private", False)

    private_collection_slug = None

    if is_private:
        for l in lines:
            product = l.variant.product

            private = (
                PrivateProduct.objects
                .select_related("collection")
                .filter(product=product)
                .first()
            )

            if private:
                private_collection_slug = private.collection.slug
                break

    ctx = {
        "is_private": is_private,
        "private_collection_slug": private_collection_slug,
        "items": try_on_items,                         # „Noriu pasimatuoti“
        "fit_total": sum(l.qty for l in try_on_items),

        "total": sum(l.line_total for l in order_items),  # „Jūsų užsakymas“
        "order_items": order_items,
        "order_items_len": len(order_items),
    }

     # 🟢 DPD taškai JSON formatu (frontendui)
    points = get_all_dpd_points()
    ctx["dpd_points_json"] = json.dumps(points, ensure_ascii=False)

    return render(request, "cart/view.html", ctx)


@require_POST
def cart_add(request):

    mode = (request.POST.get("mode") or "buy").lower()
    intent = "try_on" if mode == "fit" else "purchase"

    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkamas prekės ID."}, status=400)
        return redirect("cart:cart_view")

    v = Variant.objects.select_related("product").filter(pk=variant_id).first()
    if not v:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Prekė nerasta."}, status=404)
        return redirect("cart:cart_view")

    is_private_flow = request.POST.get("private_flow") == "1"

    if is_private_flow:
        request.session["is_private"] = True

    if is_private_flow:
        # ✔️ leidžiam tik jei produktas yra private kolekcijoje
        if not PrivateProduct.objects.filter(product=v.product).exists():
            if _is_ajax(request):
                return JsonResponse({"ok": False, "error": "Neprieinama prekė."}, status=403)
            return redirect("cart:cart_view")

    else:
        # ❗ uždraudžiam private produktus per public
        if PrivateProduct.objects.filter(product=v.product).exists():
            if _is_ajax(request):
                return JsonResponse({"ok": False, "error": "Neprieinama prekė."}, status=403)
            return redirect("cart:cart_view")

        # ✔️ public – tik active
        if not v.is_active or not v.product.is_active:
            if _is_ajax(request):
                return JsonResponse({"ok": False, "error": "Prekė neaktyvi."}, status=403)
            return redirect("cart:cart_view")

    if intent == "purchase" and getattr(v, "stock", 0) <= 0:
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Šio varianto nebėra sandėlyje."}, status=400)
        return redirect(reverse("catalog:detail", kwargs={"slug": v.product.slug}))

    cart = Cart(request)
    cart.add(variant_id=v.id, qty=1, intent=intent)

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")

    if next_url:
        request.session["return_url"] = next_url

    if _is_ajax(request):
        return JsonResponse(_cart_counts_payload(cart))

    return redirect(next_url or "cart:cart_view")

@require_POST
def cart_update(request):
    try:
        variant_id = int(request.POST.get("variant_id", 0))
        qty = int(request.POST.get("qty", 1))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkami duomenys."}, status=400)
        return redirect("cart:cart_view")

    cart = Cart(request)
    cart.set(variant_id, 1 if qty > 0 else 0)

    if _is_ajax(request):
        return JsonResponse(_cart_counts_payload(cart))

    return redirect("cart:cart_view")


@require_POST
def cart_remove(request):
    try:
        variant_id = int(request.POST.get("variant_id", 0))
    except (TypeError, ValueError):
        if _is_ajax(request):
            return JsonResponse({"ok": False, "error": "Netinkamas prekės ID."}, status=400)
        return redirect("cart:cart_view")

    cart = Cart(request)
    cart.remove(variant_id)

    if _is_ajax(request):
        data = _cart_counts_payload(cart)
        data["removed_id"] = variant_id
        return JsonResponse(data)

    return redirect("cart:cart_view")


# ─────────────────────── try-on submit (AJAX) ─────────────────────── #

def _json_error(msg, status=400):
    return JsonResponse({"ok": False, "errors": {"__all__": [msg]}}, status=status)


@require_POST
def tryon_submit(request):
    cart = Cart(request)

    # 0) IP rate-limit: max 5 bandymų per 60 s
    ip = _client_ip(request)
    rl_key = f"tryon-rl:{ip}"
    count = cache.get(rl_key, 0) + 1
    cache.set(rl_key, count, 60)
    if count > 5:
        return _json_error("Per daug bandymų. Pabandykite vėliau.", status=429)

    # 1) Honeypot: jei „company“ užpildyta – apsimetam sėkme ir nieko nedarom
    if request.POST.get("company"):
        resp = HttpResponse("Rezervacija patvirtinta")
        resp["HX-Trigger-After-Settle"] = json.dumps({"cart-updated": _cart_counts_payload(cart)})
        return resp

    # 2) Min. pildymo laikas (>= 3 s)
    try:
        started = int(request.POST.get("form_started", "0"))
    except ValueError:
        started = 0
    if time() - started < 3:
        return _json_error("Pateikta per greitai. Pabandykite dar kartą.", status=429)

    # 3) turi būti bent viena try_on eilutė
    if not any(l.intent == "try_on" for l in cart.items()):
        return _json_error("Krepšelis tuščias.")

    ## 4) laukų paėmimas
    name = (request.POST.get("name") or "").strip()
    email = (request.POST.get("email") or "").strip()
    phone = (request.POST.get("phone") or "").strip()[:32]
    comment = (request.POST.get("comment") or "").strip()

    # 5) validacija
    missing = {}
    if not name:
        missing["name"] = ["Privalomas laukas."]
    if not email:
        missing["email"] = ["Privalomas laukas."]
    if not phone:
        missing["phone"] = ["Privalomas laukas."]

    if missing:
        return JsonResponse({"ok": False, "errors": missing}, status=400)

    if request.POST.get("terms_accepted") not in ("on", "true", "1"):
        return JsonResponse({
            "ok": False,
            "errors": {"terms_accepted": ["Būtina sutikti su sąlygomis."]}
        }, status=400)

    marketing = request.POST.get("marketing_consent") in ("on", "true", "1")

    # 5) snapshot -> DB
    snapshot = cart.snapshot("try_on")
    tor = TryOnRequest.objects.create(
        name=name,
        email=email,
        phone=phone,
        comment=comment,
        terms_accepted=True,
        marketing_consent=marketing,
        items_json=snapshot,
    )

    # 6) jei pažymėtas marketingas – sukurti/ar atnaujinti subscriber'į
    if marketing and Subscriber is not None:
        Subscriber.objects.update_or_create(
            email=email,
            defaults={
                "is_active": True,
                "source": "cart_tryon",
                "phone": phone,
            },
        )

    # 7) el. laiškai (KLIENTUI + ADMINUI) — nepriklausomai nuo marketingo
    try:
        # Prekių sąrašas paprastame tekste
        items_text = "\n".join(
            f"- {it.get('name','Prekė')} (dydis {it.get('size','–')})"
            for it in (snapshot or [])
        ) or "- (be įrašų)"

        # ✅ „Atsisakyti prenumeratos“ – tik jei pažymėtas marketingo sutikimas
        if marketing:
            # paprasta versija be specialaus tokeno / backend’o
            host = getattr(settings, "SITE_HOST", "urock.lt")
            scheme = getattr(settings, "SITE_SCHEME", "https")
            unsub_url = f"{scheme}://{host}/unsubscribe?email={email}"
            unsubscribe_line = (
                "\n—\n"
                "Jei nebenorite gauti naujienų, "
                f"atsisakykite prenumeratos čia: {unsub_url}\n"
            )
        else:
            unsubscribe_line = ""

        # Klientui
        customer_subject = "Jūsų užklausa gauta – UROCK"
        customer_body = (
            "Sveiki,\n\n"
            "Ačiū! Gavome Jūsų užklausą.\n"
            "Mūsų komanda artimiausiu metu su Jumis susisieks.\n\n"
            "Jūsų pasirinktos prekės:\n"
            f"{items_text}\n\n"
            "Jei turite klausimų, atsakykite į šį laišką.\n\n"
            "Su pagarba,\nUROCK komanda\n"
            "www.urock.lt\n"
            f"{unsubscribe_line}"
        )
        send_mail(
            subject=customer_subject,
            message=customer_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        # Administratoriui
        admin_subject = "Nauja TRY-ON užklausa – UROCK"
        admin_body = (
            "Yra nauja užklausa.\n\n"
            f"Vardas: {name}\n"
            f"El. paštas: {email}\n"
            f"Tel.: {phone}\n"
            f"Komentaras: {comment}\n"
            f"Rinkodara: {'Taip' if marketing else 'Ne'}\n\n"
            "Prekės:\n"
            f"{items_text}\n"
        )
        admin_to = [getattr(settings, "ORDER_ADMIN_EMAIL", "info@urock.lt")]
        send_mail(
            subject=admin_subject,
            message=admin_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_to,
            fail_silently=False,
        )
    except Exception:
        # nenumušam srauto, jei laiškas nepavyko – UI vis tiek rodo „išsiųsta“
        pass

    # 8) išvalom tik try_on
    cart.clear_try_on()

    # 9) grąžinam mygtuko tekstą ir event'ą
    return JsonResponse({
        "ok": True,
        "message": "Rezervacija patvirtinta",
        "cart": _cart_counts_payload(cart)
    })