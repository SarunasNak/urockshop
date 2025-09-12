import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import ProductImage

@receiver(post_delete, sender=ProductImage)
def delete_file_on_image_delete(sender, instance, **kwargs):
    """Pašalina failą iš disko, kai ištrini ProductImage įrašą DB."""
    if instance.image and hasattr(instance.image, "path") and os.path.isfile(instance.image.path):
        try:
            os.remove(instance.image.path)
        except OSError:
            pass

@receiver(pre_save, sender=ProductImage)
def delete_old_file_on_change(sender, instance, **kwargs):
    """Pašalina seną failą, kai tame pačiame įraše įkeli naują nuotrauką."""
    if not instance.pk:
        return  # naujas įrašas, senos nuotraukos nėra
    try:
        old = ProductImage.objects.get(pk=instance.pk)
    except ProductImage.DoesNotExist:
        return
    if old.image and old.image != instance.image:
        if hasattr(old.image, "path") and os.path.isfile(old.image.path):
            try:
                os.remove(old.image.path)
            except OSError:
                pass
