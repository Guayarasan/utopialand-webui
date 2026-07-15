(function () {
    "use strict";
    const { toast, fetchJSON, escapeHTML, formatNumber } = window.Utopialand;

    const textarea = document.getElementById("sql-editor");
    const runBtn = document.getElementById("btn-run-sql");
    const saveFavBtn = document.getElementById("btn-save-favorite");
    const copySqlBtn = document.getElementById("btn-copy-sql");
    const resultMeta = document.getElementById("sql-result-meta");
    const resultTable = document.getElementById("sql-result-table");
    const exportActions = document.getElementById("sql-export-actions");
    const favoritesList = document.getElementById("sql-favorites-list");
    const historyList = document.getElementById("sql-history-list");

    let lastResult = null;

    // -------- Editor con resaltado de sintaxis + autocompletado --------
    // Columnas reales de LOGDATA, documentadas en services/query_builder.py
    // -- no inventar otras.
    const LOGDATA_COLUMNS = [
        "id_pk", "uuid", "id", "name", "pos_x", "pos_y", "pos_z", "world",
        "obj_id", "obj_name", "time", "type", "data", "status",
    ];

    let cm = null;
    if (window.CodeMirror) {
        cm = CodeMirror.fromTextArea(textarea, {
            mode: "text/x-mysql",
            theme: "dracula",
            lineNumbers: true,
            matchBrackets: true,
            autoCloseBrackets: true,
            indentWithTabs: true,
            hintOptions: {
                tables: { LOGDATA: LOGDATA_COLUMNS },
            },
            extraKeys: {
                "Ctrl-Enter": () => runQuery(),
                "Cmd-Enter": () => runQuery(),
                "Ctrl-Space": "autocomplete",
                "Cmd-Space": "autocomplete",
            },
        });
        cm.setSize("100%", "260px");
        cm.on("inputRead", (instance, change) => {
            if (change.text[0] && /[a-zA-Z_.]/.test(change.text[0])) {
                instance.showHint({ completeSingle: false });
            }
        });
    }

    function getSQL() {
        return (cm ? cm.getValue() : textarea.value).trim();
    }

    function setSQL(value) {
        if (cm) cm.setValue(value || "");
        else textarea.value = value || "";
    }

    async function runQuery() {
        const sql = getSQL();
        if (!sql) {
            toast("Escribe una consulta antes de ejecutar.", "error");
            return;
        }
        runBtn.disabled = true;
        runBtn.textContent = "Ejecutando…";
        resultMeta.textContent = "Ejecutando consulta…";

        try {
            const data = await fetchJSON("/api/sql/ejecutar", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sql }),
            });
            lastResult = data;
            renderResult(data);
            loadHistory();
        } catch (err) {
            resultMeta.textContent = "";
            resultTable.querySelector("thead").innerHTML = "<tr><th class=\"table-empty\"></th></tr>";
            resultTable.querySelector("tbody").innerHTML =
                `<tr><td class="table-empty">❌ ${escapeHTML(err.message)}</td></tr>`;
            exportActions.style.display = "none";
            toast(err.message, "error");
            loadHistory();
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = "▶ Ejecutar";
        }
    }

    function renderResult(data) {
        resultMeta.textContent = `${formatNumber(data.row_count)} filas · ${data.duration_ms} ms` +
            (data.truncated ? ` · resultado truncado a ${formatNumber(data.row_count)} filas` : "");

        const thead = resultTable.querySelector("thead");
        const tbody = resultTable.querySelector("tbody");

        if (!data.columns.length) {
            thead.innerHTML = "<tr><th class=\"table-empty\"></th></tr>";
            tbody.innerHTML = `<tr><td class="table-empty">Consulta ejecutada sin resultados tabulares.</td></tr>`;
            exportActions.style.display = "none";
            return;
        }

        thead.innerHTML = "<tr>" + data.columns.map((c) => `<th>${escapeHTML(c)}</th>`).join("") + "</tr>";
        tbody.innerHTML = data.rows.length
            ? data.rows.map((row) => "<tr>" + data.columns.map((c) => `<td>${escapeHTML(formatCell(row[c]))}</td>`).join("") + "</tr>").join("")
            : `<tr><td colspan="${data.columns.length}" class="table-empty">Sin resultados.</td></tr>`;

        exportActions.style.display = data.rows.length ? "flex" : "none";
    }

    function formatCell(value) {
        if (value === null || value === undefined) return "";
        if (typeof value === "object") return JSON.stringify(value);
        return String(value);
    }

    function rowsToTSV(data) {
        const header = data.columns.join("\t");
        const body = data.rows.map((r) => data.columns.map((c) => formatCell(r[c])).join("\t")).join("\n");
        return header + "\n" + body;
    }

    function downloadBlob(content, filename, mime) {
        const blob = new Blob([content], { type: mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }

    exportActions.addEventListener("click", async (e) => {
        const btn = e.target.closest("[data-export]");
        if (!btn || !lastResult) return;
        const format = btn.dataset.export;

        if (format === "csv") {
            const csv = [lastResult.columns.join(",")]
                .concat(lastResult.rows.map((r) => lastResult.columns.map((c) => `"${String(formatCell(r[c])).replace(/"/g, '""')}"`).join(",")))
                .join("\n");
            downloadBlob(csv, "consulta_sql.csv", "text/csv");
        } else if (format === "json") {
            downloadBlob(JSON.stringify(lastResult.rows, null, 2), "consulta_sql.json", "application/json");
        } else if (format === "clipboard") {
            try {
                await navigator.clipboard.writeText(rowsToTSV(lastResult));
                toast("Resultados copiados al portapapeles", "success");
            } catch (err) {
                toast("No se pudo copiar al portapapeles", "error");
            }
        }
    });

    copySqlBtn.addEventListener("click", async () => {
        const sql = getSQL();
        if (!sql) {
            toast("No hay consulta que copiar.", "error");
            return;
        }
        try {
            await navigator.clipboard.writeText(sql);
            toast("Consulta copiada al portapapeles", "success");
        } catch (err) {
            toast("No se pudo copiar", "error");
        }
    });

    // -------- Favoritas (agrupadas por categoría) --------

    async function loadFavorites() {
        try {
            const data = await fetchJSON("/api/sql/favoritas");
            favoritesList.innerHTML = data.results.length
                ? groupedFavoritesHTML(data.results)
                : `<li class="table-empty">Sin consultas guardadas.</li>`;
        } catch (err) {
            favoritesList.innerHTML = `<li class="table-empty">Error al cargar.</li>`;
        }
    }

    function groupedFavoritesHTML(rows) {
        const groups = new Map();
        rows.forEach((f) => {
            const key = f.category || (f.is_example ? "Ejemplos" : "Sin categoría");
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(f);
        });
        let html = "";
        groups.forEach((items, category) => {
            html += `<li class="sql-list-category">${escapeHTML(category)}</li>`;
            html += items.map(favoriteItemHTML).join("");
        });
        return html;
    }

    function favoriteItemHTML(fav) {
        return `
            <li class="sql-list-item" data-sql="${escapeHTML(fav.sql_text)}">
                <div class="sql-list-item-title">
                    <span>${fav.is_example ? "📌 " : ""}${escapeHTML(fav.name)}</span>
                    <span class="sql-list-item-actions">
                        <button class="sql-list-item-copy" data-copy-sql="${escapeHTML(fav.sql_text)}" title="Copiar consulta">📋</button>
                        ${fav.is_example ? "" : `<button class="sql-list-item-delete" data-delete-fav="${fav.id}" title="Eliminar">✕</button>`}
                    </span>
                </div>
                <div class="sql-list-item-sql">${escapeHTML(fav.sql_text.replace(/\s+/g, " "))}</div>
            </li>
        `;
    }

    favoritesList.addEventListener("click", async (e) => {
        const copyBtn = e.target.closest("[data-copy-sql]");
        if (copyBtn) {
            e.stopPropagation();
            try {
                await navigator.clipboard.writeText(copyBtn.dataset.copySql);
                toast("Consulta copiada", "success");
            } catch (err) {
                toast("No se pudo copiar", "error");
            }
            return;
        }
        const delBtn = e.target.closest("[data-delete-fav]");
        if (delBtn) {
            e.stopPropagation();
            try {
                await fetchJSON(`/api/sql/favoritas/${delBtn.dataset.deleteFav}`, { method: "DELETE" });
                loadFavorites();
            } catch (err) {
                toast(err.message, "error");
            }
            return;
        }
        const item = e.target.closest(".sql-list-item");
        if (item) setSQL(item.dataset.sql);
    });

    async function loadHistory() {
        try {
            const data = await fetchJSON("/api/sql/historial");
            historyList.innerHTML = data.results.length
                ? data.results.map(historyItemHTML).join("")
                : `<li class="table-empty">Aún no has ejecutado consultas.</li>`;
        } catch (err) {
            historyList.innerHTML = `<li class="table-empty">Error al cargar.</li>`;
        }
    }

    function historyItemHTML(h) {
        const icon = h.success ? "✅" : "❌";
        return `
            <li class="sql-list-item" data-sql="${escapeHTML(h.sql_text)}">
                <div class="sql-list-item-title">
                    <span>${icon} ${escapeHTML(h.executed_at_fmt)}</span>
                    <span class="sql-list-item-actions">
                        <button class="sql-list-item-copy" data-copy-sql="${escapeHTML(h.sql_text)}" title="Copiar consulta">📋</button>
                    </span>
                </div>
                <div class="sql-list-item-sql">${escapeHTML(h.sql_text.replace(/\s+/g, " "))}</div>
            </li>
        `;
    }

    historyList.addEventListener("click", async (e) => {
        const copyBtn = e.target.closest("[data-copy-sql]");
        if (copyBtn) {
            e.stopPropagation();
            try {
                await navigator.clipboard.writeText(copyBtn.dataset.copySql);
                toast("Consulta copiada", "success");
            } catch (err) {
                toast("No se pudo copiar", "error");
            }
            return;
        }
        const item = e.target.closest(".sql-list-item");
        if (item) setSQL(item.dataset.sql);
    });

    saveFavBtn.addEventListener("click", async () => {
        const sql = getSQL();
        if (!sql) {
            toast("Escribe una consulta primero.", "error");
            return;
        }
        const name = prompt("Nombre para esta consulta guardada:");
        if (!name) return;
        const category = prompt("Categoría (opcional, ej. Investigación, Rankings):", "") || "";
        try {
            await fetchJSON("/api/sql/favoritas", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, sql, category }),
            });
            toast("Consulta guardada", "success");
            loadFavorites();
        } catch (err) {
            toast(err.message, "error");
        }
    });

    runBtn.addEventListener("click", runQuery);
    textarea.addEventListener("keydown", (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            e.preventDefault();
            runQuery();
        }
    });

    loadFavorites();
    loadHistory();
})();
