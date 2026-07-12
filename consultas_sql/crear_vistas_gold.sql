-- =============================================
-- CAPA GOLD - Vistas de analisis y prediccion
-- =============================================
-- Estas vistas agregan los datos de Silver para el
-- dashboard y los modelos predictivos.


-- 1. KPIs generales del negocio
CREATE OR REPLACE VIEW public.v_gold_kpi_generales AS
SELECT
    (SELECT COUNT(*) FROM public.v_silver_solicitudes) AS total_solicitudes,
    (SELECT COUNT(*) FROM public.v_silver_recepciones) AS total_recepciones,
    (SELECT COUNT(DISTINCT codigo_articulo) FROM public.v_silver_articulos) AS total_articulos,
    (SELECT COUNT(*) FROM public.v_silver_proveedores) AS total_proveedores,
    (SELECT COUNT(*) FROM public.v_silver_grupos) AS total_grupos,
    (SELECT SUM(monto_total) FROM public.v_silver_solicitudes) AS monto_total_solicitado,
    (SELECT SUM(monto_recibido) FROM public.v_silver_recepciones) AS monto_total_recibido,
    (SELECT ROUND(AVG(dias_demora)::numeric, 1) FROM public.v_silver_recepciones WHERE dias_demora > 0) AS promedio_dias_demora;


-- 2. Demanda mensual (para series de tiempo y prediccion)
CREATE OR REPLACE VIEW public.v_gold_demanda_mensual AS
SELECT
    DATE_TRUNC('month', fecha_solicitud) AS mes,
    EXTRACT(YEAR FROM fecha_solicitud) AS anio,
    EXTRACT(MONTH FROM fecha_solicitud) AS num_mes,
    COUNT(*) AS cantidad_solicitudes,
    SUM(cantidad) AS total_unidades,
    SUM(monto_total) AS monto_total,
    COUNT(DISTINCT codigo_articulo) AS articulos_diferentes,
    COUNT(DISTINCT proveedor) AS proveedores_diferentes
FROM public.v_silver_solicitudes
WHERE fecha_solicitud IS NOT NULL
GROUP BY DATE_TRUNC('month', fecha_solicitud), EXTRACT(YEAR FROM fecha_solicitud), EXTRACT(MONTH FROM fecha_solicitud)
ORDER BY mes;


-- 3. Costos mensuales por grupo
CREATE OR REPLACE VIEW public.v_gold_costos_mensual AS
SELECT
    DATE_TRUNC('month', fecha_solicitud) AS mes,
    nombre_grupo,
    ROUND(AVG(precio_unitario)::numeric, 2) AS costo_promedio,
    SUM(monto_total) AS monto_total_grupo,
    COUNT(*) AS cantidad_solicitudes
FROM public.v_silver_solicitudes
WHERE fecha_solicitud IS NOT NULL AND precio_unitario > 0
GROUP BY DATE_TRUNC('month', fecha_solicitud), nombre_grupo
ORDER BY mes, nombre_grupo;


-- 4. Estado actual del inventario
CREATE OR REPLACE VIEW public.v_gold_inventario_estado AS
SELECT
    a.codigo_articulo,
    a.descripcion,
    a.unidad_medida,
    a.ubicacion_almacen,
    a.stock_actual,
    a.costo_unitario,
    a.nombre_grupo,
    ROUND((a.stock_actual * a.costo_unitario)::numeric, 2) AS valor_inventario,
    a.costo_sugerido
FROM public.v_silver_articulos a
WHERE a.stock_actual > 0
ORDER BY valor_inventario DESC;


-- 5. Ranking de proveedores
CREATE OR REPLACE VIEW public.v_gold_proveedores_ranking AS
SELECT
    p.codigo_proveedor,
    p.razon_social,
    p.ciudad,
    p.total_recepciones,
    p.monto_total_recibido,
    p.promedio_dias_demora,
    CASE
        WHEN p.total_recepciones >= 1000 THEN 'A - Alto volumen'
        WHEN p.total_recepciones >= 500 THEN 'B - Volumen medio'
        ELSE 'C - Volumen bajo'
    END AS categoria_proveedor
FROM public.v_silver_proveedores p
ORDER BY p.total_recepciones DESC;


-- 6. Top 20 articulos mas solicitados
CREATE OR REPLACE VIEW public.v_gold_top_articulos AS
SELECT
    s.codigo_articulo,
    s.descripcion,
    s.nombre_grupo,
    s.unidad_medida,
    COUNT(*) AS veces_solicitado,
    SUM(s.cantidad) AS total_unidades,
    SUM(s.monto_total) AS monto_total,
    ROUND(AVG(s.precio_unitario)::numeric, 2) AS precio_promedio
FROM public.v_silver_solicitudes s
GROUP BY s.codigo_articulo, s.descripcion, s.nombre_grupo, s.unidad_medida
ORDER BY total_unidades DESC
LIMIT 20;


-- 7. Evolucion mensual por grupo de inventario
CREATE OR REPLACE VIEW public.v_gold_evolucion_grupo AS
SELECT
    DATE_TRUNC('month', s.fecha_solicitud) AS mes,
    s.nombre_grupo,
    COUNT(*) AS cantidad_solicitudes,
    SUM(s.monto_total) AS monto_total,
    SUM(s.cantidad) AS total_unidades
FROM public.v_silver_solicitudes s
WHERE s.fecha_solicitud IS NOT NULL
GROUP BY DATE_TRUNC('month', s.fecha_solicitud), s.nombre_grupo
ORDER BY mes, s.nombre_grupo;


-- 8. Demora de entregas por mes y proveedor
CREATE OR REPLACE VIEW public.v_gold_demora_entregas AS
SELECT
    DATE_TRUNC('month', r.fecha_recepcion) AS mes,
    r.proveedor,
    COUNT(*) AS total_entregas,
    ROUND(AVG(r.dias_demora)::numeric, 1) AS promedio_dias_demora,
    MIN(r.dias_demora) AS minimo_dias,
    MAX(r.dias_demora) AS maximo_dias,
    SUM(r.monto_recibido) AS monto_total
FROM public.v_silver_recepciones r
WHERE r.fecha_recepcion IS NOT NULL AND r.dias_demora > 0
GROUP BY DATE_TRUNC('month', r.fecha_recepcion), r.proveedor
ORDER BY mes, r.proveedor;
