from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import PopupLead, MarketingPopup
from newsletter.models import Subscriber

from .models import PrivatePresentationLead

from django.shortcuts import render, redirect

from .models import PrivatePageVisit


@require_POST
def popup_submit(request):
    # ---- 1. Paimam duomenis ----
    name = request.POST.get("name", "").strip()
    email = request.POST.get("email", "").strip()
    phone = request.POST.get("phone", "").strip()
    city = request.POST.get("city", "").strip()
    message = request.POST.get("message", "").strip()

    popup_id = request.POST.get("popup_id")
    source = request.POST.get("source", "popup_shop")

    # ---- 2. Minimalus validavimas ----
    if not name or not email or not phone or not city:
        return JsonResponse(
            {"success": False, "error": "Missing required fields"},
            status=400
        )

    # ---- 3. Randam popup (jei perduotas) ----
    popup = None
    if popup_id:
        popup = MarketingPopup.objects.filter(id=popup_id).first()

    # ---- 4. Sukuriam PopupLead ----
    PopupLead.objects.create(
        popup=popup,
        name=name,
        email=email,
        phone=phone,
        city=city,
        message=message,
        source=source,
    )

    # ---- 5. (Optional) Įrašom į Newsletter ----
    Subscriber.objects.get_or_create(
        email=email,
        defaults={
            "source": source,
            "is_active": True,
        }
    )

    # ---- 6. Atsakymas frontendui ----
    return JsonResponse({"success": True})

def private_presentation(request):

    if request.user.is_staff:
        return render(request, "presentation/landing.html")

    # 👇 tik 1 kartą per session
    if not request.session.get("private_visited"):
        PrivatePageVisit.objects.create()
        request.session["private_visited"] = True

    if request.method == "POST":

        name = request.POST.get("name")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        city = request.POST.get("city")

        PrivatePresentationLead.objects.create(
            name=name,
            email=email,
            phone=phone,
            city=city
        )

        return redirect("marketing:presentation_thanks")

    return render(request, "presentation/landing.html")


def presentation_thanks(request):
    return render(request, "presentation/thanks.html")

