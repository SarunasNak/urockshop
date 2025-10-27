from django.contrib import admin
from django.urls import path
from django.utils import timezone
from django.template.response import TemplateResponse
from datetime import datetime
from django.db.models import Avg, Sum
from .models import PageView


def analytics_overview_view(request):
    """Rodo analitikos santrauką su pasirinktu datų filtru (nuo–iki)."""

    # 🔹 Datų filtrai iš GET (pvz. ?start=2025-10-01&end=2025-10-25)
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

    now = timezone.now()
    today = now.date()
    start_of_week = now - timezone.timedelta(days=now.weekday())
    start_of_month = now.replace(day=1)

    # 🔹 Bazinis queryset
    pageviews = PageView.objects.all()

    # 🔹 Filtravimas pagal pasirinktas datas
    if start_date:
        pageviews = pageviews.filter(created_at__date__gte=start_date)
    if end_date:
        pageviews = pageviews.filter(created_at__date__lte=end_date)

    # 🔹 Unikalūs lankytojai
    today_count = pageviews.filter(created_at__date=today).values("ip_hash").distinct().count()
    week_count = pageviews.filter(created_at__gte=start_of_week).values("ip_hash").distinct().count()
    month_count = pageviews.filter(created_at__gte=start_of_month).values("ip_hash").distinct().count()

    # 🔹 Vidutinė buvimo trukmė
    avg_duration = pageviews.aggregate(avg_duration=Avg("duration"))["avg_duration"] or 0

    # 🔹 Grupavimas pagal sesiją (viso sesijos trukmė)
    sessions = pageviews.values("session_id").annotate(total=Sum("duration"))
    total_sessions = sessions.count() or 1

    # 🔹 Įsitraukimo kategorijos (e-commerce tipui)
    quick_exits = sessions.filter(total__lt=20).count()           # < 20 s
    short_visits = sessions.filter(total__gte=20, total__lt=90).count()  # 20–90 s
    engaged_visits = sessions.filter(total__gte=90).count()       # > 90 s

    # 🔹 Procentai
    quick_pct = round((quick_exits / total_sessions) * 100, 1)
    short_pct = round((short_visits / total_sessions) * 100, 1)
    engaged_pct = round((engaged_visits / total_sessions) * 100, 1)

    # 🔹 Kontekstas perduodamas į HTML
    context = {
        **admin.site.each_context(request),
        "title": "📊 Analytics Overview",

        # viršutiniai rodikliai
        "today_count": today_count,
        "week_count": week_count,
        "month_count": month_count,
        "avg_duration": round(avg_duration, 1),

        # įsitraukimo blokas
        "quick_exits": quick_exits,
        "short_visits": short_visits,
        "engaged_visits": engaged_visits,
        "quick_pct": quick_pct,
        "short_pct": short_pct,
        "engaged_pct": engaged_pct,

        # datų filtrai
        "start_date": start_str or "",
        "end_date": end_str or "",
    }

    return TemplateResponse(request, "admin/analytics_overview.html", context)


# ✅ URL registravimas admin'e
def get_custom_urls():
    return [
        path(
            "analytics/overview/",
            admin.site.admin_view(analytics_overview_view),
            name="analytics-overview",
        ),
    ]


# ✅ Pakeičiam defaultinius admin URL'us, kad pridėtume savo
original_get_urls = admin.site.get_urls


def get_urls():
    return get_custom_urls() + original_get_urls()


admin.site.get_urls = get_urls
