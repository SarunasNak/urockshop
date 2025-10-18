from django import forms
import re
from django.core.exceptions import ValidationError

class CheckoutForm(forms.Form):
    # Pirkėjas
    first_name   = forms.CharField(max_length=100, label="Vardas",    error_messages={"required":"Įveskite vardą."})
    last_name    = forms.CharField(max_length=100, label="Pavardė",   error_messages={"required":"Įveskite pavardę."})
    email        = forms.EmailField(label="El. paštas",               error_messages={"required":"Įveskite el. paštą."})
    phone        = forms.CharField(max_length=30,  label="Telefonas", error_messages={"required":"Įveskite telefoną."})
    address      = forms.CharField(max_length=250, label="Adresas",   error_messages={"required":"Įveskite adresą."})
    city         = forms.CharField(max_length=100, label="Miestas",   error_messages={"required":"Įveskite miestą."})
    postal_code  = forms.CharField(max_length=20,  label="Pašto kodas", error_messages={"required":"Įveskite pašto kodą."})
    country      = forms.CharField(max_length=100, required=False)  # jei reikia

    # Pristatymas
    SHIPPING_CHOICES = ("dpd_courier", "dpd_pickup")
    shipping_method = forms.CharField(label="Pristatymo būdas", error_messages={"required":"Pasirinkite pristatymo būdą."})

    dpd_pickup_id   = forms.CharField(max_length=100, required=False)
    dpd_pickup_name = forms.CharField(max_length=250, required=False)
    dpd_pickup_addr = forms.CharField(max_length=250, required=False)

    # Atsiskaitymas
    PAYMENT_CHOICES = ("COD", "PAYSERA", "STRIPE")
    payment_method = forms.CharField(label="Apmokėjimo būdas", error_messages={"required":"Pasirinkite apmokėjimo būdą."})

    # ✅ Nauji laukai – sąskaitos faktūrai
    needs_invoice = forms.BooleanField(required=False, label="Reikalinga SF")
    company_name  = forms.CharField(max_length=255, required=False, label="Įmonės pavadinimas")
    company_code  = forms.CharField(max_length=50, required=False, label="Įmonės kodas")

    # Taisyklės
    terms_agreed = forms.BooleanField(required=True, error_messages={"required":"Turite sutikti su sąlygomis ir taisyklėmis."})

    # Marketingo sutikimas (opt-in)
    marketing_consent = forms.BooleanField(required=False)

    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean_phone(self):
        raw = (self.cleaned_data.get("phone") or "").strip()
        if not re.fullmatch(r"[0-9+\-\s()]{6,30}", raw):
            raise ValidationError("Įveskite teisingą telefono numerį.")
        return raw

    def clean(self):
        data = super().clean()

        # --- Shipping ---
        raw_shipping = (data.get("shipping_method") or "").strip().lower()
        alias_map = {"kurjeris": "dpd_courier", "pastomatas": "dpd_pickup"}
        if raw_shipping in alias_map:
            data["shipping_method"] = alias_map[raw_shipping]

        shipping = data.get("shipping_method")
        if not shipping:
            self.add_error("shipping_method", "Pasirinkite pristatymo būdą.")
        elif shipping not in self.SHIPPING_CHOICES:
            self.add_error("shipping_method", "Neteisingas pristatymo būdas.")
        if shipping == "dpd_pickup" and not data.get("dpd_pickup_id"):
            self.add_error("dpd_pickup_id", "Pasirinkite DPD paštomatą.")

        # --- Payment ---
        raw_payment = (data.get("payment_method") or "").strip().upper()
        if not raw_payment:
            self.add_error("payment_method", "Pasirinkite apmokėjimo būdą.")
        elif raw_payment in self.PAYMENT_CHOICES:
            data["payment_method"] = raw_payment
        else:
            self.add_error("payment_method", "Neteisingas apmokėjimo būdas.")

        # --- Terms ---
        if not data.get("terms_agreed"):
            self.add_error("terms_agreed", "Turite sutikti su sąlygomis ir taisyklėmis.")

        # ✅ SF validacija – jei pažymėta, privalomi pavadinimas ir kodas
        if data.get("needs_invoice"):
            if not data.get("company_name"):
                self.add_error("company_name", "Įveskite įmonės pavadinimą.")
            if not data.get("company_code"):
                self.add_error("company_code", "Įveskite įmonės kodą.")

        return data

    # (pasirenkama) orderio kūrimo pavyzdys
    def save(self, request=None):
        """
        Pavyzdys:
        order = Order.objects.create(
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            phone=self.cleaned_data["phone"],
            address=self.cleaned_data["address"],
            city=self.cleaned_data["city"],
            postal_code=self.cleaned_data["postal_code"],
            country=self.cleaned_data.get("country") or "",
            shipping_method=self.cleaned_data["shipping_method"],
            payment_method=self.cleaned_data["payment_method"],
            dpd_pickup_id=self.cleaned_data.get("dpd_pickup_id") or "",
            dpd_pickup_name=self.cleaned_data.get("dpd_pickup_name") or "",
            dpd_pickup_addr=self.cleaned_data.get("dpd_pickup_addr") or "",
            # ✅ nauji
            needs_invoice=self.cleaned_data.get("needs_invoice", False),
            company_name=self.cleaned_data.get("company_name") or "",
            company_code=self.cleaned_data.get("company_code") or "",
        )
        return order
        """
        raise NotImplementedError("Įgyvendink orderio kūrimą pagal savo modelius.")
