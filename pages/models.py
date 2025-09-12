from django.db import models


class SiteSettings(models.Model):
    site_name = models.CharField(max_length=120, default="Urock")
    logo = models.ImageField(upload_to="branding/", null=True, blank=True)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=250, blank=True)

    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    tiktok = models.URLField(blank=True)

    footer_html = models.TextField(blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Global settings"


class StaticPage(models.Model):
    slug = models.SlugField(max_length=140, unique=True)  # pvz. "about"
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    hero = models.ImageField(upload_to="pages/", null=True, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.title
