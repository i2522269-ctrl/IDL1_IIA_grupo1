# HANDOFF - Continuar ETL capa GOLD (normalizado -> gold)

> Pausado el 13/ago/2026. Esto queda para que el siguiente agente siga donde
> se quedó sin rehacer el análisis. Leer completo antes de tocar nada.

## Estado del proyecto (contexto)

Pipeline ETL ya implementado y verificado: `bronze -> silver -> normalizado`.
Scripts y evidencias en `evidencia/` (01..07), SQL en `sql/`. La app Streamlit
(`app.py`) lee de `normalizado` (no usa gold, así que regenerar gold no rompe nada).

Lo que faltaba: **capa gold**. Existen 2 tablas gold en la BD, creadas sueltas
sin ETL que las reproduzca:
- `gold.metricas_prediccion_proveedor` (383 filas)
- `gold.prediccion_demanda_mensual` (33,010 filas)

## Qué se hizo hasta ahora

1. Se inspeccionó la BD (`gold`, `normalizado`, `silver`, `bronze`): conteos y
   columnas documentados en `sql/gold.sql` (ya existe, PERO LA DEFINICION DE
   `prediccion_demanda_mensual` ESTA MAL, ver abajo).
2. Se validó reproducción desde `normalizado`:
   - `metricas_prediccion_proveedor`: **reproduce EXACTO** (383 proveedores, 0
     diferencias). Fuente: `normalizado.fact_recepcion JOIN proveedores`,
     `WHERE nrcfec IS NOT NULL AND solfec IS NOT NULL`, agrupado por `acrecodi`.
   - `prediccion_demanda_mensual`: NO reproduce exacto desde normalizado.

## Por que `prediccion_demanda_mensual` no reproduce desde normalizado

El gold original se genero sobre los datos crudos/silver, ANTES de que la
normalizacion hiciera NULL a los huerfanos. Evidencia concreta:

- `frecuencia_pedidos` = `COUNT(DISTINCT solnum)` usando el `solnum` REAL.
  En `normalizado`, las 957 recepciones huerfanas (solnum sin pedido) quedaron
  con `solnum = NULL`, asi que contarlas desde normalizado da numeros distintos.
  Ejemplo: `ART-06237 2023-02` tiene 4 recepciones huerfanas con el mismo
  solnum -> gold dice 1 (correcto contando el solnum real), normalizado diria 0.
- La fila con `artcitem` fuera de catalogo (1 recepcion, 2024-11) aparece en
  gold bajo su **codigo original**. En normalizado ese `artcitem` es NULL y
  gold NO tiene fila con artcitem NULL.
- `cantidad_total_despachada` (SUM solcan), `precio_promedio_pactado`
  (AVG solpre) y `ultimo_stock_registrado` (ultimo artstock del mes) SI
  coinciden desde normalizado. La diferencia es solo el conteo y el codigo
  del huerfano.

Conclusion: para reproducir gold EXACTO, `prediccion_demanda_mensual` debe
leer de **`silver.recepcion`** (donde los huerfanos conservan solnum y
artcitem), no de normalizado. Documentar esta ironia en los comentarios
(estilo AGENTS.md).

## Siguiente paso inmediato

1. Correr el script de hipotesis (ya escrito y arreglado, solo falta ejecutar):
   ```
   .\.venv\Scripts\python.exe "C:\Users\joanz\AppData\Local\Temp\opencode\hip4.py"
   ```
   Comprueba si "gold desde silver" reproduce las 33,010 filas exacto:
   frecuencia = `COUNT(DISTINCT solnum)`, cantidad = `SUM(solcan)`,
   precio = `AVG(solpre)`, stock = ultimo `artstock` por (artcitem, mes),
   todo con `WHERE nrcfec IS NOT NULL`. Debe dar 0 diferencias.
   (silver ya tiene tipos limpios: nrcfec date, solcan/artstock/solpre numeric).

2. Re-escribir `sql/gold.sql` completo con las definiciones correctas:
   - `metricas_prediccion_proveedor`: desde normalizado (ya validado 1:1).
   - `prediccion_demanda_mensual`: desde `silver.recepcion` con
     `COUNT(DISTINCT solnum)`, `SUM(solcan)`, `AVG(solpre)` y el ultimo
     `artstock` por (artcitem, mes) usando window function (NO LATERAL ni
     subquery correlacionada: tarda demasiado, da timeout).
   - `periodo_mes` debe quedar `TIMESTAMPTZ` a medianoche UTC del primer dia
     del mes (ej: 2023-01-01 00:00:00+00). Usar
     `DATE_TRUNC('month', nrcfec)::date` y luego `AT TIME ZONE 'UTC'`.
   - Mantener `artgrinv` y `grupo_nombre` via LEFT JOIN a
     `normalizado.maestro_articulos` / `normalizado.grupos` (o silver
     equivalente; elegir el que deje los mismos valores, verificar con la
     comparacion).
   - Comentarios estilo AGENTS.md (espanol, sarcasmo, primera persona).

3. Reescribir `evidencia/etl_gold.py` (el borrador que hay tiene un error de
   sintaxis: linea suelta `("  el maestro queda..."` sin llamada log()).
   Copiar el patron de `evidencia/etl_normalizado.py`:
   - `get_conn()` con .env primero y respaldo hardcodeado (mismas credenciales
     que etl_normalizado.py).
   - FASE 1: Reproducibilidad (comparar gold actual vs consultas, SOLO lectura)
     -> guardar `08_reproducibilidad_gold.txt`.
   - FASE 2: Carga, ejecutar `sql/gold.sql` (DROP SCHEMA gold CASCADE) ->
     guardar conteos.
   - FASE 3: Verificacion (conteos, tipos, muestras, check analitico) ->
     guardar `09_resultados_gold.txt`.
   - Usar consultas con CTE/window functions (rapidas), no subconsultas
     correlacionadas.
   - Al final: conteos esperados metricas=383, demanda=33,010.

4. Ejecutar:
   ```
   .\.venv\Scripts\python.exe evidencia\etl_gold.py
   ```
   (OJO: borra y recrea el schema gold. Es lo deseado. Aplica a una BD de
   desarrollo.)

5. Verificar que los conteos y valores finales coinciden con los originales
   (383 y 33,010) y que las diferencias de frecuencia/artcitem quedaron
   resueltas.

6. Actualizar `README.md` documentando la capa gold (tablas, definiciones,
   fuente, evidencias 08/09, y la nota de que la demanda se genera desde
   silver porque la normalizacion pierde los FKs huerfanos).

7. NO hacer commit a menos que el usuario lo pida.

## Notas tecnicas

- Python: usar `.\.venv\Scripts\python.exe` (psycopg2 instalado).
- Conexion: `.env` funciona (se conecta bien). Respaldo en
  `evidencia/etl_normalizado.py`.
- Consultas lentas sobre `fact_recepcion` (43k filas) dan timeout; usar
  ventanas/CTEs como en `hip4.py`.
- Scripts de analisis temporales en `C:\Users\joanz\AppData\Local\Temp\opencode\`:
  `insp_gold.py`, `cmp_gold.py`, `hip_frec.py`, `hip2.py`, `hip3.py`,
  `hip4.py` (el vigente). No van al repo.
- `evidencia/limpieza_capa_silver.sql` es el SQL de la capa silver (ya
  ejecutado, sirve de referencia de estilo).
