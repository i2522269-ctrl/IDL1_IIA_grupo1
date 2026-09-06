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


# La misma serie mensual que usa la app (normalizado.fact_recepcion).
# Si la app y la validacion no leen lo mismo, el "ajustar modelos" no
# significa nada, asi que no inventamos otra fuente.
def cargar_serie_stock_mensual(conn):
    df = pd.read_sql("""
        SELECT DATE_TRUNC('month', nrcfec)::date AS mes, SUM(artstock) AS stock_total
        FROM normalizado.fact_recepcion
        WHERE nrcfec IS NOT NULL
        GROUP BY DATE_TRUNC('month', nrcfec)::date
        ORDER BY mes
    """, conn)
    df["mes"] = pd.to_datetime(df["mes"])
    df.rename(columns={"mes": "ds", "stock_total": "y"}, inplace=True)
    return df


def metricas_ventana(real, pred):
    real = np.asarray(real, dtype=float)
    pred = np.asarray(pred, dtype=float)
    dif = real - pred
    mae = float(np.mean(np.abs(dif)))
    rmse = float(np.sqrt(np.mean(dif ** 2)))
    mape = float(np.mean(np.abs(dif) / np.where(real == 0, np.nan, real))) * 100
    return mae, rmse, mape


# ============================================
# MODELOS: puros, sin decoradores de streamlit
# ============================================

def pronostico_naive(df, h=6):
    # el classico de referencia: el proximo mes igual al ultimo.
    # Si un modelo fancy no le gana a esto, no le gana a nada.
    return np.full(h, float(df["y"].iloc[-1]))


def pronostico_regresion(df, h=6):
    # regresion lineal con numpy sobre el indice del tiempo.
    y = df["y"].values
    x = np.arange(len(y))
    coef = np.polyfit(x, y, 1)
    futuro = np.arange(len(y), len(y) + h)
    return np.polyval(coef, futuro)


def pronostico_prophet(df, h=6):
    from prophet import Prophet
    modelo = Prophet(weekly_seasonality=False)
    modelo.fit(df[["ds", "y"]])
    futuro = modelo.make_future_dataframe(periods=h, freq="MS")
    pred = modelo.predict(futuro)["yhat"].values
    return pred[-h:]


def pronostico_keras(df, h=1):
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense

    tf.keras.utils.set_random_seed(42)

    y = df["y"].values
    if len(y) == 0:
        return np.full(h, 0.0)
    ymin, ymax = y.min(), y.max()
    ventana = 12
    if ymax == ymin or len(y) <= ventana:
        base = float(ymin) if ymax == ymin else float(y[-1])
        return np.full(h, base)

    y_norm = (y - ymin) / (ymax - ymin)
    X, Y = [], []
    for i in range(len(y_norm) - ventana):
        X.append(y_norm[i:i + ventana])
        Y.append(y_norm[i + ventana])
    X = np.array(X)
    Y = np.array(Y)

    modelo = Sequential([
        Dense(32, activation="relu", input_shape=(ventana,)),
        Dense(16, activation="relu"),
        Dense(1)
    ])
    modelo.compile(optimizer="adam", loss="mse")
    modelo.fit(X, Y, epochs=200, verbose=0)

    ultimo = y_norm[-ventana:].copy()
    pronostico_norm = []
    for _ in range(h):
        pred = float(modelo.predict(ultimo.reshape(1, -1), verbose=0)[0, 0])
        pronostico_norm.append(pred)
        ultimo = np.append(ultimo[1:], pred)
    return np.array(pronostico_norm) * (ymax - ymin) + ymin


def pronostico_torch(df, h=1):
    import torch
    import torch.nn as nn

    np.random.seed(42)
    torch.manual_seed(42)

    y = df["y"].values
    if len(y) == 0:
        return np.full(h, 0.0)
    ymin, ymax = y.min(), y.max()
    ventana = 12
    if ymax == ymin or len(y) <= ventana:
        base = float(ymin) if ymax == ymin else float(y[-1])
        return np.full(h, base)

    y_norm = (y - ymin) / (ymax - ymin)
    X, Y = [], []
    for i in range(len(y_norm) - ventana):
        X.append(y_norm[i:i + ventana])
        Y.append(y_norm[i + ventana])
    X = torch.tensor(np.array(X), dtype=torch.float32)
    Y = torch.tensor(np.array(Y), dtype=torch.float32)

    class MiniRed(nn.Module):
        def __init__(self):
            super().__init__()
            self.capa = nn.Sequential(
                nn.Linear(ventana, 32), nn.ReLU(),
                nn.Linear(32, 16), nn.ReLU(),
                nn.Linear(16, 1))

        def forward(self, x):
            return self.capa(x)

    modelo = MiniRed()
    optimizador = torch.optim.Adam(modelo.parameters())
    perdida = nn.MSELoss()
    for _ in range(300):
        optimizador.zero_grad()
        loss = perdida(modelo(X).squeeze(), Y)
        loss.backward()
        optimizador.step()

    ultimo = torch.tensor(y_norm[-ventana:], dtype=torch.float32)
    pronostico_norm = []
    for _ in range(h):
        pred = modelo(ultimo).item()
        pronostico_norm.append(pred)
        ultimo = torch.cat([ultimo[1:], torch.tensor([pred])])
    return np.array(pronostico_norm) * (ymax - ymin) + ymin


