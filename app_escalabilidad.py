# -*- coding: utf-8 -*-
# App de presentacion centrada SOLO en la escalabilidad del proyecto.
#
# A proposito NO toca la base de datos: en plena exposicion no quiero que un
# timeout de Supabase me deje hablando solo. Todo lo que se ve aca sale de lo
# que ya quedó documentado (REUSO.md, METRICAS.md, evidencias y el v6).
#
# Uso: streamlit run app_escalabilidad.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ============================================
# DATOS DE LA PRESENTACION (curados a mano, cero magia)
# ============================================
# Esto es una presentacion, no un ETL: si cambia el proyecto, se actualiza aca
# y listo. No lo saco de la BD porque el objetivo es contar, no consultar.

# Ejes de escalabilidad y su madurez actual (escala 1-5, evaluacion honesta).
# Modelos y Operativa van mas bajo a proposito: son los que todavia tienen tarea.
EJES = [
    ("Datos", 4, "Medallon + 3FN aguantan volumen; falta particionar los hechos cuando sean millones."),
    ("Arquitectura", 5, "Capas desacopladas: puedo meter una fuente nueva sin tocar lo que ya funciona."),
    ("ETL", 4, "Ingesta incremental y CTEs; el modo incremental de gold esta disenado, falta validarlo."),
    ("Modelos", 3, "RF por articulo paralelizable; toca entrenar offline y guardar artefactos."),
    ("Operativa", 3, "Orquestador listo; falta colgarlo de un Task Scheduler y que corra solo."),
    ("App", 4, "El tablero solo lee de gold/normalizado con agregados ya hechos."),
    ("Organizacional", 5, "REUSO.md + handoffs + diccionario: otro retoma esto sin adivinar."),
]

# Fases del roadmap. Estado: hecho / disenado / pendiente / conceptual.
ROADMAP = [
    (0, "Linea base", "Pipeline verificado y evidencias 01-11", "Hecho"),
    (1, "Orquestacion", "run_etl_completo.ps1 + Task Scheduler", "Hecho"),
    (2, "Gold incremental", "upsert con equivalencia 0 diferencias", "Disenado"),
    (3, "ML offline", "entrenar por lote y versionar artefactos", "Pendiente"),
    (4, "Particionado", "hechos por fecha cuando pase millones", "Pendiente"),
    (5, "Multiempresa", "dim_empresa y compatibilidad hacia atras", "Conceptual"),
]

# Cuellos de botella y como se tapan.
CUELLOS = [
    ("Recrear gold entero (DROP + CREATE)", "Baja hoy / Media en produccion", "Medio",
     "Modo incremental por upsert (sql/gold_incremental.sql), con equivalencia obligatoria."),
    ("Entrenar RF articulo por articulo", "Baja-Media", "Bajo-Medio",
     "Paralelizar por lotes o entrenar offline y guardar los modelos."),
    ("Modelos on-demand en la app", "Baja", "Bajo",
     "Cachear resultados o mover el entrenamiento a batch y dejar la app de solo consulta."),
    ("Consultas con historico gigante", "Baja (hoy)", "Medio (futuro)",
     "Particionar los hechos por mes/ano e indexar por FK y fecha."),
    ("Dependencia de Supabase", "Externa", "Medio",
     "Backup ya versionado; migrable a otro Postgres gestionado si hace falta."),
]

ESTADO_COLOR = {
    "Hecho": "#2e7d32",
    "Disenado": "#1565c0",
    "Pendiente": "#ef6c00",
    "Conceptual": "#6a1b9a",
}


# ============================================
# RENDER DE CADA SECCION
# ============================================

