import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables desde el archivo .env
load_dotenv()

# Obtener credenciales de forma segura
SUPABASE_URL = "https://buafaugwwcqsbrwaycro.supabase.co" # Tu URL de proyecto
SUPABASE_KEY = os.getenv("buafaugwwcqsbrwaycro")

# Inicializar cliente
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    try:
        # Prueba simple para verificar conexión
        response = supabase.table("vulnerabilities").select("*").limit(1).execute()
        print("Conexión a Supabase establecida con éxito.")
    except Exception as e:
        print(f"Error al conectar: {e}")

if __name__ == "__main__":
    test_connection()