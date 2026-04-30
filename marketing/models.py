from django.db import models


class MarketingPopup(models.Model):
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=255)
    message = models.TextField()

    delay_seconds = models.PositiveIntegerField(default=5)
    hide_after_seconds = models.PositiveIntegerField(default=0)

    active = models.BooleanField(default=True)

    for_product_page = models.BooleanField(default=True)
    for_catalog_page = models.BooleanField(default=False)

    priority = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["priority"]

    def __str__(self):
        return f"{self.priority}. {self.name}"

class PopupLead(models.Model):
    popup = models.ForeignKey(
        "MarketingPopup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
        help_text="Iš kurio popup gautas leadas"
    )

    # Kontaktiniai duomenys
    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=32)
    city = models.CharField(max_length=255)
    message = models.TextField(blank=True)

    # Iš kurios vietos puslapyje
    source = models.CharField(
        max_length=100,
        default="popup",
        help_text="Pvz: popup_shop, popup_blog, popup_product"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        popup_name = self.popup.name if self.popup else "Nenurodyta"
        return f"{self.email} ({popup_name})"

class PrivatePresentationLead(models.Model):

    CITY_CHOICES = [
        ("vilnius", "Vilnius"),
        ("kaunas", "Kaunas"),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=32, blank=True)

    city = models.CharField(
        max_length=50,
        choices=CITY_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)

    source = models.CharField(
        max_length=100,
        default="landing"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} – {self.city}"

class PrivatePageVisit(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Visit {self.created}"
