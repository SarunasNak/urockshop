from .models import MarketingPopup

def marketing_popup(request):
    resolver = request.resolver_match
    if not resolver:
        return {"popup": None}

    url_name = resolver.url_name

    qs = MarketingPopup.objects.filter(active=True)

    if url_name == "product_detail":
        qs = qs.filter(for_product_page=True)

    elif url_name == "product_list":
        qs = qs.filter(for_catalog_page=True)

    else:
        return {"popup": None}

    popup = qs.order_by("priority").first()
    return {"popup": popup}
