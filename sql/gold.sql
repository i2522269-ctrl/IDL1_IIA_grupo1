-- ============================================================
-- CAPA GOLD - METRICAS Y DEMANDA AGREGADA
-- ============================================================
-- Reproduce las tablas gold que ya existian pero sin un ETL que
-- las generara. Ahora nadie se pregunta de donde salieron esos
-- numeros (mentira, se preguntaban, y bastante).

-- Definiciones validadas contra las tablas originales:
--   metricas_prediccion_proveedor: 383 proveedores (0 diferencias)
--   prediccion_demanda_mensual: 33,010 filas (0 diferencias)

-- Ironia del dato original (la documentamos porque da risa):
--   "cantidad_total_despachada" y "volumen_total_suministrado"
--   suman SOLCAN (lo solicitado), no nrdcac (lo recibido).
--   Asi estaba la tabla cuando llegamos, asi la dejamos.

-- Y la segunda ironia: la demanda se arma desde SILVER, no desde
-- normalizado. La normalizacion volvio NULL los FK huerfanos
-- (957 recepciones sin pedido y 1 artcitem fuera de catalogo) y
-- eso rompe el conteo de frecuencia_pedidos. Los huerfanos en
-- silver conservan su solnum y artcitem real, asi que para
-- reproducir EXACTO el gold hay que leer de donde se leia antes
-- de normalizar. La normalizacion es mas linda, pero este conteo
-- quiere el dato sucio. No preguntes por que.


DROP SCHEMA IF EXISTS gold CASCADE;
CREATE SCHEMA gold;

-- ============================================================
-- 1. METRICAS POR PROVEEDOR
-- ============================================================
CREATE TABLE gold.metricas_prediccion_proveedor (
    proveedor_id               TEXT,
    total_atenciones           BIGINT,
    lead_time_promedio_dias    NUMERIC,
    desviacion_lead_time       NUMERIC,
    volumen_total_suministrado NUMERIC
);

INSERT INTO gold.metricas_prediccion_proveedor
    (proveedor_id, total_atenciones, lead_time_promedio_dias,
     desviacion_lead_time, volumen_total_suministrado)
SELECT p.acrecodi,
       COUNT(*) AS total_atenciones,
       -- dias entre la recepcion y la solicitud; el tiempo que
       -- el proveedor se toma para entregar (o para que nos fumemos)
       AVG(f.nrcfec - f.solfec) AS lead_time_promedio_dias,
       STDDEV(f.nrcfec - f.solfec) AS desviacion_lead_time,
       SUM(f.solcan) AS volumen_total_suministrado
FROM normalizado.fact_recepcion f
JOIN normalizado.proveedores p ON f.solpro = p.acrecodi
WHERE f.nrcfec IS NOT NULL AND f.solfec IS NOT NULL
GROUP BY p.acrecodi;

-- ============================================================
-- 2. DEMANDA MENSUAL POR ARTICULO
-- ============================================================
CREATE TABLE gold.prediccion_demanda_mensual (
    artcitem                   TEXT,
    artgrinv                   TEXT,
    grupo_nombre               TEXT,
    periodo_mes                TIMESTAMP WITH TIME ZONE,
    cantidad_total_despachada  NUMERIC,
    frecuencia_pedidos         BIGINT,
    precio_promedio_pactado    NUMERIC,
    ultimo_stock_registrado    NUMERIC
);

INSERT INTO gold.prediccion_demanda_mensual
    (artcitem, artgrinv, grupo_nombre, periodo_mes, cantidad_total_despachada,
     frecuencia_pedidos, precio_promedio_pactado, ultimo_stock_registrado)
SELECT g.artcitem,
       g.artgrinv,
       g.grupo_nombre,
       g.mes AT TIME ZONE 'UTC' AS periodo_mes,
       g.cantidad,
       g.frecuencia,
       g.precio,
       s.artstock AS ultimo_stock
FROM (
    -- Stock del ultimo movimiento del mes. Usamos ROW_NUMBER y no una
    -- subconsulta correlacionada porque esa ya nos dio timeout una vez
    -- y aprendimos (a la mala) que la ventana es la que manda.
    SELECT artcitem,
           DATE_TRUNC('month', nrcfec)::date AS mes,
           artstock,
           ROW_NUMBER() OVER (PARTITION BY artcitem, DATE_TRUNC('month', nrcfec)
                              ORDER BY nrcfec DESC, nrcnum DESC) AS rn
    FROM silver.recepcion
    WHERE nrcfec IS NOT NULL AND artstock IS NOT NULL
) s
RIGHT JOIN (
    -- Demanda mensual: lo solicitado y lo que se pidio ese mes.
    -- frecuencia cuenta los pedidos DISTINTOS, que en normalizado se
    -- pierden por los huerfanos; por eso esto vive en silver.
    SELECT r.artcitem,
           r.artgrinv,
           g.nombre AS grupo_nombre,
           DATE_TRUNC('month', r.nrcfec)::date AS mes,
           SUM(r.solcan) AS cantidad,
           COUNT(DISTINCT r.solnum) AS frecuencia,
           AVG(r.solpre) AS precio
    FROM silver.recepcion r
    LEFT JOIN silver.grupos g ON r.artgrinv = g.artgrinv
    WHERE r.nrcfec IS NOT NULL
    GROUP BY r.artcitem, r.artgrinv, g.nombre, DATE_TRUNC('month', r.nrcfec)
) g ON g.artcitem = s.artcitem AND g.mes = s.mes AND s.rn = 1;


-- ============================================================
-- VERIFICACION FINAL
-- ============================================================
-- Conteos esperados (iguales a las tablas gold previas):
--   gold.metricas_prediccion_proveedor:   383
--   gold.prediccion_demanda_mensual:   33,010
