import os

import psycopg2
from dotenv import load_dotenv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROYECTO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
load_dotenv(os.path.join(_PROYECTO_DIR, ".env"))

# Igual que los otros ETL: las credenciales viven en .env y listo.
# El respaldo hardcodeado se jubilo despues del susto con git.
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

OUTPUT_DIR = SCRIPT_DIR
SQL_FILE = os.path.join(_PROYECTO_DIR, "sql", "gold.sql")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def log(msg, lines=None):
    print(msg)
    if lines is not None:
        lines.append(msg)


def save_evidence(filename, lines):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  -> Guardado: {filename}")


# La consulta que reproduce la demanda mensual desde silver. La razon de
# leer de silver y no de normalizado ya quedo documentada en sql/gold.sql
# (spoiler: la normalizacion nos vuela los huerfanos y este conteo los
# necesita vivos). Ventanas y CTEs nomás, que las correlacionadas nos
# dieron timeout y eso no se repite.
_DEMANDA_REPRO = """
WITH stock AS (
    SELECT artcitem,
           DATE_TRUNC('month', nrcfec)::date AS mes,
           artstock,
           ROW_NUMBER() OVER (PARTITION BY artcitem, DATE_TRUNC('month', nrcfec)
                              ORDER BY nrcfec DESC, nrcnum DESC) AS rn
    FROM silver.recepcion
    WHERE nrcfec IS NOT NULL AND artstock IS NOT NULL
),
agrupado AS (
    SELECT r.artcitem,
           r.artgrinv,
           g.nombre AS grupo_nombre,
           DATE_TRUNC('month', r.nrcfec)::date AS mes,
           SUM(r.solcan) AS cantidad,
           COUNT(DISTINCT r.solnum) AS frecuencia,
           AVG(r.solpre) AS precio
    FROM silver.recepcion r
    LEFT JOIN silver.grupos g ON r.artgrinv = g.artgrinv
    WHERE r.nrcfec IS NOT NULL
    GROUP BY r.artcitem, r.artgrinv, g.nombre, DATE_TRUNC('month', r.nrcfec)
),
repro AS (
    SELECT g.artcitem, g.artgrinv, g.grupo_nombre, g.mes,
           g.cantidad, g.frecuencia, g.precio, s.artstock AS ultimo_stock
    FROM agrupado g
    LEFT JOIN stock s ON s.artcitem = g.artcitem AND s.mes = g.mes AND s.rn = 1
)
SELECT 'gold_total' AS chk, COUNT(*) FROM gold.prediccion_demanda_mensual
UNION ALL SELECT 'repro_total', COUNT(*) FROM repro
UNION ALL SELECT 'sin_key', COUNT(*) FROM gold.prediccion_demanda_mensual gd
    LEFT JOIN repro r ON r.artcitem = gd.artcitem
        AND r.mes = DATE_TRUNC('month', gd.periodo_mes)::date
    WHERE r.artcitem IS NULL
UNION ALL SELECT 'extras', COUNT(*) FROM repro r
    LEFT JOIN gold.prediccion_demanda_mensual gd ON gd.artcitem = r.artcitem
        AND DATE_TRUNC('month', gd.periodo_mes)::date = r.mes
    WHERE gd.artcitem IS NULL
UNION ALL SELECT 'dif_total', COUNT(*) FROM repro r
    JOIN gold.prediccion_demanda_mensual gd ON gd.artcitem = r.artcitem
        AND DATE_TRUNC('month', gd.periodo_mes)::date = r.mes
    WHERE gd.artgrinv IS DISTINCT FROM r.artgrinv
       OR gd.grupo_nombre IS DISTINCT FROM r.grupo_nombre
       OR gd.cantidad_total_despachada IS DISTINCT FROM r.cantidad
       OR gd.frecuencia_pedidos IS DISTINCT FROM r.frecuencia
       OR gd.precio_promedio_pactado IS DISTINCT FROM r.precio
       OR gd.ultimo_stock_registrado IS DISTINCT FROM r.ultimo_stock
"""

