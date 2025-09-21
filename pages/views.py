# pages/views.py
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404

from .models import StaticPage, HomePage


class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        home = (
            HomePage.objects
            .prefetch_related("tiles")
            .only(
                "hero_title", "hero_subtitle", "hero_note",
                "hero_cta_text", "hero_cta_url",
                "seo_title", "seo_description", "hero_image"
            )
            .first()
        )
        tiles = home.tiles.filter(is_active=True).order_by("order") if home else []

        ctx.update({
            "home": home,               # <— pasirinkau 'home'
            "tiles": tiles,
            "meta_title": (home.seo_title or "Urockas") if home else "Urockas",
            "meta_description": (home.seo_description or "Urockas – pasveikinimo puslapis ir mūsų parduotuvė.") if home else "Urockas – pasveikinimo puslapis ir mūsų parduotuvė.",
            "meta_robots": "index,follow",
            "canonical_url": self.request.build_absolute_uri(self.request.path),
            # OG paveikslėlis (jei hero_image naudojamas kaip OG)
            "og_image": home.hero_image.url if (home and home.hero_image) else None,
        })
        return ctx


def about_view(request):
    page = get_object_or_404(StaticPage, slug="about", is_published=True)
    ctx = {
        "page": page,
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "static_pages/about.html", ctx)
