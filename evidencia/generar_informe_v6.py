# -*- coding: utf-8 -*-
# Generador del informe v6.
#
# En vez de rearmar el Word desde cero (que fue lo que hizo el v5 y quedó pobre,
# solo las secciones 13-16 y sin las figuras), tomo el v4 COMPLETO como base y le
# inserto la parte nueva de escalabilidad (14.6 y 15.4) más conclusiones y
# recomendaciones extra. Así no se pierde nada de lo editado en el v4.
#
# Si cambia el v4, hay que releer esto; no duplico el informe a mano porque ya
# sabemos cómo termina eso (dos lados desfasados y a llorar en la defensa).
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

RUTA_BASE = "Informe_Proyecto_Productivo_IIA_v4.docx"
RUTA_OUT = "Informe_Proyecto_Productivo_IIA_v6.docx"

# Los styleId vienen en español porque el Word nació en español (obvio).
ST_TITULO1 = "Ttulo1"
ST_TITULO2 = "Ttulo2"
ST_BULLET = "Listaconvietas"


def _parrafo(texto, style_id=None):
    """Arma un <w:p> a mano con el estilo pedido. Menos drama que pelear con python-docx."""
    p = OxmlElement("w:p")
    if style_id:
        pPr = OxmlElement("w:pPr")
        pStyle = OxmlElement("w:pStyle")
        pStyle.set(qn("w:val"), style_id)
        pPr.append(pStyle)
        p.append(pPr)
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = texto
    r.append(t)
    p.append(r)
    return p


def _buscar(doc, prefijo):
    for p in doc.paragraphs:
        if p.text.strip().startswith(prefijo):
            return p
    raise RuntimeError(f"No encontré el párrafo que empieza con: {prefijo!r}")


def _insertar_antes(ref_el, bloques):
    for texto, style_id in bloques:
        ref_el.addprevious(_parrafo(texto, style_id))


def _insertar_despues(ref_p, bloques):
    actual = ref_p._p
    for texto, style_id in bloques:
        nuevo = _parrafo(texto, style_id)
        actual.addnext(nuevo)
        actual = nuevo


