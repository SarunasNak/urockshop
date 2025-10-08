from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST  # <-- ŠITAS IMPORTAS
from .forms import SubscribeForm

@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if form.is_valid():
        form.save(source=request.POST.get("source", "footer"))
        return JsonResponse({"ok": True})
    return HttpResponseBadRequest("Invalid email")
