import os
import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

st.set_page_config(page_title="IDL1 IIA", page_icon="🛡️", layout="wide")
st.title("Proyecto IDL1 IIA")
st.write("Conexión básica con Supabase")

supabase_url = os.getenv("SUPABASE_URL") or os.getenv("SUPABASE_DB_URL")
supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    st.error("No se encontraron las variables de entorno para Supabase.")
    st.stop()

client = create_client(supabase_url, supabase_key)

try:
    response = client.table("grupos_sheet1").select("*").limit(10).execute()
    data = response.data or []
    st.success("Conexión a Supabase establecida")
    st.dataframe(data)
except Exception as exc:
    st.error(f"No se pudo consultar Supabase: {exc}")
