# Utopialand WebUI

Panel web profesional para consultar, filtrar e investigar los registros
generados por **Tianyan** (plugin de logging para Minecraft Bedrock sobre
Endstone), pensado como equivalente a *CoreProtect Inspector* pero para
Bedrock, con foco en rendimiento sobre tablas de millones de filas.

## Tecnologías

- **Backend**: Python, Flask, PyMySQL, DBUtils (pool de conexiones)
- **Frontend**: HTML, CSS y JavaScript puro (sin frameworks), Chart.js vía CDN para gráficos
- **Base de datos**: MySQL (Aiven) — tabla principal `LOGDATA` + tablas propias de la app (usuarios, historial SQL, filtros/consultas guardadas)
- **Hosting**: Render (Gunicorn)

## Estructura del proyecto

```
app.py                  # Application factory, blueprints, gate de autenticación global
config.py                # Configuración centralizada (variables de entorno)
database.py               # Pool de conexiones, health-check, streaming de filas
services/
    query_builder.py       # Filtros y WHERE/ORDER BY compartidos, con whitelist
    records.py              # Registros individuales (paginación por página)
    players.py               # Agregados por jugador
    blocks.py                 # Agregados por bloque/objeto
    coordinates.py             # Búsqueda por proximidad (bounding box + distancia)
    stats.py                    # Estadísticas cacheadas (dashboard de Estadísticas)
    export.py                    # Exportación CSV / XLSX / JSON en streaming
    admin_db.py                   # Bootstrap de tablas propias + admin inicial
    users.py                       # CRUD de subusuarios
    sql_console.py                  # Consola SQL de solo lectura + historial + favoritas
    saved_filters.py                 # Filtros favoritos de Registros
routes/                  # Blueprints Flask: una página + sus endpoints /api/*
utils/
    cache.py                # Caché TTL en memoria para agregados costosos
    formatting.py             # Fechas Unix -> legibles, parseo de JSON, etc.
    security.py                # Autenticación, hashing, decoradores de rol
templates/                # Jinja2 (base.html + una plantilla por página)
static/css/style.css      # Diseño (tema oscuro, responsive)
static/js/                 # Un archivo JS por página + utilidades comunes (app.js)
sql/indexes.sql            # Índices recomendados (ejecución manual)
```

## Autenticación y roles

La WebUI requiere iniciar sesión. Hay 3 roles:

| Rol         | Puede ver todas las páginas de consulta | Consola SQL (solo lectura) | Gestionar subusuarios |
|-------------|:---:|:---:|:---:|
| `viewer`    | ✅ | ❌ | ❌ |
| `moderator` | ✅ | ✅ | ❌ |
| `admin`     | ✅ | ✅ | ✅ |

En el primer arranque se crea automáticamente un usuario `admin`. Si no
definiste `ADMIN_PASSWORD` como variable de entorno, se genera una
contraseña aleatoria que se imprime **una sola vez** en los logs del
servidor — revísalos justo después del primer despliegue y cámbiala
desde *Configuración → Cambiar contraseña*.

## Consola SQL

`/sql` permite ejecutar **solo** `SELECT` / `WITH` / `SHOW` / `EXPLAIN` /
`DESCRIBE`. Cualquier sentencia de escritura o DDL (`INSERT`, `UPDATE`,
`DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, etc.) se rechaza antes
de llegar a MySQL. Esto es intencional: es una consola de *consulta*
para investigar (griefs, robos, actividad por jugador/coordenadas/fecha),
no un cliente SQL genérico — así ningún query mal escrito puede dañar
`LOGDATA`. Incluye historial personal y consultas guardadas (con varios
ejemplos precargados: grief, robos, actividad por coordenadas/fechas).

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

- **Pool de conexiones** (`DBUtils.PooledDB`) en vez de abrir una conexión
  TCP nueva por request.
- **Caché en memoria con TTL** para agregados costosos (conteos, distribución
  por tipo/mundo/hora, series temporales, heatmap) usados en Dashboard y Estadísticas.
- **Exportación en streaming** (CSV, XLSX y JSON) con `SSCursor`, sin cargar
  todo el resultado en memoria del servidor.
- **Paginación por página** en "Registros", ordenable por cualquier columna
  de una whitelist explícita (evita inyección SQL vía `ORDER BY`). El salto
  de página está acotado (`MAX_JUMPABLE_PAGE`) como salvaguarda.
- **Consola SQL de solo lectura** con límite de filas y `MAX_EXECUTION_TIME`
  por sesión, para que una consulta pesada no bloquee al resto de usuarios.
- **Índices recomendados** en `sql/indexes.sql` (no se aplican automáticamente:
  alterar una tabla de millones de filas es una decisión operativa que debe
  tomar un administrador en una ventana de mantenimiento).

## Columnas de `LOGDATA`

`id_pk, uuid, id, name, pos_x, pos_y, pos_z, world, obj_id, obj_name, time, type, data, status`

`time` es un Unix timestamp. No se usan columnas fuera de esta lista.

Las tablas `webui_users`, `webui_saved_queries`, `webui_query_history`,
`webui_saved_filters`, `webui_favorite_locations`, `webui_alert_rules` y
`webui_appearance_settings` son metadata propia de la aplicación (usuarios,
consultas e historial, favoritos, reglas de alertas, preferencias visuales),
completamente independientes de `LOGDATA`. Se crean solas en el primer
arranque (`services/admin_db.py`), incluyendo migraciones de columnas nuevas
sobre tablas que ya existieran de una instalación previa.

## Novedades de la mejora integral

- **Bloques**: corregido el bug de raíz que mostraba "Desconocido" (agrupación
  por `COALESCE(NULLIF(obj_name,''), obj_id)`), más un modal de detalle por
  bloque con estadísticas completas.
- **Dashboard**: widgets en vivo (actividad reciente, jugadores activos,
  bloques más modificados, explosiones, muertes, eventos importantes),
  auto-refresco cada 60s.
- **Jugadores**: ficha enriquecida con gráficos de actividad diaria/por hora,
  rankings de bloques/entidades y zonas frecuentes.
- **Coordenadas**: lugares favoritos guardados por usuario.
- **Registros**: búsqueda instantánea, filtros recientes, acciones rápidas de
  coordenadas (copiar / buscar por radio).
- **Consola SQL**: editor con resaltado de sintaxis y autocompletado
  (CodeMirror), categorías en consultas guardadas, copiar consulta.
- **Alertas**: reglas de vigilancia con vista previa contra datos reales;
  infraestructura de envío a Discord preparada (no activada aún).
- **Apariencia**: tema, color, fondo, tipografía, densidad y animaciones
  personalizables y guardados por usuario en la base de datos.
- **Modo Investigación**: informe cronológico por jugador y/o zona, sin SQL.
