# Consultas a la capa Gold (datos agregados para analisis y prediccion)

import pandas as pd
from config import get_cliente


def consultar_vista(nombre_vista, limite=1000):
    """Consulta una vista y la devuelve como DataFrame de pandas"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    datos = respuesta.data or []
    return pd.DataFrame(datos)


def get_kpi_generales():
    return consultar_vista('v_gold_kpi_generales', limite=1)


def get_demanda_mensual(limite=100):
    df = consultar_vista('v_gold_demanda_mensual', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_costos_mensual(limite=500):
    df = consultar_vista('v_gold_costos_mensual', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_inventario_estado(limite=500):
    return consultar_vista('v_gold_inventario_estado', limite)


def get_proveedores_ranking(limite=500):
    return consultar_vista('v_gold_proveedores_ranking', limite)


def get_top_articulos(limite=20):
    return consultar_vista('v_gold_top_articulos', limite)


def get_evolucion_grupo(limite=500):
    df = consultar_vista('v_gold_evolucion_grupo', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_demora_entregas(limite=500):
    df = consultar_vista('v_gold_demora_entregas', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df
