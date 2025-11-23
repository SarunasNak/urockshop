import os
from django.conf import settings
from django.shortcuts import render
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from urllib.parse import urlparse
from analytics.utils import detect_source

EXCLUDE_NAMESPACES = {"admin"}  # paliekam adminą
BYPASS_TOKEN = os.getenv("MAINTENANCE_BYPASS_TOKEN", "secret123")  # iš .env.production

# 👇 URL'ai, kuriems netaikomas maintenance
EXEMPT_PATHS = {
    "/paysera/callback/",
    "/paysera/success/",
    "/paysera/cancel/",
    "/paysera_16afce7474e450a6515c53d90d004fef.html",
}


class MaintenanceCoverMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # ✅ Visada praleidžiam statinius failus (pvz. /static/js/analytics.js)
        if path.startswith("/static/"):
            return self.get_response(request)

        # ⚙️ Jei prašomas vienas iš išimtinių URL — praleidžiam
        if path.rstrip("/") in {p.rstrip("/") for p in EXEMPT_PATHS}:
            return self.get_response(request)

        # ✅ Slaptas URL leidžia apeiti maintenance
        if request.GET.get("bypass_maintenance") == BYPASS_TOKEN:
            response = self.get_response(request)
            response.set_cookie("maintenance_bypass", "true", max_age=3600 * 6)  # 6 valandos
            return response

        # ✅ Jei jau turi bypass slapuką – praleidžiam
        if request.COOKIES.get("maintenance_bypass") == "true":
            return self.get_response(request)

        # 🔒 Jei maintenance įjungtas – rodom puslapį
        if getattr(settings, "MAINTENANCE_COVER", False):
            try:
                match = resolve(request.path_info)
                if match.namespace in EXCLUDE_NAMESPACES:
                    return self.get_response(request)
            except Exception:
                pass
            # Viskas kas nepraeina išimčių → rodom maintenance
            return render(request, "maintenance_cover.html", status=503)

        # Jei maintenance išjungtas – tęsiam normaliai
        return self.get_response(request)

class TrafficSourceMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ref = request.META.get("HTTP_REFERER", "")
        ua = request.META.get("HTTP_USER_AGENT", "")
        host = request.get_host()

        request.source = detect_source(ref, host, ua)

class DisableAnalyticsForStaffMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.is_staff:
            # ✅ nustatome slapuką, kad JS galėtų atpažinti adminą ir nevesti analitikos
            response.set_cookie(
                "no_analytics", "1",
                path="/",
                max_age=60 * 60 * 24 * 30,  # galioja 30 dienų
                httponly=False,              # JS turi jį matyti
                samesite="Lax"
            )
        return response
