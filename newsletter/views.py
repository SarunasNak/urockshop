from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from .forms import SubscribeForm
from .emails import send_welcome_email
import threading


@require_POST
@csrf_protect
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        obj = form.save(source=request.POST.get("source", "footer"))

        # ✅ Atsakymą frontendui grąžinam iškart (kad "Užsiprenumeruota" pasirodytų be vėlavimo)
        response = JsonResponse({"ok": True, "email": obj.email})

        # 🧩 Tik kai DB įrašas tikrai išsaugotas – tada fone siunčiam laiškus
        def send_emails():
            try:
                # Siunčiam tik pirmą pasveikinimo laišką
                send_welcome_email(obj.email)
                # 🔸 Antrą laišką dabar siunčia cron užduotis (send_scheduled_emails.py)
            except Exception as e:
                print(f"Klaida siunčiant laišką {obj.email}: {e}")

        transaction.on_commit(lambda: threading.Thread(target=send_emails).start())

        return response

    return JsonResponse({"ok": False, "errors": form.errors}, status=400)
