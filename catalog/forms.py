from django import forms
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Product

class ProductForm(forms.ModelForm):
    description = forms.CharField(
        label="Aprašymas",
        required=False,
        widget=CKEditor5Widget(config_name="products"),  # <- naudok šį profilį
    )
    class Meta:
        model = Product
        fields = "__all__"

