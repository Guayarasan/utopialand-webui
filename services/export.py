"""Exportación de registros filtrados a CSV, Excel (XLSX) o JSON, en streaming."""

import io
import json

from config import Config
from database import stream_rows
from services.query_builder import TABLE, Filters, build_where_sql

CSV_COLUMNS = [
    "id_pk", "uuid", "id", "name", "pos_x", "pos_y", "pos_z", "world",
    "obj_id", "obj_name", "time", "type", "data", "status",
]


def _build_export_query(args):
    filters = Filters(args)
    clauses, params = filters.where()
    where_sql = build_where_sql(clauses)
    sql = f"""
        SELECT {', '.join(CSV_COLUMNS)}
        FROM {TABLE}
        {where_sql}
        ORDER BY time DESC, id_pk DESC
        LIMIT %s
    """
    return sql, params + [Config.EXPORT_MAX_ROWS]


def stream_records_csv(args):
    """
    Genera un CSV fila por fila usando un cursor de servidor (SSCursor),
    de forma que exportar cientos de miles de registros no cargue todo
    el resultado en memoria ni bloquee el worker de Flask.
    """
    import csv

    sql, params = _build_export_query(args)

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_COLUMNS)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        count = 0
        for row in stream_rows(sql, params):
            writer.writerow([row.get(col) for col in CSV_COLUMNS])
            count += 1
            if count % 500 == 0:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        yield buffer.getvalue()

    return generate()


def stream_records_json(args):
    """JSON en streaming (array de objetos), sin cargar todo en memoria."""
    sql, params = _build_export_query(args)

    def generate():
        yield "["
        first = True
        for row in stream_rows(sql, params):
            chunk = json.dumps(row, default=str, ensure_ascii=False)
            yield (chunk if first else "," + chunk)
            first = False
        yield "]"

    return generate()


def build_records_xlsx(args):
    """
    Genera un .xlsx en memoria usando el modo write_only de openpyxl
    (streaming interno de la librería), apto para exportaciones grandes
    sin disparar el uso de memoria del proceso.
    """
    from openpyxl import Workbook

    sql, params = _build_export_query(args)

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Registros")
    sheet.append(CSV_COLUMNS)

    for row in stream_rows(sql, params):
        sheet.append([_xlsx_safe(row.get(col)) for col in CSV_COLUMNS])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer


def _xlsx_safe(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return value
