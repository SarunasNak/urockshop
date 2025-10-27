from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from newsletter.models import Subscriber
from newsletter.emails import send_personalized_email


class Command(BaseCommand):
    help = "Tikrina prenumeratorius ir siunčia asmeninius laiškus po 46h 30min, bet tik dienos metu (07:00–22:00)."

    def handle(self, *args, **options):
        # ⏰ Vietinis laikas (Lietuva)
        current_hour = timezone.localtime().hour
        if current_hour < 7 or current_hour >= 22:
            self.stdout.write("Naktis – laiškai nebus siunčiami.")
            return

        # 🕒 Randam prenumeratorius, kuriems jau laikas gauti antrą laišką
        cutoff = timezone.now() - timedelta(hours=46, minutes=30)
        subscribers = Subscriber.objects.filter(
            created_at__lte=cutoff,
            personalized_email_sent=False
        )

        if not subscribers.exists():
            self.stdout.write("Nėra prenumeratorių, kuriems reikia siųsti laišką.")
            return

        for sub in subscribers:
            try:
                send_personalized_email(sub.email)
                sub.personalized_email_sent = True
                sub.save(update_fields=['personalized_email_sent'])
                self.stdout.write(self.style.SUCCESS(f"Išsiųstas asmeninis laiškas: {sub.email}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Klaida siunčiant {sub.email}: {str(e)}"))
