# Consultas a la capa Silver (datos limpios y estandarizados)
# Estas vistas ya tienen fechas, montos y nombres normalizados

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


def consultar_vista(nombre_vista, limite=500):
    """Consulta una vista y la devuelve como DataFrame de pandas"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    datos = respuesta.data or []
    return pd.DataFrame(datos)


def consultar_vista_lista(nombre_vista, limite=500):
    """Consulta una vista y la devuelve como lista de diccionarios"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    return respuesta.data or []


# ---- Funciones para cada vista Silver ----

def get_silver_grupos(limite=100):
    return consultar_vista('v_silver_grupos', limite)


def get_silver_solicitudes(limite=500):
    return consultar_vista('v_silver_solicitudes', limite)


def get_silver_recepciones(limite=500):
    return consultar_vista('v_silver_recepciones', limite)


def get_silver_articulos(limite=500):
    return consultar_vista('v_silver_articulos', limite)


def get_silver_proveedores(limite=500):
    return consultar_vista('v_silver_proveedores', limite)


def get_silver_maestro(limite=500):
    return consultar_vista('v_silver_maestro', limite)
