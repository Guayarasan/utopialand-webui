(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, typeBadge, buildQueryString, setupModal } = window.Utopialand;

    const form = document.getElementById("filters-form");
    const tbody = document.getElementById("records-tbody");
    const resultsCount = document.getElementById("results-count");
    const resetBtn = document.getElementById("btn-reset");
    const pageSizeSelect = document.getElementById("page-size-select");
    const paginationEl = document.getElementById("pagination");
    const table = document.getElementById("records-table");

    const modal = setupModal("record-modal", "record-modal-close");
    const modalBody = document.getElementById("record-modal-body");

    const COLUMN_STORAGE_KEY = "utopialand_records_columns";
    const ALL_COLUMNS = [
        { key: "fecha", label: "Fecha" },
        { key: "name", label: "Jugador" },
        { key: "type", label: "Acción" },
        { key: "obj_name", label: "Objeto" },
        { key: "world", label: "Mundo" },
        { key: "coords", label: "Coordenadas" },
        { key: "status", label: "Estado" },
    ];

    let state = {
        page: 1,
        sort: "time",
        order: "DESC",
        rows: [],
    };

    // ---------------- Filtros ----------------

    function localToUnix(value) {
        if (!value) return null;
        const t = new Date(value).getTime();
        return Number.isNaN(t) ? null : Math.floor(t / 1000);
    }

    function currentFilters() {
        const formData = new FormData(form);
        const typeSelect = document.getElementById("f-type");
        const selectedTypes = Array.from(typeSelect.selectedOptions).map((o) => o.value).filter(Boolean);

        return {
            player: formData.get("player") || "",
            type: selectedTypes,
            world: formData.get("world") || "",
            block: formData.get("block") || "",
            date_from: localToUnix(formData.get("date_from_local")),
            date_to: localToUnix(formData.get("date_to_local")),
        };
    }

    function applyFilters(filters) {
        document.getElementById("f-player").value = filters.player || "";
        document.getElementById("f-world").value = filters.world || "";
        document.getElementById("f-block").value = filters.block || "";

        const typeSelect = document.getElementById("f-type");
        const types = filters.type || [];
        Array.from(typeSelect.options).forEach((opt) => {
            opt.selected = types.includes(opt.value);
        });

        document.getElementById("f-date-from").value = filters.date_from ? unixToLocalInput(filters.date_from) : "";
        document.getElementById("f-date-to").value = filters.date_to ? unixToLocalInput(filters.date_to) : "";
    }

    function unixToLocalInput(unixSeconds) {
        const d = new Date(unixSeconds * 1000);
        const pad = (n) => String(n).padStart(2, "0");
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }

    document.querySelectorAll("[data-range]").forEach((btn) => {
        btn.addEventListener("click", () => {
            const hours = parseInt(btn.dataset.range, 10);
            const now = new Date();
            const from = new Date(now.getTime() - hours * 3600 * 1000);
            document.getElementById("f-date-from").value = unixToLocalInput(Math.floor(from.getTime() / 1000));
            document.getElementById("f-date-to").value = "";
            state.page = 1;
            loadRecords();
        });
    });

    // ---------------- Carga y render ----------------

    function fmtCoords(r) {
        const fmt = (v) => (v === null || v === undefined ? "?" : Math.round(v));
        return `${fmt(r.pos_x)} / ${fmt(r.pos_y)} / ${fmt(r.pos_z)}`;
    }

    function rowHTML(r) {
        return `
            <tr>
                <td data-col="fecha">${escapeHTML(r.fecha)}</td>
                <td data-col="name">${escapeHTML(r.name || "-")}</td>
                <td data-col="type">${typeBadge(r.type)}</td>
                <td data-col="obj_name">${escapeHTML(r.obj_name || "-")}</td>
                <td data-col="world">${escapeHTML(r.world || "-")}</td>
                <td data-col="coords">${fmtCoords(r)}</td>
                <td data-col="status">${escapeHTML(r.status ?? "-")}</td>
                <td data-col="actions"><button class="row-link" data-id="${r.id_pk}">Ver</button></td>
            </tr>
        `;
    }

    async function loadRecords() {
        tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Cargando registros…</td></tr>`;

        const filters = currentFilters();
        const params = {
            ...filters,
            sort: state.sort,
            order: state.order,
            page: state.page,
            limit: pageSizeSelect.value,
        };

        try {
            const data = await fetchJSON(`/api/registros?${buildQueryString(params)}`);
            state.rows = data.results;

            tbody.innerHTML = data.results.length
                ? data.results.map(rowHTML).join("")
                : `<tr><td colspan="8" class="table-empty">No se encontraron registros con esos filtros.</td></tr>`;

            resultsCount.textContent = `${formatNumber(data.total)} coincidencias`;
            renderPagination(data.page, data.total_pages);
            applyColumnVisibility();
            updateSortIndicators();
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Error al cargar registros: ${escapeHTML(err.message)}</td></tr>`;
            toast(err.message, "error");
        }
    }

    function renderPagination(page, totalPages) {
        if (totalPages <= 1) {
            paginationEl.innerHTML = "";
            return;
        }
        const windowSize = 5;
        let start = Math.max(1, page - Math.floor(windowSize / 2));
        let end = Math.min(totalPages, start + windowSize - 1);
        start = Math.max(1, end - windowSize + 1);

        let html = `<button data-page="1" ${page === 1 ? "disabled" : ""}>«</button>`;
        html += `<button data-page="${page - 1}" ${page === 1 ? "disabled" : ""}>‹</button>`;
        for (let p = start; p <= end; p++) {
            html += `<button data-page="${p}" class="${p === page ? "active" : ""}">${p}</button>`;
        }
        html += `<button data-page="${page + 1}" ${page === totalPages ? "disabled" : ""}>›</button>`;
        html += `<button data-page="${totalPages}" ${page === totalPages ? "disabled" : ""}>»</button>`;
        paginationEl.innerHTML = html;
    }

    paginationEl.addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-page]");
        if (!btn || btn.disabled) return;
        state.page = parseInt(btn.dataset.page, 10);
        loadRecords();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // ---------------- Ordenar por columna ----------------

    table.querySelectorAll("th[data-sort]").forEach((th) => {
        th.addEventListener("click", () => {
            const col = th.dataset.sort;
            if (state.sort === col) {
                state.order = state.order === "ASC" ? "DESC" : "ASC";
            } else {
                state.sort = col;
                state.order = "DESC";
            }
            state.page = 1;
            loadRecords();
        });
    });

    function updateSortIndicators() {
        table.querySelectorAll("th[data-sort]").forEach((th) => {
            const arrow = th.querySelector(".sort-arrow");
            arrow.className = "sort-arrow";
            if (th.dataset.sort === state.sort) {
                arrow.classList.add(state.order === "ASC" ? "asc" : "desc");
            }
        });
    }

    // ---------------- Columnas visibles ----------------

    const columnsMenu = document.getElementById("columns-menu");
    columnsMenu.innerHTML = ALL_COLUMNS.map((c) => `
        <label><input type="checkbox" data-col-toggle="${c.key}" checked> ${escapeHTML(c.label)}</label>
    `).join("");

    function getHiddenColumns() {
        try {
            return JSON.parse(localStorage.getItem(COLUMN_STORAGE_KEY) || "[]");
        } catch (e) {
            return [];
        }
    }

    function setHiddenColumns(hidden) {
        localStorage.setItem(COLUMN_STORAGE_KEY, JSON.stringify(hidden));
    }

    function applyColumnVisibility() {
        const hidden = getHiddenColumns();
        document.querySelectorAll("[data-col]").forEach((el) => {
            el.classList.toggle("col-hidden", hidden.includes(el.dataset.col));
        });
        columnsMenu.querySelectorAll("[data-col-toggle]").forEach((cb) => {
            cb.checked = !hidden.includes(cb.dataset.colToggle);
        });
    }

    columnsMenu.addEventListener("change", (e) => {
        const cb = e.target.closest("[data-col-toggle]");
        if (!cb) return;
        const hidden = new Set(getHiddenColumns());
        if (cb.checked) hidden.delete(cb.dataset.colToggle); else hidden.add(cb.dataset.colToggle);
        setHiddenColumns(Array.from(hidden));
        applyColumnVisibility();
    });

    setupDropdown("btn-columns-toggle", "columns-menu");

    // ---------------- Dropdowns genéricos ----------------

    function setupDropdown(buttonId, menuId) {
        const button = document.getElementById(buttonId);
        const menu = document.getElementById(menuId);
        button.addEventListener("click", (e) => {
            e.stopPropagation();
            const isHidden = menu.hidden;
            document.querySelectorAll(".export-menu, .column-toggle-menu").forEach((m) => (m.hidden = true));
            menu.hidden = !isHidden;
        });
        document.addEventListener("click", (e) => {
            if (!menu.contains(e.target) && e.target !== button) menu.hidden = true;
        });
    }

    // ---------------- Exportar ----------------

    setupDropdown("btn-export-toggle", "export-menu");

    document.getElementById("export-menu").addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-export]");
        if (!btn) return;
        const format = btn.dataset.export;
        const filters = currentFilters();

        if (format === "clipboard") {
            if (!state.rows.length) {
                toast("No hay filas cargadas para copiar.", "error");
                return;
            }
            const cols = ALL_COLUMNS.filter((c) => c.key !== "coords").map((c) => c.key === "fecha" ? "fecha" : c.key);
            const header = ["fecha", "name", "type", "obj_name", "world", "status"].join("\t");
            const body = state.rows.map((r) => [r.fecha, r.name, r.type, r.obj_name, r.world, r.status].join("\t")).join("\n");
            try {
                await navigator.clipboard.writeText(header + "\n" + body);
                toast("Página actual copiada al portapapeles", "success");
            } catch (err) {
                toast("No se pudo copiar al portapapeles", "error");
            }
            return;
        }

        window.open(`/api/registros/exportar/${format}?${buildQueryString(filters)}`, "_blank");
    });

    // ---------------- Filtros favoritos ----------------

    setupDropdown("btn-favorites-toggle", "favorites-menu");

    async function loadFavoriteFilters() {
        const menu = document.getElementById("favorites-menu");
        try {
            const data = await fetchJSON("/api/registros/filtros-favoritos");
            menu.innerHTML = data.results.length
                ? data.results.map((f) => `
                    <button data-apply-filter='${escapeHTML(JSON.stringify(f.filters))}'>
                        ${escapeHTML(f.name)}
                        <span data-delete-filter="${f.id}" style="float:right;opacity:.6;">✕</span>
                    </button>
                `).join("")
                : `<button disabled>Sin filtros guardados</button>`;
        } catch (err) {
            menu.innerHTML = `<button disabled>Error al cargar</button>`;
        }
    }

    document.getElementById("favorites-menu").addEventListener("click", async (e) => {
        const delTarget = e.target.closest("[data-delete-filter]");
        if (delTarget) {
            e.stopPropagation();
            try {
                await fetchJSON(`/api/registros/filtros-favoritos/${delTarget.dataset.deleteFilter}`, { method: "DELETE" });
                loadFavoriteFilters();
            } catch (err) {
                toast(err.message, "error");
            }
            return;
        }
        const btn = e.target.closest("[data-apply-filter]");
        if (btn) {
            applyFilters(JSON.parse(btn.dataset.applyFilter));
            state.page = 1;
            loadRecords();
        }
    });

    document.getElementById("btn-save-filter").addEventListener("click", async () => {
        const name = prompt("Nombre para este filtro guardado:");
        if (!name) return;
        try {
            await fetchJSON("/api/registros/filtros-favoritos", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, filters: currentFilters() }),
            });
            toast("Filtro guardado", "success");
            loadFavoriteFilters();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    // ---------------- Detalle de registro ----------------

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

    // ---------------- Eventos generales ----------------

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        state.page = 1;
        loadRecords();
    });

    resetBtn.addEventListener("click", () => {
        form.reset();
        state.page = 1;
        loadRecords();
    });

    pageSizeSelect.addEventListener("change", () => {
        state.page = 1;
        loadRecords();
    });

    function applyFiltersFromURL() {
        const params = new URLSearchParams(window.location.search);
        if (!params.toString()) return;
        const incoming = {
            player: params.get("player") || "",
            world: params.get("world") || "",
            block: params.get("block") || "",
            type: params.getAll("type"),
        };
        if (incoming.player || incoming.world || incoming.block || incoming.type.length) {
            applyFilters(incoming);
        }
    }

    applyColumnVisibility();
    loadFavoriteFilters();
    applyFiltersFromURL();
    loadRecords();
})();
