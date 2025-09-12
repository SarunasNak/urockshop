# catalog/views.py — SSR: produktų sąrašas ir detalė (su SEO kontekstu)
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.utils.html import strip_tags
from django.utils.text import Truncator

from .models import Product, Category, Variant, ProductImage


# ----- Helperiai -------------------------------------------------------------

def _abs_url(request, url: str | None) -> str | None:
    """Padaro absoliutų URL; priima ir /media/... ir pilnus URL. Jei None – grąžina None."""
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    # užtikrinam, kad prasideda nuo '/'
    if not url.startswith("/"):
        url = "/" + url
    return request.build_absolute_uri(url)

def _truncate(text: str, length: int) -> str:
    return Truncator(strip_tags(text or "")).chars(length)

def _build_canonical(request, allowed=("category", "page")) -> str:
    """
    Sudaro kanoninį URL iš esamo prašymo, paliekant tik leidžiamus parametrus.
    - Paieškos ("q") specialiai NEįtraukiame į canonical (kad neindeksuotume visų kombinacijų).
    - Jei page=1, parametrą pašaliname.
    """
    parts = urlsplit(request.build_absolute_uri())
    qs_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False) if k in allowed]

    # drop page=1
    qs_pairs = [(k, v) for (k, v) in qs_pairs if not (k == "page" and v in ("1", 1))]

    query = urlencode(qs_pairs)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


# ----- Views -----------------------------------------------------------------

class ProductListView(View):
    template_name = "shop/list.html"
    paginate_by = 12

    def get(self, request):
        q = (request.GET.get("q") or "").strip()
        current_category = (request.GET.get("category") or "").strip()

        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.all()),
                Prefetch("variants", queryset=Variant.objects.filter(is_active=True).order_by("price")),
            )
            .order_by("-id")
        )
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if current_category:
            qs = qs.filter(category__slug=current_category)

        paginator = Paginator(qs, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page") or 1)

        # --- SEO logika ---
        # Bazinis pavadinimas pagal kategoriją/paiešką
        base_title = "Parduotuvė – Urock"
        meta_description = "Mūsų produktų katalogas."
        og_type = "website"

        if current_category:
            try:
                cat = Category.objects.get(slug=current_category)
                base_title = f"{cat.name} – Urock"
                if getattr(cat, "description", None):
                    meta_description = _truncate(cat.description, 160)
            except Category.DoesNotExist:
                pass

        if q:
            # Paieškos puslapiai: noindex, canonical be ?q
            base_title = f"Paieška „{q}“ – Urock"
            meta_description = f"Rezultatai užklausai „{q}“."
            meta_robots = "noindex,follow"
            canonical_url = _build_canonical(request, allowed=("category", "page"))
        else:
            meta_robots = "index,follow"
            canonical_url = _build_canonical(request, allowed=("category", "page"))

        # Jei puslapis >1, pridėkim numerį į title (ne canonical, canonical jau tvarkingas)
        if page_obj.number and page_obj.number > 1:
            meta_title = f"{base_title} – psl. {page_obj.number}"
        else:
            meta_title = base_title

        ctx = {
            "page_obj": page_obj,
            "categories": Category.objects.all().order_by("name"),
            "current_category": current_category,
            "q": q,

            # SEO kontekstas
            "meta_title": meta_title,
            "meta_description": meta_description,
            "meta_robots": meta_robots,
            "canonical_url": canonical_url,
            "og_type": og_type,
            "og_title": meta_title,
            "og_description": meta_description,
            # "og_image": _abs_url(request, static('img/catalog_og.jpg')),  # jei turite
        }
        return render(request, self.template_name, ctx)


class ProductDetailView(View):
    template_name = "shop/detail.html"

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.filter(is_active=True).select_related("category").prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.all()),
                Prefetch("variants", queryset=Variant.objects.filter(is_active=True)),
            ),
            slug=slug,
        )

        desc = _truncate(getattr(product, "description", "") or "", 160)
        long_desc = _truncate(getattr(product, "description", "") or "", 200)

        # --- og:image: bandome main_image_url, tada pirmą iš images ---
        main_img = getattr(product, "main_image_url", None)
        if not main_img:
            first_img = product.images.first() if hasattr(product, "images") else None
            if first_img:
                # jei yra ImageField "image" -> imame .url
                if hasattr(first_img, "image") and getattr(first_img.image, "url", None):
                    main_img = first_img.image.url
                # jei modelyje yra 'url' atributas -> naudok jį
                elif getattr(first_img, "url", None):
                    main_img = first_img.url

        ctx = {
            "product": product,

            # SEO kontekstas
            "meta_title": product.name,
            "meta_description": desc,
            "meta_robots": "index,follow",
            "canonical_url": request.build_absolute_uri(),

            # OG/Twitter
            "og_type": "product",
            "og_title": product.name,
            "og_description": long_desc,
            # ↓↓↓ svarbu: nebe str(main_img), o tiesiai main_img; _abs_url padarys absoliutų
            "og_image": _abs_url(request, main_img) if main_img else None,
        }
        return render(request, self.template_name, ctx)

