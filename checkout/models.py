from django.db import models
from catalog.models import Variant
from decimal import Decimal, ROUND_HALF_UP

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Laukiama apmokėjimo"),
        ("cod_placed", "Pateiktas (COD)"),
        ("paid", "Apmokėta"),
        ("failed", "Nepavyko"),
        ("canceled", "Atšaukta"),
    ]

    PAYMENT_CHOICES = [
        ("cod", "Mokėjimas kurjeriui"),
        ("paysera", "Paysera"),
        ("stripe", "Stripe"),
    ]

    SHIPPING_CHOICES = (
        ("dpd_courier", "DPD kurjeris"),
        ("dpd_pickup",  "DPD paštomatas"),
    )

    # Pirkėjas
    first_name   = models.CharField(max_length=100)
    last_name    = models.CharField(max_length=100)
    email        = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, default="")
    address      = models.CharField(max_length=250)
    city         = models.CharField(max_length=100)
    postal_code  = models.CharField(max_length=20)

    # SF (invoice) — tik du laukai + flagas
    needs_invoice = models.BooleanField(default=False)       # ← PRIDĖTA
    company_name  = models.CharField(max_length=255, blank=True, default="")  # ← PRIDĖTA
    company_code  = models.CharField(max_length=64,  blank=True, default="")  # ← PRIDĖTA

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cod")

    shipping_method = models.CharField(max_length=30, choices=SHIPPING_CHOICES, default="dpd_courier")
    dpd_pickup_id   = models.CharField(max_length=64,  null=True, blank=True)
    dpd_pickup_name = models.CharField(max_length=128, null=True, blank=True)
    dpd_pickup_addr = models.CharField(max_length=256, null=True, blank=True)

    stripe_pi_id = models.CharField(max_length=64, blank=True, null=True)
    coupon_code = models.CharField(max_length=50, blank=True, default="")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return f"Order #{self.id} ({self.email})"

    def recalc_total(self):
        items_total = sum([item.line_total for item in self.items.all()]) or Decimal("0.00")
        self.total = (items_total + (self.shipping_cost or Decimal("0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return self.total

    @property
    def is_paid(self):
        return self.status == "paid"

    @property
    def is_dpd_pickup(self) -> bool:
        return self.shipping_method == "dpd_pickup"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    variant = models.ForeignKey(Variant, on_delete=models.PROTECT)
    product_name = models.CharField(max_length=200)
    variant_sku = models.CharField(max_length=50)
    qty = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.qty}"

    def save(self, *args, **kwargs):
        if not self.line_total:
            self.line_total = self.price * self.qty
        super().save(*args, **kwargs)
