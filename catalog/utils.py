# catalog/utils.py
from typing import Iterable, List
from django.db.models import QuerySet
from .models import Product, Size, Category
from django.db.models import Q

ACCESSORIES_SLUG = "aksesuarai"  # atnaujink, jei pas tave kitas

def get_next_size(size: Size) -> Size | None:
    if not size:
        return None
    return Size.objects.filter(is_active=True, order__gt=size.order).order_by("order").first()

def pick_from(seq: Iterable, picked_ids: List[int], limit: int) -> List[int]:
    """
    Paimam iki 'limit' elementų id (pk) iš 'seq' (gali būti queryset'as su objektais
    arba values_list(...) su int’ais) ir papildom 'picked_ids' be dublikatų.
    """
    left = limit - len(picked_ids)
    if left <= 0:
        return picked_ids

    # jei seq yra QuerySet – iteruojam objektais; jei ints – tiesiog ints
    # paimam šiek tiek daugiau nei reikia, kad galėtume atmesti dublikatus
    head = seq[: left * 3] if hasattr(seq, '__getitem__') else seq

    for item in head:
        pid = getattr(item, "pk", item)  # jei objektas -> pk, jei int -> pats
        try:
            pid = int(pid)
        except Exception:
            continue
        if pid not in picked_ids:
            picked_ids.append(pid)
            if len(picked_ids) >= limit:
                break
    return picked_ids

def auto_related_for(product: Product, limit: int = 4) -> List[Product]:
    base = Product.objects.filter(is_active=True).exclude(pk=product.pk)
    base = base.select_related("category", "size")

    same_cat = base.filter(category=product.category)
    same_size = product.size
    next_size = get_next_size(same_size) if same_size else None

    picked_ids: List[int] = []

    # 1) ta pati kategorija + tas pats dydis
    if same_size:
        qs1 = same_cat.filter(size=same_size).order_by("-created_at")
        picked_ids = pick_from(qs1, picked_ids, limit)

    # 2) ta pati kategorija + vienu dydžiu didesnis
    if len(picked_ids) < limit and next_size:
        qs2 = same_cat.filter(size=next_size).order_by("-created_at")
        picked_ids = pick_from(qs2, picked_ids, limit)

    # 3) kitos kategorijos + tas pats dydis
    if len(picked_ids) < limit and same_size:
        qs3 = base.exclude(category=product.category).filter(size=same_size).order_by("-created_at")
        picked_ids = pick_from(qs3, picked_ids, limit)

    # 3.5) užpildymas, jei dar trūksta
    if len(picked_ids) < limit:
        qs4 = base.order_by("-created_at")
        picked_ids = pick_from(qs4, picked_ids, limit)

    # 4) visada pabandom įterpti 1 aksesuarą
    acc_cat = Category.objects.filter(Q(slug=ACCESSORIES_SLUG) | Q(name__icontains="aksesuar")).first()
    if acc_cat:
        acc_qs = base.filter(category=acc_cat).exclude(pk__in=picked_ids).order_by("-created_at")
        acc = acc_qs.first()
        if acc:
            if len(picked_ids) >= limit:
                picked_ids[-1] = acc.pk
            else:
                picked_ids.append(acc.pk)

    # grąžinam produktus originalia eiliškumo tvarka
    objs = list(Product.objects.filter(pk__in=picked_ids))
    pos = {pid: i for i, pid in enumerate(picked_ids)}
    objs.sort(key=lambda o: pos.get(o.pk, 10**9))
    return objs[:limit]

# ----------------------------------------------------------
# Balansuotas produktų rodymas (ant modelio / ant žemės)
# ----------------------------------------------------------

# ----------------------------------------------------------
# Balansuotas produktų rodymas (ant modelio / ant žemės)
# ----------------------------------------------------------

def get_balanced_products(products, per_page: int = 12) -> list[Product]:
    """
    Globaliai subalansuoja visą produktų sąrašą,
    kad on_model būtų tolygiai paskirstyti per visus puslapius.
    """

    products = list(products)

    if not products:
        return []

    # atskiriam grupes
    model_products = [p for p in products if p.on_model]
    ground_products = [p for p in products if not p.on_model]

    total = len(products)

    if not model_products or not ground_products:
        # jei viena grupė tuščia – grąžinam kaip yra
        return products

    model_count = len(model_products)
    model_ratio = model_count / total

    result = []

    model_i = 0
    ground_i = 0

    model_step = 1 / model_ratio if model_ratio > 0 else float("inf")
    next_model_at = 0.0

    for i in range(total):

        if i >= next_model_at and model_i < model_count:
            result.append(model_products[model_i])
            model_i += 1
            next_model_at += model_step

        elif ground_i < len(ground_products):
            result.append(ground_products[ground_i])
            ground_i += 1

        elif model_i < model_count:
            result.append(model_products[model_i])
            model_i += 1

    return result
