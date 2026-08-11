import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv
from sklearn.linear_model import LinearRegression
from datetime import datetime

load_dotenv()

st.set_page_config(page_title="Proyecto Productivo IIA", layout="wide")

# ============================================
# CONFIGURACION DE CREDENCIALES
# ============================================
def config(key, default=None):
    """Lee una configuracion desde st.secrets o variables de entorno."""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


# ============================================
# CONEXION A SUPABASE
# ============================================
@st.cache_resource
def conectar():
    return psycopg2.connect(
        host=config("DB_HOST"),
        port=int(config("DB_PORT", "5432")),
        dbname=config("DB_NAME", "postgres"),
        user=config("DB_USER"),
        password=config("DB_PASSWORD"),
    )

def cargar_datos(consulta):
    conn = conectar()
    return pd.read_sql(consulta, conn)

# ============================================
# PAGINA PRINCIPAL
# ============================================
st.title("Proyecto Productivo IIA")
st.subheader("Analisis de datos de inventario y compras")

# barra lateral con opciones
opcion = st.sidebar.selectbox(
    "Selecciona una seccion",
    ["Resumen General", "Solicitudes", "Recepcion", "Articulos", "Proyecciones"]
)

# ============================================
# SECCION: RESUMEN GENERAL
# ============================================
if opcion == "Resumen General":
    st.header("Resumen General")

    try:
        col1, col2, col3, col4 = st.columns(4)

        total_solicitudes = cargar_datos("SELECT COUNT(*) as total FROM silver.solicitudes")["total"][0]
        total_recepcion = cargar_datos("SELECT COUNT(*) as total FROM silver.recepcion")["total"][0]
        total_articulos = cargar_datos("SELECT COUNT(DISTINCT artcitem) as total FROM silver.maestro_articulos")["total"][0]
        total_proveedores = cargar_datos("SELECT COUNT(*) as total FROM silver.proveedores")["total"][0]

        col1.metric("Solicitudes", f"{total_solicitudes:,}")
        col2.metric("Recepciones", f"{total_recepcion:,}")
        col3.metric("Articulos", f"{total_articulos:,}")
        col4.metric("Proveedores", f"{total_proveedores:,}")

        st.markdown("---")

        # articulos por grupo
        st.subheader("Articulos por Grupo")
        df_grupos = cargar_datos("""
            SELECT g.nombre as grupo, COUNT(DISTINCT m.artcitem) as cantidad
            FROM silver.maestro_articulos m
            JOIN silver.grupos g ON m.artgrinv = g.artgrinv
            GROUP BY g.nombre
            ORDER BY cantidad DESC
        """)
        fig = px.bar(df_grupos, x="grupo", y="cantidad", color="cantidad",
                     color_continuous_scale="Blues")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo cargar el resumen general: {e}")

