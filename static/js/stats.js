(function () {
    "use strict";
    const { fetchJSON, formatNumber, toast } = window.Utopialand;

    const COLORS = ["#5b8cff", "#34d399", "#fbbf24", "#f87171", "#a78bfa", "#38bdf8", "#fb923c", "#f472b6", "#4ade80", "#facc15"];
    const TEXT_MUTED = "#93a0bd";
    const GRID_COLOR = "rgba(147,160,189,.12)";

    Chart.defaults.color = TEXT_MUTED;
    Chart.defaults.font.family = "Segoe UI, Roboto, Inter, Arial, sans-serif";

    async function loadOverview() {
        try {
            const data = await fetchJSON("/api/estadisticas/overview");
            document.getElementById("stat-total").textContent = formatNumber(data.total);
            document.getElementById("stat-today").textContent = formatNumber(data.today);
            document.getElementById("stat-week").textContent = formatNumber(data.last_7_days);
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

    loadOverview();
    loadTimeseries();
    loadTypes();
    loadTopPlayers();
    loadWorlds();
})();
