# Consultas a la capa Bronze (tablas raw de Supabase)
# Estas son las tablas originales sin procesar

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def get_cliente():
    """Crea y devuelve un cliente de Supabase"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    return create_client(url, key)


def consultar_tabla(nombre_tabla, limite=100):
    """Consulta una tabla raw y devuelve los datos como lista de diccionarios"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_tabla).select('*').limit(limite).execute()
    return respuesta.data or []


def contar_filas(nombre_tabla):
    """Cuenta las filas de una tabla"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_tabla).select('*', count='exact').limit(0).execute()
    return len(respuesta.data)


# Funciones para cada tabla Bronze
def get_grupos(limite=100):
    return consultar_tabla('grupos_sheet1', limite)


def get_solicitudes(limite=100):
    return consultar_tabla('solicitudes_sheet1', limite)


def get_recepciones(limite=100):
    return consultar_tabla('recepcion_sheet1', limite)


def get_articulos(limite=100):
    return consultar_tabla('articulos_sheet1', limite)


def get_proveedores(limite=100):
    return consultar_tabla('proveedores_sheet1', limite)


def get_maestro(limite=100):
    return consultar_tabla('maestro_articulos_sheet1', limite)
