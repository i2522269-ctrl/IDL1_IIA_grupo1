import psycopg2
import os
from datetime import datetime

DB_CONFIG = {
    "host": "aws-1-us-west-2.pooler.supabase.com",
    "port": 5432,
    "dbname": "postgres",
    "user": "postgres.xncfnyuaegllaubvdrqi",
    "password": "buafaugwwcqsbrwaycro",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = SCRIPT_DIR

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

def parse_date(val):
    if not val or val.strip() == "":
        return None
    val = val.strip()
    if len(val) == 6 and val.isdigit():
        try:
            return datetime.strptime(val, "%y%m%d").date()
        except ValueError:
            return None
    if len(val) == 10 and val[4] == "-" and val[7] == "-":
        try:
            return datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None

def parse_numeric(val):
    if not val or val.strip() == "":
        return None
    cleaned = "".join(c for c in val.strip() if c.isdigit() or c in ".-")
    if not cleaned or cleaned in (".", "-"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_int(val):
    if not val or val.strip() == "":
        return None
    cleaned = "".join(c for c in val.strip() if c.isdigit() or c == "-")
    if not cleaned:
        return None
    try:
        return int(float(cleaned))
    except ValueError:
        return None


def analisis_calidad(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 1: ANALISIS DE CALIDAD DE DATOS - BRONZE", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    tablas = {
        "solicitudes": ["solnum","artcitem","artdes","soltip","solcan","solurg","solusr","solfec","solord","solmon","solpre","solsts","solsta","solpro","solcpr","solara","solmaq","solfap","solfor","artmed","artgrinv","solcaf","solcen","solcac"],
        "recepcion": ["solnum","artcitem","artdes","artmed","artgrinv","solcan","nrdcac","artstock","solpre","solmon","nrcalm","solurg","solusr","nrcfec","solfec","solfor","nrcnum","solord","soltip","solcpr","solpro","nrcpro","nrcgui","solara","solcaf","solcen","solsta","solcac"],
        "maestro_articulos": ["artcitem","artdes","artmed","artgrinv","artcosu1","artstseg","artfusal","artfuent","artubi","artcoum1","artcmon","artpreu2"],
        "articulos": ["artcitem","artdes","artmed","artgrinv","ubialm","ubistock","artfusal","artuptrn","artfureq","artfuent","artfusal_1","artcoum1"],
        "grupos": ["artgrinv", "nombre"],
        "proveedores": ["acrecodi","acreraso","acredire","acretelf","acreciud","acreiden","acreruc"],
    }

    cur = conn.cursor()
    for tabla, cols in tablas.items():
        log("", lines)
        log("-" * 70, lines)
        log(f"  TABLA: bronze.{tabla}", lines)
        log("-" * 70, lines)

        cur.execute(f'SELECT COUNT(*) FROM bronze."{tabla}"')
        total = cur.fetchone()[0]
        log(f"  Total filas: {total}", lines)

        pk = cols[0]
        cur.execute(f'SELECT COUNT(DISTINCT "{pk}") FROM bronze."{tabla}"')
        distinct = cur.fetchone()[0]
        log(f"  Distinct {pk}: {distinct}", lines)
        if distinct < total:
            log(f"  *** DUPLICADOS por {pk}: {total - distinct} filas", lines)

        tiene_nulos = False
        for col in cols:
            cur.execute(f'SELECT COUNT(*) FROM bronze."{tabla}" WHERE "{col}" IS NULL OR TRIM("{col}") = %s', ('',))
            nc = cur.fetchone()[0]
            if nc > 0:
                if not tiene_nulos:
                    log("  Valores vacios/nulos:", lines)
                    tiene_nulos = True
                log(f"    {col}: {nc} ({nc * 100 / total:.1f}%)", lines)
        if not tiene_nulos:
            log("  Valores vacios/nulos: ninguno", lines)

    cur.close()
    save_evidence("01_analisis_calidad_datos.txt", lines)


def analisis_duplicados(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 2: ANALISIS DE DUPLICADOS", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()

    log("", lines)
    log("-" * 70, lines)
    log("  bronze.recepcion - Analisis por solnum", lines)
    log("-" * 70, lines)

    cur.execute("""
        SELECT solnum, COUNT(*) as cnt FROM bronze.recepcion
        GROUP BY solnum HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT 10
    """)
    log("  Top 10 solnum con mas filas:", lines)
    for r in cur.fetchall():
        log(f"    solnum={r[0]}: {r[1]} filas", lines)

    cur.execute("SELECT COUNT(*) FROM (SELECT solnum FROM bronze.recepcion GROUP BY solnum HAVING COUNT(*) > 1) t")
    log(f"\n  Total pedidos con multiples filas: {cur.fetchone()[0]}", lines)

    cur.execute("""
        SELECT solnum, artcitem, artdes, solcan, nrdcac, solpre, solusr, nrcfec
        FROM bronze.recepcion WHERE solnum = (
            SELECT solnum FROM bronze.recepcion GROUP BY solnum HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 1
        ) LIMIT 6
    """)
    log("\n  Ejemplo (solnum con mas filas):", lines)
    for r in cur.fetchall():
        log(f"    solnum={r[0]} artcitem={r[1]} solcan={r[3]} nrdcac={r[4]} solpre={r[5]} nrcfec={r[7]}", lines)

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT solnum, artcitem, COUNT(DISTINCT nrdcac) as dc
            FROM bronze.recepcion GROUP BY solnum, artcitem HAVING COUNT(DISTINCT nrdcac) > 1
        ) t
    """)
    log(f"\n  Entregas parciales (mismo solnum+artcitem, distinto nrdcac): {cur.fetchone()[0]}", lines)

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT solnum, artcitem, nrdcac, COUNT(*) as cnt
            FROM bronze.recepcion GROUP BY solnum, artcitem, nrdcac HAVING COUNT(*) > 1
        ) t
    """)
    log(f"  Duplicados por solnum+artcitem+nrdcac: {cur.fetchone()[0]}", lines)

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY solnum, artcitem, artdes, artmed, artgrinv, solcan, nrdcac, artstock,
                solpre, solmon, nrcalm, solurg, solusr, nrcfec, solfec, solfor, nrcnum, solord,
                soltip, solcpr, solpro, nrcpro, nrcgui, solara, solcaf, solcen, solsta, solcac
                ORDER BY solnum
            ) as rn FROM bronze.recepcion
        ) t WHERE rn > 1
    """)
    log(f"  Filas 100% identicas (duplicados reales): {cur.fetchone()[0]}", lines)

    log("", lines)
    log("-" * 70, lines)
    log("  bronze.articulos - Analisis por artcitem", lines)
    log("-" * 70, lines)

    cur.execute("""
        SELECT artcitem, COUNT(*) as cnt FROM bronze.articulos
        GROUP BY artcitem HAVING COUNT(*) > 1 ORDER BY cnt DESC LIMIT 10
    """)
    log("  Top 10 artcitem con mas filas:", lines)
    for r in cur.fetchall():
        log(f"    artcitem={r[0]}: {r[1]} filas", lines)

    cur.execute("""
        SELECT artcitem, artdes, ubialm, ubistock, artfusal
        FROM bronze.articulos WHERE artcitem = (
            SELECT artcitem FROM bronze.articulos GROUP BY artcitem HAVING COUNT(*) > 1 ORDER BY COUNT(*) DESC LIMIT 1
        )
    """)
    rows = cur.fetchall()
    log(f"\n  Ejemplo (artcitem={rows[0][0]}, {rows[0][1]}):", lines)
    for r in rows:
        log(f"    ubialm={r[2]} ubistock={r[3]} artfusal={r[4]}", lines)

    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY artcitem, artdes, artmed, artgrinv, ubialm, ubistock, artfusal,
                artuptrn, artfureq, artfuent, artfusal_1, artcoum1 ORDER BY artcitem
            ) as rn FROM bronze.articulos
        ) t WHERE rn > 1
    """)
    log(f"  Filas 100% identicas: {cur.fetchone()[0]}", lines)

    log("", lines)
    log("-" * 70, lines)
    log("  OTRAS TABLAS", lines)
    log("-" * 70, lines)
    for tabla, pk in [("solicitudes","solnum"),("maestro_articulos","artcitem"),("grupos","artgrinv"),("proveedores","acrecodi")]:
        cur.execute(f'SELECT COUNT(*) FROM bronze."{tabla}"')
        total = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(DISTINCT "{pk}") FROM bronze."{tabla}"')
        distinct = cur.fetchone()[0]
        dupes = total - distinct
        log(f"  {tabla}: {total} filas, {distinct} distinct {pk}, {dupes} duplicados {'***' if dupes > 0 else 'OK'}", lines)

    cur.close()
    save_evidence("02_analisis_duplicados.txt", lines)


