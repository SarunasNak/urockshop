// script.js

window.__isHistoryRestore = false;

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
window.__headroom = null;

const header = document.querySelector(".header");
if (header && window.Headroom) {
  window.__headroom = new Headroom(header, {
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

  window.__headroom.init();
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

// ----------------------------------------------------------
// VIDEO SLIDER (homepage video section)
// ----------------------------------------------------------
const videoSliderElement = document.querySelectorAll(".video-slider");

if (videoSliderElement.length && window.Swiper) {

  // apsauga nuo dvigubo init
  if (!videoSliderElement[0].classList.contains("swiper-initialized")) {

    new Swiper(".video-slider", {
      slidesPerView: 1,
      spaceBetween: 0,
      loop: false,
      navigation: {
        nextEl: ".swiper-button-next",
        prevEl: ".swiper-button-prev",
      },
      breakpoints: {
        0: {
          slidesPerView: 1.8,
          spaceBetween: 56,
          navigation: false
        },
        768: {
          slidesPerView: 3,
          spaceBetween: 56,
          navigation: {
            nextEl: ".swiper-button-next",
            prevEl: ".swiper-button-prev",
          },
        },
      },
    });

  }
}
  });

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

document.body.addEventListener('cart-updated', function (e) {
  const d = e.detail || {};
  const badge = document.getElementById('cart-count');
  if (badge) {
    badge.textContent = `(${d.cart_count ?? 0})`;
  }
});

// Maža util funkcija: sutvarko disabled pagal reikšmes
function syncDisabledFields(form) {
  ['size', 'category', 'q'].forEach(function (name) {
    var el = form.querySelector('[name="'+name+'"]');
    if (!el) return;
    var v = (el.value || '').trim();
    el.disabled = (v === '');
  });
}

// 1) Prieš kiekvieną HTMX submit – sutvarkom disabled,
// kad į URL nepatektų tušti parametrai (size=&category=)
document.addEventListener('submit', function (e) {
  var f = e.target;
  if (!f.matches('form[hx-get]')) return;
  // jei Alpine mygtukai pakeitė hidden inputų value – atsinaujins disabled
  syncDisabledFields(f);
});

// 2) Po bet kurio HTMX atnaujinimo (grid’o perload) – vėl
// persinchronizuojam disabled būsenas naujai įkeltame fragmente
document.addEventListener('htmx:afterSwap', function (e) {
  if (e.target && e.target.id === 'catalog-results') {
    var f = document.querySelector('form[hx-get]');
    if (f) syncDisabledFields(f);
  }
});

// 🔒 Headroom reset po HTMX swap (FIX header disappearing)
document.body.addEventListener("htmx:afterSwap", function () {
  if (!window.__headroom) return;

  const header = document.querySelector(".header");
  if (!header) return;

  // Priverstinai parodyti headerį
  header.classList.remove("header--unpinned");
  header.classList.add("header--pinned");

  // Resetinam Headroom būseną
  window.__headroom.destroy();
  window.__headroom.init();
});

// 3) Atsarginis variantas: kai keičiasi URL (htmx pushState),
// dar kartą sulyginam disabled (neprivaloma, bet naudinga)
window.addEventListener('popstate', function () {
  const f = document.querySelector('form[hx-get]');
  if (f) syncFormFromUrl(f);
});

// 👇 PRIDĖTI ČIA
document.body.addEventListener('htmx:historyRestore', function () {
  window.__isHistoryRestore = true;

  const f = document.querySelector('form[hx-get]');
  if (f) syncFormFromUrl(f);

  // atleidžiam PO viso HTMX ciklo
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.__isHistoryRestore = false;
    });
  });
});

document.addEventListener('DOMContentLoaded', function () {
  var f = document.querySelector('form[hx-get]');
  if (f) syncDisabledFields(f);
});

