-- =============================================
-- CAPA SILVER - Limpieza y estandarizacion
-- =============================================
-- Estas vistas limpian los datos de las tablas raw (Bronze)
-- y los preparan para el analisis en la capa Gold.

-- 1. Grupos limpios con conteo de articulos
CREATE OR REPLACE VIEW public.v_silver_grupos AS
SELECT
    g.artgrinv AS codigo_grupo,
    UPPER(TRIM(g.nombre)) AS nombre_grupo,
    COUNT(DISTINCT a.artcitem) AS total_articulos
FROM public.grupos_sheet1 g
LEFT JOIN public.articulos_sheet1 a ON g.artgrinv = a.artgrinv
GROUP BY g.artgrinv, g.nombre
ORDER BY g.artgrinv;


-- 2. Solicitudes limpias con fechas y montos
CREATE OR REPLACE VIEW public.v_silver_solicitudes AS
SELECT
    s.solnum AS numero_solicitud,
    s.artcitem AS codigo_articulo,
    s.artdes AS descripcion,
    s.soltip AS tipo,
    s.solcan AS cantidad,
    s.solpre AS precio_unitario,
    ROUND((s.solpre * s.solcan)::numeric, 2) AS monto_total,
    CASE
        WHEN s.solsts = 'R' THEN 'Recepcionado'
        WHEN s.solsts = 'T' THEN 'Terminado'
        WHEN s.solsts = 'P' THEN 'Pendiente'
        ELSE s.solsts
    END AS estado,
    s.solfec::date AS fecha_solicitud,
    s.solfap::date AS fecha_aprobacion,
    s.solfor::date AS fecha_recepcion,
    s.solpro AS proveedor,
    g.nombre AS nombre_grupo,
    s.artmed AS unidad_medida
FROM public.solicitudes_sheet1 s
LEFT JOIN public.grupos_sheet1 g ON s.artgrinv::text = g.artgrinv::text;


-- 3. Recepciones limpias con dias de demora
CREATE OR REPLACE VIEW public.v_silver_recepciones AS
SELECT
    r.solnum AS numero_solicitud,
    r.artcitem AS codigo_articulo,
    r.artdes AS descripcion,
    r.solcan AS cantidad_solicitada,
    r.nrdcac AS cantidad_recibida,
    r.solpre AS precio_unitario,
    ROUND((r.solpre * r.nrdcac)::numeric, 2) AS monto_recibido,
    r.solfec::date AS fecha_solicitud,
    r.nrcfec::date AS fecha_recepcion,
    (r.nrcfec::date - r.solfec::date) AS dias_demora,
    r.nrcpro AS proveedor,
    g.nombre AS nombre_grupo,
    r.artmed AS unidad_medida
FROM public.recepcion_sheet1 r
LEFT JOIN public.grupos_sheet1 g ON r.artgrinv::text = g.artgrinv::text;


-- 4. Articulos con grupo y costo
CREATE OR REPLACE VIEW public.v_silver_articulos AS
SELECT
    a.artcitem AS codigo_articulo,
    a.artdes AS descripcion,
    a.artmed AS unidad_medida,
    a.ubialm AS ubicacion_almacen,
    a.ubistock AS stock_actual,
    a.artcoum1 AS costo_unitario,
    g.nombre AS nombre_grupo,
    m.artcosu1 AS costo_sugerido
FROM public.articulos_sheet1 a
LEFT JOIN public.grupos_sheet1 g ON a.artgrinv = g.artgrinv
LEFT JOIN public.maestro_articulos_sheet1 m ON a.artcitem = m.artcitem;


-- 5. Proveedores con estadisticas
CREATE OR REPLACE VIEW public.v_silver_proveedores AS
SELECT
    p.acrecodi AS codigo_proveedor,
    p.acreraso AS razon_social,
    p.acredire AS direccion,
    p.acretelf AS telefono,
    p.acreciud AS ciudad,
    p.acreruc AS ruc,
    COUNT(r.numero_solicitud) AS total_recepciones,
    COALESCE(SUM(r.monto_recibido), 0) AS monto_total_recibido,
    COALESCE(ROUND(AVG(r.dias_demora)::numeric, 1), 0) AS promedio_dias_demora
FROM public.proveedores_sheet1 p
LEFT JOIN public.v_silver_recepciones r ON p.acrecodi = r.proveedor
GROUP BY p.acrecodi, p.acreraso, p.acredire, p.acretelf, p.acreciud, p.acreruc;


-- 6. Maestro de articulos limpio
CREATE OR REPLACE VIEW public.v_silver_maestro AS
SELECT
    m.artcitem AS codigo_articulo,
    m.artdes AS descripcion,
    m.artmed AS unidad_medida,
    m.artgrinv AS codigo_grupo,
    m.artcosu1 AS costo_unitario_sugerido,
    m.artcoum1 AS costo_unitario_real,
    m.artubi AS ubicacion,
    g.nombre AS nombre_grupo
FROM public.maestro_articulos_sheet1 m
LEFT JOIN public.grupos_sheet1 g ON m.artgrinv::text = g.artgrinv::text;
