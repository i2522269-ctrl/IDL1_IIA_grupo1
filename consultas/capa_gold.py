# Consultas a la capa Gold (datos agregados para analisis y prediccion)
# Estas vistas tienen los KPIs, metricas y datos listos para graficar

import os
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

load_dotenv()


def get_cliente():
    """Crea y devuelve un cliente de Supabase"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    return create_client(url, key)


def consultar_vista(nombre_vista, limite=1000):
    """Consulta una vista y la devuelve como DataFrame de pandas"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    datos = respuesta.data or []
    return pd.DataFrame(datos)


def consultar_vista_lista(nombre_vista, limite=1000):
    """Consulta una vista y la devuelve como lista"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    return respuesta.data or []


# ---- Funciones para cada vista Gold ----

def get_kpi_generales():
    """Devuelve los KPIs generales del negocio"""
    return consultar_vista('v_gold_kpi_generales', limite=1)


def get_demanda_mensual(limite=100):
    """Devuelve la demanda mensual para series de tiempo"""
    df = consultar_vista('v_gold_demanda_mensual', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_costos_mensual(limite=500):
    """Devuelve los costos mensuales por grupo"""
    df = consultar_vista('v_gold_costos_mensual', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_inventario_estado(limite=500):
    """Devuelve el estado actual del inventario"""
    return consultar_vista('v_gold_inventario_estado', limite)


def get_proveedores_ranking(limite=500):
    """Devuelve el ranking de proveedores"""
    return consultar_vista('v_gold_proveedores_ranking', limite)


def get_top_articulos(limite=20):
    """Devuelve los articulos mas solicitados"""
    return consultar_vista('v_gold_top_articulos', limite)


def get_evolucion_grupo(limite=500):
    """Devuelve la evolucion mensual por grupo"""
    df = consultar_vista('v_gold_evolucion_grupo', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df


def get_demora_entregas(limite=500):
    """Devuelve la demora de entregas por mes y proveedor"""
    df = consultar_vista('v_gold_demora_entregas', limite)
    if 'mes' in df.columns:
        df['mes'] = pd.to_datetime(df['mes'])
        df = df.sort_values('mes')
    return df
