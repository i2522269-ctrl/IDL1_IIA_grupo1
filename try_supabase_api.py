import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

project_ref = 'buafaugwwcqsbrwaycro'
SUPABASE_TOKEN = os.getenv('SUPABASE_TOKEN')

if not SUPABASE_TOKEN:
    raise ValueError('Falta la variable SUPABASE_TOKEN en el archivo .env')

url = f'https://api.supabase.com/v1/projects/{project_ref}/database/query'
headers = {'Authorization': f'Bearer {SUPABASE_TOKEN}', 'Content-Type': 'application/json'}
payload = {'query': 'select 1;'}
r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
print('status', r.status_code)
print(r.text)
