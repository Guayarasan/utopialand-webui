(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, buildQueryString, debounce, setupModal } = window.Utopialand;

    const searchInput = document.getElementById("b-search");
    const worldSelect = document.getElementById("b-world");
    const sortSelect = document.getElementById("b-sort");
    const orderSelect = document.getElementById("b-order");
    const tbody = document.getElementById("blocks-tbody");
    const countBadge = document.getElementById("blocks-count");
    const prevBtn = document.getElementById("bk-prev");
    const nextBtn = document.getElementById("bk-next");
    const pageLabel = document.getElementById("bk-page-label");

    const modal = setupModal("block-modal", "block-modal-close");
    const modalTitle = document.getElementById("block-modal-title");
    const modalBody = document.getElementById("block-modal-body");

    const PAGE_SIZE = 25;
    let offset = 0;
    let total = 0;

    // -------- Identidad del bloque (icono, nombre, namespace) --------

    function resolveIdentity(objName, objId) {
        // COALESCE del lado del cliente, igual que hace la consulta SQL:
        // si obj_name viene vacío usamos obj_id como identificador real
        // en vez de mostrar "Desconocido" sin más.
        const raw = (objName && String(objName).trim()) || (objId !== null && objId !== undefined && String(objId).trim()) || "";
        if (!raw) {
            return { raw: "", namespace: null, shortName: null, label: "Desconocido", iconSlug: null, known: false };
        }
        const parts = raw.split(":");
        const namespace = parts.length > 1 ? parts[0] : null;
        const shortName = parts.length > 1 ? parts.slice(1).join(":") : raw;
        const iconSlug = shortName.split("[")[0]; // por si viene con estado de bloque
        const label = shortName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        return { raw, namespace, shortName, label, iconSlug, known: true };
    }

    function blockIconHTML(identity) {
        if (!identity.known) {
            return `<span class="block-icon block-icon-fallback" aria-hidden="true"></span>`;
        }
        const iconUrl = `https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.20/assets/minecraft/textures/block/${identity.iconSlug}.png`;
        return `
            <span class="block-icon" aria-hidden="true">
                <img src="${iconUrl}" alt="" loading="lazy"
                     onerror="this.parentElement.classList.add('block-icon-fallback'); this.remove();">
            </span>
        `;
    }

    function blockIdentityHTML(objName, objId) {
        const identity = resolveIdentity(objName, objId);
        return `
            <div class="block-identity">
                ${blockIconHTML(identity)}
                <span class="block-identity-text">
                    <span class="block-name">${escapeHTML(identity.label)}</span>
                    ${identity.namespace
                        ? `<span class="block-namespace">${escapeHTML(identity.namespace)}:${escapeHTML(identity.shortName)}</span>`
                        : (identity.known ? `<span class="block-namespace">id ${escapeHTML(identity.raw)}</span>` : `<span class="block-namespace">sin identificador — clic para inspeccionar</span>`)}
                </span>
            </div>
        `;
    }

    function rowHTML(b) {
        return `
            <tr class="row-clickable" data-obj-name="${escapeHTML(b.obj_name || "")}" data-obj-id="${b.obj_id !== null && b.obj_id !== undefined ? escapeHTML(b.obj_id) : ""}">
                <td>${blockIdentityHTML(b.obj_name, b.obj_id)}</td>
                <td>${formatNumber(b.total)}</td>
                <td>${formatNumber(b.breaks)}</td>
                <td>${formatNumber(b.places)}</td>
                <td>${formatNumber(b.explosions)}</td>
                <td>${formatNumber(b.distinct_players)}</td>
                <td>${escapeHTML(b.last_event_fmt)}</td>
            </tr>
        `;
    }

    async function loadBlocks(reset) {
        if (reset) offset = 0;
        tbody.innerHTML = `<tr><td colspan="7" class="table-empty">Cargando bloques…</td></tr>`;

        const params = {
            block: searchInput.value,
            world: worldSelect.value,
            sort: sortSelect.value,
            order: orderSelect.value,
            limit: PAGE_SIZE,
            offset,
        };

        try {
            const data = await fetchJSON(`/api/bloques?${buildQueryString(params)}`);
            total = data.total;
            tbody.innerHTML = data.results.length
                ? data.results.map(rowHTML).join("")
                : `<tr><td colspan="7" class="table-empty">Sin resultados.</td></tr>`;

            countBadge.textContent = `${formatNumber(total)} bloques`;
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

    // -------- Modal de detalle --------

    function worldsListHTML(worlds) {
        if (!worlds.length) return `<p class="muted-text">Sin datos de mundo.</p>`;
        const max = worlds[0].total || 1;
        return `<div class="bar-list">` + worlds.map((w) => `
            <div class="bar-row">
                <span class="bar-label">${escapeHTML(w.world)}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round((w.total / max) * 100)}%"></div></div>
                <span class="bar-value">${formatNumber(w.total)}</span>
            </div>
        `).join("") + `</div>`;
    }

    function playersListHTML(players) {
        if (!players.length) return `<p class="muted-text">Sin jugadores registrados.</p>`;
        return `<div class="rank-list">` + players.map((p) => `
            <a class="quick-link" href="/registros?player=${encodeURIComponent(p.name)}">
                👤 <span>${escapeHTML(p.name)} — ${formatNumber(p.total)} eventos</span>
            </a>
        `).join("") + `</div>`;
    }

    async function openBlockModal(objName, objId) {
        const identity = resolveIdentity(objName, objId);
        modalTitle.textContent = identity.known ? identity.label : "Bloque sin identificar";
        modalBody.innerHTML = `<p class="muted-text">Cargando resumen…</p>`;
        modal.open();

        const query = buildQueryString({ obj_name: objName || "", obj_id: objId || "" });
        try {
            const data = await fetchJSON(`/api/bloques/resumen?${query}`);
            const t = data.totals || {};
            const recordsLink = `/registros?block=${encodeURIComponent(objName || (objId || ""))}`;

            modalBody.innerHTML = `
                <div class="block-identity" style="margin-bottom:16px;">
                    ${blockIconHTML(identity)}
                    <span class="block-identity-text">
                        <span class="block-name" style="max-width:none;">${escapeHTML(identity.label)}</span>
                        ${identity.namespace
                            ? `<span class="block-namespace" style="max-width:none;">${escapeHTML(identity.namespace)}:${escapeHTML(identity.shortName)}</span>`
                            : (objId ? `<span class="block-namespace">obj_id: ${escapeHTML(objId)}</span>` : `<span class="block-namespace">Sin obj_name ni obj_id — revisa el registro crudo en Registros.</span>`)}
                    </span>
                </div>

                <section class="stat-grid" style="margin-bottom:18px;">
                    <div class="stat-card"><span class="stat-label">Total eventos</span><span class="stat-value">${formatNumber(t.total)}</span></div>
                    <div class="stat-card"><span class="stat-label">Roturas</span><span class="stat-value">${formatNumber(t.breaks)}</span></div>
                    <div class="stat-card"><span class="stat-label">Colocaciones</span><span class="stat-value">${formatNumber(t.places)}</span></div>
                    <div class="stat-card"><span class="stat-label">Explosiones</span><span class="stat-value">${formatNumber(t.explosions)}</span></div>
                    <div class="stat-card"><span class="stat-label">Jugadores distintos</span><span class="stat-value">${formatNumber(t.distinct_players)}</span></div>
                    <div class="stat-card"><span class="stat-label">Mundos</span><span class="stat-value">${formatNumber(t.distinct_worlds)}</span></div>
                </section>

                <p class="muted-text" style="margin-bottom:18px;">
                    Primer evento: ${escapeHTML(t.first_event_fmt || "-")} · Último evento: ${escapeHTML(t.last_event_fmt || "-")}
                </p>

                <div class="grid-2" style="margin-bottom:18px;">
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Por mundo</h3>
                        ${worldsListHTML(data.worlds || [])}
                    </div>
                    <div>
                        <h3 style="font-size:13.5px; margin-bottom:10px; color:var(--text-muted);">Jugadores más activos</h3>
                        ${playersListHTML(data.top_players || [])}
                    </div>
                </div>

                <div class="field-actions">
                    <a class="btn btn-primary" href="${recordsLink}">🔎 Buscar en Registros</a>
                    <button class="btn btn-outline" id="block-modal-copy">Copiar identificador</button>
                </div>
            `;

            const copyBtn = document.getElementById("block-modal-copy");
            if (copyBtn) {
                copyBtn.addEventListener("click", async () => {
                    const value = objName || objId || "";
                    try {
                        await navigator.clipboard.writeText(value);
                        toast("Identificador copiado", "success");
                    } catch (e) {
                        toast("No se pudo copiar", "error");
                    }
                });
            }
        } catch (err) {
            modalBody.innerHTML = `<p class="muted-text">Error al cargar el resumen: ${escapeHTML(err.message)}</p>`;
        }
    }

    tbody.addEventListener("click", (e) => {
        const row = e.target.closest(".row-clickable");
        if (!row) return;
        openBlockModal(row.dataset.objName, row.dataset.objId);
    });

    searchInput.addEventListener("input", debounce(() => loadBlocks(true), 350));
    worldSelect.addEventListener("change", () => loadBlocks(true));
    sortSelect.addEventListener("change", () => loadBlocks(true));
    orderSelect.addEventListener("change", () => loadBlocks(true));
    prevBtn.addEventListener("click", () => { offset = Math.max(0, offset - PAGE_SIZE); loadBlocks(false); });
    nextBtn.addEventListener("click", () => { offset += PAGE_SIZE; loadBlocks(false); });

    loadBlocks(true);
})();
