import os, sys, urllib.request, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath('D:\facebook\ApexNotification\scripts\tg_alert.py'))))
def _load_env():
    try:
        from config import BOT_TOKEN, ADMIN_IDS
        return BOT_TOKEN, ADMIN_IDS
    except Exception:
        pass
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    token = ''
    admin_ids = []
    if os.path.exists(env_path):
        with open(env_path, encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                if line.startswith('BOT_TOKEN='): token = line.split('=',1)[1].strip()
                elif line.startswith('ADMIN_IDS='): admin_ids=[int(x.strip()) for x in line.split('=',1)[1].strip().split(',') if x.strip().isdigit()]
    return token, admin_ids
def send_alert(text):
    token, admin_ids = _load_env()
    if not token or not admin_ids: return
    for admin_id in admin_ids:
        try:
            payload=urllib.parse.urlencode({'chat_id':str(admin_id),'text':text,'parse_mode':'HTML'}).encode('utf-8')
            req=urllib.request.Request(f'https://api.telegram.org/bot{token}/sendMessage',data=payload,method='POST',headers={'Content-Type':'application/x-www-form-urlencoded'})
            urllib.request.urlopen(req,timeout=10)
        except Exception: pass
if __name__=='__main__':
    import sys
    if len(sys.argv)<2: print('Usage: python scripts/tg_alert.py "msg"'); sys.exit(1)
    send_alert(' '.join(sys.argv[1:]))
    print('[tg_alert] Sent: '+' '.join(sys.argv[1:])[:80])