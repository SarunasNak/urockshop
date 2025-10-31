from decimal import Decimal
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from discounts.models import Coupon
from discounts.services import validate_coupon, apply_coupon_amount, CouponError
from cart.services import Cart


@require_POST
def apply_coupon(request):
    code = (request.POST.get("code") or "").strip()
    if not code:
        return HttpResponse("<p class='text-red-600'>Įveskite nuolaidos kodą.</p>")

    try:
        coupon = Coupon.objects.get(code__iexact=code)
    except Coupon.DoesNotExist:
        return HttpResponse("<p class='text-red-600'>Toks nuolaidos kodas neegzistuoja.</p>")

    cart = Cart(request)
    cart_total = cart.total or Decimal("0.00")
    now = timezone.now()

    try:
        validate_coupon(
            coupon,
            user=request.user if request.user.is_authenticated else None,
            email=request.POST.get("email") or "",
            cart_total=cart_total,
            cart_products=[l.variant.product for l in cart.items()],
        )
    except CouponError as e:
        return HttpResponse(f"<p class='text-red-600'>{e}</p>")
    except Exception as e:
        return HttpResponse(f"<p class='text-red-600'>Kupono klaida: {e}</p>")

    # Apskaičiuojam nuolaidą
    discount_amount = apply_coupon_amount(coupon, cart_total)
    new_total = (cart_total - discount_amount).quantize(Decimal("0.01"))

    # Išsaugom sesijoje
    request.session["coupon_id"] = coupon.id
    request.session["coupon_code"] = coupon.code
    request.session["coupon_discount"] = float(discount_amount)
    request.session.modified = True

    # HTMX atsakymas
    html = f"<p class='text-green-700'>Kuponas <b>{coupon.code}</b> pritaikytas – nuolaida {discount_amount} €!</p>"
    response = HttpResponse(html)
    response["HX-Trigger"] = '{"update-total": {"new_total": "%s"}}' % new_total
    return response
