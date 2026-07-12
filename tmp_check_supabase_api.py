import os, requests
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('SUPABASE_TOKEN') or os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY')
print('token present', bool(token))
if token:
    print('token prefix', token[:15])
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
    url = 'https://api.supabase.com/v1/projects/buafaugwwcqsbrwaycro/database/config'
    r = requests.get(url, headers=headers, timeout=60)
    print('status', r.status_code)
    print(r.text[:4000])