def backtest_horizonte(conn, lines):
    log("=" * 70, lines)
    log("  FASE 1: BACKTEST A HORIZONTE FIJO (6 MESES)", lines)
    log(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}", lines)
    log("  Split cronologico: los ultimos 6 meses quedan fuera y se predicen.", lines)
    log("=" * 70, lines)

    df = cargar_serie_stock_mensual(conn)
    log(f"\n  Serie mensual: {len(df)} meses, de {df['ds'].iloc[0]:%Y-%m} a {df['ds'].iloc[-1]:%Y-%m}", lines)

    if len(df) < 13:
        log("  Serie demasiado corta para backtest (necesita >= 13 meses).", lines)
        return

    h = 6
    train = df.iloc[:-h].reset_index(drop=True)
    real = df["y"].iloc[-h:].values

    modelos = {
        "Naive (ultimo valor)": pronostico_naive,
        "Regresion lineal (numpy)": pronostico_regresion,
        "Prophet": pronostico_prophet,
        "Keras (MLP)": pronostico_keras,
        "PyTorch (MLP)": pronostico_torch,
    }

    log(f"\n  {'Modelo':<28s} {'MAE':>12s} {'RMSE':>12s} {'MAPE(%)':>9s}", lines)
    log(f"  {'-'*28} {'-'*12} {'-'*12} {'-'*9}", lines)

    for nombre, fn in modelos.items():
        try:
            pred = fn(train, h=h)
            mae, rmse, mape = metricas_ventana(real, pred)
            log(f"  {nombre:<28s} {mae:>12,.0f} {rmse:>12,.0f} {mape:>8.1f}%", lines)
        except Exception as e:
            log(f"  {nombre:<28s} ERROR: {e}", lines)

    log("\n  Nota: el MAPE se puede ir de madre si hay meses con stock 0;", lines)
    log("  se deja igual para que quede claro quien le gana al naive.", lines)


def backtest_walkforward(conn, lines):
    log("=" * 70, lines)
    log("  FASE 2: WALK-FORWARD DE 1 PASO (ULTIMOS MESES)", lines)
    log("  Cada mes se predice con solo la historia previa, 1 paso adelante.", lines)
    log("  Asi se simula el uso real: el modelo no vio el dato al predecirlo.", lines)
    log("=" * 70, lines)

    df = cargar_serie_stock_mensual(conn)
    if len(df) < 25:
        log("\n  Serie corta para walk-forward estable (necesita >= 25 meses).", lines)
        return

    minimo_hist = 13  # las redes necesitan historia para armar ventana

    fold_models = {
        "Naive": pronostico_naive,
        "Regresion lineal": pronostico_regresion,
        "Prophet": pronostico_prophet,
        "Keras": pronostico_keras,
        "PyTorch": pronostico_torch,
    }

    errores = {nombre: [] for nombre in fold_models}

    for t in range(minimo_hist, len(df) - 1):
        train = df.iloc[:t].reset_index(drop=True)
        real_val = float(df["y"].iloc[t])
        for nombre, fn in fold_models.items():
            try:
                pred = fn(train, h=1)[0]
                errores[nombre].append(abs(real_val - pred))
            except Exception:
                errores[nombre].append(np.nan)

    log(f"\n  {'Modelo':<22s} {'MAE':>12s} {'RMSE':>12s} {'n':>5s}", lines)
    log(f"  {'-'*22} {'-'*12} {'-'*12} {'-'*5}", lines)
    for nombre, errs in errores.items():
        ok = [e for e in errs if e == e]
        if not ok:
            log(f"  {nombre:<22s} sin predicciones validas", lines)
            continue
        mae = float(np.mean(ok))
        rmse = float(np.sqrt(np.mean(np.array(ok) ** 2)))
        log(f"  {nombre:<22s} {mae:>12,.0f} {rmse:>12,.0f} {len(ok):>5d}", lines)

    log("\n  Cuantos menos MAE/RMSE en el horizonte de 1 mes, mejor. Y si el", lines)
    log("  Naive gana, es la senal de que la serie no tiene patron que explotar.", lines)


if __name__ == "__main__":
    print("=" * 70)
    print("  VALIDACION DE PRONOSTICOS (RECOMENDACION 1)")
    print("  Inicio:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Nota: solo lectura, no se toca ninguna tabla.")
    print("=" * 70)

    conn = get_conn()

    lines = []
    print("\n>>> FASE 1: Backtest horizonte fijo 6 meses...")
    backtest_horizonte(conn, lines)

    print("\n>>> FASE 2: Walk-forward 1 paso...")
    backtest_walkforward(conn, lines)

    conn.close()
    save_evidence("10_validacion_pronosticos.txt", lines)

    print("\n" + "=" * 70)
    print("  VALIDACION COMPLETADA:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)