// 🔄 Atstato filtrų formą iš URL (BACK / BFCache / history)
function syncFormFromUrl(form) {
  const params = new URLSearchParams(window.location.search);

  ['q', 'size', 'category'].forEach(name => {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return;

    const val = params.get(name) || '';

    if (el.tagName === 'SELECT') {
      el.value = val;
    } else if (el.type === 'radio' || el.type === 'checkbox') {
      el.checked = el.value === val;
    } else {
      el.value = val;
    }
  });

  // po value atkūrimo – disabled logika
  syncDisabledFields(form);
}

// ─────────────────────────────────────────────
// Checkout validacija prieš submit
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const checkoutBtn = document.querySelector("#place-order-btn"); // tavo mygtukas „Užsakyti“
  const checkoutForm = document.querySelector("#checkout-post-form");

  if (!checkoutBtn || !checkoutForm) return;

  console.log("Checkout script attached");
checkoutBtn.addEventListener("click", () => {
  console.log("Our checkout click fired");
});

  checkoutBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopImmediatePropagation(); // ← pridėk šitą eilutę, kad blokuotų kitus click handlerius

    // 1. Tikrinam sąlygas
    const terms = document.querySelector('input[name="terms_agreed"]');
    if (!terms || !terms.checked) {
      alert("Turite sutikti su sąlygomis ir taisyklėmis.");
      return;
    }

    // 2. Tikrinam apmokėjimo būdą
    const payment = document.querySelector("#payment_method_hidden")?.value?.trim();
console.log("DEBUG payment_method_hidden value:", payment);
if (!payment) {
  alert("Pasirinkite apmokėjimo būdą.");
  return;
}

    // 3. Viskas gerai → siunčiam formą
    checkoutForm.submit();
  });
});

// ─────────────────────────────────────────────
// HTMX Loading Overlay Fix (STABILI BACK + MOBILE)
// ─────────────────────────────────────────────
(function() {
  const loader = document.getElementById("catalog-loading");
  if (!loader) return;

  let isLoading = false;

  function showLoader() {
    isLoading = true;
    loader.style.display = "flex";
    requestAnimationFrame(() => loader.style.opacity = "1");
  }

  function hideLoader() {
    isLoading = false;
    loader.style.opacity = "0";
    setTimeout(() => {
      if (!isLoading) {
        loader.style.display = "none";
      }
    }, 300);
  }

  // HTMX normalus request
  document.body.addEventListener("htmx:beforeRequest", showLoader);
  document.body.addEventListener("htmx:afterOnLoad", hideLoader);
  document.body.addEventListener("htmx:responseError", hideLoader);

  // 🔒 Užrakinam headerį HTMX filtrų metu (UX protection)
document.body.addEventListener("htmx:beforeRequest", () => {
  document.body.classList.add("no-headroom");
});

document.body.addEventListener("htmx:afterOnLoad", () => {
  document.body.classList.remove("no-headroom");
});

  // 🔥 BACK / FORWARD (HTMX history)
  document.body.addEventListener("htmx:historyRestore", hideLoader);

  // 🔥 MOBILE SAFARI / CHROME BFCache
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) {
      hideLoader();
    }
  });

  // 🛟 Safety fallback (jei kažkas nulūžta)
  setTimeout(hideLoader, 2500);
})();

// ==========================================================
//  Galutinė versija — URL nebeauga, filtrai lieka švarūs
// ==========================================================
window.submitCatalogFilter = function (form) {
  const base = new URL(form.getAttribute("hx-get") || form.action, window.location.origin);
  const basePath = base.pathname;

  const params = new URLSearchParams();

  const q = form.querySelector('[name=q]')?.value?.trim();
  const size = form.querySelector('[name=size]')?.value?.trim();
  const category = form.querySelector('[name=category]')?.value?.trim();

  if (q) params.set("q", q);
  if (size) params.set("size", size);
  if (category) params.set("category", category);

  const cleanUrl = params.toString()
    ? `${basePath}?${params.toString()}`
    : basePath;

  // 1️⃣ siunčiam HTMX
  htmx.trigger(form, "submit");

  // 2️⃣ atnaujinam URL
  history.replaceState({}, "", cleanUrl);

  // 3️⃣ informuojam JS state
  window.__catalogState.lastQuery = params.toString();

  console.log("✅ Filtras išsiųstas į:", cleanUrl);
};

