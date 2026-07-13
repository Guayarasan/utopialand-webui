(function () {
    "use strict";
    const { fetchJSON, toast, escapeHTML } = window.Utopialand;

    const testBtn = document.getElementById("btn-test-conn");
    const resultBox = document.getElementById("conn-result");
    const clearCacheBtn = document.getElementById("btn-clear-cache");

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
})();