def main():
    doc = Document(RUTA_BASE)

    # --- 14.6 Escalabilidad del proyecto (antes del título 15) ---
    bloques_146 = [
        ("14.6. Escalabilidad del proyecto", ST_TITULO2),
        (
            "Me pregunté si esto aguanta crecer o si se cae a la primera de cambio. "
            "La respuesta corta: aguanta, y no por magia, sino porque está armado por "
            "capas y cada una se puede tocar sin romper las demás.",
            None,
        ),
        (
            "Datos: la arquitectura medallón y el 3FN dejan crecer el volumen sin rearmar "
            "nada. Con las tablas actuales (decenas de miles de filas) PostgreSQL va sobrado; "
            "cuando esto se vaya a millones, toca particionar los hechos por fecha y listo.",
            ST_BULLET,
        ),
        (
            "Arquitectura: al estar separado en bronze, silver, normalizado y gold, puedo "
            "meter una fuente nueva (un ERP, otro proceso) sin volver a escribir lo que ya funciona.",
            ST_BULLET,
        ),
        (
            "ETL: la ingesta incremental (evidencia/etl_incremental.py) ya evita recargar todo "
            "cada vez. El modo completo (borrar y recrear gold) se queda como está porque es el "
            "que garantiza el cero diferencias de las evidencias 08 y 09; el modo incremental por "
            "upsert queda documentado en sql/gold_incremental.sql y solo se activa si se comprueba "
            "que da exactamente lo mismo.",
            ST_BULLET,
        ),
        (
            "Modelos: el Random Forest por artículo se puede entrenar en paralelo. La mejora "
            "pendiente es entrenar offline y guardar los modelos en disco, para que la app solo "
            "consulte y no entretenga a nadie esperando.",
            ST_BULLET,
        ),
        (
            "Operación: con run_etl_completo.ps1 se corre todo el flujo en orden; eso ya se puede "
            "colgar de un Task Scheduler y que trabaje solo.",
            ST_BULLET,
        ),
        (
            "App: el tablero solo lee de gold y normalizado, y los agregados ya vienen hechos, así "
            "que responde rápido. La app del informe lee un solo docx, sin copias que se desfasen.",
            ST_BULLET,
        ),
        (
            "Equipo: con REUSO.md, los handoffs y METRICAS.md, otro puede retomar esto sin adivinar. "
            "Eso es escalar gente, no solo máquinas.",
            ST_BULLET,
        ),
        (
            "Multiempresa: si algún día son varias unidades, se agrega una dimensión de empresa y se "
            "propaga a los hechos; el resto del pipeline ni se entera.",
            ST_BULLET,
        ),
        (
            "El camino lo tengo pensado por fases: (0) la base ya está, (1) orquestar la ejecución, "
            "(2) pasar gold a incremental con validación obligatoria de equivalencia, (3) entrenar los "
            "modelos offline con artefactos versionados, (4) particionar cuando el volumen lo pida y "
            "(5) abrir a multiempresa. Nada de reescribir: crecer por partes.",
            None,
        ),
    ]
    h15 = _buscar(doc, "15. Análisis económico")
    _insertar_antes(h15._p, bloques_146)

    # --- 15.1 a 15.3: subtítulos sobre el contenido que el v4 ya traía sin numerar ---
    # El v4 tenía la sección 15 en párrafos sueltos; le pongo los subtítulos para que
    # el 15.4 no quede huérfano y el índice no parezca cortado.
    _insertar_antes(
        _buscar(doc, "Analizo el costo y el beneficio")._p,
        [("15.1. Costos estimados", ST_TITULO2)],
    )
    _insertar_antes(
        _buscar(doc, "Del lado del beneficio")._p,
        [("15.2. Beneficios estimados", ST_TITULO2)],
    )
    _insertar_antes(
        _buscar(doc, "El punto de equilibrio se alcanza")._p,
        [("15.3. Punto de equilibrio", ST_TITULO2)],
    )

    # --- 15.4 Escalabilidad y economía de crecimiento (antes del título 16) ---
    bloques_154 = [
        ("15.4. Escalabilidad y economía de crecimiento", ST_TITULO2),
        (
            "La economía de esto es de reutilización, no de reinvención: lo caro ya se pagó una vez "
            "y lo que queda es mantenimiento barato.",
            None,
        ),
        (
            "Costos puntuales contra recurrentes: el desarrollo fue un golpe único; operar sale barato "
            "porque la ingesta es incremental y el proceso se puede automatizar.",
            ST_BULLET,
        ),
        (
            "Beneficios que se repiten: menos reproceso, más trazabilidad, decisiones con números "
            "validados y no con el susto.",
            ST_BULLET,
        ),
        (
            "Economía de reutilización: para otra empresa o proceso solo cambian las credenciales y el "
            "mapeo de los CSV (REUSO.md); la arquitectura se queda tal cual. Eso amortiza la inversión sola.",
            ST_BULLET,
        ),
        (
            "ROI institucional: el conocimiento queda escrito (evidencias, diccionario, handoffs), así que "
            "no depende de que yo esté disponible. Eso también es ahorro.",
            ST_BULLET,
        ),
        (
            "Escalado controlado: cada mejora (gold incremental, modelos offline, particionado) se hace por "
            "fases y sin romper la reproducibilidad, que es justamente lo que evita meter plata en reingenierías.",
            ST_BULLET,
        ),
    ]
    h16 = _buscar(doc, "16. Conclusiones")
    _insertar_antes(h16._p, bloques_154)

    # --- Conclusiones extra (después de la última conclusión existente) ---
    ref_concl = _buscar(doc, "La limitación principal es que")
    _insertar_despues(
        ref_concl,
        [
            (
                "El proyecto es escalable por evolución: está pensado para crecer con mejoras por partes "
                "(orquestación, gold incremental, modelos offline, particionado y multiempresa) y no con "
                "una reingeniería completa.",
                ST_BULLET,
            ),
            (
                "Esa escalabilidad no atropella la reproducibilidad: las mejoras propuestas pasan por las "
                "mismas validaciones que ya existen (cero diferencias en las evidencias 08 y 09, backtest "
                "contra el naive y calibración del Random Forest).",
                ST_BULLET,
            ),
        ],
    )

    # --- Recomendaciones extra (después de la última recomendación existente) ---
    ref_reco = _buscar(doc, "Escalar la solución a otros procesos")
    _insertar_despues(
        ref_reco,
        [
            (
                "Automatizar la ejecución con run_etl_completo.ps1 colgado de un Task Scheduler, para que "
                "el flujo corra solo y en orden.",
                ST_BULLET,
            ),
            (
                "Migrar gold a materialización incremental (sql/gold_incremental.sql) solo cuando el volumen "
                "lo justifique y después de comprobar que da exactamente lo mismo que el modo completo.",
                ST_BULLET,
            ),
            (
                "Entrenar los modelos offline y guardar los artefactos versionados (con semilla 42, fecha y "
                "métricas), dejando la app solo como consulta.",
                ST_BULLET,
            ),
            (
                "Evaluar el particionado de los hechos por fecha y los índices cuando el volumen supere el "
                "orden de millones de filas, sin tocar la lógica de negocio.",
                ST_BULLET,
            ),
            (
                "Si el proyecto se abre a varias unidades o empresas, agregar una dimensión de empresa y "
                "propagarla a los hechos, cuidando la compatibilidad hacia atrás.",
                ST_BULLET,
            ),
        ],
    )

    doc.save(RUTA_OUT)
    print(f"Informe v6 generado: {RUTA_OUT}")


if __name__ == "__main__":
    main()
