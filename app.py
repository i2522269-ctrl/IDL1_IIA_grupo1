import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
from datetime import datetime

# ============================================
# CONEXION A SUPABASE
# ============================================
# Las credenciales viven en .streamlit/secrets.toml (nube) o en .env
# (local). Nada de passwords en el codigo: la unica vez que dejamos una
# hardcodeada quedo un susto en el historial de git.
@st.cache_resource
def conectar():
    import os
    from dotenv import load_dotenv

    # primero las secrets de la nube; si no hay, bajamos al .env local.
    # Si tampoco esta, que truene con un mensaje que diga que configurar.
    try:
        cfg = {
            "host": st.secrets["DB_HOST"],
            "port": int(st.secrets["DB_PORT"]),
            "dbname": st.secrets["DB_NAME"],
            "user": st.secrets["DB_USER"],
            "password": st.secrets["DB_PASSWORD"],
        }
    except Exception:
        load_dotenv()
        cfg = {
            "host": os.getenv("DB_HOST"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "dbname": os.getenv("DB_NAME", "postgres"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
        }

    if not cfg["host"] or not cfg["user"] or not cfg["password"]:
        raise RuntimeError(
            "Credenciales no encontradas. Configura .streamlit/secrets.toml (nube) o .env (local)."
        )

    return psycopg2.connect(**cfg)

def cargar_datos(consulta):
    conn = conectar()
    return pd.read_sql(consulta, conn)

# Stock recibido por mes. Como lo usamos en tres lados, una sola funcion y listo.
def cargar_stock_mensual():
    df = cargar_datos("""
        SELECT DATE_TRUNC('month', nrcfec)::date as mes, SUM(artstock) as stock_total
        FROM normalizado.fact_recepcion
        WHERE nrcfec IS NOT NULL
        GROUP BY DATE_TRUNC('month', nrcfec)::date
        ORDER BY mes
    """)
    df.rename(columns={"mes": "ds", "stock_total": "y"}, inplace=True)
    # prophet no acepta fechas con zona horaria ni como objeto date
    df["ds"] = pd.to_datetime(df["ds"])
    return df

# Participacion de cada producto en el stock total de los ultimos 12 meses.
# Sirve para repartir el pronostico mensual entre los productos, porque
# los modelos predicen el total y no cada articulo (quien dijo que era facil).
def cargar_participacion_productos():
    df = cargar_datos("""
        SELECT r.artcitem, m.artdes, g.nombre as grupo,
               SUM(r.artstock) as stock_total
        FROM normalizado.fact_recepcion r
        LEFT JOIN normalizado.maestro_articulos m ON r.artcitem = m.artcitem
        LEFT JOIN normalizado.grupos g ON m.artgrinv = g.artgrinv
        WHERE r.nrcfec >= (SELECT MAX(nrcfec) - INTERVAL '12 months' FROM normalizado.fact_recepcion)
          AND r.artstock IS NOT NULL
        GROUP BY r.artcitem, m.artdes, g.nombre
    """)
    df["participacion"] = df["stock_total"] / df["stock_total"].sum()
    return df

# Convierte el pronostico total de cada mes en una tabla producto por producto.
# Reparte la cantidad segun la participacion y deja solo el top de cada mes.
def tabla_productos_por_fecha(pronostico, fechas_futuro, participacion):
    filas = []
    for mes, cantidad_total in zip(fechas_futuro, pronostico):
        df_mes = participacion.copy()
        df_mes["cantidad_estimada"] = df_mes["participacion"] * cantidad_total
        df_mes = df_mes.sort_values("cantidad_estimada", ascending=False).head(15)
        df_mes["mes"] = mes
        filas.append(df_mes)
    tabla = pd.concat(filas, ignore_index=True)
    return tabla[["artcitem", "artdes", "grupo", "mes", "cantidad_estimada"]]

# Modelo de stock con Prophet. Lo dejamos cacheado en memoria para que
# Proyecciones y el Diagnostico compartan el mismo entrenamiento.
@st.cache_resource(show_spinner="Entrenando modelo Prophet...")
def modelo_prophet(df):
    from prophet import Prophet
    modelo = Prophet(weekly_seasonality=False)
    modelo.fit(df)
    return modelo

# Red neuronal con Keras para el stock mensual. Cacheada, obvio,
# porque entrenar redes en cada clic seria el colmo.
@st.cache_resource(show_spinner="Entrenando red neuronal (Keras)...")
def entrenar_keras(df):
    import numpy as np
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Dense

    # semilla unica para python/numpy/tf; sin esto el pronostico cambia
    # de un clic a otro y nadie nos cree la evidencia
    tf.keras.utils.set_random_seed(42)

    # normalizamos para que la red no se pierda con numeros enormes
    y = df["y"].values
    if len(y) == 0:
        return np.full(6, 0.0), 0.0
    ymin, ymax = y.min(), y.max()

    ventana = 12
    # serie constante o historial que no alcanza para la ventana:
    # pronostico plano y a otra cosa, una red con una sola fila no aprende
    if ymax == ymin or len(y) <= ventana:
        base = float(ymin) if ymax == ymin else float(y[-1])
        return np.full(6, base), 0.0

    y_norm = (y - ymin) / (ymax - ymin)

    # ventana deslizante: con los ultimos 12 meses predecimos el siguiente
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
    modelo.fit(X, Y, epochs=300, verbose=0)

    # pronostico iterativo: la red se alimenta de su propia salida
    ultimo = y_norm[-ventana:].copy()
    pronostico_norm = []
    for _ in range(6):
        pred = float(modelo.predict(ultimo.reshape(1, -1), verbose=0)[0, 0])
        pronostico_norm.append(pred)
        ultimo = np.append(ultimo[1:], pred)

    # banda de incertidumbre con el error del ajuste sobre el historico
    ajuste_norm = modelo.predict(X, verbose=0).flatten()
    ajuste = ajuste_norm * (ymax - ymin) + ymin
    banda = 1.96 * (y[ventana:] - ajuste).std()

    pronostico = np.array(pronostico_norm) * (ymax - ymin) + ymin
    return pronostico, banda

# Igual que Keras pero con PyTorch, por si la profe pregunta por este.
@st.cache_resource(show_spinner="Entrenando red neuronal (PyTorch)...")
def entrenar_torch(df):
    import numpy as np
    import torch
    import torch.nn as nn

    # mismas semillas que en keras; la evidencia se toma en serio
    np.random.seed(42)
    torch.manual_seed(42)

    y = df["y"].values
    if len(y) == 0:
        return np.full(6, 0.0), 0.0
    ymin, ymax = y.min(), y.max()

    ventana = 12
    # el mismo rescate que en keras: sin datos suficientes no hay red
    # que valga, pronostico plano y nos vamos
    if ymax == ymin or len(y) <= ventana:
        base = float(ymin) if ymax == ymin else float(y[-1])
        return np.full(6, base), 0.0

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
                nn.Linear(ventana, 32),
                nn.ReLU(),
                nn.Linear(32, 16),
                nn.ReLU(),
                nn.Linear(16, 1)
            )

        def forward(self, x):
            return self.capa(x)

    modelo = MiniRed()
    optimizador = torch.optim.Adam(modelo.parameters())
    perdida = nn.MSELoss()

    for _ in range(500):
        optimizador.zero_grad()
        loss = perdida(modelo(X).squeeze(), Y)
        loss.backward()
        optimizador.step()

    # pronostico iterativo igual que en Keras
    ultimo = torch.tensor(y_norm[-ventana:], dtype=torch.float32)
    pronostico_norm = []
    for _ in range(6):
        pred = modelo(ultimo).item()
        pronostico_norm.append(pred)
        ultimo = torch.cat([ultimo[1:], torch.tensor([pred])])

    # banda con el error del ajuste
    with torch.no_grad():
        ajuste_norm = modelo(X).squeeze().numpy()
    ajuste = ajuste_norm * (ymax - ymin) + ymin
    banda = 1.96 * (y[ventana:] - ajuste).std()

    pronostico = np.array(pronostico_norm) * (ymax - ymin) + ymin
    return pronostico, banda

# ============================================
# PAGINA PRINCIPAL
# ============================================
st.set_page_config(page_title="Proyecto Productivo IIA", layout="wide")
st.title("Proyecto Productivo IIA")
st.subheader("Analisis de datos de inventario y compras")

# barra lateral con opciones
opcion = st.sidebar.selectbox(
    "Selecciona una seccion",
    ["Resumen General", "Solicitudes", "Recepcion", "Articulos", "Proyecciones", "Diagnostico Prophet", "Diagnostico Numpy", "Diagnostico Keras", "Diagnostico PyTorch"]
)

# ============================================
# SECCION: RESUMEN GENERAL
# ============================================
if opcion == "Resumen General":
    st.header("Resumen General")

    col1, col2, col3, col4 = st.columns(4)

    total_solicitudes = cargar_datos("SELECT COUNT(*) as total FROM normalizado.fact_solicitudes")["total"][0]
    total_recepcion = cargar_datos("SELECT COUNT(*) as total FROM normalizado.fact_recepcion")["total"][0]
    total_articulos = cargar_datos("SELECT COUNT(DISTINCT artcitem) as total FROM normalizado.maestro_articulos")["total"][0]
    total_proveedores = cargar_datos("SELECT COUNT(*) as total FROM normalizado.proveedores")["total"][0]

    col1.metric("Solicitudes", f"{total_solicitudes:,}")
    col2.metric("Recepciones", f"{total_recepcion:,}")
    # es el tamano del catalogo, no los que tienen stock; mejor decirlo claro
    col3.metric("Articulos (catalogo)", f"{total_articulos:,}")
    col4.metric("Proveedores", f"{total_proveedores:,}")

    st.markdown("---")

    # articulos por grupo
    st.subheader("Articulos por Grupo")
    # LEFT JOIN para no perder los articulos cuyo grupo no existe en el
    # catalogo; esos 19 duenios de grupo inexistente aparecen como (sin grupo)
    df_grupos = cargar_datos("""
        SELECT COALESCE(g.nombre, '(sin grupo)') as grupo,
               COUNT(DISTINCT m.artcitem) as cantidad
        FROM normalizado.maestro_articulos m
        LEFT JOIN normalizado.grupos g ON m.artgrinv = g.artgrinv
        GROUP BY COALESCE(g.nombre, '(sin grupo)')
        ORDER BY cantidad DESC, grupo
    """)
    fig = px.bar(df_grupos, x="grupo", y="cantidad", color="cantidad",
                 color_continuous_scale="Blues")
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# SECCION: SOLICITUDES
# ============================================
elif opcion == "Solicitudes":
    st.header("Analisis de Solicitudes")

    df_sol = cargar_datos("""
        SELECT DATE_TRUNC('month', solfec) as mes,
               COUNT(*) as cantidad,
               SUM(solcan) as total_cantidad,
               AVG(solpre) as precio_promedio
        FROM normalizado.fact_solicitudes
        WHERE solfec IS NOT NULL
        GROUP BY DATE_TRUNC('month', solfec)
        ORDER BY mes
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Solicitudes por Mes")
        fig = px.line(df_sol, x="mes", y="cantidad", markers=True,
                      color_discrete_sequence=["#2196F3"])
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Precio Promedio por Mes")
        fig = px.line(df_sol, x="mes", y="precio_promedio", markers=True,
                      color_discrete_sequence=["#FF9800"])
        st.plotly_chart(fig, use_container_width=True)

    # top articulos mas solicitados
    st.subheader("Articulos Mas Solicitados")
    # los articulos que no estan en el catalogo (artcitem NULL) no cuentan
    # para el ranking; si no, todos juntos quedarian primeros y seria raro.
    df_top = cargar_datos("""
        SELECT s.artcitem, m.artdes, COUNT(*) as veces_solicitado,
               SUM(s.solcan) as total_cantidad
        FROM normalizado.fact_solicitudes s
        LEFT JOIN normalizado.maestro_articulos m ON s.artcitem = m.artcitem
        WHERE s.artcitem IS NOT NULL
        GROUP BY s.artcitem, m.artdes
        ORDER BY veces_solicitado DESC, s.artcitem
        LIMIT 15
    """)
    fig = px.bar(df_top, x="artcitem", y="veces_solicitado", color="total_cantidad",
                 color_continuous_scale="Reds")
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# SECCION: RECEPCION
# ============================================
elif opcion == "Recepcion":
    st.header("Analisis de Recepcion")

    df_rec = cargar_datos("""
        SELECT DATE_TRUNC('month', nrcfec) as mes,
               COUNT(*) as recepciones,
               SUM(nrdcac) as total_recibido,
               AVG(solpre) as precio_promedio
        FROM normalizado.fact_recepcion
        WHERE nrcfec IS NOT NULL
        GROUP BY DATE_TRUNC('month', nrcfec)
        ORDER BY mes
    """)

    st.subheader("Recepciones por Mes")
    fig = px.area(df_rec, x="mes", y="recepciones", color_discrete_sequence=["#4CAF50"])
    st.plotly_chart(fig, use_container_width=True)

    # proveedores principales
    st.subheader("Top Proveedores por Volumen")
    df_prov = cargar_datos("""
        SELECT p.acreraso as proveedor, COUNT(*) as recepciones,
               SUM(r.solcan) as cantidad_total
        FROM normalizado.fact_recepcion r
        JOIN normalizado.proveedores p ON r.solpro = p.acrecodi
        WHERE r.solpro IS NOT NULL
        GROUP BY p.acreraso
        ORDER BY cantidad_total DESC, proveedor
        LIMIT 10
    """)
    fig = px.pie(df_prov, values="cantidad_total", names="proveedor",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# SECCION: ARTICULOS
# ============================================
elif opcion == "Articulos":
    st.header("Analisis de Articulos")

    df_stock = cargar_datos("""
        SELECT s.artcitem, m.artdes, s.ubialm, s.ubistock
        FROM normalizado.fact_stock s
        LEFT JOIN normalizado.maestro_articulos m ON s.artcitem = m.artcitem
        WHERE s.ubistock IS NOT NULL
        ORDER BY s.ubistock DESC, s.artcitem
        LIMIT 20
    """)

    st.subheader("Top 20 Articulos con Mayor Stock")
    fig = px.bar(df_stock, x="artcitem", y="ubistock", color="ubialm",
                 color_continuous_scale="Viridis")
    st.plotly_chart(fig, use_container_width=True)

    # distribucion por unidad de medida
    st.subheader("Distribucion por Unidad de Medida")
    df_med = cargar_datos("""
        SELECT artmed, COUNT(*) as cantidad
        FROM normalizado.maestro_articulos
        WHERE artmed IS NOT NULL
        GROUP BY artmed
        ORDER BY cantidad DESC, artmed
    """)
    fig = px.pie(df_med, values="cantidad", names="artmed")
    st.plotly_chart(fig, use_container_width=True)

# ============================================
# SECCION: PROYECCIONES
# ============================================
elif opcion == "Proyecciones":
    st.header("Proyecciones y Analisis")

    # proyeccion simple de solicitudes
    st.subheader("Proyeccion de Solicitudes (Proximos 6 meses)")
    try:
        df_proy = cargar_datos("""
            SELECT DATE_TRUNC('month', solfec) as mes,
                   COUNT(*) as cantidad
            FROM normalizado.fact_solicitudes
            WHERE solfec IS NOT NULL
            GROUP BY DATE_TRUNC('month', solfec)
            ORDER BY mes
        """)

        import numpy as np
        df_proy["mes_num"] = range(len(df_proy))
        x = df_proy["mes_num"].values
        y = df_proy["cantidad"].values

        # ajuste simple
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)

        # predecir 6 meses mas; si la tendencia se va a negativo lo
        # cortamos en cero, un pedido negativo no existe ni en broma
        x_future = np.arange(len(df_proy), len(df_proy) + 6)
        y_future = np.maximum(p(x_future), 0)

        df_futuro = pd.DataFrame({
            "mes": pd.date_range(start=df_proy["mes"].max(), periods=7, freq="MS")[1:],
            "cantidad": y_future.astype(int)
        })

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_proy["mes"], y=df_proy["cantidad"],
                                 mode="lines+markers", name="Real"))
        fig.add_trace(go.Scatter(x=df_futuro["mes"], y=df_futuro["cantidad"],
                                 mode="lines+markers", name="Proyeccion",
                                 line=dict(dash="dash", color="red")))
        st.plotly_chart(fig, use_container_width=True)
        st.info("Proyeccion basada en tendencia lineal simple")
    except Exception as e:
        st.error(f"Error en proyeccion: {e}")

    # prediccion de precios futuros
    st.subheader("Prediccion de Precios Futuros")
    try:
        # esta seccion falla intencionalmente
        from sklearn.ensemble import RandomForestRegressor
        df_precios = cargar_datos("""
            SELECT solfec, solpre, solcan
            FROM normalizado.fact_solicitudes
            WHERE solfec IS NOT NULL AND solpre > 0
        """)
        modelo = RandomForestRegressor(n_estimators=100)
        modelo.fit(df_precios[["solcan"]], df_precios["solpre"])
        prediccion = modelo.predict([[100]])
        st.write(f"Precio estimado para 100 unidades: ${prediccion[0]:.2f}")
    except Exception as e:
        st.warning("Prediccion de precios no disponible - modelo en desarrollo")

    # analisis de tendencias de stock
    st.subheader("Analisis de Tendencias de Stock")
    try:
        # stock recibido por mes; asi Prophet no se atraganta con 900+ dias
        df_stock = cargar_stock_mensual()

        # el modelo ya quedo cacheado arriba, aqui solo graficamos
        modelo = modelo_prophet(df_stock)
        futuro = modelo.make_future_dataframe(periods=6, freq="MS")
        pred = modelo.predict(futuro)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_stock["ds"], y=df_stock["y"],
                                 mode="lines+markers", name="Historico"))
        fig.add_trace(go.Scatter(x=pred["ds"], y=pred["yhat"],
                                 mode="lines", name="Pronostico",
                                 line=dict(dash="dash", color="green")))
        st.plotly_chart(fig, use_container_width=True)
        st.info("Pronostico de stock a 6 meses con Prophet")
    except Exception as e:
        st.warning(f"Analisis de stock no disponible: {e}")

# ============================================
# SECCION: DIAGNOSTICO PROPHET
# ============================================
elif opcion == "Diagnostico Prophet":
    st.header("Diagnostico del Modelo Prophet")
    st.subheader("Pronostico de stock a 6 meses con banda de incertidumbre")

    try:
        # mismos datos mensuales que en Proyecciones, para compartir el modelo
        df_stock = cargar_stock_mensual()

        modelo = modelo_prophet(df_stock)
        futuro = modelo.make_future_dataframe(periods=6, freq="MS")
        pred = modelo.predict(futuro)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_stock["ds"], y=df_stock["y"],
                                 mode="lines+markers", name="Historico"))
        # banda de incertidumbre que diagnostica el modelo
        fig.add_trace(go.Scatter(
            x=pred["ds"].tolist() + pred["ds"].tolist()[::-1],
            y=pred["yhat_upper"].tolist() + pred["yhat_lower"].tolist()[::-1],
            fill="toself", fillcolor="rgba(0,128,0,0.15)",
            line=dict(width=0), name="Incertidumbre", hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(x=pred["ds"], y=pred["yhat"],
                                 mode="lines", name="Pronostico",
                                 line=dict(dash="dash", color="green")))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("La banda sombreada muestra el rango de incertidumbre del pronostico.")

        # productos que se solicitarian cada mes segun este pronostico
        st.subheader("Productos y fechas de solicitud segun la prediccion")
        participacion = cargar_participacion_productos()
        pronostico_total = pred["yhat"].tail(6).values
        fechas_futuro = pred["ds"].tail(6)
        st.dataframe(tabla_productos_por_fecha(pronostico_total, fechas_futuro, participacion),
                     use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo generar el diagnostico: {e}")

# ============================================
# SECCION: DIAGNOSTICO NUMPY
# ============================================
elif opcion == "Diagnostico Numpy":
    st.header("Diagnostico con Regresion Lineal (numpy)")
    st.subheader("Tendencia de stock a 6 meses con banda de incertidumbre")

    try:
        import numpy as np

        df_stock = cargar_stock_mensual()

        # el clasico ajuste lineal que ya usamos en solicitudes
        x = np.arange(len(df_stock))
        y = df_stock["y"].values
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)

        # proyectar 6 meses mas; recortamos en cero la linea central,
        # la banda de abajo puede asomarse a negativo (es la duda del
        # modelo, no una promesa de stock negativo)
        x_futuro = np.arange(len(df_stock), len(df_stock) + 6)
        y_futuro = np.maximum(p(x_futuro), 0)

        # banda de incertidumbre a partir del error del ajuste
        residuo = y - p(x)
        banda = 1.96 * residuo.std()
        fechas_futuro = pd.date_range(start=df_stock["ds"].max(), periods=7, freq="MS")[1:]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_stock["ds"], y=df_stock["y"],
                                 mode="lines+markers", name="Historico"))
        # banda de incertidumbre
        fig.add_trace(go.Scatter(
            x=fechas_futuro.tolist() + fechas_futuro.tolist()[::-1],
            y=(y_futuro + banda).tolist() + (y_futuro - banda).tolist()[::-1],
            fill="toself", fillcolor="rgba(33,150,243,0.15)",
            line=dict(width=0), name="Incertidumbre", hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(x=fechas_futuro, y=y_futuro,
                                 mode="lines", name="Pronostico",
                                 line=dict(dash="dash", color="#2196F3")))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Banda basada en el error del ajuste lineal (1.96 * desviacion).")

        # productos que se solicitarian cada mes segun esta proyeccion
        st.subheader("Productos y fechas de solicitud segun la prediccion")
        participacion = cargar_participacion_productos()
        st.dataframe(tabla_productos_por_fecha(y_futuro, fechas_futuro, participacion),
                     use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo generar el diagnostico numpy: {e}")

# ============================================
# SECCION: DIAGNOSTICO KERAS
# ============================================
elif opcion == "Diagnostico Keras":
    st.header("Diagnostico con Red Neuronal (TensorFlow/Keras)")
    st.subheader("Tendencia de stock a 6 meses con banda de incertidumbre")

    try:
        df_stock = cargar_stock_mensual()

        pronostico, banda = entrenar_keras(df_stock)
        fechas_futuro = pd.date_range(start=df_stock["ds"].max(), periods=7, freq="MS")[1:]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_stock["ds"], y=df_stock["y"],
                                 mode="lines+markers", name="Historico"))
        # banda de incertidumbre
        fig.add_trace(go.Scatter(
            x=fechas_futuro.tolist() + fechas_futuro.tolist()[::-1],
            y=(pronostico + banda).tolist() + (pronostico - banda).tolist()[::-1],
            fill="toself", fillcolor="rgba(255,152,0,0.15)",
            line=dict(width=0), name="Incertidumbre", hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(x=fechas_futuro, y=pronostico,
                                 mode="lines", name="Pronostico",
                                 line=dict(dash="dash", color="#FF9800")))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Red neuronal (MLP) entrenada con los ultimos 12 meses. Banda basada en el error del ajuste.")

        # productos que se solicitarian cada mes segun esta red
        st.subheader("Productos y fechas de solicitud segun la prediccion")
        participacion = cargar_participacion_productos()
        st.dataframe(tabla_productos_por_fecha(pronostico, fechas_futuro, participacion),
                     use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo generar el diagnostico keras: {e}")

# ============================================
# SECCION: DIAGNOSTICO PYTORCH
# ============================================
elif opcion == "Diagnostico PyTorch":
    st.header("Diagnostico con Red Neuronal (PyTorch)")
    st.subheader("Tendencia de stock a 6 meses con banda de incertidumbre")

    try:
        df_stock = cargar_stock_mensual()

        pronostico, banda = entrenar_torch(df_stock)
        fechas_futuro = pd.date_range(start=df_stock["ds"].max(), periods=7, freq="MS")[1:]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_stock["ds"], y=df_stock["y"],
                                 mode="lines+markers", name="Historico"))
        # banda de incertidumbre
        fig.add_trace(go.Scatter(
            x=fechas_futuro.tolist() + fechas_futuro.tolist()[::-1],
            y=(pronostico + banda).tolist() + (pronostico - banda).tolist()[::-1],
            fill="toself", fillcolor="rgba(156,39,176,0.15)",
            line=dict(width=0), name="Incertidumbre", hoverinfo="skip"
        ))
        fig.add_trace(go.Scatter(x=fechas_futuro, y=pronostico,
                                 mode="lines", name="Pronostico",
                                 line=dict(dash="dash", color="#9C27B0")))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Red neuronal (MLP) con PyTorch. Banda basada en el error del ajuste.")

        # productos que se solicitarian cada mes segun esta red
        st.subheader("Productos y fechas de solicitud segun la prediccion")
        participacion = cargar_participacion_productos()
        st.dataframe(tabla_productos_por_fecha(pronostico, fechas_futuro, participacion),
                     use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo generar el diagnostico pytorch: {e}")

# ============================================
# PIE DE PAGINA
# ============================================
st.markdown("---")
st.caption("Proyecto Productivo IIA - Analisis de Inventario")
st.caption(f"Ultima actualizacion: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
