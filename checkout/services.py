# checkout/services.py
from __future__ import annotations
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Iterable, List, Dict


# -------------------------------
# Duomenų modelis
# -------------------------------
@dataclass
class DpdPickup:
    id: str
    name: str
    address: str
    city: str


# -------------------------------
# Vidaus helperiai
# -------------------------------
def _data_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # .../checkout
    return os.path.join(base_dir, "data", "dpd_lt_pickup_points.json")


def _load_dpd_points() -> List[Dict]:
    with open(_data_path(), "r", encoding="utf-8") as f:
        return json.load(f)


_POINTS_CACHE: Optional[List[Dict]] = None


def _ensure_cache() -> List[Dict]:
    global _POINTS_CACHE
    if _POINTS_CACHE is None:
        _POINTS_CACHE = _load_dpd_points()
    return _POINTS_CACHE


def _norm(s: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# -------------------------------
# Viešos funkcijos (naudok views/JS)
# -------------------------------
def get_all_dpd_points() -> List[Dict]:
    """
    Grąžina visą paštomatų sąrašą (dict'ai su id/name/address/city).
    Skirta JSON API ir FE modalui.
    """
    return list(_ensure_cache())


def filter_points(query: Optional[str] = None, city: Optional[str] = None) -> List[Dict]:
    """
    Patogus filtravimas FE’ui arba backendui.
    - query: ieško pagal pavadinimą/adresą/miestą (case-insensitive, contains)
    - city: jeigu paduotas, pirmiausia filtruojam pagal miestą
    """
    pts = _ensure_cache()
    q = _norm(query)
    c = _norm(city)

    if c:
        pts = [p for p in pts if _norm(p.get("city")) == c]

    if q:
        pts = [
            p for p in pts
            if q in _norm(p.get("name")) or q in _norm(p.get("address")) or q in _norm(p.get("city"))
        ]
    return pts


def find_point_by_id(point_id: str) -> Optional[DpdPickup]:
    """
    Suranda paštomatą pagal ID. Naudinga validacijai, kai FE atsiunčia id.
    """
    pid = (point_id or "").strip()
    if not pid:
        return None
    for p in _ensure_cache():
        if str(p.get("id")) == pid:
            return DpdPickup(
                id=p["id"],
                name=p.get("name", ""),
                address=p.get("address", ""),
                city=p.get("city", ""),
            )
    return None


def select_best_dpd_point(city: str = "", postal_code: str = "") -> Optional[DpdPickup]:
    """
    Fallback automatiniam parinkimui (kai FE nepasirenka ranka).
    1) tikslus miesto sutapimas
    2) „contains“ pagal miestą
    3) pirmas sąraše (saugus default)
    """
    pts = _ensure_cache()
    city_n = _norm(city)

    # 1) tikslus atitikimas
    same_city = [p for p in pts if _norm(p.get("city")) == city_n]
    if same_city:
        p = same_city[0]
        return DpdPickup(id=p["id"], name=p["name"], address=p["address"], city=p["city"])

    # 2) fuzzy contains
    contains = [p for p in pts if city_n and city_n in _norm(p.get("city"))]
    if contains:
        p = contains[0]
        return DpdPickup(id=p["id"], name=p["name"], address=p["address"], city=p["city"])

    # 3) fallback – pirmas
    if pts:
        p = pts[0]
        return DpdPickup(id=p["id"], name=p["name"], address=p["address"], city=p["city"])

    return None
