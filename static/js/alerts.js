(function () {
    "use strict";
    const { toast, fetchJSON, escapeHTML, formatNumber, typeBadge, setupModal } = window.Utopialand;

    const form = document.getElementById("alert-form");
    const rulesList = document.getElementById("rules-list");
    const rulesCount = document.getElementById("rules-count");

    const previewModal = setupModal("alert-preview-modal", "alert-preview-close");
    const previewTitle = document.getElementById("alert-preview-title");
    const previewBody = document.getElementById("alert-preview-body");

    document.querySelectorAll(".alert-preset").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.getElementById("a-name").value = btn.dataset.presetName;
            document.getElementById("a-pattern").value = btn.dataset.presetPattern;
            document.getElementById("a-name").focus();
        });
    });

    function ruleRowHTML(rule) {
        const typesHTML = rule.event_types_list.map((t) => typeBadge(t)).join(" ");
        return `
            <tr>
                <td><strong>${escapeHTML(rule.name)}</strong></td>
                <td>${typesHTML || "-"}</td>
                <td><code>${escapeHTML(rule.block_pattern || "cualquiera")}</code></td>
                <td>
                    <label class="toggle-switch">
                        <input type="checkbox" data-toggle-rule="${rule.id}" ${rule.enabled ? "checked" : ""}>
                        <span></span>
                    </label>
                </td>
                <td>${escapeHTML(rule.last_triggered_fmt || "Nunca comprobada")}</td>
                <td>
                    <button class="row-link" data-preview-rule="${rule.id}" data-rule-name="${escapeHTML(rule.name)}">Vista previa</button>
                    <button class="row-link" data-delete-rule="${rule.id}" title="Eliminar">🗑</button>
                </td>
            </tr>
        `;
    }

    async function loadRules() {
        try {
            const data = await fetchJSON("/api/alertas/reglas");
            rulesCount.textContent = `${formatNumber(data.results.length)} reglas`;
            rulesList.innerHTML = data.results.length
                ? `
                    <div class="table-wrapper">
                        <table class="data-table">
                            <thead>
                                <tr><th>Nombre</th><th>Tipos</th><th>Patrón</th><th>Activa</th><th>Última comprobación</th><th></th></tr>
                            </thead>
                            <tbody>${data.results.map(ruleRowHTML).join("")}</tbody>
                        </table>
                    </div>
                `
                : `<p class="table-empty">Aún no configuraste reglas. Usa una plantilla arriba o crea una personalizada.</p>`;
        } catch (err) {
            rulesList.innerHTML = `<p class="table-empty">Error al cargar reglas: ${escapeHTML(err.message)}</p>`;
        }
    }

    rulesList.addEventListener("change", async (e) => {
        const toggle = e.target.closest("[data-toggle-rule]");
        if (!toggle) return;
        try {
            await fetchJSON(`/api/alertas/reglas/${toggle.dataset.toggleRule}/estado`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ enabled: toggle.checked }),
            });
            toast(toggle.checked ? "Regla activada" : "Regla desactivada", "success");
        } catch (err) {
            toast(err.message, "error");
            toggle.checked = !toggle.checked;
        }
    });

    rulesList.addEventListener("click", async (e) => {
        const delBtn = e.target.closest("[data-delete-rule]");
        if (delBtn) {
            if (!confirm("¿Eliminar esta regla de alerta?")) return;
            try {
                await fetchJSON(`/api/alertas/reglas/${delBtn.dataset.deleteRule}`, { method: "DELETE" });
                loadRules();
            } catch (err) {
                toast(err.message, "error");
            }
            return;
        }
        const previewBtn = e.target.closest("[data-preview-rule]");
        if (previewBtn) openPreview(previewBtn.dataset.previewRule, previewBtn.dataset.ruleName);
    });

    function feedItemHTML(row) {
        const coords = (row.pos_x !== undefined && row.pos_x !== null)
            ? `${Math.round(row.pos_x)}/${Math.round(row.pos_y)}/${Math.round(row.pos_z)}`
            : null;
        const bits = [row.world, coords].filter(Boolean).join(" · ");
        return `
            <div class="feed-item">
                <div class="feed-main">
                    <span class="feed-title"><strong>${escapeHTML(row.name || "?")}</strong> ${typeBadge(row.type)} <span class="feed-object">${escapeHTML(row.obj_name || row.obj_id || "")}</span></span>
                    <span class="feed-meta">${escapeHTML(bits || "-")}</span>
                </div>
                <span class="feed-time">${escapeHTML(row.fecha)}</span>
            </div>
        `;
    }

    async function openPreview(ruleId, ruleName) {
        previewModal.open();
        previewTitle.textContent = `Vista previa · ${ruleName}`;
        previewBody.innerHTML = `<p class="muted-text">Buscando coincidencias en las últimas 24 horas…</p>`;
        try {
            const data = await fetchJSON(`/api/alertas/reglas/${ruleId}/vista-previa?hours=24`);
            previewBody.innerHTML = data.results.length
                ? `<div class="activity-feed">${data.results.map(feedItemHTML).join("")}</div>`
                : `<p class="muted-text">Sin coincidencias en las últimas 24 horas para esta regla. Prueba a ampliar el rango o revisar los tipos de evento seleccionados.</p>`;
        } catch (err) {
            previewBody.innerHTML = `<p class="muted-text">Error: ${escapeHTML(err.message)}</p>`;
        }
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const typesSelect = document.getElementById("a-types");
        const types = Array.from(typesSelect.selectedOptions).map((o) => o.value);
        if (!types.length) {
            toast("Selecciona al menos un tipo de evento.", "error");
            return;
        }
        try {
            await fetchJSON("/api/alertas/reglas", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: document.getElementById("a-name").value,
                    event_types: types,
                    block_pattern: document.getElementById("a-pattern").value,
                    discord_webhook_url: document.getElementById("a-webhook").value,
                }),
            });
            toast("Regla creada", "success");
            form.reset();
            loadRules();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    loadRules();
})();
