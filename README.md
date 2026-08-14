# Proyecto Productivo IIA

Analisis predictivo de inventario y compras usando arquitectura medallion (bronze -> silver -> normalizado -> gold).

## Descripcion

Este proyecto analiza datos de solicitudes, recepciones, articulos y proveedores para identificar patrones de compra y generar proyecciones de demanda futura.

## Estructura del proyecto

```
├── evidencia/                    # Resultados del analisis de datos
│   ├── etl_silver.py             # Script completo de limpieza (bronze -> silver)
│   ├── etl_normalizado.py        # Script de normalizacion 3FN (silver -> normalizado)
│   ├── etl_gold.py               # Script de la capa gold (silver/normalizado -> gold)
│   ├── 01_analisis_calidad_datos.txt
│   ├── 02_analisis_duplicados.txt
│   ├── 03_resultados_silver.txt
│   ├── 04_analisis_redundancia.txt
│   ├── 05_integridad_referencial.txt
│   ├── 06_resultados_normalizado.txt
│   ├── 07_carga_normalizado.txt
│   ├── 08_reproducibilidad_gold.txt
│   └── 09_resultados_gold.txt
├── sql/                          # Scripts SQL
│   ├── limpieza_capa_silver.sql
│   ├── normalizacion_3fn.sql
│   └── gold.sql
├── .streamlit/secrets.toml       # Credenciales locales (NO se sube a git)
├── .env                          # Credenciales locales para scripts ETL (NO se sube a git)
├── app.py                        # Aplicacion Streamlit
└── requirements.txt              # Dependencias de Python
```

## Configuracion de credenciales

Las credenciales de Supabase **no deben ir en el codigo**.

1. **Local**: copia `.env.example` como `.env` y/o crea `.streamlit/secrets.toml`:

   ```toml
   # .streamlit/secrets.toml
   DB_HOST = "aws-1-us-west-2.pooler.supabase.com"
   DB_PORT = 5432
   DB_NAME = "postgres"
   DB_USER = "postgres.TU_PROYECTO"
   DB_PASSWORD = "TU_PASSWORD"
   ```

2. **Streamlit Cloud**: en `Settings -> Secrets` agrega las mismas claves:

   ```
   DB_HOST=...
   DB_PORT=5432
   DB_NAME=postgres
   DB_USER=...
   DB_PASSWORD=...
   ```

3. Para los scripts ETL que no usan Streamlit (`evidencia/etl_silver.py`), crea un archivo `.env` en la raiz con las mismas variables.

## Como ejecutar

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la app
streamlit run app.py
```

## Tablas en Supabase

- **bronze**: Datos crudos en formato texto
- **silver**: Datos limpiados con tipos correctos
- **normalizado**: Esquema 3FN con dimensiones y hechos (llaves foraneas)
- **gold**: Metricas y demanda agregada para el modelo predictivo

| Tabla | Registros | Descripcion |
|-------|-----------|-------------|
| grupos | 32 | Categorias de articulos |
| proveedores | 456 | Directorio de proveedores |
| maestro_articulos | 43,255 | Catalogo maestro |
| articulos | 4,130 | Stock por ubicacion |
| recepcion | 43,109 | Historial de recepciones |
| solicitudes | 41,971 | Historial de solicitudes |

Esquema `normalizado` (dimensiones + hechos con FK):

| Tabla | Registros | Contenido |
|-------|-----------|-----------|
| normalizado.grupos | 32 | Dimension de grupos |
| normalizado.proveedores | 456 | Dimension de proveedores |
| normalizado.maestro_articulos | 43,255 | Dimension de articulos |
| normalizado.fact_solicitudes | 41,971 | Hecho de solicitudes (artcitem, solpro -> FK) |
| normalizado.fact_recepcion | 43,109 | Hecho de recepciones (clave surrogate id_recepcion) |
| normalizado.fact_stock | 4,130 | Stock por ubicacion (solo columnas propias) |

Esquema `gold` (metricas y demanda agregada para el modelo):

| Tabla | Registros | Contenido | Fuente |
|-------|-----------|-----------|--------|
| gold.metricas_prediccion_proveedor | 383 | Metricas por proveedor (atenciones, lead time, volumen) | normalizado.fact_recepcion |
| gold.prediccion_demanda_mensual | 33,010 | Demanda mensual por articulo (cantidad, frecuencia, precio, stock) | silver.recepcion |

Nota sobre `prediccion_demanda_mensual`: se genera desde `silver.recepcion`
(no desde normalizado) porque la normalizacion vuelve NULL los FK huerfanos
(957 recepciones sin pedido y 1 articulo fuera de catalogo) y eso rompe el
conteo de `frecuencia_pedidos`. Los huerfanos conservan su solnum/artcitem
real en silver, asi que para reproducir exacto las 33,010 filas originales
hay que leer de ahi. Ironias de la vida.

Las evidencias `08_reproducibilidad_gold.txt` (gold vs consultas, antes de
regenerar) y `09_resultados_gold.txt` (verificacion post-carga) confirman
que ambas tablas reproducen exacto (0 diferencias). El ETL completo esta en
`evidencia/etl_gold.py` y el SQL en `sql/gold.sql`.

## Dependencias

- Python 3.11+
- Streamlit
- Pandas
- Plotly
- Psycopg2
- NumPy
- Scikit-learn

## STREAMLIT
https://idl1iiagrupo1-xujkvhuzbdgf2fz2p7qqvh.streamlit.app/
