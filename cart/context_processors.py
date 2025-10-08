# cart/context_processors.py
from .services import Cart

def cart_info(request):
    try:
        cart = Cart(request)

        # universalus būdas: jei Cart turi naujus getter’ius – naudosim juos,
        # jei ne – liksim prie senų laukų ir viskas vistiek veiks.
        count_unique = getattr(cart, "count_unique", None)
        purchase_count = getattr(cart, "purchase_count", None)
        try_on_count = getattr(cart, "try_on_count", None)

        cart_count = count_unique if isinstance(count_unique, int) else getattr(cart, "count", 0)
        return {
            "cart_count": cart_count,
            "cart_total": getattr(cart, "total", 0),
            "cart_purchase_count": purchase_count if isinstance(purchase_count, int) else None,
            "cart_try_on_count": try_on_count if isinstance(try_on_count, int) else None,
            "cart_has_items": cart_count > 0,
        }
    except Exception:
        return {
            "cart_count": 0,
            "cart_total": 0,
            "cart_purchase_count": 0,
            "cart_try_on_count": 0,
            "cart_has_items": False,
        }
