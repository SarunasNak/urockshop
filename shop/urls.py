from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from pages.views import HomeView, about_view
from stripe_payments import views as stripe_views
from django.views.static import serve
import os

# SEO
from pages.views_seo import robots_txt
from django.contrib.sitemaps.views import sitemap
from shop.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from django.views.generic import TemplateView, RedirectView

sitemaps = {
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "static": StaticViewSitemap,
}

urlpatterns = [
    # ✅ Paysera domeno patvirtinimo failas (laikinas)
    path(
        "paysera_16afce7474e450a6515c53d90d004fef.html",
        lambda request: serve(
            request,
            "paysera_16afce7474e450a6515c53d90d004fef.html",
            document_root="/home/SarunasNakvosas/django_projects/urockshop_prod/",
        ),
    ),

    path("admin/", admin.site.urls),

    # SSR maršrutai (šablonai)
    path("", HomeView.as_view(), name="home"),
    path("about/", about_view, name="about"),
    path(
        "shop/preview/",
        TemplateView.as_view(template_name="shop/detail.html"),
        name="product_detail_preview",
    ),
    path("shop/", include(("catalog.urls", "catalog"), namespace="shop")),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    path("checkout/", include("checkout.urls")),
    path("blog/", include(("blog.urls", "blog"), namespace="blog")),
    path("newsletter/", include(("newsletter.urls", "newsletter"), namespace="newsletter")),
    path("api/v1/", include("catalog.urls_api")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("paysera/", include("paysera.urls")),
    path("stripe/webhook/", stripe_views.stripe_webhook, name="stripe_webhook"),
]

urlpatterns += [
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

urlpatterns += [
    path("pirkimo-salygos/", TemplateView.as_view(template_name="static_pages/terms.html"), name="terms"),
    path("pristatymas/", TemplateView.as_view(template_name="static_pages/delivery.html"), name="shipping"),
    path("grazinimas/", TemplateView.as_view(template_name="static_pages/returns.html"), name="returns"),
    path("privatumo-politika/", TemplateView.as_view(template_name="static_pages/privacy.html"), name="privacy"),
    path("terms/", RedirectView.as_view(url="/pirkimo-salygos/", permanent=True)),
    path("delivery/", RedirectView.as_view(url="/pristatymas/", permanent=True)),
    path("returns/", RedirectView.as_view(url="/grazinimas/", permanent=True)),
    path("privacy/", RedirectView.as_view(url="/privatumo-politika/", permanent=True)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
