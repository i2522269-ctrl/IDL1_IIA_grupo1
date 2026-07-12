import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL') or 'https://buafaugwwcqsbrwaycro.supabase.co'
key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY') or os.getenv('SUPABASE_TOKEN')
print('URL', url)
print('KEY prefix', key[:10] if key else None)
client = create_client(url, key)
print('client created')
try:
    resp = client.table('grupos_sheet1').select('*').limit(5).execute()
    print('data count', len(resp.data))
    print(resp.data)
except Exception as exc:
    print(type(exc).__name__, exc)
