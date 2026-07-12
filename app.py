# =============================================
# Dashboard Principal - Proyecto IDL1 IIA
# Arquitectura Medallion + Analisis Predictivo
# =============================================

import os
import sys
import streamlit as st
import pandas as pd

# Para que pueda importar desde las carpetas del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_cliente
from consultas.capa_gold import (
    get_kpi_generales, get_demanda_mensual, get_inventario_estado,
    get_proveedores_ranking, get_top_articulos, get_evolucion_grupo
)
from graficas.estado_actual import (
    grafico_kpi_generales, grafico_distribucion_grupos,
    grafico_top_proveedores, grafico_inventario_almacen
)
from graficas.tendencias import (
    grafico_evolucion_solicitudes, grafico_evolucion_recepciones,
    grafico_evolucion_costos, grafico_demora_entregas
)
from graficas.predicciones import (
    grafico_prediccion_demanda, grafico_prediccion_costos,
    grafico_prediccion_demora, grafico_escenario_consolidado
)

# ---- Configuracion de la pagina ----
st.set_page_config(
    page_title="Dashboard IDL1 IIA",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Dashboard IDL1 IIA")
st.markdown("**Arquitectura Medallion + Analisis Predictivo**")
st.markdown("---")


# ---- Conexion a Supabase ----
try:
    cliente = get_cliente()
    st.success("Conexion a Supabase establecida correctamente")
except Exception as e:
    st.error(f"No se pudo conectar a Supabase: {e}")
    st.stop()


# ---- Sidebar con navegacion ----
st.sidebar.title("Navegacion")
seccion = st.sidebar.radio(
    "Ir a:",
    ["🏠 Estado Actual", "📈 Tendencias Historicas", "🔮 Predicciones", "📋 Datos"]
)


# =============================================
# SECCION 1: Estado Actual
# =============================================
if seccion == "🏠 Estado Actual":
    st.header("Estado Actual del Negocio")

    # KPIs rapidos arriba
    kpi = get_kpi_generales()
    if not kpi.empty:
        kpi = kpi.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Solicitudes", f"{int(kpi.get('total_solicitudes', 0)):,}")
        with col2:
            st.metric("Recepciones", f"{int(kpi.get('total_recepciones', 0)):,}")
        with col3:
            st.metric("Articulos", f"{int(kpi.get('total_articulos', 0)):,}")
        with col4:
            st.metric("Proveedores", f"{int(kpi.get('total_proveedores', 0)):,}")

        col5, col6, col7 = st.columns(3)
        with col5:
            solicitado = kpi.get('monto_total_solicitado') or 0
            st.metric("Monto Solicitado", f"${solicitado:,.0f}")
        with col6:
            recibido = kpi.get('monto_total_recibido') or 0
            st.metric("Monto Recibido", f"${recibido:,.0f}")
        with col7:
            demora = kpi.get('promedio_dias_demora') or 0
            st.metric("Demora Promedio", f"{demora} dias")

    st.markdown("---")

    # Graficos
    st.subheader("Metricas Principales")
    fig1 = grafico_kpi_generales()
    if fig1:
        st.pyplot(fig1)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Distribucion por Grupo")
        fig2 = grafico_distribucion_grupos()
        if fig2:
            st.pyplot(fig2)

    with col_b:
        st.subheader("Top Proveedores")
        fig3 = grafico_top_proveedores()
        if fig3:
            st.pyplot(fig3)

    st.subheader("Inventario por Almacen")
    fig4 = grafico_inventario_almacen()
    if fig4:
        st.pyplot(fig4)


# =============================================
# SECCION 2: Tendencias Historicas
# =============================================
elif seccion == "📈 Tendencias Historicas":
    st.header("Tendencias Historicas")
    st.markdown("Estos graficos muestran como han evolucionado los datos en el tiempo.")

    st.subheader("Evolucion de Solicitudes")
    fig5 = grafico_evolucion_solicitudes()
    if fig5:
        st.pyplot(fig5)

    st.subheader("Evolucion de Recepciones")
    fig6 = grafico_evolucion_recepciones()
    if fig6:
        st.pyplot(fig6)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("Evolucion de Costos")
        fig7 = grafico_evolucion_costos()
        if fig7:
            st.pyplot(fig7)

    with col_d:
        st.subheader("Demora de Entregas")
        fig8 = grafico_demora_entregas()
        if fig8:
            st.pyplot(fig8)


# =============================================
# SECCION 3: Predicciones
# =============================================
elif seccion == "🔮 Predicciones":
    st.header("Analisis Predictivo")
    st.markdown("Predicciones basadas en regresion lineal y media movil. "
                "Se proyectan los proximos 3 meses.")

    st.info("💡 Los graficos muestran datos historicos (linea solida) y "
            "predicciones (linea roja punteada). La zona sombreada es el periodo proyectado.")

    st.subheader("Prediccion de Demanda")
    fig9 = grafico_prediccion_demanda()
    if fig9:
        st.pyplot(fig9)

    st.subheader("Prediccion de Costos")
    fig10 = grafico_prediccion_costos()
    if fig10:
        st.pyplot(fig10)

    st.subheader("Prediccion de Dias de Entrega")
    fig11 = grafico_prediccion_demora()
    if fig11:
        st.pyplot(fig11)

    st.markdown("---")
    st.subheader("Escenario Futuro Consolidado")
    st.markdown("Resumen de todas las predicciones en un solo grafico.")
    fig12 = grafico_escenario_consolidado()
    if fig12:
        st.pyplot(fig12)


# =============================================
# SECCION 4: Datos
# =============================================
elif seccion == "📋 Datos":
    st.header("Datos Detallados")
    st.markdown("Tablas con los datos de cada capa de la arquitectura medallion.")

    sub_seccion = st.selectbox(
        "Selecciona que datos ver:",
        ["Gold - KPIs", "Gold - Demanda Mensual", "Gold - Top Articulos",
         "Gold - Proveedores", "Gold - Inventario", "Gold - Evolucion por Grupo"]
    )

    if sub_seccion == "Gold - KPIs":
        st.subheader("KPIs Generales")
        df = get_kpi_generales()
        st.dataframe(df, use_container_width=True)

    elif sub_seccion == "Gold - Demanda Mensual":
        st.subheader("Demanda Mensual")
        df = get_demanda_mensual(limite=200)
        st.dataframe(df, use_container_width=True)
        st.write(f"Total de registros: {len(df)}")

    elif sub_seccion == "Gold - Top Articulos":
        st.subheader("Top 20 Articulos Mas Solicitados")
        df = get_top_articulos(limite=20)
        st.dataframe(df, use_container_width=True)

    elif sub_seccion == "Gold - Proveedores":
        st.subheader("Ranking de Proveedores")
        df = get_proveedores_ranking(limite=50)
        st.dataframe(df, use_container_width=True)

    elif sub_seccion == "Gold - Inventario":
        st.subheader("Estado del Inventario")
        df = get_inventario_estado(limite=200)
        st.dataframe(df, use_container_width=True)
        st.write(f"Total de articulos con stock: {len(df)}")

    elif sub_seccion == "Gold - Evolucion por Grupo":
        st.subheader("Evolucion Mensual por Grupo")
        df = get_evolucion_grupo(limite=500)
        st.dataframe(df, use_container_width=True)


# ---- Pie de pagina ----
st.markdown("---")
st.markdown("Proyecto Productivo IIA - Arquitectura Medallion + Analisis Predictivo")
