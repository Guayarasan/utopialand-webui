(function () {
    "use strict";
    const { fetchJSON, formatNumber, escapeHTML, toast } = window.Utopialand;

    const COLORS = ["#5b8cff", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#38bdf8", "#fb923c", "#f472b6", "#4ade80", "#facc15"];
    const TEXT_MUTED = "#93a0bd";
    const GRID_COLOR = "rgba(147,160,189,.12)";
    const WEEKDAY_LABELS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

    Chart.defaults.color = TEXT_MUTED;
    Chart.defaults.font.family = "Segoe UI, Roboto, Inter, Arial, sans-serif";

    async function loadOverview() {
        try {
            const data = await fetchJSON("/api/estadisticas/overview");
            document.getElementById("stat-total").textContent = formatNumber(data.total);
            document.getElementById("stat-today").textContent = formatNumber(data.today);
            document.getElementById("stat-week").textContent = formatNumber(data.last_7_days);
            document.getElementById("stat-month").textContent = formatNumber(data.last_30_days);
            document.getElementById("stat-avg").textContent = formatNumber(Math.round(data.avg_daily_30d));
            document.getElementById("stat-players").textContent = formatNumber(data.distinct_players);
        } catch (err) {
            toast(err.message, "error");
        }
    }

    async function loadTimeseries() {
        try {
            const rows = await fetchJSON("/api/estadisticas/actividad");
            new Chart(document.getElementById("chart-timeseries"), {
                type: "line",
                data: {
                    labels: rows.map((r) => r.day),
                    datasets: [{
                        label: "Eventos",
                        data: rows.map((r) => r.total),
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
                        x: { grid: { color: GRID_COLOR } },
                        y: { grid: { color: GRID_COLOR }, beginAtZero: true },
                    },
                },
            });
        } catch (err) {
            toast(err.message, "error");
        }
    }

    async function loadHourly() {
        try {
            const rows = await fetchJSON("/api/estadisticas/actividad-horaria");
            new Chart(document.getElementById("chart-hourly"), {
                type: "bar",
                data: {
                    labels: rows.map((r) => `${String(r.hour).padStart(2, "0")}h`),
                    datasets: [{
                        label: "Eventos",
                        data: rows.map((r) => r.total),
                        backgroundColor: "#a78bfa",
                        borderRadius: 4,
                    }],
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { grid: { color: GRID_COLOR }, beginAtZero: true },
                    },
                },
            });
        } catch (err) {
            toast(err.message, "error");
        }
    }

    async function loadTypes() {
        try {
            const rows = await fetchJSON("/api/estadisticas/tipos");
            new Chart(document.getElementById("chart-types"), {
                type: "doughnut",
                data: {
                    labels: rows.map((r) => r.type),
                    datasets: [{
                        data: rows.map((r) => r.total),
                        backgroundColor: COLORS,
                        borderColor: "#161d2e",
                        borderWidth: 2,
                    }],
                },
                options: {
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, padding: 12 } } },
                },
            });
        } catch (err) {
            toast(err.message, "error");
        }
    }

    async function loadTopPlayers() {
        try {
            const rows = await fetchJSON("/api/estadisticas/top-jugadores");
            new Chart(document.getElementById("chart-players"), {
                type: "bar",
                data: {
                    labels: rows.map((r) => r.name),
                    datasets: [{
                        label: "Acciones",
                        data: rows.map((r) => r.total),
                        backgroundColor: "#5b8cff",
                        borderRadius: 4,
                    }],
                },
                options: {
                    indexAxis: "y",
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: GRID_COLOR }, beginAtZero: true },
                        y: { grid: { display: false } },
                    },
                },
            });
        } catch (err) {
            toast(err.message, "error");
        }
    }

    async function loadWorlds() {
        try {
            const rows = await fetchJSON("/api/estadisticas/mundos");
            new Chart(document.getElementById("chart-worlds"), {
                type: "bar",
                data: {
                    labels: rows.map((r) => r.world),
                    datasets: [{
                        label: "Eventos",
                        data: rows.map((r) => r.total),
                        backgroundColor: "#34d399",
                        borderRadius: 4,
                    }],
                },
                options: {
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false } },
                        y: { grid: { color: GRID_COLOR }, beginAtZero: true },
                    },
                },
            });
        } catch (err) {
            toast(err.message, "error");
        }
    }

    function rankListHTML(rows, valueKey, labelKey) {
        if (!rows.length) return `<p class="table-empty">Sin datos suficientes.</p>`;
        const max = rows[0][valueKey] || 1;
        return rows.map((r) => `
            <div class="bar-row">
                <span class="bar-label">${escapeHTML(r[labelKey] || "-")}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round((r[valueKey] / max) * 100)}%"></div></div>
                <span class="bar-value">${formatNumber(r[valueKey])}</span>
            </div>
        `).join("");
    }

    async function loadTopBlocks() {
        const container = document.getElementById("top-blocks-list");
        try {
            const rows = await fetchJSON("/api/estadisticas/top-bloques");
            container.innerHTML = rankListHTML(rows, "total", "obj_name");
        } catch (err) {
            container.innerHTML = `<p class="table-empty">Error al cargar.</p>`;
        }
    }

    async function loadTopEntities() {
        const container = document.getElementById("top-entities-list");
        try {
            const rows = await fetchJSON("/api/estadisticas/top-entidades");
            container.innerHTML = rankListHTML(rows, "total", "obj_name");
        } catch (err) {
            container.innerHTML = `<p class="table-empty">Error al cargar.</p>`;
        }
    }

    async function loadHeatmap() {
        const container = document.getElementById("heatmap-container");
        try {
            const rows = await fetchJSON("/api/estadisticas/heatmap");
            const max = Math.max(1, ...rows.map((r) => r.total));

            let html = '<div class="heatmap-grid">';
            html += '<div class="heatmap-corner"></div>';
            for (let h = 0; h < 24; h++) {
                html += `<div class="heatmap-hour-label">${h % 3 === 0 ? h : ""}</div>`;
            }
            for (let wd = 0; wd < 7; wd++) {
                html += `<div class="heatmap-day-label">${WEEKDAY_LABELS[wd]}</div>`;
                for (let h = 0; h < 24; h++) {
                    const cell = rows.find((r) => r.weekday === wd && r.hour === h);
                    const total = cell ? cell.total : 0;
                    const intensity = total / max;
                    html += `<div class="heatmap-cell" style="background:rgba(91,140,255,${0.08 + intensity * 0.85})" title="${WEEKDAY_LABELS[wd]} ${h}h: ${total} eventos"></div>`;
                }
            }
            html += "</div>";
            container.innerHTML = html;
        } catch (err) {
            container.innerHTML = `<p class="table-empty">Error al cargar el mapa de calor.</p>`;
        }
    }

    loadOverview();
    loadTimeseries();
    loadHourly();
    loadTypes();
    loadTopPlayers();
    loadWorlds();
    loadTopBlocks();
    loadTopEntities();
    loadHeatmap();
})();
