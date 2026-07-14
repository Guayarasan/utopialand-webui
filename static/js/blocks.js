(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, buildQueryString, debounce } = window.Utopialand;

    const searchInput = document.getElementById("b-search");
    const worldSelect = document.getElementById("b-world");
    const sortSelect = document.getElementById("b-sort");
    const orderSelect = document.getElementById("b-order");
    const tbody = document.getElementById("blocks-tbody");
    const countBadge = document.getElementById("blocks-count");
    const prevBtn = document.getElementById("bk-prev");
    const nextBtn = document.getElementById("bk-next");
    const pageLabel = document.getElementById("bk-page-label");

    const PAGE_SIZE = 25;
    let offset = 0;
    let total = 0;

    function blockIdentity(objName) {
        const raw = objName || "desconocido";
        const parts = raw.split(":");
        const namespace = parts.length > 1 ? parts[0] : null;
        const shortName = parts.length > 1 ? parts.slice(1).join(":") : raw;
        const label = shortName.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        const iconSlug = shortName.split("[")[0]; // por si viene con estado de bloque
        const iconUrl = `https://cdn.jsdelivr.net/gh/InventivetalentDev/minecraft-assets@1.20/assets/minecraft/textures/block/${iconSlug}.png`;

        return `
            <div class="block-identity">
                <span class="block-icon" aria-hidden="true">
                    <img src="${iconUrl}" alt="" loading="lazy"
                         onerror="this.parentElement.classList.add('block-icon-fallback'); this.remove();">
                </span>
                <span class="block-identity-text">
                    <span class="block-name">${escapeHTML(label)}</span>
                    ${namespace ? `<span class="block-namespace">${escapeHTML(namespace)}:${escapeHTML(shortName)}</span>` : ""}
                </span>
            </div>
        `;
    }

    function rowHTML(b) {
        return `
            <tr>
                <td>${blockIdentity(b.obj_name)}</td>
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

    searchInput.addEventListener("input", debounce(() => loadBlocks(true), 350));
    worldSelect.addEventListener("change", () => loadBlocks(true));
    sortSelect.addEventListener("change", () => loadBlocks(true));
    orderSelect.addEventListener("change", () => loadBlocks(true));
    prevBtn.addEventListener("click", () => { offset = Math.max(0, offset - PAGE_SIZE); loadBlocks(false); });
    nextBtn.addEventListener("click", () => { offset += PAGE_SIZE; loadBlocks(false); });

    loadBlocks(true);
})();
