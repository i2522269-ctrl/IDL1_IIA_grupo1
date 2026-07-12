# IDL1_IIA_grupo1

Este repositorio ya incluye una base simple para trabajar con Streamlit y Supabase.

## Requisitos

- Python 3.11+
- Paquetes de Python listados en requirements.txt

## Instalar dependencias

```bash
pip install -r requirements.txt
```

## Ejecutar la app

```bash
streamlit run app.py
```

## Variables de entorno

Crea un archivo .env con estas variables:

```env
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-clave-anonima-o-service-role
SUPABASE_DB_URL=postgresql://postgres:password@host:5432/postgres
```
