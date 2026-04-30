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

    // 🔹 Unikalus lankytojo ID (veikia tiek www, tiek be www)
    function getVisitorId() {
        let vid = localStorage.getItem("urock_visitor_id");

        if (!vid) {
            // pabandom paimti iš cookie
            vid = document.cookie
                .split("; ")
                .find(row => row.startsWith("urock_visitor_id="))
                ?.split("=")[1];
        }

        if (!vid) {
            // sukuriam naują
            vid = "vis-" + Math.random().toString(36).substring(2) + Date.now().toString(36);
            const domain = window.location.hostname.includes("urock.lt") ? ".urock.lt" : window.location.hostname;
            document.cookie = `urock_visitor_id=${vid}; path=/; domain=${domain}; max-age=31536000; SameSite=None; Secure`;
        }

        // sinchronizuojam į localStorage, kad greičiau veiktų
        localStorage.setItem("urock_visitor_id", vid);
        return vid;
    }

    const visitorId = getVisitorId();

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
        visitor_id: visitorId,
        session_id: sessionId,
        path: pagePath,
        event_name: name,
        data: data,
        referrer: document.referrer || null,
        device: /Mobi|Android|iPhone|iPad/i.test(navigator.userAgent)
            ? "mobile"
            : "desktop"
    };

        navigator.sendBeacon
            ? navigator.sendBeacon(endpoint, JSON.stringify(payload))
            : fetch(endpoint, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload),
              });
    };

    // --- ir tik po to AUTOMATIC PAGE VIEW ---
    sendEvent("page_view");

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

    // 🔹 Kategorijos filtravimas — veikia ir po HTMX swap (Alpine @click.stop nebekliudo)

// 1️⃣ Atskiriam handlerį, kad galėtume jį pašalinti
function categoryClickHandler(e) {
  const cat = e.target.closest("[data-category]");
  if (!cat) return;

  const category = cat.getAttribute("data-category");
  if (!category || category === "VISI") return;

  console.log("category_selected fired", category); // debug
  sendEvent("category_selected", { category: category.toLowerCase() });
}

// 2️⃣ Funkcija, kuri visada nuima seną listenerį prieš pridedant naują
function bindCategoryTracking() {
  document.body.removeEventListener("click", categoryClickHandler, true);
  document.body.addEventListener("click", categoryClickHandler, true);
}

// 3️⃣ Pirmas pririšimas
bindCategoryTracking();

// 4️⃣ Perregistruojam po kiekvieno HTMX turinio pakeitimo (be dubliavimosi)
document.body.addEventListener("htmx:afterSwap", () => {
  bindCategoryTracking();
});

})();


