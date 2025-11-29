from django.db import models

class VideoCategory(models.TextChoices):
    TIPS = "tips", "Stiliaus patarimai"
    COLLECTION = "collection", "Kolekcija"


class Video(models.Model):
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=VideoCategory.choices)

    cloudflare_id = models.CharField(
        max_length=200,
        help_text="Cloudflare VIDEO id arba full HLS URL"
    )

    # Desktop viršelis (1112×940)
    cover_desktop = models.ImageField(
        upload_to="video_covers/desktop/",
        help_text="Desktop viršelis (rekomenduojama 1112×940)",
        blank=True,
        null=True,
    )

    # Mobilus viršelis (~400×400)
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
        # Jeigu įrašyta visa URL — naudoti ją
        if self.cloudflare_id.startswith("http"):
            return self.cloudflare_id

        # Kitaip generuojam Cloudflare Stream embed
        subdomain = "customer-t0fo6ed5zml8bph1.cloudflarestream.com"
        return f"https://{subdomain}/{self.cloudflare_id}/iframe"
