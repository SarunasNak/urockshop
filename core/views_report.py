# core/views_report.py
import json
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def report_error(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    url = data.get("url", "(nežinomas URL)")
    message = data.get("message", "Nežinoma klaida")
    ua = data.get("userAgent", "(nežinoma naršyklė)")
    time = data.get("time")

    subject = f"⚠️ 500 klaida svetainėje – {url}"
    body = (
        f"💥 Aptikta 500 klaida svetainėje Urock.lt\n\n"
        f"URL: {url}\n"
        f"Žinutė: {message}\n"
        f"Naudotojo naršyklė: {ua}\n"
        f"Laikas: {time}\n"
    )

    send_mail(
        subject,
        body,
        "noreply@urock.lt",
        ["info@urock.lt", "sarunasnakvosas@gmail.com"],
        fail_silently=True,
    )

    return JsonResponse({"ok": True})
