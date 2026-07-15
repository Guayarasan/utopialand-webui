(function () {
    "use strict";
    const { toast, fetchJSON, formatNumber, escapeHTML, typeBadge, buildQueryString } = window.Utopialand;

    const form = document.getElementById("coord-form");
    const tbody = document.getElementById("coord-tbody");
    const countBadge = document.getElementById("coord-count");
    const favList = document.getElementById("favorite-locations");
    const saveLocationBtn = document.getElementById("btn-save-location");

    function guessIcon(name) {
        const n = name.toLowerCase();
        if (n.includes("spawn")) return "🏠";
        if (n.includes("base")) return "🏰";
        if (n.includes("tienda") || n.includes("shop")) return "🏪";
        if (n.includes("granja") || n.includes("farm")) return "🌾";
        if (n.includes("cofre") || n.includes("chest") || n.includes("almac")) return "📦";
        if (n.includes("mina") || n.includes("mine")) return "⛏️";
        return "📍";
    }

    function lastResultRowHTML(r) {
        const fmt = (v) => (v === null || v === undefined ? "?" : Math.round(v));
        const coordsText = `${fmt(r.pos_x)}, ${fmt(r.pos_y)}, ${fmt(r.pos_z)}`;
        return `
            <tr>
                <td>${escapeHTML(r.fecha)}</td>
                <td>${escapeHTML(r.name || "-")}</td>
                <td>${typeBadge(r.type)}</td>
                <td>${escapeHTML(r.obj_name || "-")}</td>
                <td>${fmt(r.pos_x)} / ${fmt(r.pos_y)} / ${fmt(r.pos_z)}</td>
                <td><span class="badge badge-primary">${r.distance} bloques</span></td>
                <td>${escapeHTML(r.world || "-")}</td>
                <td>
                    <button class="row-link coord-copy" data-coords="${coordsText}" title="Copiar coordenadas">📋</button>
                    <button class="row-link coord-recenter" data-x="${r.pos_x}" data-y="${r.pos_y}" data-z="${r.pos_z}" data-world="${escapeHTML(r.world || "")}" title="Buscar cerca de aquí">🎯</button>
                </td>
            </tr>
        `;
    }

    document.querySelectorAll("[data-radius]").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.getElementById("c-radius").value = btn.dataset.radius;
        });
    });

    async function runSearch() {
        const formData = new FormData(form);
        const params = {
            x: formData.get("x"),
            y: formData.get("y"),
            z: formData.get("z"),
            radius: formData.get("radius"),
            world: formData.get("world"),
        };

        tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Buscando…</td></tr>`;
        try {
            const data = await fetchJSON(`/api/coordenadas/buscar?${buildQueryString(params)}`);
            tbody.innerHTML = data.results.length
                ? data.results.map(lastResultRowHTML).join("")
                : `<tr><td colspan="8" class="table-empty">No hay eventos en ese radio.</td></tr>`;
            countBadge.textContent = `${formatNumber(data.meta.matched)} eventos (de ${formatNumber(data.meta.scanned)} escaneados)`;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="8" class="table-empty">Error: ${escapeHTML(err.message)}</td></tr>`;
            toast(err.message, "error");
        }
    }

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        runSearch();
    });

    tbody.addEventListener("click", async (e) => {
        const copyBtn = e.target.closest(".coord-copy");
        if (copyBtn) {
            try {
                await navigator.clipboard.writeText(copyBtn.dataset.coords);
                toast("Coordenadas copiadas", "success");
            } catch (err) {
                toast("No se pudo copiar", "error");
            }
            return;
        }
        const recenterBtn = e.target.closest(".coord-recenter");
        if (recenterBtn) {
            document.getElementById("c-x").value = Math.round(recenterBtn.dataset.x);
            document.getElementById("c-y").value = Math.round(recenterBtn.dataset.y);
            document.getElementById("c-z").value = Math.round(recenterBtn.dataset.z);
            if (recenterBtn.dataset.world) document.getElementById("c-world").value = recenterBtn.dataset.world;
            runSearch();
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    });

    // -------- Lugares favoritos --------

    async function loadFavorites() {
        try {
            const data = await fetchJSON("/api/coordenadas/favoritos");
            favList.innerHTML = data.results.length
                ? data.results.map((f) => `
                    <button type="button" class="chip" data-fav-x="${f.pos_x}" data-fav-y="${f.pos_y}" data-fav-z="${f.pos_z}" data-fav-world="${escapeHTML(f.world || "")}">
                        ${escapeHTML(f.icon || "📍")} ${escapeHTML(f.name)}
                        <span class="chip-remove" data-fav-delete="${f.id}" title="Eliminar">✕</span>
                    </button>
                `).join("")
                : `<span class="muted-text">Aún no guardaste lugares. Busca unas coordenadas y pulsa "Guardar estas coordenadas".</span>`;
        } catch (err) {
            favList.innerHTML = `<span class="muted-text">No se pudieron cargar los lugares guardados.</span>`;
        }
    }

    favList.addEventListener("click", (e) => {
        const delTarget = e.target.closest("[data-fav-delete]");
        if (delTarget) {
            e.stopPropagation();
            fetchJSON(`/api/coordenadas/favoritos/${delTarget.dataset.favDelete}`, { method: "DELETE" })
                .then(loadFavorites)
                .catch((err) => toast(err.message, "error"));
            return;
        }
        const chip = e.target.closest(".chip");
        if (chip) {
            document.getElementById("c-x").value = Math.round(chip.dataset.favX);
            document.getElementById("c-y").value = Math.round(chip.dataset.favY);
            document.getElementById("c-z").value = Math.round(chip.dataset.favZ);
            if (chip.dataset.favWorld) document.getElementById("c-world").value = chip.dataset.favWorld;
            runSearch();
        }
    });

    saveLocationBtn.addEventListener("click", async () => {
        const formData = new FormData(form);
        const x = formData.get("x"), y = formData.get("y"), z = formData.get("z");
        if (!x || !y || !z) {
            toast("Completa X, Y y Z antes de guardar.", "error");
            return;
        }
        const name = prompt("Nombre para este lugar (ej. Spawn, Base principal, Tienda):");
        if (!name) return;
        try {
            await fetchJSON("/api/coordenadas/favoritos", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name, world: formData.get("world"), x, y, z, icon: guessIcon(name),
                }),
            });
            toast("Lugar guardado", "success");
            loadFavorites();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    // -------- Prellenado desde URL (ej. enlace "Buscar por radio" desde Registros) --------

    function prefillFromURL() {
        const params = new URLSearchParams(window.location.search);
        if (!params.has("x") || !params.has("y") || !params.has("z")) return false;
        document.getElementById("c-x").value = params.get("x");
        document.getElementById("c-y").value = params.get("y");
        document.getElementById("c-z").value = params.get("z");
        if (params.has("radius")) document.getElementById("c-radius").value = params.get("radius");
        if (params.has("world")) document.getElementById("c-world").value = params.get("world");
        return true;
    }

    loadFavorites();
    if (prefillFromURL()) runSearch();
})();
