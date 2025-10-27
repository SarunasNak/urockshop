from decimal import Decimal
from django.db import transaction

def mark_paid_and_decrease_stock(order):
    """
    Pažymi užsakymą 'paid', sumažina kiekvieno varianto likutį
    ir, jei likutis tampa 0, paslepia variantą (ir produktą – jei nori).
    """
    from catalog.models import Variant  # lokalus importas, kad išvengtume ciklinių

    with transaction.atomic():
        # 1) sumažinam likučius
        for item in order.items.select_related("variant").select_for_update():
            v: Variant = item.variant
            v.stock = max(0, v.stock - item.qty)
            fields_to_update = ["stock"]

            # 2) jei likutis 0 – paslepiam variantą
            if v.stock == 0 and hasattr(v, "is_active") and v.is_active:
                v.is_active = False
                fields_to_update.append("is_active")

            v.save(update_fields=fields_to_update)

            # 3) (pasirinktinai) jei vienetinis produktas – slėpk ir patį produktą
            #   Jei to NENORI – šį bloką ištrink arba pakomentuok.
            p = getattr(v, "product", None)
            if p and hasattr(p, "is_active") and p.is_active and v.stock == 0:
                p.is_active = False
                p.save(update_fields=["is_active"])

        # 4) pažymim užsakymą apmokėtu
        if order.status != "paid":
            order.status = "paid"
            order.save(update_fields=["status"])
