from django.http import HttpResponse
from django.conf import settings

def robots_txt(request):
    host = getattr(settings, "SITE_HOST", request.get_host() or "")
    body = f"""User-agent: *
Disallow:

Sitemap: https://{host}/sitemap.xml
"""
    return HttpResponse(body, content_type="text/plain")
