# pages/views.py
from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404

from .models import StaticPage

class HomeView(TemplateView):
    template_name = "home.html"

    # ↓↓↓ pridėk šitą metodą ↓↓↓
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            "meta_title": "Urockas",
            "meta_description": "Urockas – pasveikinimo puslapis ir mūsų parduotuvė.",
            "meta_robots": "index,follow",
            "canonical_url": self.request.build_absolute_uri(self.request.path),
        })
        return ctx
# ↑↑↑ tiek užtenka Home’ui

def about_view(request):
    page = get_object_or_404(StaticPage, slug="about", is_published=True)
    ctx = {
        "page": page,
        "canonical_url": request.build_absolute_uri(request.path),
    }
    return render(request, "static_pages/about.html", ctx)