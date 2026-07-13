-- ============================================================================
-- Índices recomendados para LOGDATA (Utopialand WebUI / Tianyan)
-- ============================================================================
-- Este script NO se ejecuta automáticamente. En una tabla con millones de
-- filas, crear índices puede tardar minutos y consumir I/O importante, así
-- que es una decisión que debe tomar un administrador conscientemente,
-- idealmente en una ventana de bajo tráfico.
--
-- Ejecutar manualmente contra la base de datos de Aiven, por ejemplo con:
--   mysql -h <host> -P <port> -u <user> -p <database> < sql/indexes.sql
-- ============================================================================

-- Paginación / orden principal de "Registros" (time DESC, id_pk DESC).
ALTER TABLE LOGDATA ADD INDEX idx_logdata_time_id (time, id_pk);

-- Búsqueda y agregados por jugador.
ALTER TABLE LOGDATA ADD INDEX idx_logdata_name (name);

-- Búsqueda y agregados por bloque/objeto.
ALTER TABLE LOGDATA ADD INDEX idx_logdata_objname (obj_name);

-- Filtro por tipo de evento (usado en casi todas las páginas).
ALTER TABLE LOGDATA ADD INDEX idx_logdata_type (type);

-- Filtro por mundo.
ALTER TABLE LOGDATA ADD INDEX idx_logdata_world (world);

-- Búsqueda por coordenadas (página "Coordenadas"): bounding box sobre
-- pos_x/pos_y/pos_z. El orden de columnas importa: world primero porque
-- suele filtrarse siempre, luego pos_x que es la que más acota el rango.
ALTER TABLE LOGDATA ADD INDEX idx_logdata_world_pos (world, pos_x, pos_y, pos_z);
