# Create your models here.
from django.db import models
from django.utils import timezone
import hashlib


def hash_ip(ip_address):
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode()).hexdigest()[:16]


class PageView(models.Model):
    session_id = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    path = models.CharField(max_length=512)
    referer = models.CharField(max_length=512, null=True, blank=True)
    source = models.CharField(max_length=50, default="Direct")  # Organic, Ads, Referral, Direct
    device = models.CharField(max_length=50, default="unknown")
    created_at = models.DateTimeField(default=timezone.now)
    duration = models.FloatField(default=0.0)  # sekundėmis

    def __str__(self):
        return f"{self.path} ({self.source})"


class Event(models.Model):
    pageview = models.ForeignKey(PageView, on_delete=models.CASCADE, related_name="events")
    name = models.CharField(max_length=100)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.name} @ {self.pageview.path}"
