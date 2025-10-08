# discounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from checkout.models import Order
from discounts.models import Coupon, CouponRedemption

def _pick_email(o: Order) -> str:
    # pritaikykite pavadinimus prie savo Order laukų
    return (
        getattr(o, "email", None)
        or getattr(o, "customer_email", None)
        or getattr(o, "billing_email", None)
        or getattr(o, "shipping_email", None)
        or ""
    )

@receiver(post_save, sender=Order, dispatch_uid="order_paid_create_coupon_redemption")
def create_coupon_redemption(sender, instance: Order, **kwargs):
    if (instance.status or "").lower() != "paid":
        return
    code = (instance.coupon_code or "").strip()
    if not code:
        return

    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        return

    email = _pick_email(instance)

    obj, created = CouponRedemption.objects.get_or_create(
        order_id=instance.id,                       # pas jus nėra FK, todėl order_id
        defaults={"coupon": coupon, "user": None, "email": email},
    )

    # jei įrašas jau buvo, bet email dar
