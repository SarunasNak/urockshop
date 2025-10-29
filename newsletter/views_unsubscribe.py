# newsletter/views_unsubscribe.py
from django.shortcuts import render
from newsletter.models import Subscriber

def unsubscribe_view(request):
    email = request.GET.get("email", "").strip()
    context = {"email": email, "success": False}

    if email:
        try:
            sub = Subscriber.objects.filter(email=email).first()
            if sub:
                sub.is_active = False
                sub.save(update_fields=["is_active"])
                context["success"] = True
        except Exception:
            pass  # tyčia nekeliam klaidos, jei el. pašto nėra

    return render(request, "newsletter/unsubscribe_done.html", context)
