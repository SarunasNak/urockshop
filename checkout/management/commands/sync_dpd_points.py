import json, os, tempfile
from urllib.request import Request, urlopen
from django.core.management.base import BaseCommand
from django.conf import settings


def _headers():
    """Sukuriam headerius (jei reikalingas autorizacijos tokenas)."""
    h = {"Accept": "application/json"}
    if settings.DPD_POINTS_AUTH:
        h["Authorization"] = settings.DPD_POINTS_AUTH
    return h


def _map_record(p):
    """Sutvarkom laukus iš DPD JSON į mūsų struktūrą."""
    addr = p.get("address") or {}
    loc = p.get("location") or {}
    return {
        "id": str(p.get("id") or p.get("parcelShopId") or p.get("pudoId")),
        "name": p.get("name") or p.get("label") or p.get("description") or "DPD punktas",
        "address": addr.get("street") or addr.get("addressLine") or p.get("address") or "",
        "city": addr.get("city") or p.get("city") or "",
        # galima ateity saugoti ir koordinates
        # "lat": loc.get("lat"), "lng": loc.get("lng"),
    }


class Command(BaseCommand):
    help = "Atsisiunčia DPD pickup/locker taškus ir išsaugo JSON faile (lokali cache)."

    def handle(self, *args, **opts):
        url = settings.DPD_POINTS_URL
        if not url:
            self.stderr.write("❌ DPD_POINTS_URL nenurodytas settingsuose ar env faile.")
            return

        self.stdout.write(f"➡️  Gaunam DPD duomenis iš: {url}")

        # 1. Paimam duomenis iš DPD feedo
        req = Request(url, headers=_headers())
        with urlopen(req, timeout=30) as r:
            raw = json.load(r)

        # 2. Ištraukiam sąrašą
        items = raw.get("points") or raw.get("data") or raw
        mapped = [_map_record(p) for p in items if p]
        mapped = [m for m in mapped if m["id"] and m["name"] and m["city"]]

        # 3. Išsaugom atominiu būdu
        os.makedirs(os.path.dirname(settings.DPD_CACHE_FILE), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(settings.DPD_CACHE_FILE))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(mapped, f, ensure_ascii=False, indent=2)
            os.replace(tmp, settings.DPD_CACHE_FILE)
        finally:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass

        self.stdout.write(self.style.SUCCESS(f"✅ Sėkmingai sinchronizuota {len(mapped)} DPD taškų."))
