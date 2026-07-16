(function () {
    "use strict";
    const { fetchJSON, toast, escapeHTML } = window.Utopialand;

    const testBtn = document.getElementById("btn-test-conn");
    const resultBox = document.getElementById("conn-result");
    const clearCacheBtn = document.getElementById("btn-clear-cache");
    const changePasswordForm = document.getElementById("change-password-form");

    testBtn.addEventListener("click", async () => {
        testBtn.disabled = true;
        testBtn.textContent = "Probando…";
        try {
            const data = await fetchJSON("/api/config/test-conexion", { method: "POST" });
            resultBox.className = "conn-result show " + (data.ok ? "ok" : "error");
            resultBox.textContent = data.ok
                ? `✅ ${data.message} (${data.latency_ms} ms)`
                : `❌ ${data.message}`;
            toast(data.ok ? "Conexión correcta" : "Fallo de conexión", data.ok ? "success" : "error");
        } catch (err) {
            resultBox.className = "conn-result show error";
            resultBox.textContent = `❌ ${escapeHTML(err.message)}`;
        } finally {
            testBtn.disabled = false;
            testBtn.textContent = "🔄 Probar conexión";
        }
    });

    clearCacheBtn.addEventListener("click", async () => {
        try {
            await fetchJSON("/api/config/limpiar-cache", { method: "POST" });
            toast("Caché limpiada correctamente", "success");
        } catch (err) {
            toast(err.message, "error");
        }
    });

    if (changePasswordForm) {
        changePasswordForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            try {
                await fetchJSON("/api/auth/cambiar-password", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        current_password: document.getElementById("cp-current").value,
                        new_password: document.getElementById("cp-new").value,
                    }),
                });
                toast("Contraseña actualizada correctamente", "success");
                changePasswordForm.reset();
            } catch (err) {
                toast(err.message, "error");
            }
        });
    }

    const saveUserTzBtn = document.getElementById("btn-save-user-tz");
    if (saveUserTzBtn) {
        saveUserTzBtn.addEventListener("click", async () => {
            try {
                await fetchJSON("/api/config/zona-horaria/mia", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ timezone: document.getElementById("tz-user").value }),
                });
                toast("Zona horaria guardada", "success");
                window.location.reload();
            } catch (err) {
                toast(err.message, "error");
            }
        });
    }

    const saveAppTzBtn = document.getElementById("btn-save-app-tz");
    if (saveAppTzBtn) {
        saveAppTzBtn.addEventListener("click", async () => {
            try {
                await fetchJSON("/api/config/zona-horaria/app", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ timezone: document.getElementById("tz-app").value }),
                });
                toast("Zona horaria de la aplicación guardada", "success");
                window.location.reload();
            } catch (err) {
                toast(err.message, "error");
            }
        });
    }
})();
