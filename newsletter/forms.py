from django import forms
from .models import Subscriber

class SubscribeForm(forms.Form):
    email = forms.EmailField()
    hp = forms.CharField(required=False)  # honeypot

    def clean(self):
        data = super().clean()
        if data.get("hp"):  # botai užpildo
            raise forms.ValidationError("Spam")
        return data

    def save(self, source="footer"):
        email = self.cleaned_data["email"].lower()
        obj, _ = Subscriber.objects.get_or_create(email=email, defaults={"source": source})
        if not obj.is_active:
            obj.is_active = True
            obj.save(update_fields=["is_active"])
        return obj
