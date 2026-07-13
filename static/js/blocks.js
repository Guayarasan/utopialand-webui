(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, buildQueryString, debounce } = window.Utopialand;

    const searchInput = document.getElementById("b-search");
    const worldSelect = document.getElementById("b-world");
    const sortSelect = document.getElementById("b-sort");
    const tbody = document.getElementById("blocks-tbody");
    const countBadge = document.getElementById("blocks-count");
    const prevBtn = document.getElementById("bk-prev");
    const nextBtn = document.getElementById("bk-next");
    const pageLabel = document.getElementById("bk-page-label");

    const PAGE_SIZE = 25;
    let offset = 0;
    let total = 0;

    function rowHTML(b) {
        return `
            <tr>
                <td><strong>${escapeHTML(b.obj_name)}</strong></td>
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
    prevBtn.addEventListener("click", () => { offset = Math.max(0, offset - PAGE_SIZE); loadBlocks(false); });
    nextBtn.addEventListener("click", () => { offset += PAGE_SIZE; loadBlocks(false); });

    loadBlocks(true);
})();
