# Urock – Staging

## Aprašymas
Django projektas su FE šablonais `templates/fe/` ir statiniais `static/fe/`. FE kol kas naudoja CDN (Tailwind/Alpine/Swiper). Deploy – PythonAnywhere (staging.urock.lt).

## Reikalavimai
- Python 3.11
- Virtualenv (arba PythonAnywhere virtualenv)
- Django (versija kaip `requirements.txt`)

## Greitas startas (lokaliai)
```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
