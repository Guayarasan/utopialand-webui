(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, typeBadge, buildQueryString, setupModal } = window.Utopialand;

    const form = document.getElementById("filters-form");
    const tbody = document.getElementById("records-tbody");
    const resultsCount = document.getElementById("results-count");
    const loadMoreBtn = document.getElementById("btn-load-more");
    const orderSelect = document.getElementById("order-select");
    const exportLink = document.getElementById("btn-export");
    const resetBtn = document.getElementById("btn-reset");

    const modal = setupModal("record-modal", "record-modal-close");
    const modalBody = document.getElementById("record-modal-body");

    let currentCursor = null;
    let currentRows = [];
    let loading = false;

    function localToUnix(value) {
        if (!value) return null;
        const t = new Date(value).getTime();
        return Number.isNaN(t) ? null : Math.floor(t / 1000);
    }

    function currentFilters() {
        const formData = new FormData(form);
        const typeSelect = document.getElementById("f-type");
        const selectedTypes = Array.from(typeSelect.selectedOptions)
            .map((o) => o.value)
            .filter(Boolean);

        return {
            player: formData.get("player") || "",
            type: selectedTypes,
            world: formData.get("world") || "",
            block: formData.get("block") || "",
            date_from: localToUnix(formData.get("date_from_local")),
            date_to: localToUnix(formData.get("date_to_local")),
        };
    }

    function rowHTML(r) {
        return `
            <tr>
                <td>${escapeHTML(r.fecha)}</td>
                <td>${escapeHTML(r.name || "-")}</td>
                <td>${typeBadge(r.type)}</td>
                <td>${escapeHTML(r.obj_name || "-")}</td>
                <td>${escapeHTML(r.world || "-")}</td>
                <td>${fmtCoords(r)}</td>
                <td>${escapeHTML(r.status ?? "-")}</td>
                <td><button class="row-link" data-id="${r.id_pk}">Ver</button></td>
            </tr>
        `;
    }

    function fmtCoords(r) {
        const fmt = (v) => (v === null || v === undefined ? "?" : Math.round(v));
        return `${fmt(r.pos_x)} / ${fmt(r.pos_y)} / ${fmt(r.pos_z)}`;
    }

    async function loadRecords({ reset }) {
        if (loading) return;
        loading = true;

        if (reset) {
            currentCursor = null;
            currentRows = [];
            tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Cargando registros…</td></tr>`;
        }

        const filters = currentFilters();
        const params = {
            ...filters,
            order: orderSelect.value,
        };
        if (currentCursor) {
            params.cursor_time = currentCursor.time;
            params.cursor_id = currentCursor.id_pk;
        }

        try {
            const data = await fetchJSON(`/api/registros?${buildQueryString(params)}`);
            currentRows = reset ? data.results : currentRows.concat(data.results);
            currentCursor = data.next_cursor;

            tbody.innerHTML = currentRows.length
                ? currentRows.map(rowHTML).join("")
                : `<tr><td colspan="8" class="table-empty">No se encontraron registros con esos filtros.</td></tr>`;

            loadMoreBtn.style.display = currentCursor ? "inline-flex" : "none";

            if (reset) {
                loadCount(filters);
            }

            exportLink.href = `/api/registros/export?${buildQueryString(filters)}`;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Error al cargar registros: ${escapeHTML(err.message)}</td></tr>`;
            toast(err.message, "error");
        } finally {
            loading = false;
        }
    }

    async function loadCount(filters) {
        try {
            const data = await fetchJSON(`/api/registros/count?${buildQueryString(filters)}`);
            resultsCount.textContent = `${formatNumber(data.total)} coincidencias`;
        } catch (e) {
            resultsCount.textContent = "";
        }
    }

    async function openDetail(id) {
        modal.open();
        modalBody.innerHTML = "<p>Cargando…</p>";
        try {
            const r = await fetchJSON(`/api/registros/${id}`);
            modalBody.innerHTML = `
                <dl class="detail-grid">
                    <dt>Fecha</dt><dd>${escapeHTML(r.fecha)}</dd>
                    <dt>Jugador</dt><dd>${escapeHTML(r.name || "-")}</dd>
                    <dt>UUID</dt><dd>${escapeHTML(r.uuid || "-")}</dd>
                    <dt>Acción</dt><dd>${typeBadge(r.type)}</dd>
                    <dt>Objeto</dt><dd>${escapeHTML(r.obj_name || "-")} ${r.obj_id !== null ? "(id " + escapeHTML(r.obj_id) + ")" : ""}</dd>
                    <dt>Mundo</dt><dd>${escapeHTML(r.world || "-")}</dd>
                    <dt>Coordenadas</dt><dd>${fmtCoords(r)}</dd>
                    <dt>Estado</dt><dd>${escapeHTML(r.status ?? "-")}</dd>
                    <dt>ID interno</dt><dd>${escapeHTML(r.id ?? "-")} (pk ${escapeHTML(r.id_pk)})</dd>
                </dl>
                <h4 style="margin-bottom:8px;">Datos crudos</h4>
                <div class="detail-json">${escapeHTML(
                    r.data_parsed ? JSON.stringify(r.data_parsed, null, 2) : (r.data || "(sin datos)")
                )}</div>
            `;
        } catch (err) {
            modalBody.innerHTML = `<p>Error: ${escapeHTML(err.message)}</p>`;
        }
    }

    tbody.addEventListener("click", (e) => {
        const btn = e.target.closest(".row-link");
        if (btn) openDetail(btn.dataset.id);
    });

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        loadRecords({ reset: true });
    });

    resetBtn.addEventListener("click", () => {
        form.reset();
        loadRecords({ reset: true });
    });

    loadMoreBtn.addEventListener("click", () => loadRecords({ reset: false }));
    orderSelect.addEventListener("change", () => loadRecords({ reset: true }));

    loadRecords({ reset: true });
})();
