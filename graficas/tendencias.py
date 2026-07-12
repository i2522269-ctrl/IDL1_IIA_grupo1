# Graficos de Tendencias Historicas
# Muestran como han evolucionado los datos en el tiempo

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graficas.utilidades import (
    configurar_grafico, agregar_leyenda_inferior,
    COLORES, COLORES_SERIES
)
from consultas.capa_gold import (
    get_demanda_mensual, get_costos_mensual, get_demora_entregas
)


def grafico_evolucion_solicitudes():
    """
    Grafico 5: Evolucion Mensual de Solicitudes
    Muestra como ha cambiado la cantidad de solicitudes mes a mes.
    """
    datos = get_demanda_mensual(limite=100)
    if datos.empty or len(datos) < 2:
        print('No hay suficientes datos de demanda')
        return None

    fig, ax = configurar_grafico(
        'Evolucion Mensual de Solicitudes de Compra',
        xlabel='Periodo',
        ylabel='Cantidad de Solicitudes',
        tamanho=(12, 5)
    )

    ax.plot(datos['mes'], datos['cantidad_solicitudes'],
            color=COLORES['primario'], linewidth=2, marker='o', markersize=4,
            label='Solicitudes mensuales')

    # Linea de tendencia
    ax.plot(datos['mes'], datos['cantidad_solicitudes'].rolling(3).mean(),
            color=COLORES['peligro'], linewidth=2, linestyle='--',
            label='Promedio movil (3 meses)')

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    agregar_leyenda_inferior(fig,
        'Linea azul: cantidad de solicitudes cada mes. '
        'Linea roja punteada: promedio movil de 3 meses (suaviza las fluctuaciones). '
        'Permite ver la tendencia general del volumen de solicitudes.'
    )

    return fig


def grafico_evolucion_recepciones():
    """
    Grafico 6: Evolucion Mensual de Recepciones
    Muestra las recepciones mes a mes.
    """
    datos = get_demanda_mensual(limite=100)
    if datos.empty or len(datos) < 2:
        print('No hay suficientes datos')
        return None

    fig, ax = configurar_grafico(
        'Evolucion Mensual de Recepciones',
        xlabel='Periodo',
        ylabel='Cantidad de Recepciones',
        tamanho=(12, 5)
    )

    ax.plot(datos['mes'], datos['articulos_diferentes'],
            color=COLORES['exito'], linewidth=2, marker='s', markersize=4,
            label='Recepciones mensuales')

    ax.plot(datos['mes'], datos['articulos_diferentes'].rolling(3).mean(),
            color=COLORES['secundario'], linewidth=2, linestyle='--',
            label='Promedio movil (3 meses)')

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    agregar_leyenda_inferior(fig,
        'Linea verde: cantidad de recepciones cada mes. '
        'Linea naranja punteada: promedio movil de 3 meses. '
        'Permite ver si las recepciones estan creciendo o decreciendo.'
    )

    return fig


def grafico_evolucion_costos():
    """
    Grafico 7: Evolucion Mensual de Costos
    Muestra como han cambiado los costos promedio.
    """
    datos = get_costos_mensual(limite=500)
    if datos.empty or len(datos) < 2:
        print('No hay suficientes datos de costos')
        return None

    # Agrupar por mes y sacar promedio general
    costos_por_mes = datos.groupby('mes')['costo_promedio'].mean().reset_index()
    costos_por_mes = costos_por_mes.sort_values('mes')

    fig, ax = configurar_grafico(
        'Evolucion Mensual de Costos Promedio',
        xlabel='Periodo',
        ylabel='Costo Promedio ($)',
        tamanho=(12, 5)
    )

    ax.plot(costos_por_mes['mes'], costos_por_mes['costo_promedio'],
            color=COLORES['peligro'], linewidth=2, marker='D', markersize=4,
            label='Costo promedio mensual')

    ax.plot(costos_por_mes['mes'], costos_por_mes['costo_promedio'].rolling(3).mean(),
            color=COLORES['purpura'], linewidth=2, linestyle='--',
            label='Promedio movil (3 meses)')

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    agregar_leyenda_inferior(fig,
        'Linea roja: costo promedio por unidad solicitada cada mes. '
        'Linea morada punteada: promedio movil de 3 meses. '
        'Permite ver si los precios estan subiendo o bajando.'
    )

    return fig


def grafico_demora_entregas():
    """
    Grafico 8: Demora Promedio de Entregas
    Muestra los dias promedio que tardan las entregas.
    """
    datos = get_demora_entregas(limite=500)
    if datos.empty or len(datos) < 2:
        print('No hay suficientes datos de demora')
        return None

    # Agrupar por mes
    demora_por_mes = datos.groupby('mes')['promedio_dias_demora'].mean().reset_index()
    demora_por_mes = demora_por_mes.sort_values('mes')

    fig, ax = configurar_grafico(
        'Demora Promedio de Entregas por Mes',
        xlabel='Periodo',
        ylabel='Dias Promedio de Entrega',
        tamanho=(12, 5)
    )

    ax.fill_between(demora_por_mes['mes'], demora_por_mes['promedio_dias_demora'],
                     alpha=0.3, color=COLORES['secundario'])
    ax.plot(demora_por_mes['mes'], demora_por_mes['promedio_dias_demora'],
            color=COLORES['secundario'], linewidth=2, marker='o', markersize=4,
            label='Dias promedio de entrega')

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    agregar_leyenda_inferior(fig,
        'La linea naranja muestra cuantos dias promedio tarda una entrega desde que se solicita. '
        'El area sombreada facilita visualizar la magnitud. '
        'Si la linea sube, las entregas estan tardando mas de lo normal.'
    )

    return fig
