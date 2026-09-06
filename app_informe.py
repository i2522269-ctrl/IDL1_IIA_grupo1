# -*- coding: utf-8 -*-
# App del informe: convierte el docx v4 en una pagina navegable.
# Si cambia el Word, cambia la app; aqui no duplicamos contenido a mano,
# porque la ultima vez que se edito el texto en dos lados quedo un desfase
# que solo se noto en la defensa. Ironias de la vida.
import streamlit as st
import pandas as pd
from docx import Document
from docx.oxml.ns import qn

RUTA_INFORME = "Informe_Proyecto_Productivo_IIA_v4.docx"

# El docx nacio en espanol (Word en espanol, obvio), asi que los styleId
# vienen como 'Ttulo1' y 'Listaconvietas'. Con este mapa no dependemos de
# que python-docx resuelva el nombre y de paso nos ahorramos el warning.
MAPA_ESTILOS = {
    "Ttulo1": "Heading 1",
    "Ttulo2": "Heading 2",
    "Listaconvietas": "List Bullet",
}


# Extrae las imagenes incrustadas de un parrafo del docx y las devuelve
# como bytes listos para st.image. Los blips guardan el rId y del part
# se saca el blob; si no hay blip, el parrafo es solo texto y vuelve vacio.
def _imagenes_parrafo(p_xml, part):
    imagenes = []
    for blip in p_xml.iter(qn("a:blip")):
        r_id = blip.get(qn("r:embed"))
        if not r_id:
            continue
        try:
            img = part.related_parts[r_id].blob
        except Exception:
            continue
        if img:
            imagenes.append(img)
    return imagenes


# Lee el contenido completo del docx en orden real (parrafos y tablas
# revueltos), devuelve bloques planos que st puede renderizar. Los bytes
# de las imagenes viajan por aca sin drama porque es toda data cruda.
def _leer_informe():
    doc = Document(RUTA_INFORME)
    part = doc.part
    bloques = []

    # los elementos del cuerpo no son los que devuelve doc.paragraphs:
    # ahi se pierden las tablas, asi que recorremos el XML tal como viene.
    for child in doc.element.body.iterchildren():
        tag = child.tag

        if tag.endswith("}tbl"):
            filas = []
            for tr in child.iter(qn("w:tr")):
                celdas = []
                for tc in tr.iter(qn("w:tc")):
                    texto = "".join(t.text or "" for t in tc.iter(qn("w:t")))
                    # las celdas fusionadas (FODA, por ejemplo) repiten el
                    # texto; con borrar las repetidas seguidas queda legible
                    if not (celdas and celdas[-1] == texto):
                        celdas.append(texto)
                if any(c.strip() for c in celdas):
                    filas.append(celdas)
            if filas:
                bloques.append({"tipo": "tabla", "tabla": filas})
            continue

        if tag.endswith("}p"):
            texto = "".join(t.text or "" for t in child.iter(qn("w:t")))
            imagenes = _imagenes_parrafo(child, part)
            if imagenes:
                bloques.append({"tipo": "imagen", "imagenes": imagenes})
            if not texto.strip():
                continue
            pPr = child.find(qn("w:pPr"))
            estilo = pPr.find(qn("w:pStyle")) if pPr is not None else None
            sid = estilo.get(qn("w:val")) if estilo is not None else None
            nombre = MAPA_ESTILOS.get(sid)
            if nombre == "Heading 1":
                bloques.append({"tipo": "h1", "texto": texto})
            elif nombre == "Heading 2":
                bloques.append({"tipo": "h2", "texto": texto})
            elif nombre == "List Bullet":
                bloques.append({"tipo": "bullet", "texto": texto})
            elif texto.startswith("Figura") or texto.startswith("Backtest") or texto.startswith("Calibracion"):
                bloques.append({"tipo": "figura", "texto": texto})
            else:
                bloques.append({"tipo": "texto", "texto": texto})

    return bloques


# Parte los bloques en secciones usando los Heading 1 como cortina.
# Todo lo que cae antes del primer titulo va a Portada (logos incluidos).
def _agrupar_secciones(bloques):
    secciones = []
    actual = None
    for b in bloques:
        if b["tipo"] == "h1":
            actual = {"titulo": b["texto"], "bloques": []}
            secciones.append(actual)
        else:
            if actual is None:
                actual = {"titulo": "Portada", "bloques": []}
                secciones.append(actual)
            if b["tipo"] == "h1":
                continue
            actual["bloques"].append(b)
    return secciones


@st.cache_data(show_spinner="Leyendo el informe...")
def cargar_secciones():
    return _agrupar_secciones(_leer_informe())


def render_tabla(filas):
    ancho = max(len(f) for f in filas)
    filas = [f + [""] * (ancho - len(f)) for f in filas]
    df = pd.DataFrame(filas[1:], columns=filas[0])
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_seccion(seccion):
    st.header(seccion["titulo"])
    for b in seccion["bloques"]:
        tipo = b["tipo"]
        if tipo == "h2":
            st.subheader(b["texto"])
        elif tipo == "bullet":
            st.markdown(f"- {b['texto']}")
        elif tipo == "figura":
            st.caption(b["texto"])
        elif tipo == "texto":
            st.markdown(b["texto"])
        elif tipo == "imagen":
            for img in b["imagenes"]:
                st.image(img, use_container_width=True)
        elif tipo == "tabla":
            render_tabla(b["tabla"])


def main():
    st.set_page_config(page_title="Informe - Proyecto Productivo IIA", layout="wide")
    secciones = cargar_secciones()

    titulos = [s["titulo"] for s in secciones]
    eleccion = st.sidebar.radio("Secciones del informe", titulos)

    # cabecera fija arriba, con la misma onda que el dashboard hermano
    st.title("Informe del Proyecto Productivo IIA")
    st.caption("Version 4 - el informe completo con el tono humano que le faltaba al Word original")

    for s in secciones:
        if s["titulo"] == eleccion:
            render_seccion(s)

    st.markdown("---")
    st.caption("Proyecto Productivo IIA - informe navegable generado desde el docx v4")
    st.caption("Repositorio: https://github.com/i2522269-ctrl/IDL1_IIA_grupo1")


if __name__ == "__main__":
    main()