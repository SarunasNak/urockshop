# cart/context_processors.py
from .services import Cart

def cart_info(request):
    try:
        cart = Cart(request)
        return {"cart_count": cart.count, "cart_total": cart.total}
    except Exception:
        return {"cart_count": 0, "cart_total": 0}
