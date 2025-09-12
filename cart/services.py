# cart/services.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict
from catalog.models import Variant

CART_SESSION_KEY = "cart"

@dataclass
class CartLine:
    variant: Variant
    qty: int
    @property
    def line_total(self) -> Decimal:
        return (self.variant.price or Decimal("0")) * self.qty

class Cart:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self._data: Dict[str, int] = {
            str(k): int(v) for k, v in self.session.get(CART_SESSION_KEY, {}).items() if int(v) > 0
        }
    def _save(self):
        self.session[CART_SESSION_KEY] = self._data
        self.session.modified = True
    def add(self, variant_id: int, qty: int = 1):
        key = str(variant_id)
        self._data[key] = self._data.get(key, 0) + max(1, int(qty))
        self._save()
    def set(self, variant_id: int, qty: int):
        key = str(variant_id); qty = int(qty)
        if qty <= 0: self._data.pop(key, None)
        else: self._data[key] = qty
        self._save()
    def remove(self, variant_id: int):
        self._data.pop(str(variant_id), None); self._save()
    def items(self) -> List[CartLine]:
        ids = [int(k) for k in self._data.keys()]
        variants = Variant.objects.select_related("product").in_bulk(ids)
        lines: List[CartLine] = []
        for k, qty in self._data.items():
            v = variants.get(int(k))
            if v: lines.append(CartLine(variant=v, qty=int(qty)))
        return lines
    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self.items()), Decimal("0"))
    @property
    def count(self) -> int:
        return sum(int(q) for q in self._data.values())
