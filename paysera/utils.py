# paysera/utils.py
import base64
import hashlib
import urllib.parse
from django.conf import settings

# Oficiali Paysera mokėjimų forma
PAYMENT_URL = "https://bank.paysera.com/pay/"

# --- Base64 helperiai ---------------------------------------------------------

def _b64_urlsafe_encode(s: str) -> str:
    """
    Klasikinis base64, po to darom URL-safe pakeitimus:
      + -> -, / -> _
    (padding '=' paliekam; naršyklės vistiek teisingai su-URL-enkodins)
    """
    b64 = base64.b64encode(s.encode("utf-8")).decode("ascii")
    return b64.replace("+", "-").replace("/", "_")

def _b64_urlsafe_decode(b64: str) -> str:
    """
    Tolerantiškas dekodavimas:
    - atstatom URL-safe simbolius
    - pridedam trūkstamą padding'ą '='
    """
    s = b64.replace("-", "+").replace("_", "/")
    # padding (iki ilgio, kuris dalinasi iš 4)
    pad = (-len(s)) % 4
    if pad:
        s = s + ("=" * pad)
    return base64.b64decode(s).decode("utf-8")

# --- Sign helperiai -----------------------------------------------------------

def _sign_md5_data_plus_pwd(data: str) -> str:
    """md5(data + password) — aprašyta naujesnėje specifikacijoje (1.6)."""
    raw = (data + settings.PAYSERA_SIGN_PASSWORD).encode("utf-8")
    return hashlib.md5(raw).hexdigest()

def _sign_md5_pwd_data_pwd(data: str) -> str:
    """md5(password + data + password) — istoriškai naudotas variantas (libwebtopay)."""
    raw = (settings.PAYSERA_SIGN_PASSWORD + data + settings.PAYSERA_SIGN_PASSWORD).encode("utf-8")
    return hashlib.md5(raw).hexdigest()

# -----------------------------------------------------------------------------

def make_payment_data(params: dict) -> dict:
    """
    SS1 siuntimui:
      data = base64(urlencode(params)) su URL-safe pakeitimais
      sign = md5(data + password)   # praktikoje su 1.6 veikia būtent šis variantas
    """
    clean = {k: str(v) for k, v in params.items() if v is not None}
    qs = urllib.parse.urlencode(clean)              # a=b&c=d...
    data = _b64_urlsafe_encode(qs)
    sign = _sign_md5_data_plus_pwd(data)
    return {"data": data, "sign": sign}

def parse_callback(payload: dict) -> dict:
    """
    Priima request.POST/GET ir grąžina dekoduotus parametrus (dict), patikrinus sign.

    Palaiko abu lauko pavadinimus:
      - 'sign' (senesnis)
      - 'ss1' / 'ss2' (dažnai naudojami grįžimo/SS2 atvejais)

    Ir abi MD5 formules:
      - md5(data + password)
      - md5(password + data + password)
    """
    # Kai payload ateina kaip QueryDict, get() grąžins string'ą (gerai).
    data = payload.get("data", "") or ""
    sig  = payload.get("sign") or payload.get("ss1") or payload.get("ss2") or ""

    if not data or not sig:
        raise ValueError("Missing data/sign")

    expected_new = _sign_md5_data_plus_pwd(data)
    expected_old = _sign_md5_pwd_data_pwd(data)

    if sig not in (expected_new, expected_old):
        raise ValueError("Bad sign")

    # Dekoduojam 'data' -> "a=b&c=d..." -> dict
    decoded = _b64_urlsafe_decode(data)
    parsed  = urllib.parse.parse_qs(decoded, keep_blank_values=True)
    flat    = {k: (v[0] if isinstance(v, list) and v else "") for k, v in parsed.items()}
    return flat
