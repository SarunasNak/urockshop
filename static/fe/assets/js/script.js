// script.js

// 🔥 TURI BŪTI PAČIOJE VIRŠUTINĖJE script.js DALYJE:
window.addEventListener("alpine:init", () => {
    console.log("STORE INIT OK");
    Alpine.store("video", {
        open: false,
        url: ""
    });
});

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

// ----------------------------------------------------------
// VIDEO SLIDER (homepage video section)
// ----------------------------------------------------------
const videoSliderElement = document.querySelectorAll(".video-slider");

if (videoSliderElement.length && window.Swiper) {
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
        navigation: false,
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

// 3) Atsarginis variantas: kai keičiasi URL (htmx pushState),
// dar kartą sulyginam disabled (neprivaloma, bet naudinga)
window.addEventListener('popstate', function () {
  var f = document.querySelector('form[hx-get]');
  if (f) syncDisabledFields(f);
});

document.addEventListener('DOMContentLoaded', function () {
  var f = document.querySelector('form[hx-get]');
  if (f) syncDisabledFields(f);
});

document.body.addEventListener('htmx:configRequest', function (e) {
  var f = document.querySelector('form[hx-get]');
  if (f) syncDisabledFields(f);
});

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
// HTMX Loading Overlay Fix (su fade efektu)
(function() {
  const loader = document.getElementById("catalog-loading");
  if (!loader) return;

  function showLoader() {
    loader.style.display = "flex";
    requestAnimationFrame(() => loader.style.opacity = "1");
  }

  function hideLoader() {
    loader.style.opacity = "0";
    setTimeout(() => loader.style.display = "none", 300);
  }

  document.body.addEventListener("htmx:beforeRequest", showLoader);
  document.body.addEventListener("htmx:afterOnLoad", hideLoader);
})();

// ==========================================================
//  Galutinė versija — URL nebeauga, filtrai lieka švarūs
// ==========================================================
window.submitCatalogFilter = function (form) {
  // ✅ visada imam bazinį URL (be senų parametrų)
  const base = new URL(form.getAttribute("hx-get") || form.action, window.location.origin);
  const basePath = base.pathname; // pvz. /shop/

  const params = new URLSearchParams();

  // Surenkam reikšmes iš laukų
  const q = form.querySelector('[name=q]')?.value?.trim();
  const size = form.querySelector('[name=size]')?.value?.trim();
  const category = form.querySelector('[name=category]')?.value?.trim();

  if (q) params.set("q", q);
  if (size) params.set("size", size);
  if (category) params.set("category", category);

  // Sukuriam švarų URL be pasikartojimų
  const cleanUrl = params.toString()
    ? `${basePath}?${params.toString()}`
    : basePath;

  // 🔧 Atnaujinam tik hx-get (action nebeliečiam!)
  form.setAttribute("hx-get", cleanUrl);
  form.setAttribute("hx-push-url", "false");

  // Paleidžiam HTMX užklausą
  htmx.trigger(form, "submit");

  // 🔗 Atnaujinam naršyklės URL — gražus, švarus
  history.replaceState({}, "", cleanUrl);

  console.log("✅ Filtras išsiųstas į:", cleanUrl);
};

// ==========================================================
// 🔄 Pagination fix — visada naudojam AKTYVŲ filtrą, ne seną
// ==========================================================
document.body.addEventListener("htmx:configRequest", function (evt) {
  // Reaguojam tik jei tai pagination
  if (!evt.detail.path.includes("page=")) return;

  const form = document.querySelector('form[hx-get]');
  if (!form) return;

  const params = new URLSearchParams();

  // Surenkam naujausius filtrus iš formos
  const q = form.querySelector('[name=q]')?.value?.trim();
  const size = form.querySelector('[name=size]')?.value?.trim();
  const category = form.querySelector('[name=category]')?.value?.trim();

  if (q) params.set("q", q);
  if (size) params.set("size", size);
  if (category) params.set("category", category);

  // Ištraukiam puslapio numerį iš linko (pvz. ?page=2)
  const [path, query] = evt.detail.path.split("?");
  const clicked = new URLSearchParams(query || "");
  if (clicked.has("page")) params.set("page", clicked.get("page"));

  // Sudarom galutinį, švarų URL
  const cleanUrl = params.toString()
    ? `${path}?${params.toString()}`
    : path;

  // 💥 Pakeičiam kelią, kad HTMX siųstų teisingą request'ą
  evt.detail.path = cleanUrl;

  console.log("📄 Pagination path atnaujintas į:", cleanUrl);
});

// ==========================================================
// Filtrų reset į 1 puslapį (be papildomų funkcijų ar kvietimų)
// + apsauga nuo dvigubo "grįžimo į 1 puslapį"
// ==========================================================
let lastRequestPath = "";
let lastQuery = "";
let justChangedFilters = false; // 👈 naujas flag

// Kai HTMX ruošiasi siųsti užklausą
document.body.addEventListener("htmx:configRequest", function (e) {
  const [path, query] = e.detail.path.split("?");
  const params = new URLSearchParams(query || "");

  const filterKeys = ["size", "category", "q"];
  const currentFilters = filterKeys.map(k => params.get(k) || "").join("|");

  const sameFilters = currentFilters === lastQuery;
  const samePath = path === lastRequestPath;

  // 1️⃣ Jei filtrai pasikeitė – pažymim, kad ką tik keitėsi
  if (!sameFilters) {
    justChangedFilters = true;
    setTimeout(() => (justChangedFilters = false), 600); // 👈 0.6s "langas"
  }

  // 2️⃣ Jei yra "page" parametras ir tai naujas filtras — resetinam
  if (params.has("page") && (!sameFilters || !samePath)) {
    if (!justChangedFilters) {
      // tik jei ne ką tik po filtro keitimo (kad pagination veiktų iškart)
      params.delete("page");
      e.detail.path = path + (params.toString() ? "?" + params.toString() : "");
      console.log("↩️ Grįžtam į pirmą puslapį dėl naujo filtro:", e.detail.path);
    } else {
      console.log("⏸️ Praleidžiam pirmą pagination po filtro (apsauga)");
    }
  }

  lastRequestPath = path;
  lastQuery = currentFilters;
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