# ============================================
# SECCION: SOLICITUDES
# ============================================
elif opcion == "Solicitudes":
    st.header("Analisis de Solicitudes")

    try:
        df_sol = cargar_datos("""
            SELECT DATE_TRUNC('month', solfec) as mes,
                   COUNT(*) as cantidad,
                   SUM(solcan) as total_cantidad,
                   AVG(solpre) as precio_promedio
            FROM silver.solicitudes
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
        df_top = cargar_datos("""
            SELECT artcitem, artdes, COUNT(*) as veces_solicitado,
                   SUM(solcan) as total_cantidad
            FROM silver.solicitudes
            GROUP BY artcitem, artdes
            ORDER BY veces_solicitado DESC
            LIMIT 15
        """)
        fig = px.bar(df_top, x="artcitem", y="veces_solicitado", color="total_cantidad",
                     color_continuous_scale="Reds")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo cargar el analisis de solicitudes: {e}")

# ============================================
# SECCION: RECEPCION
# ============================================
elif opcion == "Recepcion":
    st.header("Analisis de Recepcion")

    try:
        df_rec = cargar_datos("""
            SELECT DATE_TRUNC('month', nrcfec) as mes,
                   COUNT(*) as recepciones,
                   SUM(nrdcac) as total_recibido,
                   AVG(solpre) as precio_promedio
            FROM silver.recepcion
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
            SELECT solpro as proveedor, COUNT(*) as recepciones,
                   SUM(solcan) as cantidad_total
            FROM silver.recepcion
            WHERE solpro IS NOT NULL
            GROUP BY solpro
            ORDER BY cantidad_total DESC
            LIMIT 10
        """)
        fig = px.pie(df_prov, values="cantidad_total", names="proveedor",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo cargar el analisis de recepcion: {e}")

# ============================================
# SECCION: ARTICULOS
# ============================================
elif opcion == "Articulos":
    st.header("Analisis de Articulos")

    try:
        df_stock = cargar_datos("""
            SELECT artcitem, artdes, ubialm, ubistock
            FROM silver.articulos
            WHERE ubistock IS NOT NULL
            ORDER BY ubistock DESC
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
            FROM silver.maestro_articulos
            WHERE artmed IS NOT NULL
            GROUP BY artmed
            ORDER BY cantidad DESC
        """)
        fig = px.pie(df_med, values="cantidad", names="artmed")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo cargar el analisis de articulos: {e}")

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
            FROM silver.solicitudes
            WHERE solfec IS NOT NULL
            GROUP BY DATE_TRUNC('month', solfec)
            ORDER BY mes
        """)

        if len(df_proy) >= 2:
            df_proy["mes_num"] = range(len(df_proy))
            x = df_proy["mes_num"].values
            y = df_proy["cantidad"].values

            # ajuste lineal
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)

            # predecir 6 meses mas
            x_future = np.arange(len(df_proy), len(df_proy) + 6)
            y_future = p(x_future)

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
        else:
            st.info("Datos insuficientes para proyectar solicitudes")
    except Exception as e:
        st.error(f"Error en proyeccion de solicitudes: {e}")

    # prediccion de precios futuros
    st.subheader("Prediccion de Precios Futuros")
    try:
        df_precios = cargar_datos("""
            SELECT solcan, solpre
            FROM silver.solicitudes
            WHERE solcan > 0 AND solpre > 0
        """)
        df_precios = df_precios.dropna()

        if len(df_precios) >= 30:
            # filtrar valores atipicos para que el modelo sea estable
            limite = df_precios["solpre"].quantile(0.98)
            df_precios = df_precios[df_precios["solpre"] <= limite]

            modelo = LinearRegression()
            modelo.fit(df_precios[["solcan"]], df_precios["solpre"])
            r2 = modelo.score(df_precios[["solcan"]], df_precios["solpre"])

            cantidad = st.slider(
                "Cantidad a predecir",
                min_value=int(df_precios["solcan"].min()),
                max_value=int(df_precios["solcan"].max()),
                value=int(df_precios["solcan"].median())
            )
            precio = float(modelo.predict([[cantidad]])[0])

            c1, c2, c3 = st.columns(3)
            c1.metric("Precio estimado", f"${precio:,.2f}")
            c2.metric("Precio promedio historico", f"${df_precios['solpre'].mean():,.2f}")
            c3.metric("Precision del modelo (R2)", f"{r2:.2%}")

            fig = px.scatter(
                df_precios.sample(min(5000, len(df_precios))),
                x="solcan", y="solpre",
                opacity=0.4, title="Precio vs Cantidad solicitada"
            )
            x_linea = np.linspace(df_precios["solcan"].min(), df_precios["solcan"].max(), 50)
            fig.add_trace(go.Scatter(
                x=x_linea, y=modelo.predict(x_linea.reshape(-1, 1)),
                mode="lines", name="Regresion lineal"
            ))
            fig.add_vline(x=cantidad, line_dash="dash",
                          annotation_text=f"cantidad={cantidad}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Datos insuficientes para la prediccion de precios")
    except Exception as e:
        st.error(f"Error en prediccion de precios: {e}")

    # analisis de tendencias de stock
    st.subheader("Analisis de Tendencias de Stock")
    try:
        df_stock = cargar_datos("""
            SELECT DATE_TRUNC('month', nrcfec) as mes, SUM(artstock) as stock_total
            FROM silver.recepcion
            WHERE nrcfec IS NOT NULL
            GROUP BY DATE_TRUNC('month', nrcfec)
            ORDER BY mes
        """)

        if len(df_stock) >= 3:
            df_stock["mes_num"] = range(len(df_stock))
            z = np.polyfit(df_stock["mes_num"], df_stock["stock_total"], 1)
            p = np.poly1d(z)

            x_future = np.arange(len(df_stock), len(df_stock) + 6)
            y_future = p(x_future)

            df_futuro = pd.DataFrame({
                "mes": pd.date_range(start=df_stock["mes"].max(), periods=7, freq="MS")[1:],
                "stock_total": y_future
            })

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_stock["mes"], y=df_stock["stock_total"],
                                     mode="lines+markers", name="Historico"))
            fig.add_trace(go.Scatter(x=df_futuro["mes"], y=df_futuro["stock_total"],
                                     mode="lines+markers", name="Proyeccion",
                                     line=dict(dash="dash", color="green")))
            st.plotly_chart(fig, use_container_width=True)
            st.info("Proyeccion de stock recibido basada en tendencia lineal")
        else:
            st.info("Datos insuficientes para el analisis de stock")
    except Exception as e:
        st.error(f"Error en analisis de stock: {e}")

# ============================================
# PIE DE PAGINA
# ============================================
st.markdown("---")
st.caption("Proyecto Productivo IIA - Analisis de Inventario")
st.caption(f"Ultima actualizacion: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
