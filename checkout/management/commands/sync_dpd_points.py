import os
import json
import base64
import tempfile
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Atsisiunčia DPD pickup/locker taškus iš eSiunta API ir išsaugo JSON faile."

    def handle(self, *args, **options):
        auth_url = getattr(settings, "DPD_AUTH_URL", "https://esiunta.dpd.lt/api/v1/auth/tokens")
        lockers_url = getattr(settings, "DPD_POINTS_URL", "https://esiunta.dpd.lt/api/v1/lockers")
        country = getattr(settings, "DPD_COUNTRY", "LT")

        username = getattr(settings, "DPD_USERNAME", "")
        password = getattr(settings, "DPD_PASSWORD", "")
        cache_file = getattr(settings, "DPD_CACHE_FILE", "checkout/data/dpd_lt_pickup_points.json")

        if not username or not password:
            self.stderr.write("❌ Trūksta DPD_USERNAME arba DPD_PASSWORD aplinkos kintamųjų.")
            return

        # 1️⃣ Gauti Bearer token
        token = self._get_token(auth_url, username, password)
        if not token:
            self.stderr.write("❌ Nepavyko gauti DPD API tokeno.")
            return

        # 2️⃣ Gauti locker punktus
        self.stdout.write(f"➡️  Gaunam DPD duomenis iš: {lockers_url}?countryCode={country}")
        points = self._get_lockers(lockers_url, token, country)

        if not points:
            self.stderr.write("❌ Nepavyko gauti DPD locker duomenų (tuščias atsakas).")
            return

        # 3️⃣ Išsaugoti JSON faile
        self._save_to_file(points, cache_file)
        self.stdout.write(self.style.SUCCESS(f"✅ Sėkmingai sinchronizuota {len(points)} DPD taškų."))

    # ------------------------------------------------------
    def _get_token(self, url, username, password):
        """Grąžina Bearer token pagal DPD eSiunta dokumentaciją."""
        headers = {
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(f"{username}:{password}".encode()).decode(),
            "Content-Type": "application/json",
        }
        body = json.dumps({"name": "UrockIntegration", "ttl": 9999999999}).encode()

        req = Request(url, headers=headers, data=body, method="POST")
        try:
            with urlopen(req, timeout=20) as r:
                data = json.load(r)
                token = data.get("token") or data.get("secretId")
                if token:
                    self.stdout.write("🔑 Gautas DPD API token.")
                    return token
                else:
                    self.stderr.write("⚠️  Nepavyko išgauti token iš atsakymo.")
                    return None
        except HTTPError as e:
            self.stderr.write(f"❌ HTTP klaida gaunant token: {e.code} {e.reason}")
        except URLError as e:
            self.stderr.write(f"❌ Tinklo klaida gaunant token: {e}")
        except Exception as e:
            self.stderr.write(f"❌ Nežinoma klaida gaunant token: {e}")
        return None

    # ------------------------------------------------------
    def _get_lockers(self, url, token, country):
        """Grąžina visų locker taškų sąrašą."""
        headers = {
            "Accept": "application/json+fulldata",
            "Authorization": f"Bearer {token}",
        }
        full_url = f"{url}?countryCode={country}"
        req = Request(full_url, headers=headers, method="GET")

        try:
            with urlopen(req, timeout=30) as r:
                raw = json.load(r)
                # 🟢 Palaikyk abi formas: list ir dict
                if isinstance(raw, list):
                    items = raw
                else:
                    items = raw.get("data") or raw.get("points") or raw

                mapped = []
                for p in items:
                    addr = p.get("address") or {}
                    mapped.append({
                        "id": str(p.get("id") or p.get("pudoId") or p.get("parcelShopId")),
                        "name": p.get("name") or p.get("label") or "DPD paštomatas",
                        "address": addr.get("street") or p.get("address") or "",
                        "city": addr.get("city") or p.get("city") or "",
                    })
                return [m for m in mapped if m["id"] and m["city"]]
        except HTTPError as e:
            self.stderr.write(f"❌ HTTP klaida gaunant lockers: {e.code} {e.reason}")
        except Exception as e:
            self.stderr.write(f"❌ Klaida gaunant lockers: {e}")
        return []

    # ------------------------------------------------------
    def _save_to_file(self, data, path):
        """Išsaugo JSON į failą atominiu būdu."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        finally:
            try:
                os.remove(tmp)
            except FileNotFoundError:
                pass
