from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from django.utils import timezone
from django.db.models import Count
from datetime import datetime
from .models import Event
from django.db.models import Count, F


def events_overview_view(request):
    """🛍️ Elgsenos įvykių santrauka (dydžiai, kategorijos, veiksmai)."""
    start_str = request.GET.get("start")
    end_str = request.GET.get("end")

    try:
        start_date = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else None
    except Exception:
        start_date = None
    try:
        end_date = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
    except Exception:
        end_date = None

    events = Event.objects.all()
    if start_date:
        events = events.filter(created_at__date__gte=start_date)
    if end_date:
        events = events.filter(created_at__date__lte=end_date)

    # Dydžiai
    size_summary = (
        events.filter(name="size_selected")
        .values(size=F("data__size"))
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    
    # Kategorijos
    category_summary = (
        events.filter(name="category_selected")
        .values(category=F("data__category"))
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    action_summary = (
        events.filter(name__in=["add_to_cart", "try_on_click"])
        .values("name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    context = {
        **admin.site.each_context(request),
        "title": "🛍️ Events Overview",
        "size_summary": size_summary,
        "category_summary": category_summary,
        "action_summary": action_summary,
        "start_date": start_str or "",
        "end_date": end_str or "",
    }

    # ⚡️ Svarbu: naudok „admin/analytics/events_overview.html“
    return TemplateResponse(request, "admin/events_overview.html", context)


# ✅ Registruojam kaip global admin view (ne modelio)
def get_custom_urls():
    return [
        path(
            "analytics/events_overview/",
            admin.site.admin_view(events_overview_view),
            name="events-overview",
        ),
    ]


original_get_urls = admin.site.get_urls


def get_urls():
    return get_custom_urls() + original_get_urls()


admin.site.get_urls = get_urls
