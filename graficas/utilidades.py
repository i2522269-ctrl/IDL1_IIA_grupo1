# Utilidades compartidas para los graficos
# Funciones de formato, estilos y leyendas

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Para que no intente abrir ventanas


# Colores del proyecto (bonitos pero simples)
COLORES = {
    'primario': '#2196F3',      # Azul
    'secundario': '#FF9800',    # Naranja
    'exito': '#4CAF50',         # Verde
    'peligro': '#F44336',       # Rojo
    'advertencia': '#FFC107',   # Amarillo
    'gris': '#9E9E9E',          # Gris
    'purpura': '#9C27B0',       # Purpura
}

# Lista de colores para graficos con varias series
COLORES_SERIES = ['#2196F3', '#FF9800', '#4CAF50', '#F44336', '#9C27B0', '#00BCD4', '#FF5722', '#795548']


def configurar_grafico(titulo, xlabel='', ylabel='', tamanho=(10, 5)):
    """
    Configura basico de un grafico matplotlib.
    Retorna la figura y los ejes para seguir trabajando.
    """
    fig, ax = plt.subplots(figsize=tamanho)
    ax.set_title(titulo, fontsize=14, fontweight='bold', pad=15)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    return fig, ax


def agregar_leyenda_inferior(fig, texto_leyenda):
    """
    Agrega una leyenda explicativa en la parte inferior del grafico.
    Esto ayuda a entender que muestra el grafico.
    """
    fig.text(
        0.5, -0.08,       # Posicion: centrado horizontal, abajo del grafico
        texto_leyenda,
        ha='center',       # Alineacion horizontal centrada
        va='top',          # Alineacion vertical arriba del texto
        fontsize=9,
        style='italic',
        color='#555555',
        wrap=True,
        bbox=dict(
            boxstyle='round,pad=0.5',
            facecolor='lightyellow',
            edgecolor='#CCCCCC',
            alpha=0.8
        )
    )
    fig.subplots_adjust(bottom=0.22)  # Dejar espacio para la leyenda


def formato_numero(numero):
    """Formatea un numero con separadores de miles"""
    if numero is None:
        return '0'
    if isinstance(numero, float):
        return f'{numero:,.2f}'
    return f'{numero:,}'


def formato_moneda(numero):
    """Formatea un numero como moneda"""
    if numero is None:
        return '$0'
    return f'${numero:,.2f}'


def guardar_grafico(fig, nombre_archivo, dpi=150):
    """Guarda el grafico como imagen PNG"""
    fig.savefig(nombre_archivo, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'Grafico guardado: {nombre_archivo}')
