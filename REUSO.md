# Guia de reutilizacion y escala del pipeline

> Objetivo de esta recomendacion: que esto no muera con el proyecto. El pipeline
> esta pensado para aplicarse a otra empresa o proceso con ajustes menores, y
> aqui esta la receta en pasos, en el mismo orden en que la sufrimos nosotros.

## Que se reutiliza tal cual

- La arquitectura medallion completa: `bronze -> silver -> normalizado -> gold`.
- Los scripts ETL de `evidencia/` (silver, 3FN, gold) y el SQL de `sql/`.
- La app Streamlit (`app.py`) con sus 9 secciones y la pagina de proyecciones.
- Los modelos de pronostico (regresion, Prophet, Keras, PyTorch) y el RF de precios.
- Las evidencias 01-11 como plantilla de verificacion (no se entrega nada sin evidencia).

## Que hay que cambiar SIEMPRE

### 1. Credenciales
- Copiar `.env.example` a `.env` y `.streamlit/secrets.toml` con los datos de la nueva BD.
- Nunca versionar `.env` ni `secrets.toml` (ya aprendimos eso a las malas).

### 2. Datos de origen
- Colocar los CSV nuevos en `datos_entrada/` (o donde apunte `CARPETA_ENTRADA`).
- Revisar el mapeo `TABLAS_BRONZE` en `evidencia/etl_incremental.py`: el nombre del
  archivo y la(s) columna(s) que identifican una fila unica.
- El resto del mapeo vive en los SQL de `sql/` y en `etl_silver.py` (columnas y tipos).

### 3. Logica de negocio
- Si la empresa nueva maneja otras unidades o monedas, revisar los formatos de
  fecha y numero en `parse_date`/`parse_numeric` de `etl_silver.py`.
- Si el esquema fuente cambia de columnas, ajustar primero `bronze` en la BD y
  despues el `SELECT` de `etl_silver.py` y el SQL correspondiente.

## Pasos para desplegar en otra empresa

```bash
# 1) instalar dependencias
pip install -r requirements.txt

# 2) configurar credenciales (nunca hardcodear)
#    copiar .env.example -> .env  y ajustar .streamlit/secrets.toml

# 3) ingesta incremental (primera vez trae todo, luego solo lo nuevo)
python evidencia\etl_incremental.py --carpeta datos_entrada --apply
python evidencia\etl_silver.py
python evidencia\etl_normalizado.py
python evidencia\etl_gold.py

# 4) validar que los conteos cuadran (evidencias 01-09)
#    los numeros esperados cambian por empresa; los chequeos no.

# 5) calibrar el modelo de precios (recomendacion 3)
python evidencia\calibracion_rf.py

# 6) validar pronosticos contra el negocio real (recomendacion 1)
python evidencia\etl_validacion_pronosticos.py

# 7) levantar el tablero
streamlit run app.py
```

## Integracion con ERP / tiempo real (recomendacion 2)

No hay que esperar a tener un ERP bonito. El punto de entrada es una carpeta de
archivos planos; el ERP (o el proceso manual) solo tiene que dejar ahi los
registros nuevos y correr:

```bash
python evidencia\etl_incremental.py --carpeta datos_entrada --apply
```

El script no recarga todo: compara contra un checkpoint (`checkpoint_ingesta.json`)
y solo inserta en bronze lo que no existia. Con un `cron`/`Task Scheduler` que
ejecute eso cada dia, ya tienes "tiempo real" del bueno.

Opciones para acoplar una API de verdad mas adelante:
- Cambiar `leer_csv` por una funcion que lea de un endpoint y devuelva filas (dicts) iguales.
- O un scheduler que descargue el CSV del ERP y luego corra el mismo script de siempre.

## Como verificar que la copia quedo sana

- Los conteos por capa deben crecer o mantenerse, nunca bajar (salvo limpieza real).
- Las evidencias 01-11 deben regenerarse con la data nueva, no arrastrarse.
- El backtest (evidencia 10) siempre corre contra `normalizado`/`silver`; si el naive
  le gana a todos, la serie no tiene patron o la limpieza fallo antes.

## Checklist rapida antes de entregar

- [ ] `.env` y secrets configurados, sin credenciales en git.
- [ ] CSV en `datos_entrada/` con el mapeo correcto.
- [ ] ETL corrido en orden y evidencias renovadas (01-11).
- [ ] Modelos re-entrenados con la data nueva (semilla 42).
- [ ] Backtest y calibracion ejecutados y revisados.
- [ ] Dashboard levantado y consultando la BD nueva.

Si algo de esto falla, revisa primero la data; el codigo ya soporto verme
sufrir una vez y no tiene ganas de repetir la experiencia.

## Ejecución automatizada (orquestación)

Para ejecutar el pipeline completo en orden y de forma repetible (Windows/PowerShell):

```powershell
# Solo lectura/checkpoint (recomendado para validar)
.\run_etl_completo.ps1

# Aplicando ingesta incremental en bronze
.\run_etl_completo.ps1 -ApplyIncremental
```

El script ejecuta en orden: `etl_incremental.py` → `etl_silver.py` → `etl_normalizado.py` → `etl_gold.py` y valida códigos de salida por fase. Esto no modifica la lógica de los ETL, solo asegura el orden correcto para escalar la operación.

Para ejecución programada (diaria/semanal), usar **Task Scheduler** (Windows) o **cron** (Linux). El punto de entrada incremental (`etl_incremental.py --apply`) evita recargar todo cuando crece el volumen.
