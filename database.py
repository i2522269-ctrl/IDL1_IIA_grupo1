import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")


def get_client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Faltan las variables SUPABASE_URL y SUPABASE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def test_connection(table_name="vulnerabilities"):
    client = get_client()
    response = client.table(table_name).select("*").limit(1).execute()
    print("Conexión a Supabase establecida con éxito.")
    return response.data


if __name__ == "__main__":
    try:
        rows = test_connection()
        print(rows)
    except Exception as exc:
        print(f"Error al conectar: {exc}")