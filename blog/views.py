from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Post

def post_list(request):
    qs = Post.objects.filter(is_published=True)
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(title__icontains=q)  # paprasta paieška
    page = request.GET.get("page") or 1
    page_obj = Paginator(qs, 10).get_page(page)
    return render(request, "blog/list.html", {"page_obj": page_obj, "q": q})

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, is_published=True)
    return render(request, "blog/detail.html", {"post": post})
