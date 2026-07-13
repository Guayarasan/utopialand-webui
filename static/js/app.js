/**
 * Utilidades compartidas por todas las páginas: sidebar móvil, toasts,
 * helpers de fetch/formato y un pequeño debounce. Cada página tiene su
 * propio archivo JS (records.js, players.js, ...) que se apoya en estas
 * funciones expuestas en `window.Utopialand`.
 */
(function () {
    "use strict";

    // ---------- Sidebar móvil ----------
    const sidebar = document.getElementById("sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle");
    const overlay = document.getElementById("sidebar-overlay");

    function openSidebar() {
        sidebar.classList.add("open");
        overlay.classList.add("show");
    }
    function closeSidebar() {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
    }
    if (toggleBtn) toggleBtn.addEventListener("click", () => {
        sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
    });
    if (overlay) overlay.addEventListener("click", closeSidebar);

    // ---------- Toasts ----------
    function toast(message, type) {
        const container = document.getElementById("toast-container");
        if (!container) return;
        const el = document.createElement("div");
        el.className = "toast" + (type ? " toast-" + type : "");
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4200);
    }

    // ---------- fetch JSON con manejo de errores uniforme ----------
    async function fetchJSON(url, options) {
        const res = await fetch(url, options);
        let body = null;
        try {
            body = await res.json();
        } catch (e) {
            /* respuesta sin cuerpo JSON */
        }
        if (!res.ok) {
            const message = (body && body.error) || `Error ${res.status}`;
            throw new Error(message);
        }
        return body;
    }

    // ---------- debounce ----------
    function debounce(fn, wait) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), wait);
        };
    }

    // ---------- formato ----------
    function formatNumber(n) {
        if (n === null || n === undefined) return "-";
        return Number(n).toLocaleString("es-ES");
    }

    function escapeHTML(str) {
        if (str === null || str === undefined) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function typeBadge(type) {
        return `<span class="type-badge">${escapeHTML(type || "-")}</span>`;
    }

    function buildQueryString(params) {
        const search = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
            if (value === null || value === undefined || value === "") return;
            if (Array.isArray(value)) {
                value.filter(Boolean).forEach((v) => search.append(key, v));
            } else {
                search.append(key, value);
            }
        });
        return search.toString();
    }

    // ---------- modal genérico ----------
    function setupModal(backdropId, closeId) {
        const backdrop = document.getElementById(backdropId);
        const closeBtn = document.getElementById(closeId);
        if (!backdrop) return { open: () => {}, close: () => {} };

        function close() {
            backdrop.hidden = true;
        }
        function open() {
            backdrop.hidden = false;
        }
        if (closeBtn) closeBtn.addEventListener("click", close);
        backdrop.addEventListener("click", (e) => {
            if (e.target === backdrop) close();
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") close();
        });
        return { open, close };
    }

    window.Utopialand = {
        toast,
        fetchJSON,
        debounce,
        formatNumber,
        escapeHTML,
        typeBadge,
        buildQueryString,
        setupModal,
    };
})();
