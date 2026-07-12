# Modelos de prediccion simples
# Usa Regresion Lineal y Media Movil para predecir tendencias futuras
# Codigo basico-medio para un proyecto productivo

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


def regresion_lineal(x, y, meses_futuros=3):
    """
    Hace una prediccion usando regresion lineal.

    Parametros:
        x: array con los valores del eje X (numeros de mes)
        y: array con los valores del eje Y (datos historicos)
        meses_futuros: cuantos meses adelante predecir

    Retorna:
        meses_futuros_valores: valores predichos para el futuro
        modelo: el modelo entrenado (para metricas)
    """
    # Convertir a arrays de numpy
    x = np.array(x).reshape(-1, 1)
    y = np.array(y)

    # Crear y entrenar el modelo
    modelo = LinearRegression()
    modelo.fit(x, y)

    # Predecir los meses futuros
    ultimo_mes = x[-1][0]
    meses_futuros_x = np.array(range(int(ultimo_mes) + 1, int(ultimo_mes) + 1 + meses_futuros)).reshape(-1, 1)
    predicciones = modelo.predict(meses_futuros_x)

    return predicciones, modelo


def media_movil(datos, ventana=3):
    """
    Calcula la media movil de una serie de datos.

    Parametros:
        datos: array con los datos historicos
        ventana: cuantos periodos usar para el promedio

    Retorna:
        array con la media movil
    """
    serie = pd.Series(datos)
    return serie.rolling(window=ventana, min_periods=1).mean().values


def media_movil_ponderada(datos, ventana=3):
    """
    Media movil ponderada (el peso mas reciente vale mas).

    Parametros:
        datos: array con los datos historicos
        ventana: cuantos periodos usar

    Retorna:
        valor predicho (un solo valor)
    """
    pesos = np.arange(1, ventana + 1, dtype=float)
    pesos = pesos / pesos.sum()

    if len(datos) < ventana:
        ventana = len(datos)

    ultimos_datos = datos[-ventana:]
    return np.sum(ultimos_datos * pesos[-ventana:])


def calcular_tendencia(datos):
    """
    Indica si la tendencia es creciente, estable o decreciente.

    Retorna:
        string con la tendencia y el porcentaje de cambio
    """
    if len(datos) < 2:
        return "Sin datos suficientes", 0

    # Comparar el promedio de los ultimos 3 meses con los 3 meses anteriores
    ultimos_3 = np.mean(datos[-3:])
    anteriores_3 = np.mean(datos[-6:-3]) if len(datos) >= 6 else np.mean(datos[:3])

    if anteriores_3 == 0:
        return "Sin referencia", 0

    cambio = ((ultimos_3 - anteriores_3) / anteriores_3) * 100

    if cambio > 5:
        return "Creciente", round(cambio, 1)
    elif cambio < -5:
        return "Decreciente", round(cambio, 1)
    else:
        return "Estable", round(cambio, 1)


def prediccion_completa(df_demanda, meses_futuros=3):
    """
    Hace una prediccion completa de demanda mensual.
    Devuelve el historico + las predicciones.

    Parametros:
        df_demanda: DataFrame con columnas 'mes' y 'cantidad_solicitudes'
        meses_futuros: cuantos meses predecir

    Retorna:
        dict con historico, predicciones, tendencia y metricas
    """
    if df_demanda.empty or len(df_demanda) < 3:
        return None

    # Preparar datos
    datos = df_demanda.sort_values('mes').copy()
    datos['numero_mes'] = range(len(datos))

    x = datos['numero_mes'].values
    y = datos['cantidad_solicitudes'].values

    # Regresion lineal
    predicciones, modelo = regresion_lineal(x, y, meses_futuros)

    # Media movil
    mm = media_movil(y, ventana=3)

    # Tendencia
    tendencia_texto, cambio_pct = calcular_tendencia(y)

    # Metricas del modelo
    r_cuadrado = modelo.score(x.reshape(-1, 1), y)

    # Crear fechas futuras
    ultimo_mes = datos['mes'].max()
    meses_futuros_fechas = pd.date_range(
        start=ultimo_mes + pd.DateOffset(months=1),
        periods=meses_futuros,
        freq='MS'
    )

    return {
        'historico_fechas': datos['mes'].values,
        'historico_valores': y,
        'media_movil': mm,
        'prediccion_fechas': meses_futuros_fechas.values,
        'prediccion_valores': predicciones,
        'tendencia': tendencia_texto,
        'cambio_porcentaje': cambio_pct,
        'r_cuadrado': round(r_cuadrado, 4),
    }


