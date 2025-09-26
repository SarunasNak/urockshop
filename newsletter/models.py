from django.db import models

# Create your models here.
from django.db import models

class Subscriber(models.Model):
    email = models.EmailField(unique=True, db_index=True)
    source = models.CharField(max_length=100, blank=True, default="footer")  # iš kur gauta
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
