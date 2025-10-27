# catalog/templatetags/qparams.py
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def qurl(context, **kwargs):
    """
    Naudojimas:
      href="{% qurl page=i %}"
      hx-get="{% qurl page=i %}"
    Palieka esamus GET (q, size, category) ir pakeičia/nuima, ką paduodi.
    Paduok None, kad nuimtum parametrą, pvz. {% qurl page=None %}
    """
    request = context["request"]
    params = request.GET.copy()

    for k, v in kwargs.items():
        if v is None:
            params.pop(k, None)
        else:
            params[k] = v

    qs = params.urlencode()
    return f"?{qs}" if qs else "?"