def limpieza_silver(conn):
    lines = []
    log("=" * 70, lines)
    log("  FASE 3: CAPA SILVER - LIMPIEZA Y CARGA", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("=" * 70, lines)

    cur = conn.cursor()

    log("\n[0] Preparando esquema silver...", lines)
    cur.execute("DROP SCHEMA IF EXISTS silver CASCADE")
    cur.execute("CREATE SCHEMA silver")
    conn.commit()
    log("  Esquema silver creado.", lines)

    log("\n[1/6] silver.grupos", lines)
    cur.execute("DROP TABLE IF EXISTS silver.grupos")
    cur.execute("CREATE TABLE silver.grupos (artgrinv TEXT PRIMARY KEY, nombre TEXT NOT NULL)")
    cur.execute("""
        INSERT INTO silver.grupos (artgrinv, nombre)
        SELECT TRIM(artgrinv), TRIM(nombre) FROM bronze.grupos
        WHERE TRIM(artgrinv) IS NOT NULL AND TRIM(artgrinv) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.grupos")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("\n[2/6] silver.proveedores", lines)
    cur.execute("DROP TABLE IF EXISTS silver.proveedores")
    cur.execute("CREATE TABLE silver.proveedores (acrecodi TEXT PRIMARY KEY, acreraso TEXT, acredire TEXT, acretelf TEXT, acreciud TEXT, acreiden TEXT, acreruc TEXT)")
    cur.execute("""
        INSERT INTO silver.proveedores (acrecodi, acreraso, acredire, acretelf, acreciud, acreiden, acreruc)
        SELECT TRIM(acrecodi), TRIM(acreraso), NULLIF(TRIM(acredire),''),
               NULLIF(TRIM(acretelf),''), NULLIF(TRIM(acreciud),''),
               NULLIF(TRIM(acreiden),''), NULLIF(TRIM(acreruc),'')
        FROM bronze.proveedores WHERE TRIM(acrecodi) IS NOT NULL AND TRIM(acrecodi) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.proveedores")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("\n[3/6] silver.maestro_articulos", lines)
    cur.execute("DROP TABLE IF EXISTS silver.maestro_articulos")
    cur.execute("""CREATE TABLE silver.maestro_articulos (
        artcitem TEXT PRIMARY KEY, artdes TEXT, artmed TEXT, artgrinv TEXT,
        artcosu1 NUMERIC(15,2), artstseg INTEGER, artfusal DATE, artfuent DATE,
        artubi TEXT, artcoum1 NUMERIC(15,2), artcmon TEXT, artpreu2 NUMERIC(15,2)
    )""")
    cur.execute("""
        INSERT INTO silver.maestro_articulos
            (artcitem,artdes,artmed,artgrinv,artcosu1,artstseg,artfusal,artfuent,artubi,artcoum1,artcmon,artpreu2)
        SELECT TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv),
            NULLIF(REGEXP_REPLACE(artcosu1,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(REGEXP_REPLACE(artstseg,'[^0-9\\-]','','g'),'')::INTEGER,
            CASE WHEN artfusal ~ '^[0-9]{6}$' THEN TO_DATE(artfusal,'YYMMDD')
                 WHEN artfusal ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal,'YYYY-MM-DD') ELSE NULL END,
            CASE WHEN artfuent ~ '^[0-9]{6}$' THEN TO_DATE(artfuent,'YYMMDD')
                 WHEN artfuent ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfuent,'YYYY-MM-DD') ELSE NULL END,
            NULLIF(TRIM(artubi),''),
            NULLIF(REGEXP_REPLACE(artcoum1,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(TRIM(artcmon),''),
            NULLIF(REGEXP_REPLACE(artpreu2,'[^0-9.\\-]','','g'),'')::NUMERIC
        FROM bronze.maestro_articulos WHERE TRIM(artcitem) IS NOT NULL AND TRIM(artcitem) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.maestro_articulos")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("\n[4/6] silver.articulos", lines)
    cur.execute("DROP TABLE IF EXISTS silver.articulos")
    cur.execute("""CREATE TABLE silver.articulos (
        artcitem TEXT, artdes TEXT, artmed TEXT, artgrinv TEXT, ubialm TEXT,
        ubistock NUMERIC(15,2), artfusal DATE, artuptrn TEXT, artfureq DATE,
        artfuent DATE, artfusal_1 DATE, artcoum1 NUMERIC(15,2), PRIMARY KEY (artcitem, ubialm)
    )""")
    cur.execute("""
        INSERT INTO silver.articulos
            (artcitem,artdes,artmed,artgrinv,ubialm,ubistock,artfusal,artuptrn,artfureq,artfuent,artfusal_1,artcoum1)
        SELECT TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv), TRIM(ubialm),
            NULLIF(REGEXP_REPLACE(ubistock,'[^0-9.\\-]','','g'),'')::NUMERIC,
            CASE WHEN artfusal ~ '^[0-9]{6}$' THEN TO_DATE(artfusal,'YYMMDD')
                 WHEN artfusal ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal,'YYYY-MM-DD') ELSE NULL END,
            NULLIF(TRIM(artuptrn),''),
            CASE WHEN artfureq ~ '^[0-9]{6}$' THEN TO_DATE(artfureq,'YYMMDD')
                 WHEN artfureq ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfureq,'YYYY-MM-DD') ELSE NULL END,
            CASE WHEN artfuent ~ '^[0-9]{6}$' THEN TO_DATE(artfuent,'YYMMDD')
                 WHEN artfuent ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfuent,'YYYY-MM-DD') ELSE NULL END,
            CASE WHEN artfusal_1 ~ '^[0-9]{6}$' THEN TO_DATE(artfusal_1,'YYMMDD')
                 WHEN artfusal_1 ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(artfusal_1,'YYYY-MM-DD') ELSE NULL END,
            NULLIF(REGEXP_REPLACE(artcoum1,'[^0-9.\\-]','','g'),'')::NUMERIC
        FROM bronze.articulos WHERE TRIM(artcitem) IS NOT NULL AND TRIM(artcitem) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.articulos")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("\n[5/6] silver.recepcion", lines)
    cur.execute("DROP TABLE IF EXISTS silver.recepcion")
    cur.execute("""CREATE TABLE silver.recepcion (
        solnum INTEGER, artcitem TEXT, artdes TEXT, artmed TEXT, artgrinv TEXT,
        solcan NUMERIC(15,2), nrdcac NUMERIC(15,2), artstock NUMERIC(15,2),
        solpre NUMERIC(15,2), solmon INTEGER, solurg TEXT, solusr TEXT,
        nrcfec DATE, solfec DATE, nrcnum INTEGER, solord INTEGER, soltip TEXT, solpro TEXT
    )""")
    cur.execute("""
        INSERT INTO silver.recepcion
            (solnum,artcitem,artdes,artmed,artgrinv,solcan,nrdcac,artstock,solpre,solmon,
             solurg,solusr,nrcfec,solfec,nrcnum,solord,soltip,solpro)
        SELECT NULLIF(REGEXP_REPLACE(solnum,'[^0-9\\-]','','g'),'')::INTEGER,
            TRIM(artcitem), TRIM(artdes), TRIM(artmed), TRIM(artgrinv),
            NULLIF(REGEXP_REPLACE(solcan,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(REGEXP_REPLACE(nrdcac,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(REGEXP_REPLACE(artstock,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(REGEXP_REPLACE(solpre,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(REGEXP_REPLACE(solmon,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(TRIM(solurg),''), NULLIF(TRIM(solusr),''),
            CASE WHEN nrcfec ~ '^[0-9]{6}$' THEN TO_DATE(nrcfec,'YYMMDD')
                 WHEN nrcfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(nrcfec,'YYYY-MM-DD') ELSE NULL END,
            CASE WHEN solfec ~ '^[0-9]{6}$' THEN TO_DATE(solfec,'YYMMDD')
                 WHEN solfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(solfec,'YYYY-MM-DD') ELSE NULL END,
            NULLIF(REGEXP_REPLACE(nrcnum,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(REGEXP_REPLACE(solord,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(TRIM(soltip),''), NULLIF(TRIM(solpro),'')
        FROM bronze.recepcion WHERE TRIM(solnum) IS NOT NULL AND TRIM(solnum) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.recepcion")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("\n[6/6] silver.solicitudes", lines)
    cur.execute("DROP TABLE IF EXISTS silver.solicitudes")
    cur.execute("""CREATE TABLE silver.solicitudes (
        solnum INTEGER, artcitem TEXT, artdes TEXT, soltip TEXT,
        solcan NUMERIC(15,2), solurg TEXT, solusr TEXT, solfec DATE,
        solord INTEGER, solmon INTEGER, solpre NUMERIC(15,2), solsts TEXT,
        solsta INTEGER, solpro TEXT, artmed TEXT, artgrinv TEXT
    )""")
    cur.execute("""
        INSERT INTO silver.solicitudes
            (solnum,artcitem,artdes,soltip,solcan,solurg,solusr,solfec,
             solord,solmon,solpre,solsts,solsta,solpro,artmed,artgrinv)
        SELECT NULLIF(REGEXP_REPLACE(solnum,'[^0-9\\-]','','g'),'')::INTEGER,
            TRIM(artcitem), TRIM(artdes), NULLIF(TRIM(soltip),''),
            NULLIF(REGEXP_REPLACE(solcan,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(TRIM(solurg),''), NULLIF(TRIM(solusr),''),
            CASE WHEN solfec ~ '^[0-9]{6}$' THEN TO_DATE(solfec,'YYMMDD')
                 WHEN solfec ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' THEN TO_DATE(solfec,'YYYY-MM-DD') ELSE NULL END,
            NULLIF(REGEXP_REPLACE(solord,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(REGEXP_REPLACE(solmon,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(REGEXP_REPLACE(solpre,'[^0-9.\\-]','','g'),'')::NUMERIC,
            NULLIF(TRIM(solsts),''),
            NULLIF(REGEXP_REPLACE(solsta,'[^0-9\\-]','','g'),'')::INTEGER,
            NULLIF(TRIM(solpro),''),
            NULLIF(TRIM(artmed),''), NULLIF(TRIM(artgrinv),'')
        FROM bronze.solicitudes WHERE TRIM(solnum) IS NOT NULL AND TRIM(solnum) != ''
    """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM silver.solicitudes")
    log(f"  -> {cur.fetchone()[0]} filas", lines)

    log("", lines)
    log("=" * 70, lines)
    log("  VERIFICACION FINAL: BRONZE vs SILVER", lines)
    log("=" * 70, lines)
    log(f"  {'Tabla':<25s} {'Bronze':>10s} {'Silver':>10s}", lines)
    log(f"  {'-'*25} {'-'*10} {'-'*10}", lines)
    for t in ["grupos","proveedores","maestro_articulos","articulos","recepcion","solicitudes"]:
        cur.execute(f'SELECT COUNT(*) FROM bronze."{t}"')
        bc = cur.fetchone()[0]
        cur.execute(f'SELECT COUNT(*) FROM silver."{t}"')
        sc = cur.fetchone()[0]
        log(f"  {t:<25s} {bc:>10,} {sc:>10,}", lines)

    log("", lines)
    log("=" * 70, lines)
    log("  TIPOS DE DATOS EN SILVER", lines)
    log("=" * 70, lines)
    for t in ["grupos","proveedores","maestro_articulos","articulos","recepcion","solicitudes"]:
        cur.execute(f"""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_schema = 'silver' AND table_name = '{t}' ORDER BY ordinal_position
        """)
        log(f"\n  silver.{t}:", lines)
        for c in cur.fetchall():
            log(f"    {c[0]:<20s} -> {c[1]}", lines)

    log("", lines)
    log("=" * 70, lines)
    log("  MUESTRAS DE DATOS", lines)
    log("=" * 70, lines)
    for t in ["solicitudes","recepcion","maestro_articulos","articulos","proveedores"]:
        cur.execute(f"SELECT * FROM silver.{t} LIMIT 3")
        cols = [d[0] for d in cur.description]
        log(f"\n  silver.{t}:", lines)
        log(f"    Columnas: {cols}", lines)
        for r in cur.fetchall():
            log(f"    {r}", lines)

    cur.close()
    save_evidence("03_resultados_silver.txt", lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  ETL COMPLETO: BRONZE -> SILVER")
    print("  Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    conn = get_conn()

    print("\n>>> FASE 1: Analisis de calidad...")
    analisis_calidad(conn)

    print("\n>>> FASE 2: Analisis de duplicados...")
    analisis_duplicados(conn)

    print("\n>>> FASE 3: Limpieza y carga silver...")
    limpieza_silver(conn)

    conn.close()

    print("\n" + "=" * 70)
    print("  ETL COMPLETADO:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Archivos generados en:", OUTPUT_DIR)
    print("=" * 70)
