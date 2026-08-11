# Proyecto Productivo IIA

Analisis predictivo de inventario y compras usando arquitectura medallion (bronze -> silver).

## Descripcion

Este proyecto analiza datos de solicitudes, recepciones, articulos y proveedores para identificar patrones de compra y generar proyecciones de demanda futura.

## Estructura del proyecto

```
├── evidencia/                    # Resultados del analisis de datos
│   ├── etl_silver.py             # Script completo de limpieza (bronze -> silver)
│   ├── 01_analisis_calidad_datos.txt
│   ├── 02_analisis_duplicados.txt
│   ├── 03_resultados_silver.txt
│   └── limpieza_capa_silver.sql
├── sql/                          # Scripts SQL
│   └── limpieza_capa_silver.sql
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

| Tabla | Registros | Descripcion |
|-------|-----------|-------------|
| grupos | 32 | Categorias de articulos |
| proveedores | 456 | Directorio de proveedores |
| maestro_articulos | 43,255 | Catalogo maestro |
| articulos | 4,130 | Stock por ubicacion |
| recepcion | 43,109 | Historial de recepciones |
| solicitudes | 41,971 | Historial de solicitudes |

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
