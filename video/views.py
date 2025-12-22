from django.shortcuts import render
from .models import Video, VideoCategory

def video_page(request):
    tips = Video.objects.filter(category=VideoCategory.TIPS)
    collection = Video.objects.filter(category=VideoCategory.COLLECTION)

    for v in collection:
        print(v.title, "=>", v.video_url)

    return render(request, "video/video.html", {
        "tips": tips,
        "collection": collection,
    })
