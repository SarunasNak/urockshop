// script.js

// Example: Alpine.js reactive state
document.addEventListener("alpine:init", () => {
  Alpine.data("dropdown", () => ({
    open: false,
    toggle() {
      this.open = !this.open;
    },
  }));
});

// Example: Initialize Swiper
document.addEventListener("DOMContentLoaded", () => {
  const productSliderElement = document.querySelectorAll(".product-slider");

  // Example: Headroom
  const header = document.querySelector(".header");
  if (header && window.Headroom) {
    const headroom = new Headroom(header, {
      offset: 100,
      tolerance: { up: 0, down: 0 },
      classes: {
        initial: "header",
        pinned: "header--pinned",
        unpinned: "header--unpinned",
        top: "header--top",
        notTop: "header--scrolled",
        bottom: "header--bottom",
        notBottom: "header--not-bottom",
      },
      scroller: window,
    });
    headroom.init();
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");
      if (!href || href === "#") return; // skip triggers
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const yOffset = 0;
        const y = target.getBoundingClientRect().top + window.pageYOffset + yOffset;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    });
  });

  // Product slider
  if (productSliderElement.length && window.Swiper) {
    new Swiper(".product-slider", {
      slidesPerView: 1,
      spaceBetween: 0,
      loop: false,
      navigation: {
        nextEl: ".swiper-button-next",
        prevEl: ".swiper-button-prev",
      },
      breakpoints: {
        0:  { slidesPerView: 1.5, spaceBetween: 10, navigation: false },
        768:{ slidesPerView: 1,   spaceBetween: 0,
              navigation: { nextEl: ".swiper-button-next", prevEl: ".swiper-button-prev" } },
      },
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Cart: remove line via AJAX (delegation on document)
  // ─────────────────────────────────────────────────────────────
  document.addEventListener("click", function (e) {
    // gaudom tik mygtuką, esantį formoje su action, kuriame yra "cart_remove"
    const btn = e.target.closest('form[action*="cart_remove"] button');
    if (!btn) return;

    e.preventDefault();

    const form = btn.closest("form");
    if (!form) return;

    const formData = new FormData(form);

    fetch(form.action, {
      method: "POST",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      body: formData
    })
      .then(r => r.json())
      .then(data => {
        if (!data || !data.ok) return;

        // 1) Pašalinti pašalintos prekės kortelę iš DOM
        const id = form.querySelector('input[name="variant_id"]').value;
        const card =
          form.closest(`[data-variant-id="${id}"]`) ||
          form.closest(".flex.items-start.justify-between"); // atsarginis variantas
        if (card) card.remove();

        // 2) Atnaujinti header’io skaičiuką
        const badge = document.getElementById("cart-count");
        if (badge) badge.textContent = `(${data.cart_count || 0})`;

        // 3) (pasirinktinai) atnaujinti sumas, jei turi ID elementų
        // pvz.: <span id="order-total">...</span>
        // if (typeof data.total !== "undefined") {
        //   const totalEl = document.getElementById("order-total");
        //   if (totalEl) totalEl.textContent = Number(data.total).toFixed(2);
        // }
      })
      .catch(console.error);
  });
});

document.body.addEventListener('cart-updated', function (e) {
  const d = e.detail || {};
  const badge = document.getElementById('cart-count');
  if (badge) {
    badge.textContent = `(${d.cart_count ?? 0})`;
  }
});
