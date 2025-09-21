# Contributing gairės

## Kur ką keisti

### Frontend (FE)
- **Leidžiamos direktorijos:**  
  - `templates/fe/**` – HTML šablonai (CDN režimu)  
  - `static/fe/**` – jei reikia vietinių failų: `css/`, `js/`, `img/`  
- **Nedaryti pakeitimų** kituose Django šablonuose ar Python failuose.

---

## CDN ir versijos

- Naudojame **fiksuotas** CDN versijas (ne `latest`).  
  Pavyzdys:
  ```html
  <script src="https://cdn.jsdelivr.net/npm/swiper@11.1.3/swiper-bundle.min.js"></script>
  
## SEO
Staging aplinkoje visuose FE HTML privaloma įdėti:
<meta name="robots" content="noindex,nofollow">