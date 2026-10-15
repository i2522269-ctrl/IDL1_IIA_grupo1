# -*- coding: utf-8 -*-
# Generador del informe v7 (la presentación final).
#
# El v6 me dejaba bien las secciones 13-16 pero "a ras": una línea por idea. Para
# la entrega final quería desarrollarlas a fondo SIN tocar el resto. Así que tomo
# el v6 entero, dejo la portada y las secciones 1-12 intactas, y reemplazo solo el
# bloque 13-16. Los bloques de después (Actualización, Cumplimiento, Referencias,
# Anexos) también se quedan tal cual.
#
# Cómo lo hago: ubico el título "13..." y el título "Actualización del proyecto"
# en el cuerpo del documento, borro lo que hay entre medio y meto lo nuevo justo
# antes de "Actualización". Nada de rearmar el Word a mano: eso ya lo sufrimos con
# el v5 y quedó pobre (solo 13-16 y sin figuras). No lo repetimos.
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

RUTA_BASE = "Informe_Proyecto_Productivo_IIA_v6.docx"
RUTA_OUT = "Informe_Proyecto_Productivo_IIA_v7.docx"

# Los styleId vienen en español porque el Word nació en español (obvio).
ST_TITULO1 = "Ttulo1"
ST_TITULO2 = "Ttulo2"
ST_BULLET = "Listaconvietas"
ST_TABLA = "Tablanormal2"  # el "Plain Table 2" del documento, para que las tablas combinen


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


def _texto_de(el):
    return "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()


def _crear_tabla(doc, headers, rows):
    """Crea una tabla con el mismo estilo del documento y la devuelve como elemento <w:tbl>."""
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    # Le clavo el styleId directo; pelearme con el nombre localizado del estilo es perder el tiempo.
    tblPr = t._tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        t._tbl.insert(0, tblPr)
    for s in tblPr.findall(qn("w:tblStyle")):
        tblPr.remove(s)
    st = OxmlElement("w:tblStyle")
    st.set(qn("w:val"), ST_TABLA)
    tblPr.insert(0, st)
    for j, h in enumerate(headers):
        t.rows[0].cells[j].text = str(h)
    for i, fila in enumerate(rows):
        for j, v in enumerate(fila):
            t.rows[i + 1].cells[j].text = str(v)
    return t._tbl


def _bloque_a_elemento(doc, bloque):
    tipo, valor = bloque
    if tipo == "p":
        return _parrafo(valor, None)
    if tipo == "b":
        return _parrafo(valor, ST_BULLET)
    if tipo == "h1":
        return _parrafo(valor, ST_TITULO1)
    if tipo == "h2":
        return _parrafo(valor, ST_TITULO2)
    if tipo == "tabla":
        return _crear_tabla(doc, valor[0], valor[1])
    raise ValueError(f"Tipo de bloque desconocido: {tipo!r}")


