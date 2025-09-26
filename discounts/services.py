from decimal import Decimal
from django.utils import timezone
from .models import Coupon
from typing import Optional
from django.contrib.auth.models import AnonymousUser
from .models import CouponRedemption

class CouponError(Exception): pass

def validate_coupon(coupon: Coupon, *, user=None, email=None, cart_total: Decimal, cart_products=None):
    now = timezone.now()
    if not coupon.is_active: raise CouponError("Kuponas neaktyvus.")
    if coupon.starts_at and now < coupon.starts_at: raise CouponError("Kuponas dar negalioja.")
    if coupon.ends_at and now > coupon.ends_at: raise CouponError("Kupono galiojimas pasibaigė.")
    if coupon.min_order_total and cart_total < coupon.min_order_total: raise CouponError("Nepasiektas minimalus krepšelio dydis.")
    if coupon.assigned_user and (not user or user != coupon.assigned_user): raise CouponError("Šis kuponas yra asmeninis.")
    if coupon.allowed_emails:
        wl = {e.strip().lower() for e in coupon.allowed_emails.split(";") if e.strip()}
        if email and email.lower() not in wl: raise CouponError("Šis kuponas galioja tik konkretiems el. paštams.")
    if not coupon.applies_to_all and cart_products:
        prod_ids = {p.id for p in cart_products}
        cat_ids = {p.category_id for p in cart_products}
        if not (coupon.products.filter(id__in=prod_ids).exists() or coupon.categories.filter(id__in=cat_ids).exists()):
            raise CouponError("Kuponas netaikomas šiam krepšeliui.")

def apply_coupon_amount(coupon: Coupon, cart_total: Decimal) -> Decimal:
    if coupon.type == Coupon.PERCENT:
        return (cart_total * coupon.value / Decimal("100")).quantize(Decimal("0.01"))
    return min(cart_total, coupon.value).quantize(Decimal("0.01"))

def log_coupon_redemption(order, user: Optional[object] = None):
    """
    Įrašo kupono panaudojimą, kai užsakymas jau apmokėtas.
    Naudoja order.coupon_code ir order.email.
    Duplikatų nekuria.
    """
    code = (getattr(order, "coupon_code", "") or "").strip().upper()
    if not code:
        return

    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
    except Coupon.DoesNotExist:
        return

    # kad nekurtume dublikatų (jei webhook atėjo kelis kartus ir pan.)
    if CouponRedemption.objects.filter(coupon=coupon, order_id=str(order.id)).exists():
        return

    u = None
    if user and not isinstance(user, AnonymousUser) and getattr(user, "is_authenticated", False):
        u = user

    CouponRedemption.objects.create(
        coupon=coupon,
        order_id=str(order.id),
        user=u,
        email=(getattr(order, "email", "") or ""),
    )
