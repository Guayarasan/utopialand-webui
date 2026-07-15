(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, buildQueryString, setupModal, debounce, typeBadge } = window.Utopialand;

    const searchInput = document.getElementById("p-search");
    const sortSelect = document.getElementById("p-sort");
    const orderSelect = document.getElementById("p-order");
    const tbody = document.getElementById("players-tbody");
    const countBadge = document.getElementById("players-count");
    const prevBtn = document.getElementById("p-prev");
    const nextBtn = document.getElementById("p-next");
    const pageLabel = document.getElementById("p-page-label");

    const modal = setupModal("player-modal", "player-modal-close");
    const modalTitle = document.getElementById("player-modal-title");
    const modalBody = document.getElementById("player-modal-body");

    const PAGE_SIZE = 25;
    let offset = 0;
    let total = 0;
    let charts = [];

    const GRID_COLOR = "rgba(147,160,189,.12)";
    const TEXT_MUTED = "#93a0bd";
    if (window.Chart) {
        Chart.defaults.color = TEXT_MUTED;
        Chart.defaults.font.family = "Segoe UI, Roboto, Inter, Arial, sans-serif";
    }

    function rowHTML(p) {
        return `
            <tr>
                <td><strong>${escapeHTML(p.name)}</strong></td>
                <td>${formatNumber(p.total)}</td>
                <td>${formatNumber(p.breaks)}</td>
                <td>${formatNumber(p.places)}</td>
                <td>${formatNumber(p.combat)}</td>
                <td>${escapeHTML(p.last_seen_fmt)}</td>
                <td><button class="row-link" data-name="${escapeHTML(p.name)}">Ver</button></td>
            </tr>
        `;
    }

    async function loadPlayers(reset) {
        if (reset) offset = 0;
        tbody.innerHTML = `<tr><td colspan="7" class="table-empty">Cargando jugadores…</td></tr>`;

        const params = {
            search: searchInput.value,
            sort: sortSelect.value,
            order: orderSelect.value,
            limit: PAGE_SIZE,
            offset,
        };

        try {
            const data = await fetchJSON(`/api/jugadores?${buildQueryString(params)}`);
            total = data.total;
            tbody.innerHTML = data.results.length
                ? data.results.map(rowHTML).join("")
                : `<tr><td colspan="7" class="table-empty">Sin resultados.</td></tr>`;

            countBadge.textContent = `${formatNumber(total)} jugadores`;
            const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
            const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
            pageLabel.textContent = `Página ${currentPage} de ${totalPages}`;
            prevBtn.disabled = offset === 0;
            nextBtn.disabled = offset + PAGE_SIZE >= total;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">Error: ${escapeHTML(err.message)}</td></tr>`;
            toast(err.message, "error");
        }
    }

    // -------- Ficha del jugador --------

    function blockLabel(row) {
        const raw = (row.obj_name && String(row.obj_name).trim()) || (row.obj_id !== null && row.obj_id !== undefined ? String(row.obj_id) : "");
        if (!raw) return "Desconocido";
        const shortName = raw.includes(":") ? raw.split(":").slice(1).join(":") : raw;
        return shortName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    }

    function rankListHTML(rows, valueKey, labelFn) {
        if (!rows.length) return `<p class="table-empty">Sin datos suficientes.</p>`;
        const max = rows[0][valueKey] || 1;
        return rows.map((r) => `
            <div class="bar-row">
                <span class="bar-label">${escapeHTML(labelFn(r))}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round((r[valueKey] / max) * 100)}%"></div></div>
                <span class="bar-value">${formatNumber(r[valueKey])}</span>
            </div>
        `).join("");
    }

    function destroyCharts() {
        charts.forEach((c) => c.destroy());
        charts = [];
    }

    function renderCharts(daily, hourly) {
        if (!window.Chart) return;
        const dailyCanvas = document.getElementById("player-chart-daily");
        const hourlyCanvas = document.getElementById("player-chart-hourly");
        if (dailyCanvas) {
            charts.push(new Chart(dailyCanvas, {
                type: "line",
                data: {
                    labels: daily.map((r) => r.day),
                    datasets: [{
                        label: "Eventos",
                        data: daily.map((r) => r.total),
                        borderColor: "#5b8cff",
                        backgroundColor: "rgba(91,140,255,.15)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                    }],
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { maxTicksLimit: 6 } },
                        y: { grid: { color: GRID_COLOR }, beginAtZero: true },
                    },
                },
            }));
        }
        if (hourlyCanvas) {
            charts.push(new Chart(hourlyCanvas, {
                type: "bar",
                data: {
                    labels: hourly.map((r) => `${String(r.hour).padStart(2, "0")}h`),
                    datasets: [{
                        label: "Eventos",
                        data: hourly.map((r) => r.total),
                        backgroundColor: "#a78bfa",
                        borderRadius: 4,
                    }],
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
                        y: { grid: { color: GRID_COLOR }, beginAtZero: true },
                    },
                },
            }));
        }
    }

    function timelineHTML(rows) {
        if (!rows.length) return `<p class="table-empty">Sin actividad registrada.</p>`;
        return rows.map((r) => {
            const coords = (r.pos_x !== undefined && r.pos_x !== null)
                ? `${Math.round(r.pos_x)}/${Math.round(r.pos_y)}/${Math.round(r.pos_z)}`
                : null;
            const bits = [r.world, coords].filter(Boolean).join(" · ");
            const label = blockLabel(r);
            return `
                <div class="feed-item">
                    <div class="feed-main">
                        <span class="feed-title">${typeBadge(r.type)} ${label !== "Desconocido" ? `<span class="feed-object">${escapeHTML(label)}</span>` : ""}</span>
                        <span class="feed-meta">${escapeHTML(bits || "-")}</span>
                    </div>
                    <span class="feed-time">${escapeHTML(r.fecha)}</span>
                </div>
            `;
        }).join("");
    }

    function coordsTableHTML(rows) {
        if (!rows.length) return `<p class="table-empty">Sin coordenadas registradas.</p>`;
        return `
            <div class="table-wrapper">
                <table class="data-table">
                    <thead><tr><th>Mundo</th><th>Zona (centro)</th><th>Altura media</th><th>Eventos</th><th></th></tr></thead>
                    <tbody>
                        ${rows.map((r) => `
                            <tr>
                                <td>${escapeHTML(r.world || "-")}</td>
                                <td>${Math.round(r.zone_x)} / ${Math.round(r.zone_z)}</td>
                                <td>${Math.round(r.avg_y)}</td>
                                <td>${formatNumber(r.total)}</td>
                                <td><button class="row-link coord-copy" data-coords="${Math.round(r.zone_x)}, ${Math.round(r.avg_y)}, ${Math.round(r.zone_z)}">Copiar</button></td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function openPlayer(name) {
        modal.open();
        modalTitle.textContent = name;
        destroyCharts();
        modalBody.innerHTML = `<p class="muted-text">Cargando ficha…</p>`;

        try {
            const data = await fetchJSON(`/api/jugadores/${encodeURIComponent(name)}/ficha`);
            const s = data.summary;
            const recordsLink = `/registros?player=${encodeURIComponent(name)}`;

            modalBody.innerHTML = `
                <section class="stat-grid" style="margin-bottom:18px;">
                    <div class="stat-card"><span class="stat-label">Total acciones</span><span class="stat-value">${formatNumber(s.total)}</span></div>
                    <div class="stat-card"><span class="stat-label">Breaks</span><span class="stat-value">${formatNumber(s.breaks)}</span></div>
                    <div class="stat-card"><span class="stat-label">Places</span><span class="stat-value">${formatNumber(s.places)}</span></div>
                    <div class="stat-card"><span class="stat-label">Combate</span><span class="stat-value">${formatNumber(s.combat)}</span></div>
                    <div class="stat-card"><span class="stat-label">Mundos visitados</span><span class="stat-value">${formatNumber(s.worlds_visited)}</span></div>
                    <div class="stat-card"><span class="stat-label">Días activo</span><span class="stat-value">${formatNumber(s.active_days)}</span></div>
                </section>
                <p class="muted-text" style="margin-bottom:18px;">
                    Primera actividad: ${escapeHTML(s.first_seen_fmt)} · Última actividad: ${escapeHTML(s.last_seen_fmt)}
                </p>

                <div class="grid-2" style="margin-bottom:18px;">
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Actividad diaria (30 días)</h3>
                        <canvas id="player-chart-daily" height="160"></canvas>
                    </div>
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Actividad por hora</h3>
                        <canvas id="player-chart-hourly" height="160"></canvas>
                    </div>
                </div>

                <div class="grid-2" style="margin-bottom:18px;">
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Bloques más rotos</h3>
                        ${rankListHTML(data.top_broken, "total", blockLabel)}
                    </div>
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Bloques más colocados</h3>
                        ${rankListHTML(data.top_placed, "total", blockLabel)}
                    </div>
                </div>

                <div class="grid-2" style="margin-bottom:18px;">
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Entidades atacadas</h3>
                        ${rankListHTML(data.entities_attacked, "total", blockLabel)}
                    </div>
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Mundos visitados</h3>
                        ${rankListHTML(data.worlds, "total", (r) => r.world || "-")}
                    </div>
                </div>

                <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Coordenadas frecuentes</h3>
                <div style="margin-bottom:18px;">${coordsTableHTML(data.frequent_coords)}</div>

                <div class="card-header">
                    <h3 style="font-size:13.5px; color:var(--text-muted);">Línea de tiempo reciente</h3>
                    <a class="btn btn-outline btn-sm" href="${recordsLink}">Ver historial completo</a>
                </div>
                <div class="activity-feed">${timelineHTML(data.timeline)}</div>
            `;

            renderCharts(data.daily, data.hourly);

            modalBody.querySelectorAll(".coord-copy").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    try {
                        await navigator.clipboard.writeText(btn.dataset.coords);
                        toast("Coordenadas copiadas", "success");
                    } catch (e) {
                        toast("No se pudo copiar", "error");
                    }
                });
            });
        } catch (err) {
            modalBody.innerHTML = `<p class="muted-text">Error: ${escapeHTML(err.message)}</p>`;
        }
    }

    tbody.addEventListener("click", (e) => {
        const btn = e.target.closest(".row-link");
        if (btn) openPlayer(btn.dataset.name);
    });

    searchInput.addEventListener("input", debounce(() => loadPlayers(true), 350));
    sortSelect.addEventListener("change", () => loadPlayers(true));
    orderSelect.addEventListener("change", () => loadPlayers(true));
    prevBtn.addEventListener("click", () => { offset = Math.max(0, offset - PAGE_SIZE); loadPlayers(false); });
    nextBtn.addEventListener("click", () => { offset += PAGE_SIZE; loadPlayers(false); });

    loadPlayers(true);
})();
