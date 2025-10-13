# newsletter/models.py
from django.db import models

class Subscriber(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    # iš kur kontaktas gautas: "footer", "cart_tryon", "checkout", ...
    source = models.CharField(max_length=100, blank=True, default="")
    is_active = models.BooleanField(default=True)

    # Nauji laukai – optional, kad nekliūtų esami įrašai
    phone = models.CharField(max_length=32, blank=True, default="")
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
