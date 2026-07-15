(function () {
    "use strict";
    const { fetchJSON, formatNumber, escapeHTML, typeBadge, toast, blockLabel } = window.Utopialand;

    const REFRESH_MS = 60000;

    function timeAgo(unixSeconds) {
        if (!unixSeconds) return "-";
        const diff = Math.max(0, Math.floor(Date.now() / 1000) - unixSeconds);
        if (diff < 60) return "hace segundos";
        if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
        if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
        return `hace ${Math.floor(diff / 86400)} d`;
    }

    function feedItemHTML(row) {
        const block = blockLabel(row);
        const coords = (row.pos_x !== undefined && row.pos_x !== null)
            ? `${Math.round(row.pos_x)}/${Math.round(row.pos_y)}/${Math.round(row.pos_z)}`
            : null;
        const bits = [row.world, coords].filter(Boolean).join(" · ");
        return `
            <div class="feed-item">
                <div class="feed-main">
                    <span class="feed-title">
                        <strong>${escapeHTML(row.name || "?")}</strong> ${typeBadge(row.type)} ${block ? `<span class="feed-object">${escapeHTML(block)}</span>` : ""}
                    </span>
                    <span class="feed-meta">${escapeHTML(bits || "-")}</span>
                </div>
                <span class="feed-time" title="${escapeHTML(row.fecha || "")}">${timeAgo(row.time)}</span>
            </div>
        `;
    }

    function feedListHTML(rows) {
        if (!rows.length) return `<p class="table-empty">Sin actividad registrada.</p>`;
        return rows.map(feedItemHTML).join("");
    }

    function rankListHTML(rows, labelKey, valueKey, formatLabel) {
        if (!rows.length) return `<p class="table-empty">Sin datos suficientes.</p>`;
        const max = rows[0][valueKey] || 1;
        return rows.map((r) => `
            <div class="bar-row">
                <span class="bar-label">${escapeHTML(formatLabel ? formatLabel(r) : (r[labelKey] || "-"))}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round((r[valueKey] / max) * 100)}%"></div></div>
                <span class="bar-value">${formatNumber(r[valueKey])}</span>
            </div>
        `).join("");
    }

    async function safeLoad(id, url, render) {
        const el = document.getElementById(id);
        if (!el) return;
        try {
            const data = await fetchJSON(url);
            el.innerHTML = render(data.results || data);
        } catch (err) {
            el.innerHTML = `<p class="table-empty">Error al cargar.</p>`;
        }
    }

    async function refreshOverview() {
        try {
            const data = await fetchJSON("/api/dashboard/resumen");
            const set = (id, value) => {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            };
            set("dash-stat-total", formatNumber(data.total));
            set("dash-stat-today-calendar", formatNumber(data.today_calendar));
            set("dash-stat-today", formatNumber(data.today));
            set("dash-stat-week", formatNumber(data.last_7_days));
            set("dash-stat-players", formatNumber(data.distinct_players));
            set("dash-stat-worlds", formatNumber(data.distinct_worlds));
            set("dash-stat-last-event", data.last_event_time_fmt || "-");
        } catch (err) {
            /* silencioso: no interrumpir el resto del dashboard por esto */
        }
    }

    function refreshAll() {
        refreshOverview();

        safeLoad("dash-recent-list", "/api/dashboard/actividad-reciente", (rows) => {
            const badge = document.getElementById("dash-recent-badge");
            if (badge) badge.textContent = `${rows.length} recientes`;
            return feedListHTML(rows);
        });

        safeLoad("dash-important-list", "/api/dashboard/eventos-importantes", feedListHTML);
        safeLoad("dash-explosions", "/api/dashboard/explosiones", feedListHTML);
        safeLoad("dash-deaths", "/api/dashboard/muertes", feedListHTML);

        safeLoad("dash-active-players", "/api/dashboard/jugadores-activos", (rows) =>
            rankListHTML(rows, "name", "total"));

        safeLoad("dash-modified-blocks", "/api/dashboard/bloques-modificados", (rows) =>
            rankListHTML(rows, "obj_name", "total", (r) => blockLabel(r) || "Desconocido"));
    }

    refreshAll();
    setInterval(refreshAll, REFRESH_MS);
})();
