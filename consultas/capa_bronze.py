# Consultas a la capa Bronze (tablas raw de Supabase)

from config import get_cliente


def consultar_tabla(nombre_tabla, limite=100):
    """Consulta una tabla raw y devuelve los datos"""
    cliente = get_cliente()
    respuesta = cliente.table(nombre_tabla).select('*').limit(limite).execute()
    return respuesta.data or []


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
