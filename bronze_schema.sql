-- =============================================
-- SCHEMA BRONZE - Sincronizacion con Supabase
-- =============================================
-- Las tablas raw (grupos_sheet1, etc.) ya existen en public.
-- Este archivo crea las vistas de analisis en public.

-- Vista resumen: conteo de filas por tabla
CREATE OR REPLACE VIEW public.v_resumen AS
SELECT 'grupos' AS tabla, COUNT(*) AS filas FROM public.grupos_sheet1
UNION ALL SELECT 'solicitudes', COUNT(*) FROM public.solicitudes_sheet1
UNION ALL SELECT 'recepcion', COUNT(*) FROM public.recepcion_sheet1
UNION ALL SELECT 'maestro_articulos', COUNT(*) FROM public.maestro_articulos_sheet1
UNION ALL SELECT 'proveedores', COUNT(*) FROM public.proveedores_sheet1
UNION ALL SELECT 'articulos', COUNT(*) FROM public.articulos_sheet1;

-- Grupos con conteo de articulos
CREATE OR REPLACE VIEW public.v_grupos_conteo AS
SELECT
    g.artgrinv,
    g.nombre,
    COUNT(DISTINCT a.artcitem) AS total_articulos
FROM public.grupos_sheet1 g
LEFT JOIN public.articulos_sheet1 a ON g.artgrinv = a.artgrinv
GROUP BY g.artgrinv, g.nombre
ORDER BY g.artgrinv;

-- Solicitudes con detalle y monto total
CREATE OR REPLACE VIEW public.v_solicitudes_detalle AS
SELECT
    s.solnum,
    s.artcitem,
    s.artdes,
    s.soltip,
    s.solcan,
    s.solpre,
    s.solpre * s.solcan AS monto_total,
    s.solsts AS estado,
    s.solfec,
    s.solpro,
    g.nombre AS grupo_nombre
FROM public.solicitudes_sheet1 s
LEFT JOIN public.grupos_sheet1 g ON s.artgrinv::bigint = g.artgrinv;

-- Recepcion consolidada
CREATE OR REPLACE VIEW public.v_recepcion_resumen AS
SELECT
    r.solnum,
    r.artcitem,
    r.artdes,
    r.solcan AS cantidad_solicitada,
    r.nrdcac AS cantidad_recibida,
    r.solpre AS precio_unitario,
    r.solpre * r.nrdcac AS monto_recibido,
    r.nrcfec AS fecha_recepcion,
    r.nrcpro AS proveedor,
    r.solfec AS fecha_solicitud
FROM public.recepcion_sheet1 r;

-- Inventario por articulo
CREATE OR REPLACE VIEW public.v_inventario AS
SELECT
    a.artcitem,
    a.artdes,
    a.artmed,
    a.ubialm,
    a.ubistock,
    a.artcoum1 AS costo_unitario,
    g.nombre AS grupo_nombre,
    m.artcosu1 AS costo_sugerido
FROM public.articulos_sheet1 a
LEFT JOIN public.grupos_sheet1 g ON a.artgrinv = g.artgrinv
LEFT JOIN public.maestro_articulos_sheet1 m ON a.artcitem = m.artcitem;

-- Proveedores con conteo de recepciones
CREATE OR REPLACE VIEW public.v_proveedores_activos AS
SELECT
    p.acrecodi,
    p.acreraso,
    p.acredire,
    p.acretelf,
    p.acreciud,
    p.acreruc,
    COUNT(r.solnum) AS total_recepciones
FROM public.proveedores_sheet1 p
LEFT JOIN public.recepcion_sheet1 r ON p.acrecodi = r.nrcpro
GROUP BY p.acrecodi, p.acreraso, p.acredire, p.acretelf, p.acreciud, p.acreruc
ORDER BY COUNT(r.solnum) DESC;

-- Metricas generales
CREATE OR REPLACE VIEW public.v_metricas AS
SELECT
    (SELECT COUNT(*) FROM public.solicitudes_sheet1) AS total_solicitudes,
    (SELECT COUNT(*) FROM public.recepcion_sheet1) AS total_recepciones,
    (SELECT COUNT(*) FROM public.articulos_sheet1) AS total_articulos,
    (SELECT COUNT(*) FROM public.proveedores_sheet1) AS total_proveedores,
    (SELECT COUNT(*) FROM public.grupos_sheet1) AS total_grupos,
    (SELECT SUM(solpre * solcan) FROM public.solicitudes_sheet1) AS monto_total_solicitado,
    (SELECT SUM(solpre * nrdcac) FROM public.recepcion_sheet1) AS monto_total_recibido;
