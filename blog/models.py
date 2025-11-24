# blog/models.py
from django.db import models
from django.utils.text import slugify

class BlogSettings(models.Model):
    # leisti turėti vieną įrašą
    singleton = models.BooleanField(default=True, editable=False, unique=True)

    # HERO (tik tekstas)
    hero_title = models.CharField(max_length=200, blank=True)

    # Bėganti brandų juosta
    ticker_enabled = models.BooleanField(default=True)
    ticker_speed = models.PositiveIntegerField(  # px/s arba bet koks skaičius FE reikšmei
        default=30, help_text="Greitis (naudojamas FE animacijai)."
    )
    ticker_separator = models.CharField(
        max_length=4, default="•", help_text="Skirtukas tarp brandų (pvz. • | /)"
    )

    # Antraštė po juosta
    must_read_title = models.CharField(max_length=80, blank=True, default="MUST READ")

    class Meta:
        verbose_name = "Blog settings"
        verbose_name_plural = "Blog settings"

    def __str__(self):
        return "Blog settings"

class BrandItem(models.Model):
    settings = models.ForeignKey(BlogSettings, related_name="brands", on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.title


class Post(models.Model):
    CARD_SMALL = "small"
    CARD_LARGE = "large"
    CARD_VARIANTS = [(CARD_SMALL, "Maža"), (CARD_LARGE, "Didesnė")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    body = models.TextField()
    cover = models.ImageField(upload_to="blog/", blank=True, null=True)
    card_image = models.ImageField(upload_to="blog/", blank=True, null=True)
    card_variant = models.CharField(max_length=10, choices=CARD_VARIANTS, default=CARD_SMALL)

    meta_title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Jei tuščia, bus naudojamas straipsnio pavadinimas."
    )

    meta_description = models.CharField(
        max_length=320,
        blank=True,
        help_text="Trumpas aprašymas (160–320 simbolių) SEO ir socialiniams tinklams."
    )

    show_in_separate_page = models.BooleanField(
        default=False,
        help_text="Pažymėjus – straipsnis atsidarys atskirame puslapyje."
    )

    published_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    # 🆕 NAUJAS LAUKAS — DRAG-AND-DROP RIKIAVIMUI
    sort_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title

    @property
    def anchor_id(self) -> str:
        return f"post-{self.slug}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:220]
        super().save(*args, **kwargs)


