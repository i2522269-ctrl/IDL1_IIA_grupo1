# Diccionario de metricas del proyecto

> Objetivo de esta recomendacion: que el equipo de compras hable el mismo idioma.
> Nada de "ese numero del tablero remoto" ni "el prome-quie-sabe". Cada metrica
> tiene nombre unico, definicion, formula y de donde sale. Si no esta aqui, no se usa.

## Convencion de nombres

- Minusculas y underscore (`metricas_prediccion_proveedor`), no espacios ni tildes.
- Prefijo para saber el origen de un vistazo:
  - `total_` -> conteo de filas o eventos.
  - `lead_time_` / `desviacion_` -> tiempos de proveedor.
  - `volumen_` / `cantidad_` -> sumas de cantidades.
  - `precio_` -> valores monetarios.
  - `frecuencia_` -> conteo de pedidos distintos.
  - `R2` / `MAE` -> metricas de precision de modelos (mayusculas por ser siglas).
- Toda metrica vive en una tabla gold o el dashboard; nunca se inventa en el aire.

## Metricas operativas (tablas gold)

### 1. Total de atenciones por proveedor
- **Nombre tecnico**: `total_atenciones`
- **Definicion**: numero de recepciones que atendio cada proveedor.
- **Formula**: `COUNT(*)` sobre `normalizado.fact_recepcion` agrupado por `proveedor_id`.
- **Fuente**: `gold.metricas_prediccion_proveedor`
- **Uso en dashboard**: KPIs de Recepcion y ranking de proveedores.

### 2. Lead time promedio
- **Nombre tecnico**: `lead_time_promedio_dias`
- **Definicion**: dias promedio entre la solicitud y la recepcion por proveedor.
- **Formula**: `AVG(nrcfec - solfec)`
- **Fuente**: `gold.metricas_prediccion_proveedor`
- **Uso en dashboard**: diagnostico de confiabilidad de entrega.

### 3. Desviacion del lead time
- **Nombre tecnico**: `desviacion_lead_time`
- **Definicion**: variabilidad del tiempo de entrega por proveedor.
- **Formula**: `STDDEV(nrcfec - solfec)`
- **Fuente**: `gold.metricas_prediccion_proveedor`
- **Uso**: si es alta, el proveedor es impredecible aunque promedie bien.

### 4. Volumen total suministrado
- **Nombre tecnico**: `volumen_total_suministrado`
- **Definicion**: cantidad total de unidades que suministro cada proveedor.
- **Formula**: `SUM(solcan)`
- **Fuente**: `gold.metricas_prediccion_proveedor`

### 5. Demanda mensual despachada
- **Nombre tecnico**: `cantidad_total_despachada`
- **Definicion**: unidades despachadas por articulo y mes.
- **Formula**: `SUM(solcan)` desde `silver.recepcion` agrupado por `(artcitem, mes)`.
- **Fuente**: `gold.prediccion_demanda_mensual`
- **Uso en dashboard**: graficas de demanda y entrada del modelo predictivo.
- **Nota**: se lee de silver (no de normalizado) porque los huerfanos se perderian. Ya lo sufrimos una vez, no lo repitas.

### 6. Frecuencia de pedidos
- **Nombre tecnico**: `frecuencia_pedidos`
- **Definicion**: cantidad de pedidos distintos que tocan un articulo en el mes.
- **Formula**: `COUNT(DISTINCT solnum)` por `(artcitem, mes)`.
- **Fuente**: `gold.prediccion_demanda_mensual`

### 7. Precio promedio pactado
- **Nombre tecnico**: `precio_promedio_pactado`
- **Definicion**: precio promedio por articulo y mes.
- **Formula**: `AVG(solpre)` por `(artcitem, mes)`.
- **Fuente**: `gold.prediccion_demanda_mensual`

### 8. Ultimo stock registrado
- **Nombre tecnico**: `ultimo_stock_registrado`
- **Definicion**: ultimo valor de stock que se registro para el articulo en el mes.
- **Formula**: `artstock` de la ultima recepcion del mes (`ROW_NUMBER()` por fecha desc).
- **Fuente**: `gold.prediccion_demanda_mensual`

### 9. Participacion de articulo en stock
- **Nombre tecnico**: `participacion`
- **Definicion**: peso de cada articulo dentro del stock total de los ultimos 12 meses.
- **Formula**: `SUM(artstock) / SUM(artstock) total` (ultimos 12 meses).
- **Fuente**: derivada en la app (`cargar_participacion_productos`), se usa para repartir el pronostico total entre articulos.

## Metricas de precision de modelos

Siguen el espanol de las siglas originales; no se traducen porque todo el mundo las dice igual.

### R2 (coeficiente de determinacion)
- **Definicion**: que proporcion de la variabilidad real explica el modelo. 1 es perfecto, 0 es tirar a la media.
- **Formula**: `1 - SSE/SST`
- **Uso**: Random Forest de precios (por articulo y tendencia gold).

### MAE (error absoluto medio)
- **Definicion**: error promedio en las mismas unidades de la variable (soles, unidades).
- **Formula**: `mean(|real - predicho|)`
- **Uso**: Random Forest de precios y backtest de pronosticos.

### RMSE (raiz del error cuadratico medio)
- **Definicion**: parecido al MAE pero penaliza errores grandes.
- **Formula**: `sqrt(mean((real - predicho)^2))`
- **Uso**: backtest de pronosticos de stock (evidencia 10).

### MAPE (error porcentual absoluto medio)
- **Definicion**: error promedio en porcentaje.
- **Formula**: `mean(|real - predicho| / real) * 100`
- **Uso**: backtest de pronosticos de stock (evidencia 10). Cuidado con meses de stock 0.

## Metricas del dashboard (calculo en vivo)

| Metrica del tablero | Formula | Fuente |
|---------------------|---------|--------|
| Total solicitudes | `COUNT(*)` | `normalizado.fact_solicitudes` |
| Total recepciones | `COUNT(*)` | `normalizado.fact_recepcion` |
| Articulos en catalogo | `COUNT(*)` | `normalizado.maestro_articulos` |
| Total proveedores | `COUNT(*)` | `normalizado.proveedores` |
| Stock mes | `SUM(artstock)` mensual | `normalizado.fact_recepcion` |

## Reglas de galvanizado (para no pelearse)

1. Si una metrica cambia de nombre, se actualiza este diccionario en el mismo commit (o no se commitea).
2. Las formulas van SIEMPRE sobre gold o normalizado, nunca sobre bronze directo.
3. Los modelos usan semilla fija `42`; si alguien la cambia, que lo avise con antelacion y una buena razon.
4. Los pronosticos se validan con la evidencia 10; un modelo cuyo MAE no supera al naive no se presenta como logro.
5. Este diccionario es la fuente de verdad para el tablero y el informe. Investigadores felices, equipo alineado.