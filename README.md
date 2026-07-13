# Utopialand WebUI

Panel web profesional para consultar, filtrar e investigar los registros
generados por **Tianyan** (plugin de logging para Minecraft Bedrock sobre
Endstone), pensado como equivalente a *CoreProtect Inspector* pero para
Bedrock, con foco en rendimiento sobre tablas de millones de filas.

## Tecnologías

- **Backend**: Python, Flask, PyMySQL, DBUtils (pool de conexiones)
- **Frontend**: HTML, CSS y JavaScript puro (sin frameworks), Chart.js vía CDN para gráficos
- **Base de datos**: MySQL (Aiven) — tabla única `LOGDATA`
- **Hosting**: Render (Gunicorn)

## Estructura del proyecto

```
app.py                  # Application factory, registro de blueprints
config.py                # Configuración centralizada (variables de entorno)
database.py               # Pool de conexiones, health-check, streaming de filas
services/
    query_builder.py       # Filtros y WHERE/ORDER BY compartidos, con whitelist
    records.py              # Registros individuales (paginación por keyset)
    players.py               # Agregados por jugador
    blocks.py                 # Agregados por bloque/objeto
    coordinates.py             # Búsqueda por proximidad (bounding box + distancia)
    stats.py                    # Estadísticas cacheadas para dashboard/gráficos
    export.py                    # Exportación CSV en streaming (SSCursor)
routes/                  # Blueprints Flask: una página + sus endpoints /api/*
utils/
    cache.py                # Caché TTL en memoria para agregados costosos
    formatting.py             # Fechas Unix -> legibles, parseo de JSON, etc.
templates/                # Jinja2 (base.html + una plantilla por página)
static/css/style.css      # Diseño (tema oscuro, responsive)
static/js/                 # Un archivo JS por página + utilidades comunes (app.js)
sql/indexes.sql            # Índices recomendados (ejecución manual)
```

## Variables de entorno

Ver `.env.example`. Como mínimo se requieren `DB_HOST`, `DB_NAME`,
`DB_USER` y `DB_PASSWORD`.

## Ejecutar en local

```bash
pip install -r requirements.txt
export DB_HOST=... DB_NAME=... DB_USER=... DB_PASSWORD=...
python app.py
```

## Despliegue en Render

Start command sugerido:

```
gunicorn app:app
```

## Rendimiento sobre tablas grandes

- **Paginación por keyset** en "Registros" (no `OFFSET`, que se degrada con
  tablas grandes): el cursor viaja como `(time, id_pk)` del último registro visto.
- **Pool de conexiones** (`DBUtils.PooledDB`) en vez de abrir una conexión
  TCP nueva por request.
- **Caché en memoria con TTL** para agregados costosos (conteos, distribución
  por tipo/mundo, series temporales) usados en Dashboard y Estadísticas.
- **Exportación CSV en streaming** con `SSCursor`, sin cargar todo el
  resultado en memoria del servidor.
- **Índices recomendados** en `sql/indexes.sql` (no se aplican automáticamente:
  alterar una tabla de millones de filas es una decisión operativa que debe
  tomar un administrador en una ventana de mantenimiento).

## Columnas de `LOGDATA`

`id_pk, uuid, id, name, pos_x, pos_y, pos_z, world, obj_id, obj_name, time, type, data, status`

`time` es un Unix timestamp. No se usan columnas fuera de esta lista.
