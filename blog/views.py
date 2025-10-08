# blog/views.py
from django.views.generic import TemplateView
from django.utils.html import strip_tags
from django.utils.text import Truncator
from .models import BlogSettings, Post

# Laikinas statinis FE vaizdas (rodo gryną FE turinį be DB)
class BlogFEView(TemplateView):
    template_name = "blog/fe_static.html"

# Dinaminis vaizdas (paliekam ateičiai – kai prisijungs TVS)
class BlogListView(TemplateView):
    template_name = "blog/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        settings = BlogSettings.objects.first()
        brands = settings.brands.filter(is_active=True).order_by("order") if settings else []
        posts = Post.objects.filter(is_published=True).order_by("-published_at")

        # Meta aprašymas iš pirmo įrašo, jei yra
        meta_desc = ""
        if posts:
            meta_desc = Truncator(strip_tags(posts[0].body or "")).chars(160)

        ctx.update({
            "settings": settings,
            "brands": brands,
            "posts": posts,
            "meta_title": (settings.hero_title or "Tinklaraštis") if settings else "Tinklaraštis",
            "meta_description": meta_desc,
            "canonical_url": self.request.build_absolute_uri(self.request.path),
        })
        return ctx
