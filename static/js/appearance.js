(function () {
    "use strict";
    const { toast, fetchJSON } = window.Utopialand;

    // Debe reflejar services/appearance.py -- solo para la previsualización
    // instantánea en el cliente; el servidor vuelve a validar todo al guardar.
    const RADIUS_PRESETS = {
        sm: ["4px", "6px", "10px"],
        md: ["6px", "10px", "16px"],
        lg: ["10px", "16px", "22px"],
        xl: ["14px", "22px", "30px"],
    };
    const DENSITY_PRESETS = {
        compact: { cell: "6px 10px", item: "7px 9px", font: "13px" },
        comfortable: { cell: "10px 14px", item: "10px 12px", font: "14px" },
        spacious: { cell: "14px 18px", item: "14px 16px", font: "15px" },
    };
    const FONT_OPTIONS = {
        system: '"Segoe UI", Roboto, Inter, Arial, sans-serif',
        inter: '"Inter", "Segoe UI", sans-serif',
        poppins: '"Poppins", "Segoe UI", sans-serif',
        mono: '"JetBrains Mono", "SFMono-Regular", Consolas, monospace',
    };

    let settings = Object.assign({}, window.__APPEARANCE_INITIAL__ || {});

    function applyLive(s) {
        const root = document.documentElement;
        root.setAttribute("data-theme", s.theme);
        root.setAttribute("data-anim", s.animations_enabled ? s.animation_speed : "off");

        root.style.setProperty("--primary", s.primary_color);
        root.style.setProperty("--bg-gradient-from", s.bg_gradient_from);
        root.style.setProperty("--bg-gradient-to", s.bg_gradient_to);

        const radius = RADIUS_PRESETS[s.radius_scale] || RADIUS_PRESETS.md;
        root.style.setProperty("--radius-sm", radius[0]);
        root.style.setProperty("--radius", radius[1]);
        root.style.setProperty("--radius-lg", radius[2]);

        const density = DENSITY_PRESETS[s.density] || DENSITY_PRESETS.comfortable;
        root.style.setProperty("--density-pad-cell", density.cell);
        root.style.setProperty("--density-pad-item", density.item);
        root.style.setProperty("--base-font-size", density.font);
        root.style.setProperty("--font-family", FONT_OPTIONS[s.font_family] || FONT_OPTIONS.system);

        root.style.setProperty("--bg-blur", `${s.bg_blur}px`);
        root.style.setProperty("--bg-opacity", String(s.bg_opacity / 100));

        let bgLayer = document.querySelector(".appearance-bg");
        if (!bgLayer) {
            bgLayer = document.createElement("div");
            bgLayer.className = "appearance-bg";
            document.body.prepend(bgLayer);
        }
        bgLayer.style.backgroundImage = s.bg_image_url ? `url('${s.bg_image_url.replace(/'/g, "%27")}')` : "";
    }

    function populateControls(s) {
        document.querySelectorAll("[data-set]").forEach((el) => {
            const key = el.dataset.set;
            if (!(key in s)) return;
            if (el.tagName === "SPAN") return; // swatches: no reflejan estado, solo aplican al click
            if (el.type === "checkbox") el.checked = !!s[key];
            else el.value = s[key];
        });
        document.getElementById("a-blur-val").textContent = s.bg_blur;
        document.getElementById("a-opacity-val").textContent = s.bg_opacity;
        document.querySelectorAll('[data-set="theme"]').forEach((btn) => {
            btn.classList.toggle("btn-primary", btn.dataset.value === s.theme);
            btn.classList.toggle("btn-outline", btn.dataset.value !== s.theme);
        });
    }

    document.querySelectorAll("[data-set]").forEach((el) => {
        const key = el.dataset.set;
        const isClickTrigger = el.tagName === "SPAN" || el.tagName === "BUTTON";
        const eventName = isClickTrigger ? "click" : "input";

        el.addEventListener(eventName, () => {
            let value;
            if (isClickTrigger) value = el.dataset.value;
            else if (el.type === "checkbox") value = el.checked;
            else value = el.value;

            settings[key] = (el.type === "range") ? Number(value) : value;
            if (key === "bg_blur") document.getElementById("a-blur-val").textContent = settings[key];
            if (key === "bg_opacity") document.getElementById("a-opacity-val").textContent = settings[key];
            populateControls(settings);
            applyLive(settings);
        });
    });

    document.getElementById("btn-save-appearance").addEventListener("click", async () => {
        try {
            const data = await fetchJSON("/api/apariencia", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings),
            });
            settings = data.settings;
            populateControls(settings);
            applyLive(settings);
            toast("Apariencia guardada", "success");
        } catch (err) {
            toast(err.message, "error");
        }
    });

    document.getElementById("btn-reset-appearance").addEventListener("click", async () => {
        if (!confirm("¿Restablecer la apariencia a los valores por defecto?")) return;
        try {
            const data = await fetchJSON("/api/apariencia/reset", { method: "POST" });
            settings = data.settings;
            populateControls(settings);
            applyLive(settings);
            toast("Apariencia restablecida", "success");
        } catch (err) {
            toast(err.message, "error");
        }
    });

    populateControls(settings);
    applyLive(settings);
})();
