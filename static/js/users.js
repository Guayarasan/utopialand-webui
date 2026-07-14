(function () {
    "use strict";
    const { toast, fetchJSON, escapeHTML, setupModal } = window.Utopialand;

    const tbody = document.getElementById("users-tbody");
    const newUserBtn = document.getElementById("btn-new-user");
    const userModal = setupModal("user-modal", "user-modal-close");
    const userForm = document.getElementById("user-form");

    const resetModal = setupModal("reset-modal", "reset-modal-close");
    const resetForm = document.getElementById("reset-form");
    const resetTitle = document.getElementById("reset-modal-title");
    let resetTargetId = null;

    const ROLE_LABELS = { admin: "Administrador", moderator: "Moderador", viewer: "Solo lectura" };

    function rowHTML(u) {
        return `
            <tr>
                <td><strong>${escapeHTML(u.username)}</strong></td>
                <td>
                    <select class="role-select" data-id="${u.id}">
                        ${Object.entries(ROLE_LABELS).map(([value, label]) =>
                            `<option value="${value}" ${u.role === value ? "selected" : ""}>${label}</option>`
                        ).join("")}
                    </select>
                </td>
                <td>
                    <span class="badge ${u.active ? "badge-success" : "badge-danger"}">${u.active ? "Activo" : "Desactivado"}</span>
                </td>
                <td>${escapeHTML(u.created_at_fmt)}</td>
                <td>${escapeHTML(u.last_login_fmt)}</td>
                <td class="user-actions">
                    <button class="btn btn-outline btn-sm" data-toggle="${u.id}" data-active="${u.active}">${u.active ? "Desactivar" : "Activar"}</button>
                    <button class="btn btn-outline btn-sm" data-reset="${u.id}" data-username="${escapeHTML(u.username)}">Contraseña</button>
                    <button class="btn btn-ghost btn-sm" data-delete="${u.id}">Eliminar</button>
                </td>
            </tr>
        `;
    }

    async function loadUsers() {
        tbody.innerHTML = `<tr><td colspan="6" class="table-empty">Cargando usuarios…</td></tr>`;
        try {
            const data = await fetchJSON("/api/usuarios");
            tbody.innerHTML = data.results.length
                ? data.results.map(rowHTML).join("")
                : `<tr><td colspan="6" class="table-empty">Sin usuarios.</td></tr>`;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="6" class="table-empty">Error: ${escapeHTML(err.message)}</td></tr>`;
        }
    }

    tbody.addEventListener("change", async (e) => {
        const select = e.target.closest(".role-select");
        if (!select) return;
        try {
            await fetchJSON(`/api/usuarios/${select.dataset.id}/rol`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ role: select.value }),
            });
            toast("Rol actualizado", "success");
        } catch (err) {
            toast(err.message, "error");
            loadUsers();
        }
    });

    tbody.addEventListener("click", async (e) => {
        const toggleBtn = e.target.closest("[data-toggle]");
        const resetBtn = e.target.closest("[data-reset]");
        const deleteBtn = e.target.closest("[data-delete]");

        if (toggleBtn) {
            const nextActive = toggleBtn.dataset.active !== "true";
            try {
                await fetchJSON(`/api/usuarios/${toggleBtn.dataset.toggle}/estado`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ active: nextActive }),
                });
                loadUsers();
            } catch (err) {
                toast(err.message, "error");
            }
        }

        if (resetBtn) {
            resetTargetId = resetBtn.dataset.reset;
            resetTitle.textContent = `Restablecer contraseña — ${resetBtn.dataset.username}`;
            resetForm.reset();
            resetModal.open();
        }

        if (deleteBtn) {
            if (!confirm("¿Eliminar este usuario? Esta acción no se puede deshacer.")) return;
            try {
                await fetchJSON(`/api/usuarios/${deleteBtn.dataset.delete}`, { method: "DELETE" });
                toast("Usuario eliminado", "success");
                loadUsers();
            } catch (err) {
                toast(err.message, "error");
            }
        }
    });

    newUserBtn.addEventListener("click", () => {
        userForm.reset();
        userModal.open();
    });

    userForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            await fetchJSON("/api/usuarios", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    username: document.getElementById("nu-username").value,
                    password: document.getElementById("nu-password").value,
                    role: document.getElementById("nu-role").value,
                }),
            });
            toast("Usuario creado", "success");
            userModal.close();
            loadUsers();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    resetForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
            await fetchJSON(`/api/usuarios/${resetTargetId}/password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password: document.getElementById("reset-password").value }),
            });
            toast("Contraseña actualizada", "success");
            resetModal.close();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    loadUsers();
})();
