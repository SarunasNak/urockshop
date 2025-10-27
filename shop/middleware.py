from django.conf import settings
from django.shortcuts import render
from django.urls import resolve

EXCLUDE_NAMESPACES = {"admin"}  # paliekam adminą

class MaintenanceCoverMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ⚙️ Leisti Paysera domeno patvirtinimo failą net jei maintenance įjungtas
        if request.path.startswith("/paysera_16afce7474e450a6515c53d90d004fef.html"):
            return self.get_response(request)

        if getattr(settings, "MAINTENANCE_COVER", False):
            try:
                match = resolve(request.path_info)
                if match.namespace in EXCLUDE_NAMESPACES:
                    return self.get_response(request)
            except Exception:
                pass
            return render(request, "maintenance_cover.html", status=503)

        return self.get_response(request)

