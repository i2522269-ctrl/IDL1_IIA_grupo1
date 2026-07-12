import os
import json
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv('SUPABASE_DB_URL')
if not DB_URL:
    raise SystemExit('Falta SUPABASE_DB_URL en .env')

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
DATA_DIR = os.path.join(PARENT_DIR, 'data')

BATCH_SIZE = 500


def resolve_file(name):
    candidates = [
        os.path.join(BASE_DIR, name),
        os.path.join(PARENT_DIR, name),
        os.path.join(DATA_DIR, name),
        os.path.join(PARENT_DIR, 'IDL_1', name),
        os.path.join(PARENT_DIR, 'IDL1_IIA_grupo1', name),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None

FILES = {
    'grupos_sheet1': resolve_file('grupos.csv'),
    'solicitudes_sheet1': resolve_file('Solicitudes_completo_ANONIMIZADO.csv'),
    'recepcion_sheet1': resolve_file('Recepcion_ANONIMIZADO.csv'),
    'maestro_articulos_sheet1': resolve_file('Maestro_Articulos_ANONIMIZADO.csv'),
    'proveedores_sheet1': resolve_file('Proveedores_ANONIMIZADO.csv'),
    'articulos_sheet1': resolve_file('Articulos_ANONIMIZADO.csv'),
}

INSERT_SQL = "INSERT INTO {} (source_file, row_number, raw_data) VALUES (%s, %s, %s::jsonb)"


def load_sheet(table_sql, file_path):
    if not os.path.exists(file_path):
        print(f'No se encontro {file_path}')
        return 0

    df = pd.read_csv(file_path)
    print(f'Procesando {table_sql} desde {os.path.basename(file_path)} con {len(df)} filas')

    source_file = os.path.basename(file_path)
    sql = INSERT_SQL.format(table_sql)
    total = 0

    batch = []
    for idx, row in df.iterrows():
        raw_json = json.dumps(row.to_dict(), ensure_ascii=False, default=str)
        row_number = int(idx) + 1
        batch.append((source_file, row_number, raw_json))

        if len(batch) >= BATCH_SIZE:
            psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
            total += len(batch)
            batch = []

    if batch:
        psycopg2.extras.execute_batch(cur, sql, batch, page_size=BATCH_SIZE)
        total += len(batch)

    return total


for table_sql, file_path in FILES.items():
    if not file_path:
        print(f'{table_sql}: no se encontro el archivo')
        continue
    try:
        count = load_sheet(table_sql, file_path)
        print(f'{table_sql}: {count} filas insertadas')
    except Exception as exc:
        print(f'Error en {table_sql}: {exc}')

cur.close()
conn.close()
