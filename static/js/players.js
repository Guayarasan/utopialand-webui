(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, buildQueryString, setupModal, debounce } = window.Utopialand;

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

    async function openPlayer(name) {
        modal.open();
        modalTitle.textContent = name;
        modalBody.innerHTML = "<p>Cargando…</p>";
        try {
            const [detail, activity] = await Promise.all([
                fetchJSON(`/api/jugadores/${encodeURIComponent(name)}`),
                fetchJSON(`/api/jugadores/${encodeURIComponent(name)}/actividad?limit=15`),
            ]);
            const s = detail.summary;
            const breakdownHTML = detail.breakdown
                .map((b) => `<span class="type-badge">${escapeHTML(b.type)}: ${formatNumber(b.total)}</span>`)
                .join(" ");

            const activityHTML = activity.results.length
                ? activity.results.map((r) => `
                    <tr>
                        <td>${escapeHTML(r.fecha)}</td>
                        <td>${escapeHTML(r.type)}</td>
                        <td>${escapeHTML(r.obj_name || "-")}</td>
                        <td>${escapeHTML(r.world || "-")}</td>
                    </tr>
                `).join("")
                : `<tr><td colspan="4" class="table-empty">Sin actividad reciente.</td></tr>`;

            modalBody.innerHTML = `
                <dl class="detail-grid">
                    <dt>Total acciones</dt><dd>${formatNumber(s.total)}</dd>
                    <dt>Breaks</dt><dd>${formatNumber(s.breaks)}</dd>
                    <dt>Places</dt><dd>${formatNumber(s.places)}</dd>
                    <dt>Mundos visitados</dt><dd>${formatNumber(s.worlds_visited)}</dd>
                    <dt>Primera actividad</dt><dd>${escapeHTML(s.first_seen_fmt)}</dd>
                    <dt>Última actividad</dt><dd>${escapeHTML(s.last_seen_fmt)}</dd>
                </dl>
                <h4 style="margin-bottom:8px;">Desglose por tipo</h4>
                <p style="margin-bottom:16px; line-height:2;">${breakdownHTML}</p>
                <h4 style="margin-bottom:8px;">Actividad reciente</h4>
                <div class="table-wrapper">
                    <table class="data-table">
                        <thead><tr><th>Fecha</th><th>Acción</th><th>Objeto</th><th>Mundo</th></tr></thead>
                        <tbody>${activityHTML}</tbody>
                    </table>
                </div>
            `;
        } catch (err) {
            modalBody.innerHTML = `<p>Error: ${escapeHTML(err.message)}</p>`;
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
