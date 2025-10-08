from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from django.utils.crypto import get_random_string

User = get_user_model()

class Coupon(models.Model):
    PERCENT = "percent"
    FIXED = "fixed"
    TYPE_CHOICES = [(PERCENT, "% nuo sumos"), (FIXED, "Fiksuota suma")]

    code = models.CharField(
        max_length=40, unique=True, db_index=True,
        validators=[RegexValidator(r"^[A-Z0-9\-]+$", "Naudokite A–Z, 0–9, -")]
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])

    # kur taikomas
    applies_to_all = models.BooleanField(default=True)
    products = models.ManyToManyField("catalog.Product", blank=True, related_name="coupons")
    categories = models.ManyToManyField("catalog.Category", blank=True, related_name="coupons")

    # laikai ir slenksčiai
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    min_order_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # ribojimai
    usage_limit_total = models.PositiveIntegerField(null=True, blank=True)
    usage_limit_per_user = models.PositiveIntegerField(null=True, blank=True)
    assigned_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name="personal_coupons")
    allowed_emails = models.TextField(blank=True, default="")  # ; atskirti el. paštai

    stackable = models.BooleanField(default=False)  # pas mus paliekam False
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        t = "%" if self.type == self.PERCENT else "€"
        return f"{self.code} ({self.value}{t})"

    @staticmethod
    def generate_code(prefix: str = "", length: int = 10) -> str:
        body = get_random_string(length=length, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        return f"{prefix}{'-' if prefix else ''}{body}"

    def is_valid_now(self) -> bool:
        now = timezone.now()
        return self.is_active and (not self.starts_at or now >= self.starts_at) and (not self.ends_at or now <= self.ends_at)

class CouponRedemption(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField(blank=True, default="")
    order_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
