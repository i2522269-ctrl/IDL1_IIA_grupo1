# Graficos de Prediccion
# Muestran las proyecciones futuras basadas en datos historicos

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graficas.utilidades import (
    configurar_grafico, agregar_leyenda_inferior,
    COLORES, formato_numero
)
from consultas.capa_gold import get_demanda_mensual, get_costos_mensual, get_demora_entregas
from modelos.prediccion import prediccion_completa, prediccion_costos, prediccion_demora


def grafico_prediccion_demanda():
    """
    Grafico 9: Prediccion de Demanda (3 meses)
    Muestra historico + prediccion de solicitudes.
    """
    datos = get_demanda_mensual(limite=100)
    if datos.empty:
        print('No hay datos para predecir')
        return None

    resultado = prediccion_completa(datos, meses_futuros=3)
    if resultado is None:
        print('Datos insuficientes para prediccion')
        return None

    fig, ax = configurar_grafico(
        'Prediccion de Demanda - Proximos 3 Meses',
        xlabel='Periodo',
        ylabel='Cantidad de Solicitudes',
        tamanho=(12, 6)
    )

    # Datos historicos
    ax.plot(resultado['historico_fechas'], resultado['historico_valores'],
            color=COLORES['primario'], linewidth=2, marker='o', markersize=4,
            label='Datos historicos')

    # Media movil
    ax.plot(resultado['historico_fechas'], resultado['media_movil'],
            color=COLORES['exito'], linewidth=2, linestyle='--',
            label='Media movil (3 meses)')

    # Prediccion
    ax.plot(resultado['prediccion_fechas'], resultado['prediccion_valores'],
            color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=8,
            label='Prediccion (regresion lineal)')

    # Sombreado en la zona de prediccion
    ax.axvspan(resultado['historico_fechas'][-1], resultado['prediccion_fechas'][-1],
               alpha=0.1, color=COLORES['peligro'], label='Zona de prediccion')

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    # Informacion adicional
    info_texto = (
        f"Tendencia: {resultado['tendencia']} "
        f"({resultado['cambio_porcentaje']:+.1f}%) | "
        f"Precision del modelo (R2): {resultado['r_cuadrado']:.2f}"
    )
    ax.text(0.02, 0.95, info_texto, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    agregar_leyenda_inferior(fig,
        'Linea azul: solicitudes historicas. '
        'Linea verde punteada: promedio movil que suaviza la tendencia. '
        'Linea roja con X: prediccion para los proximos 3 meses usando regresion lineal. '
        'La zona sombreada indica el periodo proyectado. '
        f"R2 indica que el modelo explica el {resultado['r_cuadrado']*100:.0f}% de la variacion."
    )

    return fig


def grafico_prediccion_costos():
    """
    Grafico 10: Prediccion de Costos (3 meses)
    """
    datos = get_costos_mensual(limite=500)
    if datos.empty:
        print('No hay datos de costos')
        return None

    resultado = prediccion_costos(datos, meses_futuros=3)
    if resultado is None:
        print('Datos insuficientes para prediccion de costos')
        return None

    fig, ax = configurar_grafico(
        'Prediccion de Costos - Proximo Trimestre',
        xlabel='Periodo',
        ylabel='Costo Promedio ($)',
        tamanho=(12, 6)
    )

    ax.plot(resultado['historico_fechas'], resultado['historico_valores'],
            color=COLORES['secundario'], linewidth=2, marker='D', markersize=4,
            label='Costo historico')

    ax.plot(resultado['historico_fechas'], resultado['media_movil'],
            color=COLORES['purpura'], linewidth=2, linestyle='--',
            label='Media movil')

    ax.plot(resultado['prediccion_fechas'], resultado['prediccion_valores'],
            color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=8,
            label='Prediccion')

    ax.axvspan(resultado['historico_fechas'][-1], resultado['prediccion_fechas'][-1],
               alpha=0.1, color=COLORES['peligro'])

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    info_texto = (
        f"Tendencia: {resultado['tendencia']} "
        f"({resultado['cambio_porcentaje']:+.1f}%) | "
        f"R2: {resultado['r_cuadrado']:.2f}"
    )
    ax.text(0.02, 0.95, info_texto, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    agregar_leyenda_inferior(fig,
        'Linea naranja: costo promedio historico por unidad. '
        'Linea morada: media movil de 3 meses. '
        'Linea roja: prediccion de costos para el proximo trimestre. '
        'Si la prediccion sube, se esperan precios mas altos.'
    )

    return fig


def grafico_prediccion_demora():
    """
    Grafico 11: Prediccion de Demora de Entregas
    """
    datos = get_demora_entregas(limite=500)
    if datos.empty:
        print('No hay datos de demora')
        return None

    resultado = prediccion_demora(datos, meses_futuros=3)
    if resultado is None:
        print('Datos insuficientes para prediccion de demora')
        return None

    fig, ax = configurar_grafico(
        'Prediccion de Dias de Entrega - Proximos 3 Meses',
        xlabel='Periodo',
        ylabel='Dias Promedio de Entrega',
        tamanho=(12, 6)
    )

    ax.plot(resultado['historico_fechas'], resultado['historico_valores'],
            color=COLORES['primario'], linewidth=2, marker='o', markersize=4,
            label='Dias historicos')

    ax.plot(resultado['historico_fechas'], resultado['media_movil'],
            color=COLORES['advertencia'], linewidth=2, linestyle='--',
            label='Media movil ponderada')

    ax.plot(resultado['prediccion_fechas'], resultado['prediccion_valores'],
            color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=8,
            label='Prediccion')

    ax.axvspan(resultado['historico_fechas'][-1], resultado['prediccion_fechas'][-1],
               alpha=0.1, color=COLORES['peligro'])

    ax.legend(loc='upper left')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)

    info_texto = (
        f"Tendencia: {resultado['tendencia']} "
        f"({resultado['cambio_porcentaje']:+.1f}%) | "
        f"R2: {resultado['r_cuadrado']:.2f}"
    )
    ax.text(0.02, 0.95, info_texto, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    agregar_leyenda_inferior(fig,
        'Linea azul: dias reales de entrega historicos. '
        'Linea amarilla: media movil ponderada (da mas peso a datos recientes). '
        'Linea roja: prediccion de dias de entrega futuros. '
        'Si sube, se esperan entregas mas lentas.'
    )

    return fig


def grafico_escenario_consolidado():
    """
    Grafico 12: Escenario Futuro Consolidado
    Muestra todas las predicciones juntas en un solo grafico.
    """
    # Cargar datos
    demanda = get_demanda_mensual(limite=100)
    costos = get_costos_mensual(limite=500)
    demora = get_demora_entregas(limite=500)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.suptitle('Escenario Futuro - Todas las Predicciones', fontsize=14, fontweight='bold')

    info_textos = []

    # --- Subgrafico 1: Demanda ---
    ax1 = axes[0]
    if not demanda.empty:
        res1 = prediccion_completa(demanda, meses_futuros=3)
        if res1:
            ax1.plot(res1['historico_fechas'], res1['historico_valores'],
                     color=COLORES['primario'], linewidth=2, marker='o', markersize=3)
            ax1.plot(res1['prediccion_fechas'], res1['prediccion_valores'],
                     color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=6)
            ax1.set_title('Demanda', fontsize=11)
            ax1.set_ylabel('Solicitudes')
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
            info_textos.append(f"Demanda: {res1['tendencia']} ({res1['cambio_porcentaje']:+.1f}%)")

    # --- Subgrafico 2: Costos ---
    ax2 = axes[1]
    if not costos.empty:
        res2 = prediccion_costos(costos, meses_futuros=3)
        if res2:
            ax2.plot(res2['historico_fechas'], res2['historico_valores'],
                     color=COLORES['secundario'], linewidth=2, marker='D', markersize=3)
            ax2.plot(res2['prediccion_fechas'], res2['prediccion_valores'],
                     color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=6)
            ax2.set_title('Costos', fontsize=11)
            ax2.set_ylabel('Costo Promedio ($)')
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
            info_textos.append(f"Costos: {res2['tendencia']} ({res2['cambio_porcentaje']:+.1f}%)")

    # --- Subgrafico 3: Demora ---
    ax3 = axes[2]
    if not demora.empty:
        res3 = prediccion_demora(demora, meses_futuros=3)
        if res3:
            ax3.plot(res3['historico_fechas'], res3['historico_valores'],
                     color=COLORES['exito'], linewidth=2, marker='s', markersize=3)
            ax3.plot(res3['prediccion_fechas'], res3['prediccion_valores'],
                     color=COLORES['peligro'], linewidth=2, linestyle=':', marker='x', markersize=6)
            ax3.set_title('Demora Entregas', fontsize=11)
            ax3.set_ylabel('Dias')
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
            info_textos.append(f"Demora: {res3['tendencia']} ({res3['cambio_porcentaje']:+.1f}%)")

    plt.tight_layout()

    info_completa = ' | '.join(info_textos) if info_textos else 'Sin datos suficientes'
    agregar_leyenda_inferior(fig,
        f"Resumen de tendencias: {info_completa}. "
        "En cada grafico, la linea de color es el historico y la linea roja punteada es la prediccion."
    )

    return fig
