// static/fe/assets/js/newsletter.js
(function () {
  function focusNewsletterIn(targetSelector) {
    // Rask sekciją iš hash (#id) arba fallback'ą
    var section = targetSelector ? document.querySelector(targetSelector) : null;
    if (!section) section = document.querySelector('#newsletter-footer, #newsletter, [id*="newsletter"]');
    if (!section) return;

    // Rask email inputą toje sekcijoje
    var input = section.querySelector('[data-newsletter-email], input[type="email"]');
    if (!input) return;

    // Sklandžiai nuslink ir sufokusuok
    if (input.scrollIntoView) {
      input.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
      section.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    setTimeout(function () {
      try { input.focus({ preventScroll: true }); } catch (e) { input.focus(); }
    }, 300);
  }

  // Deleguotas paspaudimas ant visų „kviečiančių“ elementų
  document.addEventListener('click', function (e) {
    var el = e.target.closest('.js-newsletter-link');
    if (!el) return;

    var target = el.getAttribute('data-target') || el.getAttribute('href') || '';
    e.preventDefault();

    if (target && target.startsWith('#')) {
      focusNewsletterIn(target);
      try { history.replaceState(null, '', target); } catch (_) {}
    } else {
      focusNewsletterIn(null);
    }
  });

  // Jei atėjome su hash (pvz., /shop#newsletter-footer ar #newsletter-product)
  if (location.hash) {
    setTimeout(function () { focusNewsletterIn(location.hash); }, 200);
  }
})();
