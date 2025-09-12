# checkout/forms.py
from django import forms

class CheckoutForm(forms.Form):
    first_name = forms.CharField(max_length=100, label="Vardas")
    last_name  = forms.CharField(max_length=100, label="Pavardė")
    email      = forms.EmailField(label="El. paštas")
    address    = forms.CharField(max_length=250, label="Adresas")
    city       = forms.CharField(max_length=100, label="Miestas")
    postal_code= forms.CharField(max_length=20,  label="Pašto kodas")
