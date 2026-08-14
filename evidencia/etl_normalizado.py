import os

import psycopg2
from dotenv import load_dotenv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROYECTO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
load_dotenv(os.path.join(_PROYECTO_DIR, ".env"))

# Igual que en la app: primero probamos el .env y si falla la auth usamos
# las de respaldo para que el ETL no truene a mitad de camino.
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# Respaldo hardcodeado por si el .env quedo con credenciales viejas
# (spoiler: siempre queda con credenciales viejas).
_FALLBACK = {
    "host": "aws-1-us-west-2.pooler.supabase.com",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres.xncfnyuaegllaubvdrqi",
    "password": "vU9FWYSIawOrYZ3s",
}

OUTPUT_DIR = SCRIPT_DIR
SQL_FILE = os.path.join(_PROYECTO_DIR, "sql", "normalizacion_3fn.sql")


def get_conn():
    try:
        return psycopg2.connect(**DB_CONFIG)
    except psycopg2.OperationalError as e:
        print(f"  [aviso] Conexion con .env fallo ({e.__class__.__name__}); usando respaldo.")
        return psycopg2.connect(**_FALLBACK)


def log(msg, lines=None):
    print(msg)
    if lines is not None:
        lines.append(msg)


def save_evidence(filename, lines):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  -> Guardado: {filename}")


