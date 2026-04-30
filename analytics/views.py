from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from urllib.parse import urlparse
import json
from .models import PageView, Event, hash_ip
from django.db.models import Count
from django.shortcuts import render
from collections import Counter
from .models import PrivateVisit


@csrf_exempt
def track_event(request):
    """Priima informaciją iš JS apie puslapio peržiūras ir įvykius."""
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": "Invalid JSON", "details": str(e)}, status=400)

    session_id = data.get("session_id")
    visitor_id = data.get("visitor_id")
    path = data.get("path")
    name = data.get("event_name", "page_view")
    event_data = data.get("data", {})
    referrer = data.get("referrer") or request.META.get("HTTP_REFERER", "")

    if not session_id or not path:
        return JsonResponse({"error": "Missing session_id or path"}, status=400)

    ip = request.META.get("REMOTE_ADDR", "")
    user_agent = request.META.get("HTTP_USER_AGENT", "").lower()

    # 🔹 Nustatome įrenginį
    device = "mobile" if "mobile" in user_agent or "android" in user_agent or "iphone" in user_agent else "desktop"

    # 🔹 Nustatome srauto šaltinį (su domeno palyginimu)
    if not referrer:
        source = "Direct"
    else:
        domain = urlparse(referrer).netloc.lower()
        current_domain = request.get_host().lower()

        # Jei vartotojas naršo tame pačiame domene – laikom kaip „Direct“
        if current_domain in domain:
            source = "Direct"
        elif "google" in domain:
            source = "Organic"
        elif any(x in domain for x in ["facebook", "instagram", "tiktok", "twitter"]):
            source = "Social"
        else:
            source = "Referral"

    # 🔹 PageView kūrimas / atnaujinimas
    pv, _ = PageView.objects.get_or_create(
        session_id=session_id,
        path=path,
        defaults={
            "visitor_id": visitor_id,
            "ip_hash": hash_ip(ip),
            "user_agent": user_agent[:255],
            "referer": referrer[:512],
            "source": source,
            "device": device,
            "duration": 0,
        },
    )

    # 🔹 Jei gauta trukmė — atnaujinam
    if "duration" in event_data:
        try:
            duration = float(event_data["duration"])
            # Išsaugom tik jei trukmė ilgesnė nei buvusi
            if duration > (pv.duration or 0):
                pv.duration = duration
                pv.save(update_fields=["duration"])
        except (TypeError, ValueError):
            pass

    # 🔹 Sukuriam event'ą
    Event.objects.create(
        pageview=pv,
        name=name,
        data=event_data,
        created_at=timezone.now(),
    )

    return JsonResponse({"status": "ok"})


def events_overview(request):
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")

    qs = Event.objects.all()
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    # 📏 DYDŽIAI (be „VISI“)
    sizes = [
        e.data.get("size")
        for e in qs.filter(name="size_selected")
        if e.data and e.data.get("size") and e.data.get("size").upper() != "VISI"
    ]
    size_summary = [{"size": k, "total": v} for k, v in Counter(sizes).items()]

    # 👕 KATEGORIJOS (be „VISI“)
    categories = [
        e.data.get("category")
        for e in qs.filter(name="category_selected")
        if e.data and e.data.get("category") and e.data.get("category").upper() != "VISI"
    ]
    category_summary = [{"category": k, "total": v} for k, v in Counter(categories).items()]

    # 🛒 VEIKSMAI (tik konkretūs veiksmai)
    action_summary = (
        qs.filter(name__in=["add_to_cart", "try_on_click", "order_click"])
        .values("name")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    context = {
        "size_summary": size_summary,
        "category_summary": category_summary,
        "action_summary": action_summary,
        "start_date": start_date or "",
        "end_date": end_date or "",
    }
    from django.contrib.admin.sites import site
    return render(request, "admin/analytics/events_overview.html", context)

@csrf_exempt
def track_private(request):
    if request.method != "POST":
        return JsonResponse({"ok": False})

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({"ok": False})

    path = data.get("path")
    session_id = data.get("session_id")

    if not path or "/private/" not in path or not session_id:
        return JsonResponse({"ok": True})

    duration = float(data.get("duration", 0))

    if duration < 1:
        return JsonResponse({"ok": True})

    collection = path.split("/private/")[-1].strip("/")

    pv = PrivateVisit.objects.filter(
        session_id=session_id,
        collection=collection
    ).order_by("-created_at").first()

    if pv:
        if duration > pv.duration:
            pv.duration = duration
            pv.save(update_fields=["duration"])
    else:
        PrivateVisit.objects.create(
            session_id=session_id,
            collection=collection,
            path=path,
            duration=duration,
        )

    return JsonResponse({"ok": True})