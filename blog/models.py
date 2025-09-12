from django.db import models
from django.utils.text import slugify

class Post(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.TextField(blank=True)
    body = models.TextField()
    cover = models.ImageField(upload_to="blog/", blank=True, null=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-published_at"]

    def save(self, *args, **kwargs):
            if not self.slug:
                self.slug = slugify(self.title)
            super().save(*args, **kwargs)

    def __str__(self):
        return self.title
