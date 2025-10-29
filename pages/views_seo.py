from django.http import HttpResponse
from django.conf import settings


def robots_txt(request):
    """
    Dinaminis robots.txt pagal aplinką:
    - Jei MAINTENANCE_COVER=True → Disallow: /
    - Jei ENVIRONMENT != 'production' → Disallow: /
    - Kitu atveju → Allow: / ir sitemap
    """
    host = getattr(settings, "SITE_HOST", request.get_host() or "").strip()
    is_production = getattr(settings, "ENVIRONMENT", "") == "production"
    under_maintenance = getattr(settings, "MAINTENANCE_COVER", False)

    if under_maintenance or not is_production:
        # Staging arba priežiūros režimas — neindeksuojame
        body = "User-agent: *\nDisallow: /\n"
    else:
        # Production – leidžiame indeksuoti
        body = f"""User-agent: *
Allow: /
Sitemap: https://{host}/sitemap.xml
"""
    return HttpResponse(body, content_type="text/plain")

