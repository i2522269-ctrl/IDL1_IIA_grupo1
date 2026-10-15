-- gold_incremental.sql
-- Diseño de materialización INCREMENTAL para capa gold (upsert).
-- REGLA: este diseño NO reemplaza el modo full. El ETL debe mantener
--        --modo full por defecto para garantizar reproducibilidad (08/09).
--        Solo usar incremental tras validar equivalencia full == incremental (0 diferencias).

-- 1) gold.metricas_prediccion_proveedor (clave natural: proveedor_id)
--    Fuente: normalizado.fact_recepcion (ya validado 1:1). Volumen pequeño (383).
WITH base_metricas AS (
  SELECT
    pr.proveedor_id,
    COUNT(*) AS total_atenciones,
    AVG(nrcfec - solfec) AS lead_time_promedio_dias,
    STDDEV(nrcfec - solfec) AS desviacion_lead_time,
    SUM(solcan) AS volumen_total_suministrado
  FROM normalizado.fact_recepcion fr
  JOIN normalizado.proveedores pr
    ON fr.acrecodi = pr.acrecodi
  WHERE fr.nrcfec IS NOT NULL
    AND fr.solfec IS NOT NULL
  GROUP BY pr.proveedor_id
),
upsert_metricas AS (
  INSERT INTO gold.metricas_prediccion_proveedor (
    proveedor_id,
    total_atenciones,
    lead_time_promedio_dias,
    desviacion_lead_time,
    volumen_total_suministrado
  )
  SELECT
    proveedor_id,
    total_atenciones,
    lead_time_promedio_dias,
    desviacion_lead_time,
    volumen_total_suministrado
  FROM base_metricas
  ON CONFLICT (proveedor_id) DO UPDATE SET
    total_atenciones           = EXCLUDED.total_atenciones,
    lead_time_promedio_dias    = EXCLUDED.lead_time_promedio_dias,
    desviacion_lead_time       = EXCLUDED.desviacion_lead_time,
    volumen_total_suministrado = EXCLUDED.volumen_total_suministrado
  RETURNING proveedor_id
)
SELECT COUNT(*) AS metricas_proveedor_upsertadas FROM upsert_metricas;

-- 2) gold.prediccion_demanda_mensual (clave natural: (artcitem, periodo_mes))
--    Fuente: silver.recepcion (para conservar huerfanos: solnum/artcitem reales).
--    No se usa LATERAL correlacionada (evita timeout). Window function para ultimo stock.
WITH recep_mensual_base AS (
  SELECT
    artcitem,
    DATE_TRUNC('month', nrcfec)::date AS periodo_mes_dt,
    solnum,
    solcan,
    solpre,
    artstock,
    ROW_NUMBER() OVER (
      PARTITION BY artcitem, DATE_TRUNC('month', nrcfec)::date
      ORDER BY nrcfec DESC, id_recepcion DESC
    ) AS rn_ultimo
  FROM silver.recepcion
  WHERE nrcfec IS NOT NULL
),
ultimo_stock_por_mes AS (
  SELECT
    artcitem,
    periodo_mes_dt,
    artstock AS ultimo_stock_registrado
  FROM recep_mensual_base
  WHERE rn_ultimo = 1
),
agregados_por_mes AS (
  SELECT
    r.artcitem,
    DATE_TRUNC('month', r.nrcfec)::date AS periodo_mes_dt,
    SUM(r.solcan) AS cantidad_total_despachada,
    COUNT(DISTINCT r.solnum) AS frecuencia_pedidos,
    AVG(r.solpre) AS precio_promedio_pactado
  FROM silver.recepcion r
  WHERE r.nrcfec IS NOT NULL
  GROUP BY r.artcitem, DATE_TRUNC('month', r.nrcfec)::date
),
gold_base_incremental AS (
  SELECT
    a.artcitem,
    m.artgrinv,
    g.grupo_nombre,
    (a.periodo_mes_dt AT TIME ZONE 'UTC') AS periodo_mes,
    a.cantidad_total_despachada,
    a.frecuencia_pedidos,
    a.precio_promedio_pactado,
    COALESCE(s.ultimo_stock_registrado, 0::numeric) AS ultimo_stock_registrado
  FROM agregados_por_mes a
  LEFT JOIN silver.maestro_articulos m
    ON a.artcitem = m.artcitem
  LEFT JOIN silver.grupos g
    ON m.artgrinv = g.artgrinv
  LEFT JOIN ultimo_stock_por_mes s
    ON a.artcitem = s.artcitem
    AND a.periodo_mes_dt = s.periodo_mes_dt
),
upsert_demanda AS (
  INSERT INTO gold.prediccion_demanda_mensual (
    artcitem,
    artgrinv,
    grupo_nombre,
    periodo_mes,
    cantidad_total_despachada,
    frecuencia_pedidos,
    precio_promedio_pactado,
    ultimo_stock_registrado
  )
  SELECT
    artcitem,
    artgrinv,
    grupo_nombre,
    periodo_mes,
    cantidad_total_despachada,
    frecuencia_pedidos,
    precio_promedio_pactado,
    ultimo_stock_registrado
  FROM gold_base_incremental
  ON CONFLICT (artcitem, periodo_mes) DO UPDATE SET
    artgrinv                   = EXCLUDED.artgrinv,
    grupo_nombre               = EXCLUDED.grupo_nombre,
    cantidad_total_despachada  = EXCLUDED.cantidad_total_despachada,
    frecuencia_pedidos         = EXCLUDED.frecuencia_pedidos,
    precio_promedio_pactado    = EXCLUDED.precio_promedio_pactado,
    ultimo_stock_registrado    = EXCLUDED.ultimo_stock_registrado
  RETURNING artcitem, periodo_mes
)
SELECT COUNT(*) AS demanda_mensual_upsertadas FROM upsert_demanda;

-- NOTA: periodo_mes se mantiene TIMESTAMP WITH TIME ZONE (primer dia del mes UTC).
--       Modo incremental por defecto NO aplicado: requiere validar equivalencia full==incremental (0 diferencias).
--       Claves propuestas: (proveedor_id) y (artcitem, periodo_mes). Ajustar si cambia esquema.
