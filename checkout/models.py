from django.db import models
from django.conf import settings
from catalog.models import Variant, Product
from decimal import Decimal, ROUND_HALF_UP


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Laukiama apmokėjimo"),   # naudosi internetiniams mokėjimams
        ("cod_placed", "Pateiktas (COD)"),    # nauja: pateiktas su „mokėjimas kurjeriui“
        ("paid", "Apmokėta"),
        ("failed", "Nepavyko"),
        ("canceled", "Atšaukta"),
    ]

    PAYMENT_CHOICES = [
        ("cod", "Mokėjimas kurjeriui"),
        ("paysera", "Paysera"),
        ("stripe", "Stripe"),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cod")  # ← nauja

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
