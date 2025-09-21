from django.views.generic import TemplateView
from .models import BlogSettings, Post

class BlogListView(TemplateView):
    template_name = "blog/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        settings = BlogSettings.objects.first()
        brands = settings.brands.filter(is_active=True).order_by("order") if settings else []

        posts = Post.objects.filter(is_published=True).order_by("-published_at")

        # Kortelių tinklelis viršuje. Jei post.card_variant tuščias – kas trečia „large“ (vidurinė).
        grid = [
            (p, p.card_variant or ("large" if i % 3 == 1 else "small"))
            for i, p in enumerate(posts)
        ]

        ctx.update({
            "settings": settings,
            "brands": brands,
            "posts": posts,         # pilni straipsniai apačioje
            "grid": grid,           # kortelės viršuje
            "meta_title": (settings.hero_title or "Blogas") if settings else "Blogas",
            "meta_description": (settings.hero_subtitle or "") if settings else "",
            "canonical_url": self.request.build_absolute_uri(self.request.path),
        })
        return ctx

