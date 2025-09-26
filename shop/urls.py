# shop/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pages.views import HomeView, about_view
from stripe_payments import views as stripe_views

# SEO
from pages.views_seo import robots_txt
from django.contrib.sitemaps.views import sitemap
from shop.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from django.views.generic import TemplateView

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
    path("shop/", include("catalog.urls")),      # list + detail
    path("cart/", include("cart.urls", namespace="cart")),
    path("checkout/", include("checkout.urls")),
    path("blog/", include("blog.urls")),
    path("newsletter/", include("newsletter.urls")),

    # API (paliekam, tik rekomenduoju suversijuoti)
    path("api/v1/", include("catalog.urls_api")),

    path("robots.txt", robots_txt, name="robots_txt"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("paysera/", include("paysera.urls")),

    #Sripe
    path("stripe/webhook/", stripe_views.stripe_webhook, name="stripe_webhook"),

]

urlpatterns += [
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

# Media failai per dev
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)