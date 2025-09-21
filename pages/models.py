from django.db import models
from django.core.exceptions import ValidationError

from django.db import models


#FOOTERIS
class SiteSettings(models.Model):
    # Prekės ženklas
    site_name = models.CharField(max_length=120, default="Urock")
    logo = models.ImageField(upload_to="branding/", null=True, blank=True)

    # Įmonės kontaktai (kairė kolona)
    company_name = models.CharField(max_length=200, blank=True)
    company_code = models.CharField(max_length=50, blank=True)
    vat_code = models.CharField(max_length=50, blank=True)
    address = models.CharField(max_length=250, blank=True)
    city = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)

    # Savininko kontaktai (centras)
    owner_name = models.CharField(max_length=120, blank=True)
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=50, blank=True)

    # Social (centro apačia)
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)

    # Naujienlaiškis (dešinė)
    newsletter_title = models.CharField(max_length=120, blank=True)
    newsletter_placeholder = models.CharField(max_length=120, blank=True)
    newsletter_button = models.CharField(max_length=40, blank=True, default="Prenumeruoti")

    # Teisinės nuorodos (dešinės apačia)
    terms_url = models.URLField(blank=True)
    shipping_url = models.URLField(blank=True)
    returns_url = models.URLField(blank=True)
    privacy_url = models.URLField(blank=True)

    # Papildomas „laisvas“ footer HTML
    footer_html = models.TextField(blank=True)

    # (palieku senus laukus dėl suderinamumo – jei nenaudosi, gali vėliau pašalinti su migration)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Global settings"

#APIE MUS
class StaticPage(models.Model):
    slug = models.SlugField(max_length=140, unique=True)   # pvz. "about"
    title = models.CharField(max_length=200)

    # BANERIS / HERO (viršuje)
    hero = models.ImageField(upload_to="pages/", null=True, blank=True)
    hero_alt = models.CharField(max_length=120, blank=True)

    # STRAIPSNIS (leidžiam tekstą + HTML (nuotraukos/video įterpimams))
    body = models.TextField(blank=True)

    # DEŠINĖ: pagrindinis (main) video viršuje
    sidebar_main_video_url = models.URLField(blank=True, help_text="Pilnas YouTube/Vimeo URL")
    sidebar_main_video_poster = models.ImageField(upload_to="pages/video_posters/", null=True, blank=True)

    # (nebūtina) SEO
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.title

    def clean(self):
        if self.sidebar_main_video_url and not (self.sidebar_main_video_url.startswith("http://") or self.sidebar_main_video_url.startswith("https://")):
            raise ValidationError({"sidebar_main_video_url": "Įrašyk pilną YouTube/Vimeo URL su http(s)://"})

# DEŠINĖS pusės baneriukai (po main video)
class PageBanner(models.Model):
    page = models.ForeignKey(StaticPage, on_delete=models.CASCADE, related_name="banners")
    title = models.CharField(max_length=80, blank=True)
    image = models.ImageField(upload_to="pages/banners/")
    link_url = models.CharField(max_length=200, blank=True, help_text='Pvz. "/shop/" arba "https://..."')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title or f"Banner #{self.pk}"

    def clean(self):
        if self.page and self.page.slug != "about":
            raise ValidationError("Dešinės banerius leidžiama pildyti tik puslapiui su slug='about'.")
        if self.link_url and not (self.link_url.startswith("/") or self.link_url.startswith("http")):
            raise ValidationError({"link_url": 'Naudok "/vidinis-kelias" arba pilną "https://...".'})

#TITULINIS
class HomePage(models.Model):
    # leidžiam turėti tik vieną įrašą (apsaugos admin)
    singleton = models.BooleanField(default=True, editable=False, unique=True)

    # HERO
    hero_title = models.CharField(max_length=120, blank=True)
    hero_subtitle = models.CharField(max_length=300, blank=True)
    hero_note = models.CharField(max_length=300, blank=True)
    hero_cta_text = models.CharField(max_length=40, blank=True)
    hero_cta_url = models.CharField(max_length=200, blank=True)  # pvz. "/shop/"
    hero_image = models.ImageField(upload_to="pages/hero/", blank=True, null=True)

    # (pasirinktinai) naujienlaiškio blokas apačioje
    newsletter_title = models.CharField(max_length=120, blank=True)
    newsletter_subtitle = models.CharField(max_length=200, blank=True)
    newsletter_button = models.CharField(max_length=40, blank=True, default="Prenumeruoti")

    # SEO
    seo_title = models.CharField(max_length=70, blank=True)
    seo_description = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name = "Titulinis"
        verbose_name_plural = "Titulinis"

    def __str__(self):
        return "Titulinis puslapis"

class HomeTile(models.Model):
    VARIANTS = (
        ("s", "1×1 (maža)"),
        ("m", "2×1 (plati)"),
        ("t", "1×2 (aukšta)"),   # ← nauja
        ("l", "3×2 (didelė)"),
    )
    LABEL_POSITIONS = (
        ("bl", "Apačia-kairė"), ("br", "Apačia-dešinė"),
        ("tl", "Viršus-kairė"), ("tr", "Viršus-dešinė"),
        ("cc", "Centras"),
    )

    home = models.ForeignKey(HomePage, on_delete=models.CASCADE, related_name="tiles")
    title = models.CharField(max_length=80, blank=True)        # pvz. „Paltai“, „Striukės“...
    alt_text = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="pages/tiles/")
    link_url = models.CharField(max_length=200, help_text='Pvz. "/shop/" arba "/category/<slug>/"')
    variant = models.CharField(max_length=10, choices=VARIANTS, default="m")
    label_pos = models.CharField(max_length=2, choices=LABEL_POSITIONS, default="bl")  # ← nauja
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Plytelė"
        verbose_name_plural = "Galerija (plytelės)"

    def __str__(self):
        return self.title or f"Plyt. {self.pk}"

    @property
    def css_cell(self) -> str:
        # 6 stulpelių grid (FE tinklelis). FE prireikus pritaikys.
        return {
            "s": "col-span-1 row-span-1",
            "m": "col-span-2 row-span-1",
            "t": "col-span-1 row-span-2",
            "l": "col-span-3 row-span-2",
        }[self.variant]

    @property
    def label_class(self) -> str:
        # padeda peržiūrai/šablonui: kur dėti užrašą
        return {
            "bl": "left-3 bottom-3",
            "br": "right-3 bottom-3",
            "tl": "left-3 top-3",
            "tr": "right-3 top-3",
            "cc": "left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2",
        }[self.label_pos]