def analisis_redundancia(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 1: ANALISIS DE REDUNDANCIA - SILVER", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()

    # Columnas repetidas en las tablas de hechos que ya viven en el maestro.
    redundantes = [
        ("solicitudes.artdes", "SELECT COUNT(*) FROM silver.solicitudes s JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE s.artdes = m.artdes"),
        ("solicitudes.artmed", "SELECT COUNT(*) FROM silver.solicitudes s JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE s.artmed = m.artmed"),
        ("solicitudes.artgrinv", "SELECT COUNT(*) FROM silver.solicitudes s JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE s.artgrinv = m.artgrinv"),
        ("recepcion.artdes", "SELECT COUNT(*) FROM silver.recepcion r JOIN silver.maestro_articulos m ON r.artcitem=m.artcitem WHERE r.artdes = m.artdes"),
        ("recepcion.artmed", "SELECT COUNT(*) FROM silver.recepcion r JOIN silver.maestro_articulos m ON r.artcitem=m.artcitem WHERE r.artmed = m.artmed"),
        ("recepcion.artgrinv", "SELECT COUNT(*) FROM silver.recepcion r JOIN silver.maestro_articulos m ON r.artcitem=m.artcitem WHERE r.artgrinv = m.artgrinv"),
        ("articulos.artdes", "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artdes = m.artdes"),
        ("articulos.artmed", "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artmed = m.artmed"),
        ("articulos.artgrinv", "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artgrinv = m.artgrinv"),
    ]
    totales = {
        "solicitudes": "SELECT COUNT(*) FROM silver.solicitudes",
        "recepcion": "SELECT COUNT(*) FROM silver.recepcion",
        "articulos": "SELECT COUNT(*) FROM silver.articulos",
    }

    log("\n  Columnas de catalogo repetidas en los hechos:", lines)
    for nombre, q in redundantes:
        cur.execute(q)
        coinciden = cur.fetchone()[0]
        tabla = nombre.split(".")[0]
        cur.execute(totales[tabla])
        total = cur.fetchone()[0]
        pct = coinciden * 100.0 / total if total else 0
        log(f"    {nombre:<25s} {coinciden:>8,} coinciden  ({pct:5.1f}%)  de {total:,}", lines)

    log("\n  Discrepancias con el maestro (dato repetido pero distinto):", lines)
    discrepancias = [
        ("articulos.artdes != maestro.artdes",
         "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artdes IS DISTINCT FROM m.artdes"),
        ("articulos.artfusal != maestro.artfusal",
         "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artfusal IS DISTINCT FROM m.artfusal"),
        ("articulos.artfuent != maestro.artfuent",
         "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artfuent IS DISTINCT FROM m.artfuent"),
        ("articulos.artcoum1 != maestro.artcoum1",
         "SELECT COUNT(*) FROM silver.articulos a JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE a.artcoum1 IS DISTINCT FROM m.artcoum1"),
    ]
    for nombre, q in discrepancias:
        cur.execute(q)
        log(f"    {nombre:<40s} {cur.fetchone()[0]:>6,}", lines)

    # solpro: en recepcion y solicitudes es un codigo de proveedor, no el nombre.
    log("\n  solpro en los hechos (codigo que referencia a proveedores):", lines)
    cur.execute("SELECT COUNT(DISTINCT solpro) FROM silver.recepcion")
    log(f"    recepcion: {cur.fetchone()[0]} codigos distintos", lines)
    cur.execute("SELECT COUNT(DISTINCT solpro) FROM silver.solicitudes")
    log(f"    solicitudes: {cur.fetchone()[0]} codigos distintos", lines)
    cur.execute("SELECT COUNT(DISTINCT acrecodi) FROM silver.proveedores")
    log(f"    proveedores (catalogo): {cur.fetchone()[0]} codigos", lines)

    log("\n  Conclusión: artdes/artmed/artgrinv repiten el catalogo en 3 hechos", lines)
    log("  y se eliminan en 3FN; solpro se convierte en FK a proveedores.", lines)

    cur.close()
    save_evidence("04_analisis_redundancia.txt", lines)


def analisis_integridad(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 2: ANALISIS DE INTEGRIDAD REFERENCIAL - SILVER", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()
    checks = [
        ("recepcion.solnum sin pedido en solicitudes", None,
         "SELECT COUNT(*) FROM silver.recepcion r LEFT JOIN silver.solicitudes s ON r.solnum=s.solnum WHERE s.solnum IS NULL"),
        ("recepcion.artcitem fuera de maestro_articulos", None,
         "SELECT COUNT(*) FROM silver.recepcion r LEFT JOIN silver.maestro_articulos m ON r.artcitem=m.artcitem WHERE m.artcitem IS NULL"),
        ("solicitudes.artcitem fuera de maestro_articulos", None,
         "SELECT COUNT(*) FROM silver.solicitudes s LEFT JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE m.artcitem IS NULL"),
        ("articulos.artcitem fuera de maestro_articulos", None,
         "SELECT COUNT(*) FROM silver.articulos a LEFT JOIN silver.maestro_articulos m ON a.artcitem=m.artcitem WHERE m.artcitem IS NULL"),
        ("solicitudes.solpro fuera de proveedores", None,
         "SELECT COUNT(*) FROM silver.solicitudes s LEFT JOIN silver.proveedores p ON s.solpro=p.acrecodi WHERE p.acrecodi IS NULL"),
        ("recepcion.solpro fuera de proveedores", None,
         "SELECT COUNT(*) FROM silver.recepcion r LEFT JOIN silver.proveedores p ON r.solpro=p.acrecodi WHERE p.acrecodi IS NULL"),
        ("maestro_articulos.artgrinv fuera de grupos", None,
         "SELECT COUNT(*) FROM silver.maestro_articulos m LEFT JOIN silver.grupos g ON m.artgrinv=g.artgrinv WHERE g.artgrinv IS NULL"),
        ("duplicados recepcion (solnum,artcitem,nrdcac)", "duplicados",
         "SELECT COUNT(*) FROM (SELECT solnum,artcitem,nrdcac FROM silver.recepcion GROUP BY solnum,artcitem,nrdcac HAVING COUNT(*)>1) t"),
        ("solicitudes.solnum unico (potencial PK)", "ok",
         "SELECT COUNT(*) - COUNT(DISTINCT solnum) FROM silver.solicitudes"),
    ]

    for nombre, tipo, q in checks:
        cur.execute(q)
        valor = cur.fetchone()[0]
        marca = "  ***" if (tipo is None and valor > 0) or (tipo == "duplicados" and valor > 0) else ""
        if tipo == "ok":
            marca = "  OK" if valor == 0 else "  ***"
        log(f"  {nombre}: {valor:,}{marca}", lines)

    cur.execute("SELECT COUNT(DISTINCT s.artcitem) FROM silver.solicitudes s LEFT JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE m.artcitem IS NULL")
    log(f"\n  Articulos distintos fuera de catalogo en solicitudes: {cur.fetchone()[0]}", lines)

    cur.execute("SELECT DISTINCT s.artcitem FROM silver.solicitudes s LEFT JOIN silver.maestro_articulos m ON s.artcitem=m.artcitem WHERE m.artcitem IS NULL ORDER BY 1 LIMIT 8")
    log("  Ejemplos de articulos fuera de catalogo:", lines)
    for r in cur.fetchall():
        log(f"    {r[0]}", lines)

    cur.execute("SELECT DISTINCT m.artgrinv FROM silver.maestro_articulos m LEFT JOIN silver.grupos g ON m.artgrinv=g.artgrinv WHERE g.artgrinv IS NULL ORDER BY 1")
    log("  Grupos referenciados pero inexistentes en catalogo:", lines)
    for r in cur.fetchall():
        log(f"    {r[0]}", lines)

    log("\n  Estos casos se conservan en 3FN como FK con valor NULL", lines)
    log("  para no perder filas (la data vale mas que el orgullo).", lines)

    cur.close()
    save_evidence("05_integridad_referencial.txt", lines)


def cargar_normalizado(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 3: CARGA DEL ESQUEMA NORMALIZADO (3FN)", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()

    log(f"\n[0] Ejecutando sql/normalizacion_3fn.sql ...", lines)
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    log("  Script SQL ejecutado sin errores.", lines)

    log("", lines)
    log("-" * 70, lines)
    log("  Conteos en normalizado", lines)
    log("-" * 70, lines)
    for t in ["grupos", "proveedores", "maestro_articulos", "fact_solicitudes", "fact_recepcion", "fact_stock"]:
        cur.execute(f'SELECT COUNT(*) FROM normalizado."{t}"')
        log(f"  normalizado.{t:<22s} -> {cur.fetchone()[0]:>8,}", lines)

    log("", lines)
    log("-" * 70, lines)
    log("  Orfanos restantes tras la normalizacion (esperados: los ya vistos)", lines)
    log("-" * 70, lines)
    checks = [
        ("fact_solicitudes.artcitem NULL", "SELECT COUNT(*) FROM normalizado.fact_solicitudes WHERE artcitem IS NULL"),
        ("fact_solicitudes.solpro NULL", "SELECT COUNT(*) FROM normalizado.fact_solicitudes WHERE solpro IS NULL"),
        ("fact_recepcion.solnum NULL", "SELECT COUNT(*) FROM normalizado.fact_recepcion WHERE solnum IS NULL"),
        ("fact_recepcion.artcitem NULL", "SELECT COUNT(*) FROM normalizado.fact_recepcion WHERE artcitem IS NULL"),
        ("maestro_articulos.artgrinv NULL", "SELECT COUNT(*) FROM normalizado.maestro_articulos WHERE artgrinv IS NULL"),
    ]
    for nombre, q in checks:
        cur.execute(q)
        log(f"  {nombre:<42s} -> {cur.fetchone()[0]:>6,}", lines)

    cur.close()
    save_evidence("07_carga_normalizado.txt", lines)


def verificar_normalizado(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 4: VERIFICACION FINAL - BRONZE / SILVER / NORMALIZADO", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()

    mapeo = [
        ("grupos", "grupos"),
        ("proveedores", "proveedores"),
        ("maestro_articulos", "maestro_articulos"),
        ("solicitudes", "fact_solicitudes"),
        ("recepcion", "fact_recepcion"),
        ("articulos", "fact_stock"),
    ]
    log(f"\n  {'Silver':<22s} {'Normalizado':<22s} {'Bronze':>10s} {'Silver':>10s} {'Normaliz.':>10s}", lines)
    log(f"  {'-'*22} {'-'*22} {'-'*10} {'-'*10} {'-'*10}", lines)
    for silver_t, normal_t in mapeo:
        cur.execute(f'SELECT COUNT(*) FROM bronze."{silver_t}"')
        b = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM silver."{silver_t}"')
        s = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM normalizado."{normal_t}"')
        n = cur.fetchone()[0]
        log(f"  {silver_t:<22s} {normal_t:<22s} {b:>10,} {s:>10,} {n:>10,}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  TIPOS DE DATOS EN NORMALIZADO", lines)
    log("-" * 70, lines)
    for t in ["grupos", "proveedores", "maestro_articulos", "fact_solicitudes", "fact_recepcion", "fact_stock"]:
        cur.execute(f"""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'normalizado' AND table_name = '{t}' ORDER BY ordinal_position
        """)
        log(f"\n  normalizado.{t}:", lines)
        for c in cur.fetchall():
            log(f"    {c[0]:<22s} -> {c[1]}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  MUESTRAS DE DATOS", lines)
    log("-" * 70, lines)
    for t in ["fact_solicitudes", "fact_recepcion", "fact_stock", "maestro_articulos", "proveedores", "grupos"]:
        cur.execute(f"SELECT * FROM normalizado.{t} LIMIT 3")
        cols = [d[0] for d in cur.description]
        log(f"\n  normalizado.{t}:", lines)
        log(f"    Columnas: {cols}", lines)
        for r in cur.fetchall():
            log(f"    {r}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  CHECK: consulta analitica sobre el esquema normalizado", lines)
    log("-" * 70, lines)
    cur.execute("""
        SELECT DATE_TRUNC('month', f.nrcfec)::date AS mes,
               COUNT(DISTINCT f.solnum) AS pedidos,
               SUM(f.nrdcac) AS recibido,
               AVG(m.artcosu1) AS costo_promedio
        FROM normalizado.fact_recepcion f
        JOIN normalizado.maestro_articulos m ON f.artcitem = m.artcitem
        WHERE f.nrcfec IS NOT NULL
        GROUP BY 1 ORDER BY 1 DESC LIMIT 5
    """)
    for r in cur.fetchall():
        log(f"    mes={r[0]} pedidos={r[1]} recibido={r[2]} costo_promedio={r[3]:.2f}", lines)

    cur.close()
    save_evidence("06_resultados_normalizado.txt", lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  ETL NORMALIZACION 3FN: SILVER -> NORMALIZADO")
    print("  Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    conn = get_conn()

    print("\n>>> FASE 1: Analisis de redundancia...")
    analisis_redundancia(conn)

    print("\n>>> FASE 2: Analisis de integridad referencial...")
    analisis_integridad(conn)

    print("\n>>> FASE 3: Carga del esquema normalizado...")
    cargar_normalizado(conn)

    print("\n>>> FASE 4: Verificacion final...")
    verificar_normalizado(conn)

    conn.close()

    print("\n" + "=" * 70)
    print("  ETL COMPLETADO:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Archivos generados en:", OUTPUT_DIR)
    print("=" * 70)
