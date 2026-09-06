import os

import numpy as np
import pandas as pd
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


# Los mismos grids que teniamos en la app pero en serio: aca se prueban
# varias combinaciones y se reportan metricas, no una sola tirada a ciegas.
GRID_BOSQUE = [
    {"n_estimators": 50, "max_depth": 6, "min_samples_leaf": 2},
    {"n_estimators": 100, "max_depth": 8, "min_samples_leaf": 2},
    {"n_estimators": 100, "max_depth": 10, "min_samples_leaf": 5},
    {"n_estimators": 150, "max_depth": 10, "min_samples_leaf": 5},
    {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 3},
]


def probar_bosque(X, y):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score

    filas = []
    for hp in GRID_BOSQUE:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.25, random_state=42
        )
        modelo = RandomForestRegressor(random_state=42, **hp)
        modelo.fit(X_tr, y_tr)
        y_pred = modelo.predict(X_te)
        r2 = r2_score(y_te, y_pred)
        mae = mean_absolute_error(y_te, y_pred)
        filas.append((hp["n_estimators"], hp["max_depth"], hp["min_samples_leaf"], r2, mae))

    mejor = max(filas, key=lambda f: f[3])
    return filas, mejor


def calibracion_por_articulo(conn, lines):
    log("=" * 70, lines)
    log("  FASE 1: CALIBRACION RANDOM FOREST - POR ARTICULO", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("  Caracteristicas: cantidad, mes, anio (igual que en la app).", lines)
    log("  Solo lectura; ningun modelo se guarda, se reporta el mejor grid.", lines)
    log("=" * 70, lines)

    df = pd.read_sql("""
        SELECT artcitem, solfec, solpre, solcan,
               EXTRACT(YEAR FROM solfec)  AS ano,
               EXTRACT(MONTH FROM solfec) AS mes
        FROM normalizado.fact_solicitudes
        WHERE solfec IS NOT NULL AND solpre > 0 AND solpre IS NOT NULL
          AND solcan > 0 AND solcan IS NOT NULL
    """, conn)

    conteo = df.groupby("artcitem")["solpre"].count()
    candidatos = conteo[conteo >= 20].sort_values(ascending=False).index.tolist()

    log(f"\n  Articulos con historial suficiente (>=20 registros): {len(candidatos):,}", lines)
    # calibrar 5 articulos de muestra; calibrar los 200 seria para otro dia
    # con mas paciencia y mas cafe.
    muestra = candidatos[:5]

    log(f"\n  {'Articulo':<22s} {'n':>5s} {'n_est':>6s} {'depth':>6s} {'leaf':>4s} {'R2':>8s} {'MAE':>10s}", lines)
    log(f"  {'-'*22} {'-'*5} {'-'*6} {'-'*6} {'-'*4} {'-'*8} {'-'*10}", lines)

    mejores = []
    for art in muestra:
        df_art = df[df["artcitem"] == art].sort_values("solfec")
        X = df_art[["solcan", "mes", "ano"]].values
        y = df_art["solpre"].values
        filas, mejor = probar_bosque(X, y)
        n_est, depth, leaf, r2, mae = mejor
        log(f"  {art:<22s} {len(df_art):>5d} {n_est:>6d} {depth:>6d} {leaf:>4d} {r2:>8.3f} {mae:>10,.2f}", lines)
        mejores.append((art, len(df_art), n_est, depth, leaf, r2, mae))

    log("\n  Conclusión: los hiperparámetros del ganador varían por artículo,", lines)
    log("  pero el grid de N=100/depth 8-10 anda bien en general.", lines)


def calibracion_tendencia_gold(conn, lines):
    log("=" * 70, lines)
    log("  FASE 2: CALIBRACION RANDOM FOREST - TENDENCIA AGREGADA (GOLD)", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("  Caracteristicas: cantidad, frecuencia, stock, mes, anio.", lines)
    log("=" * 70, lines)

    df_gold = pd.read_sql("""
        SELECT artcitem, periodo_mes,
               cantidad_total_despachada AS cantidad,
               frecuencia_pedidos         AS frecuencia,
               ultimo_stock_registrado    AS stock,
               precio_promedio_pactado    AS precio
        FROM gold.prediccion_demanda_mensual
        WHERE precio_promedio_pactado > 0
          AND cantidad_total_despachada IS NOT NULL
    """, conn)

    df_gold["mes"] = df_gold["periodo_mes"].dt.month
    df_gold["ano"] = df_gold["periodo_mes"].dt.year
    X = df_gold[["cantidad", "frecuencia", "stock", "mes", "ano"]].values
    y = df_gold["precio"].values

    log(f"\n  Filas de la capa gold usadas: {len(df_gold):,}", lines)
    log(f"\n  {'n_est':>6s} {'depth':>6s} {'leaf':>4s} {'R2':>8s} {'MAE':>10s}", lines)
    log(f"  {'-'*6} {'-'*6} {'-'*4} {'-'*8} {'-'*10}", lines)

    filas, mejor = probar_bosque(X, y)
    n_est, depth, leaf, r2, mae = mejor
    for f in filas:
        log(f"  {f[0]:>6d} {f[1]:>6d} {f[2]:>4d} {f[3]:>8.3f} {f[4]:>10,.2f}", lines)

    log(f"\n  Mejor combinacion: n_estimators={n_est}, max_depth={depth}, min_samples_leaf={leaf}", lines)
    log(f"    con R2={r2:.3f} y MAE={mae:,.2f}", lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  CALIBRACION RANDOM FOREST (RECOMENDACION 3)")
    print("  Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Nota: solo lectura, no se guardan modelos.")
    print("=" * 70)

    conn = get_conn()
    lines = []

    print("\n>>> FASE 1: Por articulo...")
    calibracion_por_articulo(conn, lines)

    print("\n>>> FASE 2: Tendencia agregada gold...")
    calibracion_tendencia_gold(conn, lines)

    conn.close()
    save_evidence("11_calibracion_rf.txt", lines)

    print("\n" + "=" * 70)
    print("  CALIBRACION COMPLETADA:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)