_METRICAS_REPRO = """
SELECT COUNT(*),
       COUNT(*) FILTER (
           WHERE gp.proveedor_id IS DISTINCT FROM a.acrecodi
              OR gp.total_atenciones IS DISTINCT FROM a.total
              OR gp.lead_time_promedio_dias IS DISTINCT FROM a.lead
              OR gp.desviacion_lead_time IS DISTINCT FROM a.dev
              OR gp.volumen_total_suministrado IS DISTINCT FROM a.vol
       )
FROM (
    SELECT p.acrecodi,
           COUNT(*) AS total,
           AVG(f.nrcfec - f.solfec) AS lead,
           STDDEV(f.nrcfec - f.solfec) AS dev,
           SUM(f.solcan) AS vol
    FROM normalizado.fact_recepcion f
    JOIN normalizado.proveedores p ON f.solpro = p.acrecodi
    WHERE f.nrcfec IS NOT NULL AND f.solfec IS NOT NULL
    GROUP BY p.acrecodi
) a
RIGHT JOIN gold.metricas_prediccion_proveedor gp ON gp.proveedor_id = a.acrecodi
"""


def fase1_reproducibilidad(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 1: REPRODUCIBILIDAD - GOLD ACTUAL vs CONSULTAS", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("  (solo lectura, las tablas gold no se tocan en esta fase)", lines)
    log("=" * 70, lines)

    cur = conn.cursor()
    cur.execute("SET statement_timeout = 180000")

    log("\n  [metricas_prediccion_proveedor]  fuente: normalizado", lines)
    cur.execute("SELECT COUNT(*) FROM gold.metricas_prediccion_proveedor")
    gold_met = cur.fetchone()[0]
    cur.execute(_METRICAS_REPRO)
    comp, diffs = cur.fetchone()
    log(f"    filas en gold actual : {gold_met:,}", lines)
    log(f"    filas repro normalizado: {comp:,}", lines)
    log(f"    filas con diferencia : {diffs:,}", lines)
    log("    resultado: " + ("REPRODUCE EXACTO" if gold_met == comp == 383 and diffs == 0 else "NO reproduce"), lines)

    log("\n  [prediccion_demanda_mensual]  fuente: silver.recepcion", lines)
    log("    (ironia documentada en sql/gold.sql: la normalizacion pierde", lines)
    log("     los huerfanos y este conteo los necesita, asi que silver)", lines)
    cur.execute(_DEMANDA_REPRO)
    chk = {r[0]: r[1] for r in cur.fetchall()}
    for k in ["gold_total", "repro_total", "sin_key", "extras", "dif_total"]:
        log(f"    {k:<12s}: {chk.get(k, 0):,}", lines)
    ok = (chk.get("gold_total") == chk.get("repro_total") == 33010
          and chk.get("sin_key") == 0 and chk.get("extras") == 0
          and chk.get("dif_total") == 0)
    log("    resultado: " + ("REPRODUCE EXACTO" if ok else "NO reproduce"), lines)

    log("\n  Resumen: si ambos dicen REPRODUCE EXACTO, regenerar gold", lines)
    log("  no cambia ni un numero y podemos borrar y recrear tranquilos.", lines)

    cur.close()
    save_evidence("08_reproducibilidad_gold.txt", lines)


def fase2_carga(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 2: CARGA DEL ESQUEMA GOLD", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()
    cur.execute("SET statement_timeout = 180000")

    log(f"\n[0] Ejecutando sql/gold.sql (DROP SCHEMA gold CASCADE incluido) ...", lines)
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    log("  Script SQL ejecutado sin errores.", lines)

    log("", lines)
    log("-" * 70, lines)
    log("  Conteos en gold tras la carga", lines)
    log("-" * 70, lines)
    cur.execute("SELECT COUNT(*) FROM gold.metricas_prediccion_proveedor")
    met = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gold.prediccion_demanda_mensual")
    dem = cur.fetchone()[0]
    log(f"  gold.metricas_prediccion_proveedor -> {met:,}", lines)
    log(f"  gold.prediccion_demanda_mensual    -> {dem:,}", lines)

    cur.close()
    save_evidence("09_resultados_gold.txt", lines)
    return met, dem


def fase3_verificacion(conn, met, dem):
    lines = []
    log("=" * 70, lines)
    log("  FASE 3: VERIFICACION FINAL - GOLD", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()
    cur.execute("SET statement_timeout = 180000")

    log("\n", lines)
    log("-" * 70, lines)
    log("  CONTEO FINAL vs ESPERADO", lines)
    log("-" * 70, lines)
    log(f"  metricas_prediccion_proveedor: {met:,}  (esperado: 383)  {'OK' if met == 383 else '*** NO COINCIDE'}", lines)
    log(f"  prediccion_demanda_mensual   : {dem:,}  (esperado: 33,010)  {'OK' if dem == 33010 else '*** NO COINCIDE'}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  TIPOS DE DATOS EN GOLD", lines)
    log("-" * 70, lines)
    for t in ["metricas_prediccion_proveedor", "prediccion_demanda_mensual"]:
        cur.execute(f"""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'gold' AND table_name = '{t}' ORDER BY ordinal_position
        """)
        log(f"\n  gold.{t}:", lines)
        for c in cur.fetchall():
            log(f"    {c[0]:<26s} -> {c[1]}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  MUESTRAS DE DATOS", lines)
    log("-" * 70, lines)
    cur.execute("SELECT * FROM gold.metricas_prediccion_proveedor LIMIT 3")
    cols = [d[0] for d in cur.description]
    log(f"\n  gold.metricas_prediccion_proveedor:", lines)
    log(f"    Columnas: {cols}", lines)
    for r in cur.fetchall():
        log(f"    {r}", lines)

    cur.execute("""
        SELECT * FROM gold.prediccion_demanda_mensual
        WHERE artcitem NOT IN (SELECT artcitem FROM silver.maestro_articulos)
        LIMIT 3
    """)
    log(f"\n  gold.prediccion_demanda_mensual (el huerfano del catalogo):", lines)
    for r in cur.fetchall():
        log(f"    {r}", lines)

    cur.execute("SELECT * FROM gold.prediccion_demanda_mensual LIMIT 3")
    cols = [d[0] for d in cur.description]
    log(f"\n  gold.prediccion_demanda_mensual (muestra general):", lines)
    log(f"    Columnas: {cols}", lines)
    for r in cur.fetchall():
        log(f"    {r}", lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  REPRODUCIBILIDAD POST-CARGA (los mismos numeros que la fase 1)", lines)
    log("-" * 70, lines)
    cur.execute(_DEMANDA_REPRO)
    chk = {r[0]: r[1] for r in cur.fetchall()}
    for k in ["gold_total", "repro_total", "sin_key", "extras", "dif_total"]:
        log(f"    {k:<12s}: {chk.get(k, 0):,}", lines)
    ok_dem = (chk.get("gold_total") == chk.get("repro_total") == 33010
              and chk.get("sin_key") == 0 and chk.get("extras") == 0
              and chk.get("dif_total") == 0)
    log("    resultado: " + ("REPRODUCE EXACTO" if ok_dem else "*** NO reproduce"), lines)

    cur.execute(_METRICAS_REPRO)
    comp, diffs = cur.fetchone()
    log(f"    metricas: repro={comp:,} diffs={diffs:,} -> "
        + ("REPRODUCE EXACTO" if comp == 383 and diffs == 0 else "*** NO reproduce"), lines)

    log("\n", lines)
    log("-" * 70, lines)
    log("  CHECK: consulta analitica sobre gold", lines)
    log("-" * 70, lines)
    cur.execute("""
        SELECT DATE_TRUNC('month', periodo_mes)::date AS mes,
               COUNT(DISTINCT artcitem) AS articulos,
               SUM(cantidad_total_despachada) AS demanda_total
        FROM gold.prediccion_demanda_mensual
        GROUP BY 1 ORDER BY 1 DESC LIMIT 5
    """)
    for r in cur.fetchall():
        log(f"    mes={r[0]} articulos={r[1]} demanda_total={r[2]}", lines)

    cur.close()
    save_evidence("09_resultados_gold.txt", lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  ETL CAPA GOLD: NORMALIZADO/SILVER -> GOLD")
    print("  Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    conn = get_conn()

    print("\n>>> FASE 1: Reproducibilidad (gold actual vs consultas)...")
    fase1_reproducibilidad(conn)

    print("\n>>> FASE 2: Carga del esquema gold...")
    met, dem = fase2_carga(conn)

    print("\n>>> FASE 3: Verificacion final...")
    fase3_verificacion(conn, met, dem)

    conn.close()

    print("\n" + "=" * 70)
    print("  ETL COMPLETADO:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Archivos generados en:", OUTPUT_DIR)
    print("=" * 70)
