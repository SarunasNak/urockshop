// === analytics.js ===
// Tikslus aktyvaus buvimo laiko matavimas (be cookies, be trečiųjų šalių)

(function () {

    // ✅ Jei admin ar staff – išjungiam analitiką
    if (document.cookie.includes("no_analytics=1")) {
        console.log("🔕 Analytics disabled for admin/staff user.");
        window.sendEvent = function() {};
        return; // ← dabar return yra funkcijos viduje, todėl klaidos nebus
    }

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
    };

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

    // 🔹 Užsakymo mygtukas krepšelyje
document.addEventListener("click", (e) => {
    const orderBtn = e.target.closest("button, a, input[type='submit']");
    if (!orderBtn) return;

    const text = (orderBtn.innerText || orderBtn.value || "").toLowerCase();

    // aptinkam „užsakyti“, „patvirtinti užsakymą“ ir pan.
    if (text.includes("užsakyti") || text.includes("užsakymą") || text.includes("patvirtinti")) {
        sendEvent("order_click", { label: text });
    }
});

    // 🔹 Dydžio pasirinkimas (S, M, L, XL, XXL, XXXL, UNI)
    document.addEventListener("click", (e) => {
        const btn = e.target.closest('[data-size], .size-option, .product-size');
        if (btn) {
            const size =
                btn.getAttribute("data-size") ||
                btn.innerText.trim().toUpperCase();

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

    // --- 🔹 PAPILDOMA SOURCE ANALYTICS LOGIKA ---
    (function () {
        const sourceKey = "urock_source";
        const urlParams = new URLSearchParams(window.location.search);
        const srcParam = urlParams.get("src");

        if (srcParam) sessionStorage.setItem(sourceKey, srcParam);

        let source = sessionStorage.getItem(sourceKey);
        if (!source) {
            const ref = document.referrer || "";
            if (!ref) source = "Direct";
            else if (ref.includes("google")) source = "Google Organic";
            else if (ref.includes("instagram")) source = "Instagram";
            else if (ref.includes("facebook")) source = "Facebook";
            else if (ref.includes("tiktok")) source = "TikTok";
            else source = "Referral";
            sessionStorage.setItem(sourceKey, source);
        }

        const originalSendEvent = window.sendEvent;
        window.sendEvent = function (name, data = {}) {
            data.source = sessionStorage.getItem(sourceKey) || source;
            originalSendEvent(name, data);
        };

        setTimeout(() => {
            if (window.location.search.includes("src=")) {
                const cleanUrl = window.location.origin + window.location.pathname;
                window.history.replaceState({}, document.title, cleanUrl);
            }
        }, 1000);
    })();

    // 🔹 Puslapio peržiūra
    setTimeout(() => {
        sendEvent("page_view", { title: document.title });
    }, 150);

})(); // 👈 uždaro pagrindinę funkciją
