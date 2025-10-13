from django import forms

class CheckoutForm(forms.Form):
    # Pirkėjas
    first_name   = forms.CharField(max_length=100, label="Vardas")
    last_name    = forms.CharField(max_length=100, label="Pavardė")
    email        = forms.EmailField(label="El. paštas")
    address      = forms.CharField(max_length=250, label="Adresas")
    city         = forms.CharField(max_length=100, label="Miestas")
    postal_code  = forms.CharField(max_length=20,  label="Pašto kodas")

    # Pristatymas
    SHIPPING_CHOICES = (
        ("dpd_courier", "DPD kurjeris"),
        ("dpd_pickup",  "DPD paštomatas"),
    )
    # BUVO: ChoiceField(choices=SHIPPING_CHOICES, ...)
    # DABAR: CharField — normalizuojame clean() viduje
    shipping_method = forms.CharField(label="Pristatymo būdas")

    # Jei pasirenkamas paštomatas
    dpd_pickup_id   = forms.CharField(max_length=100, required=False)
    dpd_pickup_name = forms.CharField(max_length=250, required=False)
    dpd_pickup_addr = forms.CharField(max_length=250, required=False)

    # Atsiskaitymas
    PAYMENT_CHOICES = (
        ("COD",     "Mokėti atsiimant"),
        ("PAYSERA", "Paysera"),
        ("STRIPE",  "Kortele (Stripe)"),
    )
    # Paliekam kaip CharField — normalizuos clean()
    payment_method = forms.CharField(label="Apmokėjimo būdas")

    # --- Normalizavimas / Validacija ---
    def clean_email(self):
        return (self.cleaned_data.get("email") or "").strip().lower()

    def clean(self):
        data = super().clean()

        # Leisk frontendui siųsti ir 'kurjeris'/'pastomatas' – sužemelink į choices
        raw_shipping = (data.get("shipping_method") or "").strip().lower()
        alias_map = {
            "kurjeris": "dpd_courier",
            "pastomatas": "dpd_pickup",
        }
        if raw_shipping in alias_map:
            data["shipping_method"] = alias_map[raw_shipping]

        # pick-up atveju – reikalauk paštomato ID
        if data.get("shipping_method") == "dpd_pickup" and not data.get("dpd_pickup_id"):
            self.add_error("dpd_pickup_id", "Pasirinkite DPD paštomatą.")

        # Saugesnis payment alias’inimas (jei ateitų mažosiomis)
        raw_payment = (data.get("payment_method") or "").strip().upper()
        if raw_payment in {"COD","PAYSERA","STRIPE"}:
            data["payment_method"] = raw_payment
        else:
            self.add_error("payment_method", "Pasirinkite apmokėjimo būdą.")

        return data

    # (pasirenkama) tavo patogumui – čia gali dėti order’io kūrimą
    def save(self, request=None):
        """
        Pavyzdys:
        order = Order.objects.create(
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
            email=self.cleaned_data["email"],
            address=self.cleaned_data["address"],
            city=self.cleaned_data["city"],
            postal_code=self.cleaned_data["postal_code"],
            shipping_method=self.cleaned_data["shipping_method"],
            payment_method=self.cleaned_data["payment_method"],
            dpd_pickup_id=self.cleaned_data.get("dpd_pickup_id") or None,
            dpd_pickup_name=self.cleaned_data.get("dpd_pickup_name") or "",
            dpd_pickup_addr=self.cleaned_data.get("dpd_pickup_addr") or "",
            # ... + krepšelio snapshot ir pan.
        )
        return order
        """
        raise NotImplementedError("Įgyvendink orderio kūrimą pagal savo modelius.")
