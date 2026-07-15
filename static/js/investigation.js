(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, typeBadge, buildQueryString, blockLabel } = window.Utopialand;

    const form = document.getElementById("inv-form");
    const resultsEl = document.getElementById("inv-results");
    const emptyEl = document.getElementById("inv-empty");
    const summaryStatsEl = document.getElementById("inv-summary-stats");
    const categoriesEl = document.getElementById("inv-categories");
    const playersWorldsEl = document.getElementById("inv-players-worlds");
    const timelineEl = document.getElementById("inv-timeline");
    const countBadge = document.getElementById("inv-count");
    const exportBtn = document.getElementById("btn-export-inv");

    let lastRows = [];

    function localToUnix(value) {
        if (!value) return null;
        const date = new Date(value);
        return Math.floor(date.getTime() / 1000);
    }

    const CATEGORY_ICONS = {
        explosion: "💥", break: "⛏️", place: "🧱", container: "📦",
        entity: "⚔️", interaction: "🤚", other: "❔",
    };

    function feedItemHTML(row) {
        const coords = (row.pos_x !== undefined && row.pos_x !== null)
            ? `${Math.round(row.pos_x)}/${Math.round(row.pos_y)}/${Math.round(row.pos_z)}`
            : null;
        const bits = [row.world, coords, row.distance !== undefined ? `${row.distance} bloques del centro` : null].filter(Boolean).join(" · ");
        const block = blockLabel(row);
        return `
            <div class="feed-item">
                <div class="feed-main">
                    <span class="feed-title">
                        ${CATEGORY_ICONS[row.category] || "❔"} <strong>${escapeHTML(row.name || "?")}</strong>
                        ${typeBadge(row.type)} ${block ? `<span class="feed-object">${escapeHTML(block)}</span>` : ""}
                    </span>
                    <span class="feed-meta">${escapeHTML(bits || "-")}</span>
                </div>
                <span class="feed-time">${escapeHTML(row.fecha)}</span>
            </div>
        `;
    }

    function categoriesHTML(byCategory) {
        if (!byCategory.length) return `<p class="table-empty">Sin eventos.</p>`;
        const max = byCategory[0].total || 1;
        return byCategory.map((c) => `
            <div class="bar-row">
                <span class="bar-label">${CATEGORY_ICONS[c.category] || ""} ${escapeHTML(c.label)}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round((c.total / max) * 100)}%"></div></div>
                <span class="bar-value">${formatNumber(c.total)}</span>
            </div>
        `).join("");
    }

    function chipListHTML(items, prefix) {
        if (!items.length) return `<p class="muted-text">Ninguno.</p>`;
        return `<div class="chip-list">` + items.map((i) => `<span class="chip" style="cursor:default;">${escapeHTML(prefix)}${escapeHTML(i)}</span>`).join("") + `</div>`;
    }

    async function runReport() {
        const formData = new FormData(form);
        const params = {
            player: formData.get("player"),
            world: formData.get("world"),
            x: formData.get("x"),
            y: formData.get("y"),
            z: formData.get("z"),
            radius: formData.get("radius"),
            date_from: localToUnix(formData.get("date_from_local")),
            date_to: localToUnix(formData.get("date_to_local")),
        };

        try {
            const data = await fetchJSON(`/api/investigacion/informe?${buildQueryString(params)}`);
            lastRows = data.results;
            renderReport(data.results, data.summary);
        } catch (err) {
            toast(err.message, "error");
        }
    }

    function renderReport(rows, summary) {
        emptyEl.hidden = true;
        resultsEl.hidden = false;

        summaryStatsEl.innerHTML = `
            <div class="stat-card"><span class="stat-label">Total de eventos</span><span class="stat-value">${formatNumber(summary.total)}</span></div>
            <div class="stat-card"><span class="stat-label">Jugadores involucrados</span><span class="stat-value">${formatNumber(summary.players.length)}</span></div>
            <div class="stat-card"><span class="stat-label">Mundos</span><span class="stat-value">${formatNumber(summary.worlds.length)}</span></div>
            <div class="stat-card"><span class="stat-label">Primer evento</span><span class="stat-value stat-value-sm">${escapeHTML(summary.first_event_fmt || "-")}</span></div>
            <div class="stat-card"><span class="stat-label">Último evento</span><span class="stat-value stat-value-sm">${escapeHTML(summary.last_event_fmt || "-")}</span></div>
        `;

        categoriesEl.innerHTML = categoriesHTML(summary.by_category);
        playersWorldsEl.innerHTML = `
            <p class="muted-text" style="margin-bottom:6px;">Jugadores</p>
            ${chipListHTML(summary.players, "👤 ")}
            <p class="muted-text" style="margin: 14px 0 6px;">Mundos</p>
            ${chipListHTML(summary.worlds, "🌍 ")}
        `;

        countBadge.textContent = `${formatNumber(rows.length)} eventos` + (summary.truncated ? " (truncado, refina los filtros)" : "");
        timelineEl.innerHTML = rows.length
            ? rows.map(feedItemHTML).join("")
            : `<p class="table-empty">Sin eventos para estos filtros.</p>`;
    }

    function downloadCSV(rows) {
        if (!rows.length) {
            toast("No hay datos que exportar.", "error");
            return;
        }
        const columns = ["fecha", "name", "type", "category", "obj_name", "obj_id", "world", "pos_x", "pos_y", "pos_z", "distance"];
        const csv = [columns.join(",")]
            .concat(rows.map((r) => columns.map((c) => `"${String(r[c] ?? "").replace(/"/g, '""')}"`).join(",")))
            .join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "informe_investigacion.csv";
        a.click();
        URL.revokeObjectURL(url);
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        runReport();
    });

    exportBtn.addEventListener("click", () => downloadCSV(lastRows));
})();
