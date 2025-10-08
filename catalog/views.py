# catalog/views.py — SSR: produktų sąrašas ir detalė (su SEO kontekstu)
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Count
from django.utils.html import strip_tags
from django.utils.text import Truncator
from .models import Product, Category, Variant, ProductImage, Size

# ----- Helperiai -------------------------------------------------------------

def _abs_url(request, url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if not url.startswith("/"):
        url = "/" + url
    return request.build_absolute_uri(url)

def _truncate(text: str, length: int) -> str:
    return Truncator(strip_tags(text or "")).chars(length)

def _build_canonical(request, allowed=("category", "page")) -> str:
    parts = urlsplit(request.build_absolute_uri())
    qs_pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False) if k in allowed]
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

        # dydžio filtravimas: vienas arba keli (?size=s&size=m)
        sizes_selected = request.GET.getlist("size")
        sizes_selected = [s.strip().lower() for s in sizes_selected if s.strip()]

        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category", "size")
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

        if sizes_selected:
            qs = qs.filter(size__slug__in=sizes_selected)

        paginator = Paginator(qs, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page") or 1)

        # --- SEO ---
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
            meta_title = f"Paieška „{q}“ – Urock"
            meta_description = f"Rezultatai užklausai „{q}“."
            meta_robots = "noindex,follow"
            canonical_url = _build_canonical(request, allowed=("category", "page"))
        else:
            meta_robots = "index,follow"
            meta_title = base_title if page_obj.number == 1 else f"{base_title} – psl. {page_obj.number}"
            canonical_url = _build_canonical(request, allowed=("category", "page"))

        ctx = {
            "page_obj": page_obj,
            "products": page_obj.object_list,    # patogu šablonams, jei nori naudoti 'products'
            "categories": Category.objects.all().order_by("name"),
            "current_category": current_category,
            "q": q,

            # Filtrų duomenys
            "sizes": Size.objects.filter(is_active=True).order_by("order", "label"),
            "sizes_selected": sizes_selected,

            # SEO
            "meta_title": meta_title,
            "meta_description": meta_description,
            "meta_robots": meta_robots,
            "canonical_url": canonical_url,
            "og_type": og_type,
            "og_title": meta_title,
            "og_description": meta_description,
        }
        return render(request, self.template_name, ctx)


class ProductDetailView(View):
    template_name = "shop/detail.html"

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.filter(is_active=True)
            .select_related("category", "size")
            .prefetch_related(
                Prefetch("images", queryset=ProductImage.objects.all().order_by("sort", "id")),
                Prefetch("variants", queryset=Variant.objects.filter(is_active=True)),
            ),
            slug=slug,
        )

        # Pagrindinė OG nuotrauka: main_image, kitaip pirma iš galerijos
        main_img_url = None
        if getattr(product, "main_image", None) and getattr(product.main_image, "url", None):
            main_img_url = product.main_image.url
        else:
            first_img = product.images.first()
            if first_img and getattr(first_img, "image", None) and getattr(first_img.image, "url", None):
                main_img_url = first_img.image.url

        # Panašūs produktai: M2M, o jei tuščia – iš tos pačios kategorijos
        related = list(product.related_products.all()[:8])
        if not related:
            related = list(
                Product.objects.filter(is_active=True, category=product.category)
                .exclude(pk=product.pk)
                .order_by("-created_at")[:8]
            )

        desc = _truncate(getattr(product, "description", "") or "", 160)
        long_desc = _truncate(getattr(product, "description", "") or "", 200)

        ctx = {
            "product": product,
            "related_products": related,

            # SEO / OG
            "meta_title": product.name,
            "meta_description": desc,
            "meta_robots": "index,follow",
            "canonical_url": request.build_absolute_uri(),
            "og_type": "product",
            "og_title": product.name,
            "og_description": long_desc,
            "og_image": _abs_url(request, main_img_url) if main_img_url else None,
        }

        # Aliasas, jei šablone kur nors naudojamas 'object'
        ctx.setdefault("object", product)

        return render(request, self.template_name, ctx)

