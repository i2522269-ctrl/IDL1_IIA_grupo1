import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_TOKEN = os.getenv("SUPABASE_TOKEN")

if not SUPABASE_TOKEN:
    raise ValueError("Falta la variable SUPABASE_TOKEN en el archivo .env")

url = 'https://api.supabase.com/v1/projects/buafaugwwcqsbrwaycro/database/config'
headers = {'Authorization': f'Bearer {SUPABASE_TOKEN}', 'Content-Type': 'application/json'}
r = requests.get(url, headers=headers, timeout=30)
print('status', r.status_code)
print(r.text[:4000])
