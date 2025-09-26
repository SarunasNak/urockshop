# cart/services.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Optional
from catalog.models import Variant

CART_SESSION_KEY = "cart"          # session struktūra: {"items": {"<id>": qty}, "coupon": "CODE"|None}
COUPON_SESSION_KEY = "cart_coupon" # (palikta suderinamumui, jei kur nors dar naudojama)

@dataclass
class CartLine:
    variant: Variant
    qty: int

    @property
    def line_total(self) -> Decimal:
        price = Decimal(self.variant.price or 0)
        return (price * Decimal(self.qty)).quantize(Decimal("0.01"))


class Cart:
    """
    Sesijinis krepšelis:
      session["cart"] = {"items": {"<variant_id>": qty, ...}, "coupon": "CODE" | None}
    """

    def __init__(self, request):
        self.request = request
        self.session = request.session

        raw = self.session.get(CART_SESSION_KEY)
        if not raw or not isinstance(raw, dict):
            raw = {"items": {}, "coupon": None}

        # normalizuojam duomenis
        items: Dict[str, int] = {}
        for k, v in (raw.get("items") or {}).items():
            try:
                q = int(v)
                if q > 0:
                    items[str(int(k))] = q
            except Exception:
                continue

        self._items: Dict[str, int] = items
        self._coupon: Optional[str] = (raw.get("coupon") or None)
        self._save()  # persistinam suvienodintą struktūrą

    # --- low-level ---

    def _save(self):
        self.session[CART_SESSION_KEY] = {"items": self._items, "coupon": self._coupon}
        self.session.modified = True

    # --- mutatoriai ---

    def add(self, variant_id: int, qty: int = 1):
        key = str(int(variant_id))
        qty = max(1, int(qty))
        self._items[key] = self._items.get(key, 0) + qty
        self._save()

    def set(self, variant_id: int, qty: int):
        key = str(int(variant_id))
        qty = int(qty)
        if qty <= 0:
            self._items.pop(key, None)
        else:
            self._items[key] = qty
        self._save()

    def remove(self, variant_id: int):
        self._items.pop(str(int(variant_id)), None)
        self._save()

    def get(self, variant_id: int) -> int:
        return int(self._items.get(str(int(variant_id)), 0))

    # --- kuponas ---

    def set_coupon(self, code: Optional[str]):
        self._coupon = (code or None)
        if self._coupon:
            self._coupon = self._coupon.strip().upper() or None
        self._save()

    @property
    def coupon_code(self) -> Optional[str]:
        return self._coupon

    # --- skaitymas ---

    def items(self) -> List[CartLine]:
        ids = [int(k) for k in self._items.keys()]
        if not ids:
            return []
        variants = Variant.objects.select_related("product").in_bulk(ids)
        lines: List[CartLine] = []
        for k, qty in self._items.items():
            v = variants.get(int(k))
            if v:
                lines.append(CartLine(variant=v, qty=int(qty)))
        return lines

    @property
    def count(self) -> int:
        return sum(int(q) for q in self._items.values())

    @property
    def subtotal(self) -> Decimal:
        return sum((line.line_total for line in self.items()), Decimal("0.00"))

    # Paliekam suderinamumui: total = subtotal (be pristatymo/nuolaidos)
    @property
    def total(self) -> Decimal:
        return self.subtotal

    # --- suvestinė su kuponu ---

    def summary(self) -> dict:
        """
        Grąžina:
          - items: List[CartLine]
          - subtotal: Decimal
          - discount: Decimal
          - total: Decimal
          - coupon_code: Optional[str]
          - coupon_error: Optional[str]
        """
        from discounts.models import Coupon
        from discounts.services import validate_coupon, apply_coupon_amount

        items = self.items()
        subtotal = self.subtotal

        discount = Decimal("0.00")
        coupon_error: Optional[str] = None
        code = self.coupon_code

        if code:
            try:
                coupon = Coupon.objects.get(code=code, is_active=True)
                validate_coupon(
                    coupon,
                    user=(self.request.user if getattr(self.request, "user", None) and self.request.user.is_authenticated else None),
                    email=(getattr(self.request.user, "email", None) if getattr(self.request, "user", None) and self.request.user.is_authenticated else None),
                    cart_total=subtotal,
                    cart_products=[line.variant.product for line in items],
                )
                discount = apply_coupon_amount(coupon, subtotal)
            except Exception as e:
                coupon_error = str(e)
                # jei netinkamas – nuimam, kad neliktų „prisikabinęs“
                self.set_coupon(None)
                code = None

        total = max(Decimal("0.00"), (subtotal - discount).quantize(Decimal("0.01")))
        return {
            "items": items,
            "subtotal": subtotal,
            "discount": discount,
            "total": total,
            "coupon_code": code,
            "coupon_error": coupon_error,
        }
