# Graficos de Estado Actual
# Muestran como esta el negocio ahora: KPIs, distribuciones, inventario

import matplotlib.pyplot as plt
import sys
import os

# Para poder importar desde la carpeta consultas
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from graficas.utilidades import (
    configurar_grafico, agregar_leyenda_inferior,
    COLORES, COLORES_SERIES, formato_numero, formato_moneda
)
from consultas.capa_gold import (
    get_kpi_generales, get_top_articulos, get_proveedores_ranking,
    get_inventario_estado, get_demanda_mensual
)


def grafico_kpi_generales():
    """
    Grafico 1: KPIs Generales
    Muestra las metricas principales del negocio en barras.
    """
    kpi = get_kpi_generales()
    if kpi.empty:
        print('No hay datos de KPIs')
        return None

    kpi = kpi.iloc[0]

    # Preparar datos
    categorias = ['Solicitudes', 'Recepciones', 'Articulos', 'Proveedores']
    valores = [
        kpi.get('total_solicitudes', 0),
        kpi.get('total_recepciones', 0),
        kpi.get('total_articulos', 0),
        kpi.get('total_proveedores', 0),
    ]
    colores = [COLORES['primario'], COLORES['exito'], COLORES['secundario'], COLORES['purpura']]

    fig, ax = configurar_grafico(
        'Metricas Generales del Negocio',
        ylabel='Cantidad'
    )

    barras = ax.bar(categorias, valores, color=colores, edgecolor='white', linewidth=1.5)

    # Agregar valores encima de cada barra
    for barra, valor in zip(barras, valores):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + max(valores) * 0.02,
            formato_numero(valor),
            ha='center', va='bottom',
            fontweight='bold', fontsize=10
        )

    ax.set_ylim(0, max(valores) * 1.15)

    agregar_leyenda_inferior(fig,
        'Este grafico muestra las metricas principales: total de solicitudes de compra, '
        'recepciones realizadas, articulos en catalogo y proveedores activos.'
    )

    return fig


def grafico_distribucion_grupos():
    """
    Grafico 2: Distribucion por Grupo de Inventario
    Muestra que porcentaje de solicitudes corresponde a cada grupo.
    """
    demanda = get_demanda_mensual(limite=1000)
    if demanda.empty:
        print('No hay datos de demanda')
        return None

    # Agrupar por grupo
    por_grupo = demanda.groupby('nombre_grupo')['monto_total'].sum().sort_values(ascending=False)
    por_grupo = por_grupo.head(8)  # Top 8 grupos

    fig, ax = configurar_grafico(
        'Distribucion de Solicitudes por Grupo de Inventario',
        tamanho=(10, 6)
    )

    wedges, texts, autotexts = ax.pie(
        por_grupo.values,
        labels=por_grupo.index,
        autopct='%1.1f%%',
        colors=COLORES_SERIES[:len(por_grupo)],
        startangle=90,
        pctdistance=0.85
    )

    # Hacer el texto mas readable
    for text in texts:
        text.set_fontsize(9)
    for autotext in autotexts:
        autotext.set_fontsize(8)
        autotext.set_fontweight('bold')

    agregar_leyenda_inferior(fig,
        'Este grafico muestra el porcentaje de solicitudes por cada grupo de inventario. '
        'Los grupos con mayor porcentaje son los que mas se solicitan.'
    )

    return fig


def grafico_top_proveedores():
    """
    Grafico 3: Top 10 Proveedores
    Muestra los proveedores con mas recepciones.
    """
    proveedores = get_proveedores_ranking(limite=10)
    if proveedores.empty:
        print('No hay datos de proveedores')
        return None

    fig, ax = configurar_grafico(
        'Top 10 Proveedores por Volumen de Recepciones',
        xlabel='Cantidad de Recepciones',
        ylabel='',
        tamanho=(10, 6)
    )

    # Invertir para que el mayor quede arriba
    nombres = proveedores['razon_social'].iloc[::-1]
    recepciones = proveedores['total_recepciones'].iloc[::-1]
    categorias = proveedores['categoria_proveedor'].iloc[::-1]

    colores_barra = []
    for cat in categorias:
        if 'A' in str(cat):
            colores_barra.append(COLORES['exito'])
        elif 'B' in str(cat):
            colores_barra.append(COLORES['secundario'])
        else:
            colores_barra.append(COLORES['gris'])

    barras = ax.barh(nombres, recepciones, color=colores_barra, edgecolor='white')

    for barra, valor in zip(barras, recepciones):
        ax.text(
            barra.get_width() + max(recepciones) * 0.01,
            barra.get_y() + barra.get_height() / 2,
            formato_numero(valor),
            ha='left', va='center',
            fontsize=9
        )

    agregar_leyenda_inferior(fig,
        'Los proveedores se clasifican en: A = Alto volumen (mas de 1000 recepciones), '
        'B = Volumen medio (500-1000), C = Volumen bajo (menos de 500). '
        'El color indica la categoria del proveedor.'
    )

    return fig


def grafico_inventario_almacen():
    """
    Grafico 4: Inventario por Almacen
    Muestra la cantidad de articulos por ubicacion de almacen.
    """
    inventario = get_inventario_estado(limite=1000)
    if inventario.empty:
        print('No hay datos de inventario')
        return None

    # Agrupar por ubicacion
    por_ubicacion = inventario.groupby('ubicacion_almacen').agg({
        'codigo_articulo': 'count',
        'valor_inventario': 'sum'
    }).reset_index()
    por_ubicacion.columns = ['ubicacion', 'cantidad', 'valor']
    por_ubicacion = por_ubicacion.sort_values('cantidad', ascending=False).head(10)

    fig, ax = configurar_grafico(
        'Inventario por Ubicacion de Almacen',
        xlabel='Ubicacion',
        ylabel='Cantidad de Articulos',
        tamanho=(10, 5)
    )

    barras = ax.bar(
        por_ubicacion['ubicacion'].astype(str),
        por_ubicacion['cantidad'],
        color=COLORES['primario'],
        edgecolor='white'
    )

    for barra, valor in zip(barras, por_ubicacion['cantidad']):
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            barra.get_height() + 5,
            str(int(valor)),
            ha='center', va='bottom',
            fontsize=9, fontweight='bold'
        )

    agregar_leyenda_inferior(fig,
        'Muestra la cantidad de articulos distintos que hay en cada ubicacion de almacen. '
        'Las ubicaciones con mas articulos son las que mayor variedad manejan.'
    )

    return fig
