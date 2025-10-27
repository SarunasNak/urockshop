# cart/models.py
from django.db import models
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class TryOnRequest(models.Model):
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    height_cm = models.PositiveIntegerField()
    weight_kg = models.PositiveIntegerField()
    terms_accepted = models.BooleanField(default=False)
    marketing_consent = models.BooleanField(default=False)
    # Krepšelio momentinė kopija (žr. Cart.snapshot)
    items_json = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Try-on užklausa"
        verbose_name_plural = "Try-on užklausos"

    def __str__(self):
        return f"TryOn #{self.id} {self.email} {self.created_at:%Y-%m-%d %H:%M}"

    # ——— Patogumui: kiek prekių užklausoje
    @property
    def items_count(self) -> int:
        return len(self.items_json or [])

    # ——— Gražus prekių sąrašas admin'e (miniatiūra + brand + pavadinimas + dydis + kaina)
    def items_pretty_html(self) -> str:
        """
        Sugeneruoja HTML su visomis try-on prekėmis.
        Naudok admin'e kaip readonly field'ą.
        Tikisi, kad items_json elementai turi:
        image_url, brand, name/product_title, size, price, sku (nebūtina – saugūs fallback'ai).
        """
        items = self.items_json or []
        if not items:
            return "–"

        blocks = []
        for it in items:
            img_url = (it.get("image_url") or "").strip()
            brand = (it.get("brand") or "").strip()
            name = (
                it.get("name")
                or it.get("product_title")
                or it.get("title")
                or "Prekė"
            )
            size = (it.get("size") or "–")
            price = (it.get("price") or "")
            sku = (it.get("sku") or "")

            img_html = (
                format_html('<img src="{}" style="max-width:100%;max-height:100%;">', img_url)
                if img_url else mark_safe('<div style="font-size:11px;color:#999">nėra</div>')
            )

            blocks.append(format_html(
                '<div style="display:flex;gap:10px;align-items:center;margin:8px 0">'
                '  <div style="width:56px;height:66px;flex:0 0 56px;border:1px solid #eee;overflow:hidden;display:grid;place-items:center;">'
                '    {}'
                '  </div>'
                '  <div style="line-height:1.25">'
                '    <div><strong>{}</strong> {}</div>'
                '    <div style="color:#666">Dydis: {}{}</div>'
                '    <div style="color:#000">{}{}</div>'
                '  </div>'
                '</div>',
                img_html,
                brand, name,
                size,
                f' • SKU: {sku}' if sku else '',
                price, ' €' if price else '',
            ))

        return mark_safe("".join(blocks))

    items_pretty_html.short_description = "Prekės (gražiai)"