def seccion_portada():
    st.title("Escalabilidad del proyecto")
    st.caption("Proyecto Productivo IIA - Analisis predictivo de inventario y compras")
    st.markdown(
        "Esta app cuenta **una sola cosa**: si el proyecto aguanta crecer o se cae "
        "a la primera de cambio. Todo lo demas (ETL, modelos, tablero) esta en las "
        "otras apps y en el informe; aca no se repite para no marear."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Capas del pipeline", "4", "bronze a gold")
    c2.metric("Evidencias de control", "11", "01-11")
    c3.metric("Fases de escalado", "6", "fase 0 a 5")
    st.markdown("---")
    st.markdown(
        "**La respuesta corta:** si aguanta, y no por magia. Esta armado por capas, "
        "cada una se puede tocar sola, y las mejoras se hacen por partes sin reescribir "
        "el nucleo. Eso es escalar por evolucion."
    )


def seccion_que_es():
    st.header("Que significa escalar aca")
    st.markdown(
        "Escalar no es solo 'que entre mas data'. Es que el proyecto siga siendo "
        "**util, barato y creible** cuando crece el volumen, cuando se suman fuentes "
        "nuevas, cuando pasan los meses o cuando se lo lleva a otra area o empresa."
    )
    izq, der = st.columns(2)
    with izq:
        st.subheader("Escalado facil")
        st.markdown(
            "- Crece el volumen de filas.\n"
            "- Se suma una fuente nueva (un ERP, otro proceso).\n"
            "- Se reentrena con data mas reciente.\n"
            "- Otro integrante retoma el trabajo."
        )
    with der:
        st.subheader("Escalado dificil (lo que evitamos)")
        st.markdown(
            "- Rehacer el pipeline entero.\n"
            "- Romper la reproducibilidad (adios '0 diferencias').\n"
            "- Que el tablero tarde o dependa de un experto.\n"
            "- Portarlo a otra empresa desde cero."
        )


def seccion_ejes():
    st.header("Ejes de escalabilidad")
    st.caption("Cada eje con su idea y su estado actual, sin adornitos.")
    for nombre, score, detalle in EJES:
        st.markdown(f"**{nombre}** - madurez {score}/5")
        st.progress(score / 5)
        st.caption(detalle)
    st.markdown("---")
    st.info(
        "Los mas bajos (Modelos y Operativa) no son un problema: son la tarea ya "
        "identificada. Lo importante es que ninguna mejora rompe lo que ya valida."
    )


def seccion_madurez():
    st.header("Madurez por eje")
    df = pd.DataFrame(EJES, columns=["Eje", "Madurez", "Detalle"])
    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=df["Madurez"].tolist() + [df["Madurez"].iloc[0]],
                theta=df["Eje"].tolist() + [df["Eje"].iloc[0]],
                fill="toself",
                name="Madurez actual",
                line_color="#1565c0",
            )
        ]
    )
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False,
        height=520,
        margin=dict(t=40, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Evaluacion cualitativa (1-5). Modelos y Operativa son los que tienen tarea pendiente.")


def seccion_roadmap():
    st.header("Roadmap por fases")
    st.markdown(
        "El plan es crecer por partes: **nada de reescribir**. Cada fase deja el "
        "sistema funcionando y verificable, y la barrera de calidad (0 diferencias, "
        "backtest contra el naive, calibracion del RF) se mantiene en todas."
    )
    df = pd.DataFrame(ROADMAP, columns=["Fase", "Nombre", "Accion", "Estado"])
    df["Etiqueta"] = df["Fase"].astype(str) + ". " + df["Nombre"]
    fig = px.bar(
        df,
        x="Fase",
        y=[1] * len(df),
        text="Etiqueta",
        color="Estado",
        color_discrete_map=ESTADO_COLOR,
        height=380,
    )
    fig.update_traces(textposition="inside", textfont_size=13)
    fig.update_yaxes(visible=False)
    fig.update_xaxes(title="Fase", dtick=1)
    fig.update_layout(showlegend=True, margin=dict(t=30, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        df[["Fase", "Nombre", "Accion", "Estado"]],
        use_container_width=True,
        hide_index=True,
    )


def seccion_cuellos():
    st.header("Cuellos de botella y como los tapa")
    st.markdown("Ninguno es un incendio hoy. Esto es lo que vigilo y con que se resuelve.")
    df = pd.DataFrame(CUELLOS, columns=["Cuello de botella", "Probabilidad", "Impacto", "Mitigante"])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("---")
    st.success(
        "Regla de oro: cualquier mejora de rendimiento pasa primero por la misma "
        "validacion que ya existe. Si no da 0 diferencias contra el modo completo, "
        "no se activa. Eso es lo que evita escalar hacia un desastre."
    )


def seccion_mensajes():
    st.header("Mensajes clave")
    st.markdown(
        "Si solo recordaran tres cosas de la exposicion, que sean estas:"
    )
    st.markdown(
        "1. **Escala por evolucion, no por reingenieria.** Cada mejora entra por fases "
        "y deja el sistema funcionando.\n"
        "2. **Escala sin perder reproducibilidad.** Las validaciones (0 diferencias, "
        "backtest vs naive, calibracion RF) son la red de seguridad de todo cambio.\n"
        "3. **Escala tambien en gente.** REUSO.md, los handoffs y el diccionario de "
        "metricas hacen que el proyecto no dependa de una sola persona."
    )
    st.markdown("---")
    st.markdown(
        "**Cierre:** el proyecto no esta pensado para Big Data ni lo necesita. Esta "
        "pensado para crecer de forma ordenada, barata y auditable. Y eso ya es un "
        "indicador sano de buen diseno."
    )


SECCIONES = {
    "1. Portada": seccion_portada,
    "2. Que es escalar aqui": seccion_que_es,
    "3. Ejes de escalabilidad": seccion_ejes,
    "4. Madurez por eje": seccion_madurez,
    "5. Roadmap por fases": seccion_roadmap,
    "6. Cuellos de botella": seccion_cuellos,
    "7. Mensajes clave": seccion_mensajes,
}


def main():
    st.set_page_config(
        page_title="Escalabilidad - Proyecto Productivo IIA",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Escalabilidad")
    st.sidebar.caption("Proyecto Productivo IIA")
    eleccion = st.sidebar.radio("Secciones", list(SECCIONES.keys()))

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "App de presentacion. No consulta la base de datos a proposito: "
        "en la exposicion quiero contar, no pelear con un timeout."
    )

    SECCIONES[eleccion]()

    st.markdown("---")
    st.caption("Proyecto Productivo IIA - escalabilidad del pipeline de inventario y compras")


if __name__ == "__main__":
    main()
