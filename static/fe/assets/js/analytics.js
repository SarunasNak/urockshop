// === analytics.js ===
// Tikslus aktyvaus buvimo laiko matavimas (be cookies, be trečiųjų šalių)

(function () {
    const endpoint = "/analytics/track/";
    const sessionKey = "urock_session_id";

    // 🔹 Sukuriame arba paimame unikalų sesijos ID
    function getSessionId() {
        let sid = sessionStorage.getItem(sessionKey);
        if (!sid) {
            sid = "sess-" + Math.random().toString(36).substring(2) + Date.now().toString(36);
            sessionStorage.setItem(sessionKey, sid);
        }
        return sid;
    }

    const sessionId = getSessionId();
    const pagePath = window.location.pathname;

    // 🔹 Aktyvaus buvimo skaičiavimas
    let activeTime = 0;
    let lastStart = Date.now();

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            activeTime += Date.now() - lastStart;
        } else {
            lastStart = Date.now();
        }
    });

    window.addEventListener("beforeunload", () => {
        activeTime += Date.now() - lastStart;
        const duration = (activeTime / 1000).toFixed(1);
        sendEvent("page_leave", { duration: parseFloat(duration) });
    });

    // 🔹 Siuntimo funkcija
    window.sendEvent = function (name, data = {}) {
        const payload = {
            session_id: sessionId,
            path: pagePath,
            event_name: name,
            data: data,
            referrer: document.referrer || null,
        };

        navigator.sendBeacon
            ? navigator.sendBeacon(endpoint, JSON.stringify(payload))
            : fetch(endpoint, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload),
              });
    }

    // 🔹 Puslapio peržiūra
    sendEvent("page_view", { title: document.title });

    // 🔹 Bendri mygtukų paspaudimai (pirkimas / pasimatuoti)
    document.addEventListener("click", (e) => {
        const target = e.target.closest("button, a");
        if (!target) return;
        const text = (target.innerText || target.getAttribute("aria-label") || "").toLowerCase();

        if (text.includes("krepšel") || text.includes("pirkti")) {
            sendEvent("add_to_cart", { label: text });
        } else if (text.includes("matuot") || text.includes("pasimatuoti")) {
            sendEvent("try_on_click", { label: text });
        }
    });

    // 🔹 Dydžio pasirinkimas (S, M, L, XL, XXL, XXXL, UNI)
    document.addEventListener("click", (e) => {
    const btn = e.target.closest('[data-size], .size-option, .product-size');
    if (btn) {
        const size =
            btn.getAttribute("data-size") ||
            btn.innerText.trim().toUpperCase();

        // ❌ Neisiunčiam, jei "VISI"
        if (size === "VISI") return;

        sendEvent("size_selected", { size: size });
    }
});

    // 🔹 Kategorijos filtravimas (pvz. "Marškiniai", "Kelnės", "Paltai")
    document.addEventListener("click", (e) => {
        const cat = e.target.closest('[data-category], .filter-category, .category-link');
        if (cat) {
            const category =
                cat.getAttribute("data-category") ||
                cat.innerText.trim().toLowerCase();
            sendEvent("category_selected", { category: category });
        }
    });
})();
