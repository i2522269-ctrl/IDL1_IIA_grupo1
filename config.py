# Configuracion central del proyecto
# Busca el .env en la carpeta del proyecto sin importar desde donde se ejecute

import os
from dotenv import load_dotenv
from supabase import create_client

# Buscar .env en la carpeta donde esta este archivo
_CARPETA_PROYECTO = os.path.dirname(os.path.abspath(__file__))
_RUTA_ENV = os.path.join(_CARPETA_PROYECTO, '.env')

load_dotenv(dotenv_path=_RUTA_ENV)


def get_cliente():
    """Crea y devuelve un cliente de Supabase"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    if not url or not key:
        raise ValueError(
            f'Faltan variables de entorno. '
            f'Buscado en: {_RUTA_ENV}'
        )
    return create_client(url, key)
