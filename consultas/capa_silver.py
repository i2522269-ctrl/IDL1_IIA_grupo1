# Consultas a la capa Silver (datos limpios y estandarizados)

import pandas as pd
from config import get_cliente


def consultar_vista(nombre_vista, limite=500):
    """Consulta una vista y la devuelve como DataFrame"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_vista).select('*').limit(limite).execute()
    datos = respuesta.data or []
    return pd.DataFrame(datos)


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
