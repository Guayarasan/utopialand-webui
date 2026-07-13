"""Exportación de registros filtrados a CSV, en streaming."""

import csv
import io

from config import Config
from database import stream_rows
from services.query_builder import TABLE, Filters, build_where_sql

CSV_COLUMNS = [
    "id_pk", "uuid", "id", "name", "pos_x", "pos_y", "pos_z", "world",
    "obj_id", "obj_name", "time", "type", "data", "status",
]


def stream_records_csv(args):
    """
    Genera un CSV fila por fila usando un cursor de servidor (SSCursor),
    de forma que exportar cientos de miles de registros no cargue todo
    el resultado en memoria ni bloquee el worker de Flask.
    """
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

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(CSV_COLUMNS)
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)

        count = 0
        for row in stream_rows(sql, params + [Config.EXPORT_MAX_ROWS]):
            writer.writerow([row.get(col) for col in CSV_COLUMNS])
            count += 1
            if count % 500 == 0:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)

        yield buffer.getvalue()

    return generate()