# ---------------------------------------------------------------------------
# Todo el contenido nuevo de 13-16, desarrollado a fondo.
# ---------------------------------------------------------------------------
CONTENIDO = [
    # ================= 13 =================
    ("h1", "13. Establecimiento de métricas"),
    (
        "p",
        "Antes de medir cualquier cosa me puse de acuerdo conmigo mismo sobre qué mide cada "
        "número. Suena obvio, pero de eso depende que el tablero, el informe y el diccionario digan "
        "lo mismo; la última vez que dos lados contaron distinto nos tocó explicar de más.",
    ),
    ("h2", "13.1. Concepto y propósito"),
    (
        "p",
        "Las métricas no son adornos del tablero: son el idioma con el que compras discute. Por eso "
        "cada una tiene nombre único, definición, fórmula y fuente declarada. Regla simple: si un "
        "número no está en este diccionario, no se usa.",
    ),
    ("h2", "13.2. Convención de nombres"),
    (
        "p",
        "Para no inventar nombres cada vez que alguien mira los datos, uso minúsculas con guion bajo "
        "y un prefijo que deja ver de dónde sale la métrica.",
    ),
    ("b", "total_ para conteos de filas o eventos (total_atenciones)."),
    ("b", "lead_time_ y desviacion_ para tiempos de entrega del proveedor."),
    ("b", "volumen_ y cantidad_ para sumas de cantidades."),
    ("b", "precio_ para valores monetarios."),
    ("b", "frecuencia_ para conteo de pedidos distintos."),
    (
        "b",
        "R2, MAE, RMSE y MAPE para precisión de modelos; en mayúsculas porque son siglas y así las "
        "nombra todo el mundo.",
    ),
    ("h2", "13.3. Métricas operativas"),
    ("p", "Salen de las tablas gold y son las que sostienen las decisiones de compra."),
    (
        "tabla",
        (
            ["Métrica", "Definición", "Fórmula", "Fuente"],
            [
                ["total_atenciones", "Recepciones que atendió cada proveedor", "COUNT(*)", "gold.metricas_prediccion_proveedor"],
                ["lead_time_promedio_dias", "Días promedio entre solicitud y recepción", "AVG(nrcfec - solfec)", "gold.metricas_prediccion_proveedor"],
                ["desviacion_lead_time", "Variabilidad del tiempo de entrega", "STDDEV(nrcfec - solfec)", "gold.metricas_prediccion_proveedor"],
                ["volumen_total_suministrado", "Unidades totales recibidas por proveedor", "SUM(solcan)", "gold.metricas_prediccion_proveedor"],
                ["cantidad_total_despachada", "Unidades por artículo y mes", "SUM(solcan)", "gold.prediccion_demanda_mensual"],
                ["frecuencia_pedidos", "Pedidos distintos por artículo y mes", "COUNT(DISTINCT solnum)", "gold.prediccion_demanda_mensual"],
                ["precio_promedio_pactado", "Precio promedio por artículo y mes", "AVG(solpre)", "gold.prediccion_demanda_mensual"],
                ["ultimo_stock_registrado", "Último stock del mes por artículo", "artstock de la última recepción", "gold.prediccion_demanda_mensual"],
                ["participacion", "Peso del artículo en el stock de 12 meses", "SUM(artstock) / total", "derivada en la app"],
            ],
        ),
    ),
    ("h2", "13.4. Métricas de precisión de los modelos"),
    (
        "p",
        "Para decir si un modelo sirve no basta con que la línea se vea bonita; hay que medirlo contra "
        "la realidad.",
    ),
    (
        "tabla",
        (
            ["Métrica", "Qué mide", "Fórmula", "Uso"],
            [
                ["R2", "Proporción de la variabilidad explicada (1 perfecto, 0 equivale a tirar la media)", "1 - SSE/SST", "Random Forest de precios"],
                ["MAE", "Error promedio en las mismas unidades", "mean(|real - predicho|)", "Random Forest y backtest"],
                ["RMSE", "Como el MAE pero castiga fuerte los errores grandes", "sqrt(mean((real - predicho)^2))", "Backtest de pronósticos"],
                ["MAPE", "Error promedio en porcentaje", "mean(|real - predicho| / real) * 100", "Backtest (ojo con meses en cero)"],
            ],
        ),
    ),
    (
        "p",
        "Regla que me puse: un modelo cuyo MAE no le gana al naive no se presenta como logro. Si no "
        "supera al de 'repetir el último valor', no aporta.",
    ),
    ("h2", "13.5. Métricas del tablero"),
    (
        "p",
        "Estas se calculan en vivo sobre las capas normalizadas, para que el tablero siempre muestre "
        "el estado actual y no una foto vieja.",
    ),
    (
        "tabla",
        (
            ["Métrica del tablero", "Fórmula", "Fuente"],
            [
                ["Total solicitudes", "COUNT(*)", "normalizado.fact_solicitudes"],
                ["Total recepciones", "COUNT(*)", "normalizado.fact_recepcion"],
                ["Artículos en catálogo", "COUNT(*)", "normalizado.maestro_articulos"],
                ["Total proveedores", "COUNT(*)", "normalizado.proveedores"],
                ["Stock del mes", "SUM(artstock) mensual", "normalizado.fact_recepcion"],
            ],
        ),
    ),
    ("h2", "13.6. Reglas de gobernanza"),
    ("p", "Para que el diccionario siga sirviendo y no se degrade con el tiempo:"),
    ("b", "Si una métrica cambia de nombre, se actualiza el diccionario en el mismo commit; si no, no se sube."),
    ("b", "Las fórmulas van siempre sobre gold o normalizado, nunca sobre bronze directo."),
    ("b", "Los modelos usan semilla fija 42; si alguien la cambia, avisa antes y con razón."),
    ("b", "Los pronósticos se validan con la evidencia 10; un modelo que no supera al naive no se presenta como logro."),
    ("b", "El diccionario (METRICAS.md) es la fuente de verdad del tablero y del informe."),

    # ================= 14 =================
    ("h1", "14. Comparación de línea de base vs analítica"),
    (
        "p",
        "La línea de base es la situación sin el proyecto: se compra a ojo, con la experiencia y el "
        "último pedido. La propuesta analítica es la que trae este trabajo: datos procesados, métricas "
        "definidas y modelos de demanda. Comparo las dos en lo técnico, lo económico y lo institucional, "
        "y cierro con la escalabilidad.",
    ),
    ("h2", "14.1. Comparación técnica del enfoque"),
    ("p", "Aquí la diferencia no es de matices: es pasar de hojas sueltas a un flujo verificable."),
    (
        "tabla",
        (
            ["Dimensión", "Línea de base", "Enfoque analítico (implementado)"],
            [
                ["Arquitectura de datos", "Reportes estáticos (Excel), cálculos dispersos", "Arquitectura medallón (bronze a silver a normalizado a gold), trazable por capas"],
                ["Calidad y trazabilidad", "Origen de los números poco auditable", "ETL por fases con controles, conteos y evidencias 01-11"],
                ["Integridad de datos", "Duplicados, nulos y redundancias", "Normalización 3FN con dimensiones, hechos y llaves foráneas"],
                ["Reproducibilidad", "Cambia según quién corre el archivo", "Determinista (semilla 42), con 0 diferencias en las evidencias 08 y 09"],
                ["Validación de modelos", "Se juzga a ojo o por una gráfica", "Backtest contra el naive (MAE, RMSE, MAPE); solo se presenta el modelo que le gana"],
                ["Calibración", "No se calibra", "Grid de hiperparámetros del Random Forest, por artículo y agregado"],
                ["Casos atípicos", "Se ignoran o se fuerzan", "Los huérfanos se conservan leyendo la demanda desde silver.recepcion (957 sin pedido y 1 fuera de catálogo)"],
                ["Evidencias", "No existen", "Cadena completa 01-11, verificable y versionada"],
            ],
        ),
    ),
    ("h2", "14.2. Comparación económica y de eficiencia"),
    ("p", "En plata, la línea de base no es gratis: cuesta en errores de compra y en horas perdidas."),
    (
        "tabla",
        (
            ["Indicador", "Línea de base", "Propuesta analítica"],
            [
                ["Tiempo de reproceso", "Manual, con horas encima y propenso a errores", "Reproducible y automatizable; la ingesta incremental evita recargar todo"],
                ["Costo de calidad de datos", "Los errores se detectan tarde", "Detección temprana por fases, con validaciones cruzadas y 0 diferencias"],
                ["Eficiencia de compra", "Según el último pedido o la intuición", "Pronósticos a 6 meses y Random Forest de precios para anticipar"],
                ["Reutilización", "Difícil de portar", "Se reutiliza la arquitectura; solo cambian credenciales y mapeo de CSV (REUSO.md)"],
                ["Mantenimiento", "Depende de quién lo hizo", "Conocimiento explícito: ETL, SQL, evidencias, diccionario y handoffs"],
            ],
        ),
    ),
    ("h2", "14.3. Impacto en la capacidad institucional y legitimidad social"),
    ("p", "Lo menos visible es lo que más pesa: que el conocimiento deje de estar en una sola cabeza."),
    (
        "tabla",
        (
            ["Dimensión", "Línea de base", "Propuesta analítica"],
            [
                ["Capacidad institucional", "Fragmentada y difícil de transferir", "Transferencia estructurada con handoffs y REUSO.md"],
                ["Lenguaje común", "Cada área interpreta los números a su manera", "Diccionario único de métricas, con fórmula y fuente"],
                ["Legitimidad técnica", "Poca auditabilidad y baja confianza", "Cadena de verificación 01-11 con hechos (0 diferencias, backtest, calibración)"],
                ["Transparencia", "Metodología implícita", "Método explícito: SQL versionado, ETL y decisiones justificadas con datos"],
                ["Formación y autonomía", "Dependencia de un experto", "Scripts reproducibles y guía de despliegue"],
                ["Ética y seguridad", "Riesgo de credenciales en el código", "Credenciales fuera del código (.env y secrets, ignorados por git)"],
            ],
        ),
    ),
    ("h2", "14.4. Síntesis de comparación"),
    (
        "p",
        "En las tres patas el enfoque analítico le gana a la línea de base. Técnicamente: mejor calidad "
        "de datos y reproducibilidad. Económicamente: menos costo por errores de compra a cambio de una "
        "inversión inicial única (que en software fue cero). Institucionalmente: el conocimiento que "
        "estaba en la cabeza pasa a estar documentado y auditable. No es una mejora de forma, es pasar de "
        "descriptivo a predictivo y de intuición a evidencia.",
    ),
    ("h2", "14.5. Argumento final de comparación"),
    (
        "p",
        "La conclusión es clara: con inversión mínima en infraestructura (herramientas gratuitas) se "
        "pasa de un modelo reactivo y de ojo a uno proactivo y con datos. La línea de base sirve para el "
        "día a día, pero no escala ni se puede auditar; el enfoque analítico deja capacidad instalada, "
        "reutilizable en otro proceso o empresa. Ese, y no solo los modelos, es el verdadero diferencial.",
    ),
    ("h2", "14.6. Escalabilidad del proyecto"),
    (
        "p",
        "Me pregunté si esto aguanta crecer o se cae a la primera de cambio. La respuesta corta: "
        "aguanta, y no por magia, sino porque está armado por capas y cada una se puede tocar sin "
        "romper las demás.",
    ),
    ("h2", "14.6.1. Ejes de escalabilidad"),
    (
        "b",
        "Datos: la arquitectura medallón y el 3FN dejan crecer el volumen sin rearmar nada. Con las "
        "tablas actuales (decenas de miles de filas) PostgreSQL va sobrado; cuando sean millones, toca "
        "particionar los hechos por fecha.",
    ),
    (
        "b",
        "Arquitectura: al estar separado en bronze, silver, normalizado y gold, se puede sumar una "
        "fuente nueva (un ERP, otro proceso) sin tocar lo que ya funciona.",
    ),
    (
        "b",
        "ETL: la ingesta incremental ya evita recargar todo. El modo completo (borrar y recrear gold) se "
        "mantiene porque garantiza el 0 diferencias de las evidencias 08 y 09; el modo incremental por "
        "upsert está documentado en sql/gold_incremental.sql y solo se activa si se comprueba que da "
        "exactamente lo mismo.",
    ),
    (
        "b",
        "Modelos: el Random Forest por artículo se puede entrenar en paralelo. La mejora pendiente es "
        "entrenar offline y guardar los modelos en disco, para que la app solo consulte.",
    ),
    (
        "b",
        "Operación: con run_etl_completo.ps1 se corre todo el flujo en orden; eso se puede colgar de un "
        "Task Scheduler y que trabaje solo.",
    ),
    (
        "b",
        "App: el tablero solo lee de gold y normalizado, y los agregados ya vienen hechos, así que "
        "responde rápido; la app del informe lee un solo docx, sin copias que se desfasen.",
    ),
    (
        "b",
        "Organizacional: con REUSO.md, los handoffs y METRICAS.md, otro retoma esto sin adivinar. Eso es "
        "escalar gente, no solo máquinas.",
    ),
    (
        "b",
        "Multiempresa: si algún día son varias unidades, se agrega una dimensión de empresa y se propaga "
        "a los hechos; el resto del pipeline ni se entera.",
    ),
    ("h2", "14.6.2. Roadmap por fases"),
    ("p", "El camino está pensado por fases; cada una deja el sistema funcionando y verificable:"),
    (
        "tabla",
        (
            ["Fase", "Nombre", "Acción", "Estado"],
            [
                ["0", "Línea base", "Pipeline verificado y evidencias 01-11", "Hecho"],
                ["1", "Orquestación", "run_etl_completo.ps1 y Task Scheduler", "Hecho"],
                ["2", "Gold incremental", "upsert con equivalencia de 0 diferencias", "Diseñado"],
                ["3", "Modelos offline", "entrenar por lote y versionar artefactos", "Pendiente"],
                ["4", "Particionado", "particionar hechos por fecha cuando pase millones", "Pendiente"],
                ["5", "Multiempresa", "dimensión de empresa con compatibilidad hacia atrás", "Conceptual"],
            ],
        ),
    ),
    ("h2", "14.6.3. Cuellos de botella y mitigantes"),
    (
        "tabla",
        (
            ["Cuello de botella", "Probabilidad", "Impacto", "Mitigante"],
            [
                ["Recrear gold entero (DROP y CREATE)", "Baja hoy, media en producción", "Medio", "Modo incremental por upsert, con equivalencia obligatoria"],
                ["Entrenar el Random Forest artículo por artículo", "Baja-media", "Bajo-medio", "Paralelizar por lotes o entrenar offline"],
                ["Modelos on-demand en la app", "Baja", "Bajo", "Cachear o mover el entrenamiento a batch"],
                ["Consultas con histórico gigante", "Baja hoy", "Medio a futuro", "Particionar los hechos e indexar por fecha y llave foránea"],
                ["Dependencia de Supabase", "Externa", "Medio", "Backup versionado y migrable a otro Postgres gestionado"],
            ],
        ),
    ),

    # ================= 15 =================
    ("h1", "15. Análisis económico de la propuesta a implementar"),
    (
        "p",
        "Analizo el costo y el beneficio de implementar la propuesta. El software es de código abierto y "
        "los servicios usados son gratuitos en sus planes básicos, así que el costo real es casi solo "
        "desarrollo y mantenimiento.",
    ),
    ("h2", "15.1. Costos estimados"),
    (
        "tabla",
        (
            ["Concepto", "Estimación", "Observación"],
            [
                ["Infraestructura", "Bajo", "PostgreSQL/Supabase existente; la incidencia fue de disponibilidad, no de costo"],
                ["Desarrollo e implementación", "Puntual (ya realizado)", "Pipeline ETL, validaciones, evidencias y app funcionando"],
                ["Operación y mantenimiento", "Muy bajo", "Scripts e ingesta incremental; automatizable con Task Scheduler"],
                ["Formación", "Bajo", "README, METRICAS, REUSO y handoffs reducen la curva de aprendizaje"],
            ],
        ),
    ),
    ("h2", "15.2. Beneficios estimados"),
    (
        "p",
        "El ahorro sale de comprar mejor: al proyectar la demanda se evitan las compras de urgencia "
        "(que casi siempre pagan sobreprecio y fletes) y se reduce la plata parada en inventario sobrante.",
    ),
    (
        "tabla",
        (
            ["Beneficio", "Tipo", "Explicación"],
            [
                ["Reducción de reproceso", "Económico", "Las validaciones por fases evitan rehacer cálculos e informes"],
                ["Mejor planeación de compras", "Económico/operativo", "Pronósticos y RF de precios permiten anticipar y evitar sobrestock o quiebres"],
                ["Menor riesgo de error", "Estratégico", "Métricas validadas contra el naive y calibración sistemática"],
                ["Capital intelectual preservado", "Institucional", "El conocimiento queda explícito y no depende de una persona"],
                ["Reutilización", "A futuro", "Se puede portar a otra empresa con ajustes menores"],
            ],
        ),
    ),
    ("h2", "15.3. Punto de equilibrio"),
    (
        "p",
        "El punto de equilibrio se alcanza con solo evitar unas cuantas compras mal hechas al mes. No "
        "mido el ahorro exacto sin una prueba piloto, pero como la inversión en software fue cero y el "
        "mantenimiento es bajo, basta con que el modelo evite algunos pedidos de urgencia para que la "
        "propuesta se pague sola.",
    ),
    ("h2", "15.4. Escalabilidad y economía de crecimiento"),
    (
        "p",
        "La economía de esto es de reutilización, no de reinvención: lo caro ya se pagó una vez y lo que "
        "queda es mantenimiento barato.",
    ),
    (
        "b",
        "Costos puntuales contra recurrentes: el desarrollo fue un golpe único; operar sale barato porque "
        "la ingesta es incremental y el proceso se puede automatizar.",
    ),
    (
        "b",
        "Beneficios que se repiten: menos reproceso, más trazabilidad y decisiones con números validados.",
    ),
    (
        "b",
        "Economía de reutilización: para otra empresa o proceso solo cambian las credenciales y el mapeo "
        "de los CSV (REUSO.md); la arquitectura se queda tal cual.",
    ),
    (
        "b",
        "ROI institucional: el conocimiento queda escrito, así que no depende de que yo esté disponible.",
    ),
    (
        "b",
        "Escalado controlado: cada mejora (gold incremental, modelos offline, particionado) se hace por "
        "fases y sin romper la reproducibilidad, que es lo que evita meter plata en reingenierías.",
    ),

    # ================= 16 =================
    ("h1", "16. Conclusiones y recomendaciones"),
    ("h2", "16.1. Conclusiones"),
    (
        "b",
        "Armé un pipeline ETL completo y verificado (bronze a silver a normalizado a gold) que convierte "
        "unas 85 mil transacciones crudas en información confiable.",
    ),
    ("b", "La arquitectura medallón, con las evidencias 01-09, deja todo el flujo trazable y reproducible."),
    (
        "b",
        "El tablero Streamlit reúne los indicadores y cuatro enfoques de pronóstico (regresión, Prophet, "
        "Keras y PyTorch) para comparar y elegir.",
    ),
    (
        "b",
        "El trabajo demuestra que se puede hacer análisis predictivo de inventario con poco presupuesto, "
        "usando herramientas abiertas.",
    ),
    (
        "b",
        "La reproducibilidad está demostrada: 0 diferencias entre el gold regenerado y las consultas "
        "esperadas (evidencias 08 y 09).",
    ),
    (
        "b",
        "Los modelos están validados, no asumidos: backtest contra el naive (evidencia 10) y calibración "
        "del Random Forest (evidencia 11).",
    ),
    (
        "b",
        "El proyecto es escalable por evolución: crece con mejoras por partes (orquestación, gold "
        "incremental, modelos offline, particionado y multiempresa) y no con una reingeniería.",
    ),
    (
        "b",
        "Esa escalabilidad no atropella la reproducibilidad: cada mejora pasa por las mismas "
        "validaciones que ya existen.",
    ),
    ("b", "La limitación principal es que falta validar con el negocio real y que depender de un historial de calidad siempre es un riesgo."),
    ("h2", "16.2. Recomendaciones"),
    ("b", "Validar los pronósticos contra el comportamiento real del negocio y ajustar los modelos con esos resultados."),
    ("b", "Integrar el pipeline con un ERP o fuente en tiempo real mediante la ingesta incremental programada."),
    ("b", "Mantener y calibrar el Random Forest de precios a medida que crezca el historial."),
    ("b", "Documentar y estandarizar las métricas para que compras adopte el tablero."),
    ("b", "Escalar la solución a otros procesos o empresas siguiendo el checklist de REUSO.md."),
    ("b", "Automatizar la ejecución con run_etl_completo.ps1 colgado de un Task Scheduler."),
    (
        "b",
        "Migrar gold a materialización incremental solo cuando el volumen lo justifique y tras comprobar "
        "0 diferencias contra el modo completo.",
    ),
    ("b", "Entrenar los modelos offline y guardar artefactos versionados (semilla 42, fecha y métricas)."),
    ("b", "Evaluar el particionado de los hechos y los índices cuando el volumen pase el orden de millones."),
    ("b", "Si se abre a varias unidades, agregar una dimensión de empresa cuidando la compatibilidad hacia atrás."),
    ("b", "Actualizar la nota de infraestructura del informe cuando Supabase se recupere, manteniendo el registro del backup."),
    (
        "b",
        "Preservar la cadena de evidencias 01-11: al regenerar capas, renovar las evidencias en vez de "
        "arrastrar números viejos.",
    ),
    ("h2", "16.3. Evidencia que respalda las conclusiones"),
    (
        "p",
        "No pido que me crean: los números están en las evidencias. En el backtest walk-forward de 1 "
        "paso, el naive es la vara.",
    ),
    (
        "tabla",
        (
            ["Modelo", "MAE", "RMSE", "Meses evaluados"],
            [
                ["Naive (último valor)", "1.115.021", "1.440.121", "28"],
                ["Regresión lineal (numpy)", "1.104.618", "1.333.136", "28"],
                ["Prophet", "1.288.772", "1.742.060", "28"],
                ["Keras (MLP)", "1.343.553", "1.734.021", "28"],
                ["PyTorch (MLP)", "1.419.231", "1.759.712", "28"],
            ],
        ),
    ),
    (
        "p",
        "La regresión lineal empata técnicamente con el naive y los demás quedan atrás; presentarlo así "
        "es más honesto que mostrar solo el modelo ganador.",
    ),
    ("p", "La calibración del Random Forest sobre la capa gold (evidencia 11) arrojó este grid:"),
    (
        "tabla",
        (
            ["n_estimators", "max_depth", "min_samples_leaf", "R2", "MAE"],
            [
                ["50", "6", "2", "0.184", "109.19"],
                ["100", "8", "2", "0.190", "106.11"],
                ["100", "10", "5", "0.186", "104.50"],
                ["150", "10", "5", "0.186", "104.37"],
                ["200", "12", "3", "0.186", "103.08"],
            ],
        ),
    ),
    (
        "p",
        "El R2 agregado es modesto porque los precios por artículo no se comportan igual que el promedio "
        "del catálogo; aun así el MAE baja al aumentar los árboles, que es lo que buscábamos.",
    ),
]


def main():
    doc = Document(RUTA_BASE)
    body = doc.element.body

    hijos = list(body.iterchildren())
    idx_13 = None
    idx_act = None
    for i, ch in enumerate(hijos):
        if not ch.tag.endswith("}p"):
            continue
        txt = _texto_de(ch)
        if idx_13 is None and txt.startswith("13. Establecimiento de métricas"):
            idx_13 = i
        elif txt.startswith("Actualización del proyecto"):
            idx_act = i
            break

    if idx_13 is None or idx_act is None or idx_act < idx_13:
        raise RuntimeError(
            f"No pude ubicar el bloque 13-16 (idx_13={idx_13}, idx_act={idx_act}). "
            "¿Cambió el v6 de forma?"
        )

    # Me guardo el ancla ANTES de borrar, que si no quedamos huérfanos.
    ancla = hijos[idx_act]
    for ch in hijos[idx_13:idx_act]:
        body.remove(ch)

    for bloque in CONTENIDO:
        ancla.addprevious(_bloque_a_elemento(doc, bloque))

    doc.save(RUTA_OUT)
    print(f"Informe v7 generado: {RUTA_OUT}")
    print(f"Bloques insertados: {len(CONTENIDO)}")


if __name__ == "__main__":
    main()
