from django.core.paginator import Paginator
from django.db.models import Q, Prefetch, Case, When, IntegerField
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.views import View
from .utils import auto_related_for
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from .utils import get_balanced_products

from django.shortcuts import redirect
from django.http import Http404

from .models import Category, Product, ProductImage, Size

from .models import PrivateCollection
from catalog.models import PrivateProduct


from checkout.models import Order

# ----- Helperiai -------------------------------------------------------------

def _abs_url(request, url: str | None) -> str | None:
    """Padaro absoliutų URL; priima ir /media/... ir pilnus URL. Jei None – grąžina None."""
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
    """
    Sudaro kanoninį URL iš esamo prašymo, paliekant tik leidžiamus parametrus.
    - Paieškos ("q") specialiai NEįtraukiame į canonical.
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
        size_selected = (request.GET.get("size") or "").strip().lower()

        images_qs = ProductImage.objects.all().order_by("sort", "id")

        qs = (
            Product.objects.filter(is_active=True)
            .select_related("category", "size")
            .prefetch_related(Prefetch("images", queryset=images_qs))
            .order_by("-id")
        )

        # Paieška
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

        # Kategorija
        if current_category:
            qs = qs.filter(category__slug=current_category)

        # DYDIS: pasirinktas + sekantis + ONE SIZE  + custom rikiavimas
        if size_selected:
            all_sizes = list(Size.objects.filter(is_active=True).order_by("order", "label"))
            slugs_lower = [s.slug.lower() for s in all_sizes]

            expanded = []
            selected_slug = None
            next_slug = None

            if size_selected in slugs_lower:
                idx = slugs_lower.index(size_selected)
                selected_slug = all_sizes[idx].slug                    # pvz., "m"
                expanded.append(selected_slug)
                if idx + 1 < len(all_sizes):                           # sekantis dydis, pvz., "l"
                    next_slug = all_sizes[idx + 1].slug
                    expanded.append(next_slug)

            # ONE SIZE variantai
            onesize_slugs = list(
                Size.objects.filter(slug__in=["one-size", "onesize"]).values_list("slug", flat=True)
            )
            expanded.extend(onesize_slugs)

            if expanded:
                # visuomet pridedam UNI variantus prie pasirinkto filtro
                uni_slugs = list(
                    Size.objects.filter(slug__in=["one-size", "onesize", "uni"]).values_list("slug", flat=True)
                )
                expanded.extend(uni_slugs)

                qs = qs.filter(size__slug__in=expanded)

                # rikiavimas: pirma selected + ONE SIZE, tada next (po to – kiti, jei būtų)
                whens = []
                if selected_slug:
                    whens.append(When(size__slug=selected_slug, then=0))
                if onesize_slugs:
                    whens.append(When(size__slug__in=onesize_slugs, then=1))
                if next_slug:
                    whens.append(When(size__slug=next_slug, then=2))

                # ⚠️ TIK annotate čia, be order_by()
                qs = qs.annotate(
                    size_priority=Case(*whens, default=9, output_field=IntegerField())
                )
        else:
            # jei dydis nepasirinktas – vis tiek duokim numatytą prioritetą
            qs = qs.annotate(
                size_priority=Case(default=9, output_field=IntegerField())
            )

        # Rikiuojam pagal prioritetą ir naujumą
        qs = qs.order_by("size_priority", "-created_at")

        # ✅ 1. Paimam VISUS produktus
        all_products = list(qs)

        # ✅ 2. GLOBALIAI subalansuojam
        balanced_all = get_balanced_products(all_products)

        # ✅ 3. Tik tada puslapiuojam
        paginator = Paginator(balanced_all, self.paginate_by)
        page_number = request.GET.get("page") or 1
        page_obj = paginator.get_page(page_number)

        page_range = paginator.get_elided_page_range(
            number=page_obj.number,
            on_each_side=1,
            on_ends=1
        )

        # --- SEO ---
        base_title = "Parduotuvė – Urock"
        meta_description = "Mūsų produktų katalogas."
        og_type = "website"

        if current_category:
            try:
                cat = Category.objects.get(slug=current_category)
                base_title = f"{cat.name} – Urock"
                if getattr(cat, "description", None):
                    meta_description = Truncator(strip_tags(cat.description)).chars(160)
            except Category.DoesNotExist:
                pass

        if q:
            meta_title = f"Paieška „{q}“ – Urock"
            meta_description = f"Rezultatai užklausai „{q}“."
            meta_robots = "noindex,follow"
            canonical_url = _build_canonical(request, allowed=("category", "page"))
        else:
            meta_title = base_title if page_obj.number == 1 else f"{base_title} – psl. {page_obj.number}"
            meta_robots = "index,follow"
            canonical_url = _build_canonical(request, allowed=("category", "page"))

        # Kontekstas
        ctx = {
            "page_obj": page_obj,
            "page_range": page_range,  # NEW: perduodam į šabloną
            "products": page_obj.object_list,

            # filtrams
            "categories": Category.objects.all().order_by("name"),
            "current_category": current_category,
            "sizes": (
                Size.objects
                .filter(is_active=True)
                .exclude(slug__in=["one-size", "onesize"])   # paslepiam iš dropdown'o
                .order_by("order", "label")
            ),
            "sizes_selected": [size_selected] if size_selected else [],
            "q": q,

            # SEO
            "meta_title": meta_title,
            "meta_description": meta_description,
            "meta_robots": meta_robots,
            "canonical_url": canonical_url,
            "og_type": og_type,
            "og_title": meta_title,
            "og_description": meta_description,
        }

        # HTMX: grąžinam tik grid'o partialą
        is_htmx = (
            request.headers.get("HX-Request") == "true"
            or request.META.get("HTTP_HX_REQUEST") == "true"
        )
        if is_htmx:
            return render(request, "shop/partials/_products_grid.html", ctx)

        # Pilnas puslapis
        return render(request, self.template_name, ctx)


class ProductDetailView(View):
    template_name = "shop/detail.html"

    def get(self, request, slug):
        # pasiruošiam optimalų prefetch'ą paveikslams
        images_qs = ProductImage.objects.all().order_by("sort", "id")

        product = get_object_or_404(
            Product.objects.filter(is_active=True)
            .select_related("category", "size")
            .prefetch_related(Prefetch("images", queryset=images_qs)),
            slug=slug,
        )

        desc = _truncate(getattr(product, "description", "") or "", 160)
        long_desc = _truncate(getattr(product, "description", "") or "", 200)

        # og:image – naudokime modelio helperį (main_image -> galerijos pirmas)
        main_img = product.primary_image_url()

        # --- PANAŠIOS PREKĖS ---
        # 1) Pirmenybė – rankiniu būdu nurodytos per M2M
        related_ids = list(
            product.related_products
            .filter(is_active=True)
            .exclude(pk=product.pk)
            .values_list("pk", flat=True)[:4]
        )

        # 2) Jei nerasta – automatinės pagal taisykles
        if not related_ids:
            auto = auto_related_for(product, limit=4)
            related_ids = [p.pk for p in auto]

        # 3) Užklausą sudarom su prefetch + išlaikom pasirinktą eiliškumą
        if related_ids:
            order = Case(
                *[When(pk=pk, then=pos) for pos, pk in enumerate(related_ids)],
                output_field=IntegerField()
            )
            related_qs = (
                Product.objects.filter(pk__in=related_ids, is_active=True)
                .select_related("category", "size")
                .prefetch_related(Prefetch("images", queryset=images_qs))
                .order_by(order)
            )
        else:
            related_qs = Product.objects.none()

        ctx = {
            "product": product,

            # SEO
            "meta_title": product.name,
            "meta_description": desc,
            "meta_robots": "index,follow",
            "canonical_url": request.build_absolute_uri(),

            # OG/Twitter
            "og_type": "product",
            "og_title": product.name,
            "og_description": long_desc,
            "og_image": _abs_url(request, main_img) if main_img else None,

            # Panašios
            "related_products": related_qs,
        }
        return render(request, self.template_name, ctx)

def category_redirect(request, slug):
    # jei slug yra kategorija → redirect į /shop/?category=slug
    if Category.objects.filter(slug=slug).exists():
        return redirect(f"/shop/?category={slug}", permanent=True)

    # jei ne — nėra nei kategorijos, nei produkto → 404
    raise Http404


def private_collection_view(request, slug):
    collection = get_object_or_404(
        PrivateCollection,
        slug=slug,
        is_active=True
    )

    items = collection.items.select_related("product").order_by("position")
    for item in items:
        item.product.is_sold = item.is_sold

    products = [item.product for item in items]

    # 👇 PADAROM kaip shop
    paginator = Paginator(products, 12)  # gali keisti kiekį
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "catalog/private_collection.html", {
        "collection": collection,
        "page_obj": page_obj,
        "is_private": True,
        "hide_cart": True,
    })

def private_product_detail_view(request, slug):
    product = get_object_or_404(Product, slug=slug)

    private_item = (
        PrivateProduct.objects
        .select_related("collection")
        .filter(product=product)
        .first()
    )

    # 👇 SOLD tik iš PrivateProduct
    if private_item:
        product.is_sold = private_item.is_sold
    else:
        product.is_sold = False

    related_products = []

    if private_item:
        items = (
            private_item.collection.items
            .select_related("product")
            .exclude(product=product)
            .order_by("position")
        )

        filtered = []
        for item in items:
            if not item.is_sold:   # 👈 NAUDOJAM TIK ČIA
                filtered.append(item.product)

            if len(filtered) == 4:
                break

        related_products = filtered

    return render(request, "shop/detail.html", {
        "product": product,
        "is_private": True,
        "hide_cart": False,
        "related_products": related_products,
    })