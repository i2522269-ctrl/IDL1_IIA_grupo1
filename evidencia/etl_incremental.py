import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys

import psycopg2
from dotenv import load_dotenv
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROYECTO_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
load_dotenv(os.path.join(_PROYECTO_DIR, ".env"))

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
}

# Carpeta donde el "ERP" (o quien sea) suelta los CSV nuevos. Mientras no
# tengamos un ERP de verdad, aqui se dejan los archivos y este script
# decide que es nuevo y que ya lo vimos. Adivina quien es el ERP aca.
CARPETA_ENTRADA = os.path.join(_PROYECTO_DIR, "datos_entrada")
CHECKPOINT = os.path.join(SCRIPT_DIR, "checkpoint_ingesta.json")

# Que archivo alimenta que tabla y con que columna(s) se identifica una fila.
# La clave es la misma logica que ya usamos en silver para no duplicar.
TABLAS_BRONZE = {
    "solicitudes.csv": ("solicitudes", ["solnum"]),
    "recepcion.csv": ("recepcion", ["solnum", "artcitem", "nrdcac"]),
    "Maestro_Articulos.csv": ("maestro_articulos", ["artcitem"]),
    "Articulos.csv": ("articulos", ["artcitem", "ubialm"]),
    "Proveedores.csv": ("proveedores", ["acrecodi"]),
    "grupos.csv": ("grupos", ["artgrinv"]),
}


def log(msg):
    print(msg)


def clave_fila(filas, cols_key):
    # una huella estable de las columnas clave; asi detectamos si ya
    # entro esa fila sin comparar los otros 20 campos de relleno.
    for f in filas:
        trozo = "|".join(str(f.get(c, "")).strip() for c in cols_key)
        h = hashlib.sha1(trozo.encode("utf-8")).hexdigest()
        f["_clave"] = h
    return filas


def leer_csv(ruta):
    with open(ruta, "r", encoding="utf-8-sig", newline="") as f:
        return [{k.strip(): v for k, v in row.items()} for row in csv.DictReader(f)]


def estado_previo():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def planificar(carpeta):
    """Identifica filas nuevas sin tocar la BD: compara contra el checkpoint."""
    previo = estado_previo()
    plan = {}
    total_nuevas = 0

    for archivo, (tabla, cols_key) in TABLAS_BRONZE.items():
        ruta = os.path.join(carpeta, archivo)
        if not os.path.exists(ruta):
            plan[tabla] = {"archivo": archivo, "existe": False, "filas": 0, "nuevas": 0}
            continue

        filas = clave_fila(leer_csv(ruta), cols_key)
        vistos = set(previo.get(tabla, {}).get("claves", []))
        nuevas = [f for f in filas if f["_clave"] not in vistos]
        plan[tabla] = {
            "archivo": archivo,
            "existe": True,
            "filas": len(filas),
            "nuevas": len(nuevas),
        }
        total_nuevas += len(nuevas)

    return plan, total_nuevas


def guardar_checkpoint(carpeta):
    """Actualiza el checkpoint con TODAS las claves actuales de la carpeta."""
    nuevo = {}
    for archivo, (tabla, cols_key) in TABLAS_BRONZE.items():
        ruta = os.path.join(carpeta, archivo)
        if not os.path.exists(ruta):
            continue
        filas = clave_fila(leer_csv(ruta), cols_key)
        nuevo[tabla] = {"claves": [f["_clave"] for f in filas], "actualizado": datetime.now().isoformat()}
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump(nuevo, f, indent=2)


def insertar_bronze(conn, tabla, filas, cols_key):
    """Inserta en bronze solo las filas nuevas (clave no existente)."""
    cur = conn.cursor()
    cols = [c for c in filas[0].keys() if c != "_clave"] if filas else []
    if not cols:
        return 0
    col_lista = ", ".join(f'"{c}"' for c in cols)
    ph = ", ".join(["%s"] * len(cols))
    sql = f'INSERT INTO bronze."{tabla}" ({col_lista}) VALUES ({ph})'

    existentes = set()
    if cols_key:
        cols_trim = [f'TRIM("{c}")' for c in cols_key]
        sel = "SELECT " + ", ".join(cols_trim) + f' FROM bronze."{tabla}"'
        cur.execute(sel)
        existentes = {tuple((r or "").strip() for r in fila) for fila in cur.fetchall()}

    insertadas = 0
    for f in filas:
        valores_clave = tuple(str(f.get(c, "") or "").strip() for c in cols_key)
        if valores_clave in existentes:
            continue
        valores = [f[c] for c in cols]
        cur.execute(sql, valores)
        insertadas += 1
    conn.commit()
    cur.close()
    return insertadas


def aplicar(carpeta):
    plan, total = planificar(carpeta)
    conn = psycopg2.connect(**DB_CONFIG)
    total_real = 0

    for tabla, info in plan.items():
        if not info["existe"] or info["nuevas"] == 0:
            continue
        ruta = os.path.join(carpeta, info["archivo"])
        filas = clave_fila(leer_csv(ruta), TABLAS_BRONZE[info["archivo"]][1])
        n = insertar_bronze(conn, tabla, filas, TABLAS_BRONZE[info["archivo"]][1])
        total_real += n
        log(f"  {tabla}: {n} filas insertadas")

    conn.close()
    guardar_checkpoint(carpeta)
    log(f"  Total insertado: {total_real} filas")
    log("  Luego correr etl_silver.py -> etl_normalizado.py -> etl_gold.py para propagar.")
    return total_real


def main():
    parser = argparse.ArgumentParser(description="Ingesta incremental a bronze (recomendacion 2).")
    parser.add_argument("--carpeta", default=CARPETA_ENTRADA, help="Carpeta con los CSV nuevos.")
    parser.add_argument("--apply", action="store_true", help="Inserta en bronze (por defecto solo simula).")
    args = parser.parse_args()

    print("=" * 70)
    print("  INGESTA INCREMENTAL / TIEMPO REAL")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Carpeta de entrada: {args.carpeta}")
    print(f"  Modo: {'APPLY (escribe en bronze)' if args.apply else 'DRY-RUN (solo simula)'}")
    print("=" * 70)

    if args.apply:
        aplicar(args.carpeta)
    else:
        plan, total = planificar(args.carpeta)
        print(f"\n  {'Tabla':<22s} {'Archivo':<26s} {'Filas':>7s} {'Nuevas':>7s}")
        print(f"  {'-'*22} {'-'*26} {'-'*7} {'-'*7}")
        for tabla, info in plan.items():
            if not info["existe"]:
                print(f"  {tabla:<22s} {info['archivo']:<26s}  (no esta en carpeta)")
            else:
                print(f"  {tabla:<22s} {info['archivo']:<26s} {info['filas']:>7d} {info['nuevas']:>7d}")
        print(f"\n  Total de filas nuevas estimadas: {total}")
        print("  (usa --apply para insertarlas de verdad; el checkpoint se actualiza)")


if __name__ == "__main__":
    main()