def prediccion_costos(df_costos, meses_futuros=3):
    """
    Prediccion de costos promedio mensuales.
    Agrupa por mes y saca el costo promedio de todos los grupos.
    """
    if df_costos.empty or len(df_costos) < 3:
        return None

    # Agrupar por mes y sacar promedio de costos
    costos_por_mes = df_costos.groupby('mes')['costo_promedio'].mean().reset_index()
    costos_por_mes = costos_por_mes.sort_values('mes')
    costos_por_mes['numero_mes'] = range(len(costos_por_mes))

    x = costos_por_mes['numero_mes'].values
    y = costos_por_mes['costo_promedio'].values

    predicciones, modelo = regresion_lineal(x, y, meses_futuros)
    mm = media_movil(y, ventana=3)
    tendencia_texto, cambio_pct = calcular_tendencia(y)
    r_cuadrado = modelo.score(x.reshape(-1, 1), y)

    ultimo_mes = costos_por_mes['mes'].max()
    meses_futuros_fechas = pd.date_range(
        start=ultimo_mes + pd.DateOffset(months=1),
        periods=meses_futuros,
        freq='MS'
    )

    return {
        'historico_fechas': costos_por_mes['mes'].values,
        'historico_valores': y,
        'media_movil': mm,
        'prediccion_fechas': meses_futuros_fechas.values,
        'prediccion_valores': predicciones,
        'tendencia': tendencia_texto,
        'cambio_porcentaje': cambio_pct,
        'r_cuadrado': round(r_cuadrado, 4),
    }


def prediccion_demora(df_demora, meses_futuros=3):
    """
    Prediccion de dias promedio de entrega.
    """
    if df_demora.empty or len(df_demora) < 3:
        return None

    # Agrupar por mes
    demora_por_mes = df_demora.groupby('mes').agg({
        'promedio_dias_demora': 'mean'
    }).reset_index()
    demora_por_mes = demora_por_mes.sort_values('mes')
    demora_por_mes['numero_mes'] = range(len(demora_por_mes))

    x = demora_por_mes['numero_mes'].values
    y = demora_por_mes['promedio_dias_demora'].values

    # Filtrar valores validos
    mask = y > 0
    if mask.sum() < 3:
        return None

    x = x[mask]
    y = y[mask]

    predicciones, modelo = regresion_lineal(x, y, meses_futuros)
    mm = media_movil(y, ventana=3)
    tendencia_texto, cambio_pct = calcular_tendencia(y)
    r_cuadrado = modelo.score(x.reshape(-1, 1), y)

    ultimo_mes = demora_por_mes['mes'].max()
    meses_futuros_fechas = pd.date_range(
        start=ultimo_mes + pd.DateOffset(months=1),
        periods=meses_futuros,
        freq='MS'
    )

    return {
        'historico_fechas': demora_por_mes.loc[mask, 'mes'].values,
        'historico_valores': y,
        'media_movil': mm,
        'prediccion_fechas': meses_futuros_fechas.values,
        'prediccion_valores': predicciones,
        'tendencia': tendencia_texto,
        'cambio_porcentaje': cambio_pct,
        'r_cuadrado': round(r_cuadrado, 4),
    }
