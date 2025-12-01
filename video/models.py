from django.db import models

class VideoCategory(models.TextChoices):
    TIPS = "tips", "Urock ir vertė"
    COLLECTION = "collection", "Drabužiai ir įvaizdis"


class Video(models.Model):
    title = models.CharField(max_length=255)
    title_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Jeigu įvesi URL – pavadinimas taps nuoroda"
    )

    category = models.CharField(max_length=20, choices=VideoCategory.choices)

    cloudflare_id = models.CharField(
        max_length=200,
        help_text="Cloudflare VIDEO id arba full HLS URL"
    )

    cover_desktop = models.ImageField(
        upload_to="video_covers/desktop/",
        help_text="Desktop viršelis (rekomenduojama 1112×940)",
        blank=True,
        null=True,
    )

    cover_mobile = models.ImageField(
        upload_to="video_covers/mobile/",
        help_text="Mobilus viršelis (rekomenduojama 400×400)",
        blank=True,
        null=True,
    )

    label = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title

    @property
    def video_url(self):
        if self.cloudflare_id.startswith("http"):
            return self.cloudflare_id

        subdomain = "customer-t0fo6ed5zml8bph1.cloudflarestream.com"
        return f"https://{subdomain}/{self.cloudflare_id}/iframe"