// ==========================================================
// ✅ VIENINTELIS HTMX configRequest (FILTRAI + PAGINATION)
// ==========================================================


// 1️⃣ init state
window.__catalogState = window.__catalogState || {
lastQuery: ""
};


// 2️⃣ init iš URL (fix pirmam pagination clickui)
(function initCatalogStateFromUrl() {
const params = new URLSearchParams(window.location.search);
const filterKeys = ["size", "category", "q"];
window.__catalogState.lastQuery = filterKeys
.map(k => params.get(k) || "")
.join("|");
})();


// 3️⃣ HTMX request korekcija
document.body.addEventListener("htmx:configRequest", function (e) {
const [path, query] = e.detail.path.split("?");
const params = new URLSearchParams(query || "");


const filterKeys = ["size", "category", "q"];
const currentFilters = filterKeys.map(k => params.get(k) || "").join("|");


// 🔒 BACK / FORWARD – NIEKO NELIEČIAM
if (window.__isHistoryRestore) {
window.__catalogState.lastQuery = currentFilters;
return;
}


const isPagination = params.has("page");
const filtersChanged = currentFilters !== window.__catalogState.lastQuery;


// 🔄 resetinam page tik kai tikrai pasikeitė filtrai
if (filtersChanged && isPagination && window.__catalogState.lastQuery !== "") {
params.delete("page");
}


e.detail.path = path + (params.toString() ? "?" + params.toString() : "");
window.__catalogState.lastQuery = currentFilters;


console.log("🔁 Final path:", e.detail.path);
});


// ==========================================================
// 500 klaidų gaudymas (HTMX + Fetch)
// ==========================================================
(function() {
  // Gaudo HTMX klaidas
  document.body.addEventListener("htmx:responseError", function (e) {
    const status = e.detail.xhr.status;
    if (status === 500) {
      report500Error(e.detail.xhr.responseURL || window.location.href, "HTMX request failed with 500");
    }
  });

  // Gaudo global fetch klaidas (jei naudoji fetch API)
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    const res = await originalFetch(...args);
    if (res.status === 500) {
      report500Error(res.url || window.location.href, "Fetch request failed with 500");
    }
    return res;
  };

  // Siunčia pranešimą į backendą
  function report500Error(url, message) {
    const payload = {
      url: url,
      message: message,
      userAgent: navigator.userAgent,
      time: new Date().toISOString()
    };

    // Bandome tyliai pranešti per Beacon (arba fallback į fetch)
    const endpoint = "/report-error/";

    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, JSON.stringify(payload));
    } else {
      fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    console.warn("🚨 500 klaida aptikta, išsiųstas pranešimas:", payload);
  }
})();

document.addEventListener("DOMContentLoaded", () => {

  new Swiper(".tips-slider", {
    slidesPerView: 1.3,
    spaceBetween: 40,
    breakpoints: {
      768: { slidesPerView: 3 }
    },
    navigation: {
      nextEl: ".tips-next",
      prevEl: ".tips-prev",
    },
  });

  new Swiper(".collection-slider", {
    slidesPerView: 1.3,
    spaceBetween: 40,
    breakpoints: {
      768: { slidesPerView: 3 }
    },
    navigation: {
      nextEl: ".collection-next",
      prevEl: ".collection-prev",
    },
  });

});

// ===============================
// PhotoSwipe init (PRODUCT PAGE)
// ===============================
document.addEventListener("DOMContentLoaded", () => {
if (!window.PhotoSwipeLightbox || !window.PhotoSwipe) return;


const gallery = document.querySelector(".product-slider");
if (!gallery) return;


const lightbox = new PhotoSwipeLightbox({
gallery: ".product-slider",
children: "a",
pswpModule: PhotoSwipe,


// 🖱️ Mouse wheel zoom
wheelToZoom: true,


// 🧠 Zoom ribos
maxZoomLevel: 4, // kiek max gali priartinti
secondaryZoomLevel: 2 // double-click / scroll mid
});


lightbox.init();
});




