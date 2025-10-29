# shop/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from pages.views import HomeView, about_view
from pages.views_seo import robots_txt
from django.contrib.sitemaps.views import sitemap
from shop.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from django.views.generic import TemplateView, RedirectView
from newsletter.views_unsubscribe import unsubscribe_view

# APP views
from checkout import views as checkout_views  # <-- naudokime šitą alias

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),

    # SSR maršrutai (šablonai)
    path("", HomeView.as_view(), name="home"),
    path("about/", about_view, name="about"),
    path("shop/", include(("catalog.urls", "catalog"), namespace="catalog")),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    path("checkout/", include(("checkout.urls", "checkout"), namespace="checkout")),
    path("paysera/", include(("paysera.urls", "paysera"), namespace="paysera")),
    path("blog/", include(("blog.urls", "blog"), namespace="blog")),
    path("newsletter/", include(("newsletter.urls", "newsletter"), namespace="newsletter")),
    path("analytics/", include("analytics.urls")),
    path("unsubscribe/", unsubscribe_view, name="unsubscribe"),

    # API
    path("api/v1/", include("catalog.urls_api")),

    # SEO
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),

    # Stripe webhook (ROUTE → tavo checkout.views.stripe_webhook)
    path("stripe/webhook/", checkout_views.stripe_webhook, name="stripe_webhook"),
]

urlpatterns += [
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

urlpatterns += [
    # LT keliai (SEO)
    path("pirkimo-salygos/",    TemplateView.as_view(template_name="static_pages/terms.html"),    name="terms"),
    path("pristatymas/",        TemplateView.as_view(template_name="static_pages/delivery.html"), name="shipping"),
    path("grazinimas/",         TemplateView.as_view(template_name="static_pages/returns.html"),  name="returns"),
    path("privatumo-politika/", TemplateView.as_view(template_name="static_pages/privacy.html"),  name="privacy"),

    # Senų EN kelių redirect'ai į LT (301)
    path("terms/",    RedirectView.as_view(url="/pirkimo-salygos/",    permanent=True)),
    path("delivery/", RedirectView.as_view(url="/pristatymas/",        permanent=True)),
    path("returns/",  RedirectView.as_view(url="/grazinimas/",         permanent=True)),
    path("privacy/",  RedirectView.as_view(url="/privatumo-politika/", permanent=True)),
]

# Media dev režime
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
