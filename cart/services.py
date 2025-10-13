# cart/services.py
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Dict, Any
from time import time
from django.conf import settings
from catalog.models import Variant

CART_SESSION_KEY = "cart"
# kiek valandų laikyti prekę krepšelyje (0 = niekada nevalyti automatiškai)
CART_ITEM_TTL_HOURS = getattr(settings, "CART_ITEM_TTL_HOURS", 48)

@dataclass
class CartLine:
    variant: Variant
    qty: int
    intent: str = "buy"   # jei nenaudoji – paliks pagal nutylėjimą

    @property
    def line_total(self) -> Decimal:
        return (self.variant.price or Decimal("0")) * self.qty

    @property
    def price(self) -> Decimal:
        return self.variant.price or Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.line_total

    @property
    def image_url(self) -> str:
        """
        Naudojama šablone kaip {{ it.image_url }}.
        Pirmiausia main_image, tada pirma galerijos nuotrauka, kitaip tuščia.
        """
        p = self.variant.product
        try:
            if getattr(p, "main_image", None) and getattr(p.main_image, "url", None):
                return p.main_image.url
            first = p.images.first()
            if first and getattr(first, "image", None) and getattr(first.image, "url", None):
                return first.image.url
        except Exception:
            pass
        return ""

class Cart:
    """
    Sesijoje laikom nauju formatu:
    {
        "<variant_id>": {"qty": 1, "intent": "purchase"|"try_on", "ts": <unix>},
        ...
    }
    Senas formatas (tik int qty) migruojamas į naują su intent='purchase'.
    """
    def __init__(self, request):
        self.request = request
        self.session = request.session
        raw: Dict[str, Any] = self.session.get(CART_SESSION_KEY, {})
        self._data: Dict[str, Dict[str, Any]] = {}
        now = int(time())

        # normalizacija + migracija
        for k, v in raw.items():
            key = str(k)
            if isinstance(v, int):
                if v > 0:
                    self._data[key] = {"qty": int(v), "intent": "purchase", "ts": now}
            elif isinstance(v, dict):
                qty = int(v.get("qty", 1))
                if qty > 0:
                    self._data[key] = {
                        "qty": qty,
                        "intent": v.get("intent", "purchase"),
                        "ts": int(v.get("ts", now)),
                    }

        # auto išvalymas pagal TTL
        self._purge_expired(now)

    # ----------------- vidinės -----------------

    def _save(self):
        self.session[CART_SESSION_KEY] = self._data
        self.session.modified = True

    def _purge_expired(self, now: int | None = None):
        if now is None:
            now = int(time())
        ttl_sec = int(CART_ITEM_TTL_HOURS) * 3600 if CART_ITEM_TTL_HOURS else 0
        if ttl_sec <= 0:
            return
        changed = False
        for key in list(self._data.keys()):
            ts = int(self._data[key].get("ts", now))
            if now - ts > ttl_sec:
                del self._data[key]
                changed = True
        if changed:
            self._save()

    # ----------------- API (view'ams) -----------------

    def add(self, variant_id: int, qty: int = 1, intent: str = "purchase"):
        key = str(variant_id)
        now = int(time())
        self._data[key] = {
            "qty": max(1, int(qty)),
            "intent": "try_on" if intent == "try_on" else "purchase",
            "ts": now,
        }
        self._save()

    def set(self, variant_id: int, qty: int):
        key = str(variant_id)
        qty = int(qty)
        if qty <= 0:
            self._data.pop(key, None)
        else:
            row = self._data.get(key, {"intent": "purchase", "ts": int(time())})
            row["qty"] = qty
            self._data[key] = row
        self._save()

    def set_intent(self, variant_id: int, intent: str):
        key = str(variant_id)
        if key in self._data:
            self._data[key]["intent"] = "try_on" if intent == "try_on" else "purchase"
            self._data[key]["ts"] = int(time())
            self._save()

    def remove(self, variant_id: int):
        self._data.pop(str(variant_id), None)
        self._save()

    # ----------------- Naudinga šablonams / procesoriui -----------------

    def items(self) -> List[CartLine]:
        ids = [int(k) for k in self._data.keys()]
        if not ids:
            return []
        variants = Variant.objects.select_related("product").in_bulk(ids)
        lines: List[CartLine] = []
        for k, row in self._data.items():
            v = variants.get(int(k))
            if not v:
                continue
            lines.append(
                CartLine(
                    variant=v,
                    qty=int(row.get("qty", 1)),
                    intent=row.get("intent", "purchase"),
                )
            )
        return lines

    # --- Filtravimas pagal intent ---

    def try_on_items(self) -> List[CartLine]:
        return [line for line in self.items() if line.intent == "try_on"]

    def purchase_items(self) -> List[CartLine]:
        return [line for line in self.items() if line.intent == "purchase"]

    @property
    def try_on_empty(self) -> bool:
        return not any(row.get("intent") == "try_on" for row in self._data.values())

    @property
    def purchase_empty(self) -> bool:
        return not any(row.get("intent") == "purchase" for row in self._data.values())

    # --- Išvalymas pagal intent ---

    def clear_try_on(self):
        keys = [k for k, r in self._data.items() if r.get("intent") == "try_on"]
        for k in keys:
            self._data.pop(k, None)
        self._save()

    def clear_purchase(self):
        keys = [k for k, r in self._data.items() if r.get("intent") == "purchase"]
        for k in keys:
            self._data.pop(k, None)
        self._save()

    def clear_all(self):
        self._data = {}
        self._save()

    # --- Momentinė „snapshot“ – saugojimui į DB / laiškams ---

    def snapshot(self, intent: str = "try_on") -> list[dict]:
        """
        Momentinė krepšelio kopija DB/laiškams.
        Grąžina: variant_id, product_id, sku, name, brand, size, price, image_url, qty.
        - name parenkamas saugiai: title -> name -> slug -> "Prekė"
        - brand bandom paimti tiek iš FK su .name, tiek iš tekstinio p.brand
        """
        lines = self.try_on_items() if intent == "try_on" else self.purchase_items()
        out: list[dict] = []

        for ln in lines:
            v = ln.variant
            p = v.product

            # Produkto pavadinimas – atspari seka
            product_title = (
                getattr(p, "title", None)
                or getattr(p, "name", None)
                or getattr(p, "slug", None)
                or "Prekė"
            )

            # Brand (toleruojam abi schemas: FK su .name arba paprastas char field)
            brand = ""
            try:
                if hasattr(p, "brand") and getattr(p, "brand"):
                    brand = getattr(p.brand, "name", None) or ""
                    if not brand:
                        brand = getattr(p, "brand", "") or ""
            except Exception:
                brand = ""

            size = getattr(v, "size_display", None) or getattr(v, "size", "") or ""
            sku  = getattr(v, "sku", "") or ""

            out.append({
                "variant_id": v.id,
                "product_id": p.id,
                "sku": sku,
                "name": product_title,
                "brand": brand,                       # <- nauja
                "size": size,
                "price": str(ln.price or Decimal("0")),
                "image_url": ln.image_url,
                "qty": ln.qty,
            })

        return out

    # --- Suvestinės / badge’ams ---

    @property
    def total(self) -> Decimal:
        return sum((line.line_total for line in self.items()), Decimal("0"))

    @property
    def count_unique(self) -> int:
        return len(self._data)

    @property
    def purchase_count(self) -> int:
        return sum(1 for line in self.items() if line.intent == "purchase")

    @property
    def try_on_count(self) -> int:
        return sum(1 for line in self.items() if line.intent == "try_on")

    @property
    def count(self) -> int:
        return self.count_unique
