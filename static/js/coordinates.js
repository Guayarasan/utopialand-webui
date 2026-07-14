(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, typeBadge, buildQueryString } = window.Utopialand;

    const form = document.getElementById("coord-form");
    const tbody = document.getElementById("coord-tbody");
    const countBadge = document.getElementById("coord-count");

    function rowHTML(r) {
        const fmt = (v) => (v === null || v === undefined ? "?" : Math.round(v));
        return `
            <tr>
                <td>${escapeHTML(r.fecha)}</td>
                <td>${escapeHTML(r.name || "-")}</td>
                <td>${typeBadge(r.type)}</td>
                <td>${escapeHTML(r.obj_name || "-")}</td>
                <td>${fmt(r.pos_x)} / ${fmt(r.pos_y)} / ${fmt(r.pos_z)}</td>
                <td><span class="badge badge-primary">${r.distance} bloques</span></td>
                <td>${escapeHTML(r.world || "-")}</td>
            </tr>
        `;
    }

    document.querySelectorAll("[data-radius]").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.getElementById("c-radius").value = btn.dataset.radius;
        });
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const formData = new FormData(form);
        const params = {
            x: formData.get("x"),
            y: formData.get("y"),
            z: formData.get("z"),
            radius: formData.get("radius"),
            world: formData.get("world"),
        };

        tbody.innerHTML = `<tr><td colspan="7" class="table-empty">Buscando…</td></tr>`;
        try {
            const data = await fetchJSON(`/api/coordenadas/buscar?${buildQueryString(params)}`);
            tbody.innerHTML = data.results.length
                ? data.results.map(rowHTML).join("")
                : `<tr><td colspan="7" class="table-empty">No hay eventos en ese radio.</td></tr>`;
            countBadge.textContent = `${formatNumber(data.meta.matched)} eventos (de ${formatNumber(data.meta.scanned)} escaneados)`;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty">Error: ${escapeHTML(err.message)}</td></tr>`;
            toast(err.message, "error");
        }
    });
})();
