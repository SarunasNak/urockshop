# checkout/emails.py
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


def _lines_from_order(order):
    """
    Grąžina prekių eilučių sąrašą universalioje struktūroje:
    [{"name":..., "size":..., "qty":..., "price":..., "total":...}, ...]
    Pirma bandom su ryšiu (order.items arba order.lines), jei jo nėra –
    krentam į JSON snapshot'ą (order.items_json).
    """
    lines = []

    # 1) bandome rasti ryšį order.items arba order.lines
    qs = None
    for rel in ("items", "lines"):
        if hasattr(order, rel):
            try:
                qs = getattr(order, rel).all()
                break
            except Exception:
                qs = None

    if qs:
        for l in qs:
            lines.append({
                "name":  getattr(l, "product_name", getattr(l, "name", "Prekė")),
                "size":  getattr(l, "size_display", getattr(l, "size", "")) or "–",
                "qty":   getattr(l, "qty", 1),
                "price": getattr(l, "price", 0),
                "total": getattr(l, "line_total", getattr(l, "total", 0)),
            })
        return lines

    # 2) jei nėra ryšio – bandome iš snapshot'o (jei tokį saugote)
    snap = getattr(order, "items_json", None) or []
    for it in snap:
        lines.append({
            "name":  it.get("name", "Prekė"),
            "size":  it.get("size", "–"),
            "qty":   it.get("qty", 1),
            "price": it.get("price", 0),
            "total": it.get("line_total", it.get("total", 0)),
        })
    return lines


def send_order_emails(order, *, customer_email=None):
    """
    Nusiųsk 2 laiškus: klientui (patvirtinimas) ir adminui (notifikacija).
    Kviečiama tik tada, kai užsakymas jau pažymėtas kaip apmokėtas.
    """
    # Iš ko siųsti ir kam adminui
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "UROCK <info@urock.lt>")
    admin_to   = [getattr(settings, "ORDER_ADMIN_EMAIL", "info@urock.lt")]

    # Gavėjo el. paštas (iš argumento ar modelio)
    customer_email = (
        customer_email
        or getattr(order, "email", None)
        or getattr(order, "customer_email", None)
    ) or None  # garantuotai None, jei nieko neradom

    # Kontekstas šablonams
    ctx = {
        "order": order,
        "lines": _lines_from_order(order),
        "order_number": getattr(order, "number", getattr(order, "id", "")),
        "total": getattr(order, "total", None) or getattr(order, "grand_total", None),
        "currency": getattr(order, "currency", "EUR"),
        "shipping_name": getattr(order, "shipping_name", "") or getattr(order, "name", ""),
        "shipping_address": getattr(order, "shipping_address", ""),
        "note": getattr(order, "note", ""),
        "phone": getattr(order, "phone", ""),
        "email": customer_email or "",
        "SITE_HOST": getattr(settings, "SITE_HOST", "urock.lt"),
        "ORDER_ADMIN_EMAIL": getattr(settings, "ORDER_ADMIN_EMAIL", "info@urock.lt"),
    }

    # ---------- Klientui ----------
    if customer_email:
        subject_c = f"Jūsų užsakymas #{ctx['order_number']} – patvirtintas"
        text_c = render_to_string("emails/order_confirmation.txt", ctx)
        html_c = render_to_string("emails/order_confirmation.html", ctx)

        msg_c = EmailMultiAlternatives(
            subject=subject_c,
            body=text_c,
            from_email=from_email,
            to=[customer_email],
        )
        msg_c.attach_alternative(html_c, "text/html")
        msg_c.send(fail_silently=False)

    # ---------- Adminui ----------
    subject_a = f"Naujas užsakymas #{ctx['order_number']} – UROCK"
    text_a = render_to_string("emails/order_notify_admin.txt", ctx)
    html_a = render_to_string("emails/order_notify_admin.html", ctx)

    msg_a = EmailMultiAlternatives(
        subject=subject_a,
        body=text_a,
        from_email=from_email,
        to=admin_to,
        reply_to=[customer_email] if customer_email else None,
    )
    msg_a.attach_alternative(html_a, "text/html")
    msg_a.send(fail_silently=False)
