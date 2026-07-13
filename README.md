# Proyecto Productivo IIA

Analisis predictivo de inventario y compras usando arquitectura medallion (bronze -> silver).

## Descripcion

Este proyecto analiza datos de solicitudes, recepciones, articulos y proveedores para identificar patrones de compra y generar proyecciones de demanda futura.

## Estructura del proyecto

```
├── data/                    # Archivos CSV originales
├── evidencia/               # Resultados del analisis de datos
│   ├── etl_silver.py        # Script completo de limpieza
│   ├── 01_analisis_calidad_datos.txt
│   ├── 02_analisis_duplicados.txt
│   ├── 03_resultados_silver.txt
│   └── limpieza_capa_silver.sql
├── sql/                     # Scripts SQL
│   └── limpieza_capa_silver.sql
├── app.py                   # Aplicacion Streamlit
└── requirements.txt         # Dependencias de Python
```

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
