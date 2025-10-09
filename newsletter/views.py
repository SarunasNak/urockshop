# newsletter/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect   # <-- teisinga vieta
from .forms import SubscribeForm

@require_POST
@csrf_protect
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        obj = form.save(source=request.POST.get("source", "footer"))
        return JsonResponse({"ok": True, "email": obj.email})
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)
