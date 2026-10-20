"""ExchangeRate-API Open Access proxy. Fixed HTTPS host; no browser credentials."""
import json,math
from datetime import datetime,timezone,timedelta
from urllib.request import urlopen,Request
from ..finance.transactions import fail,now
CURRENCIES=('BDT','USD','EUR','GBP','INR','JPY','CAD','AUD','SAR','AED')
SOURCE='ExchangeRate-API Open Access'

def fetch_rates(base):
    req=Request('https://open.er-api.com/v6/latest/'+base,headers={'User-Agent':'FINCEPT/1.0'})
    with urlopen(req,timeout=8) as response:
        data=json.loads(response.read(200000))
    if data.get('result')!='success' or data.get('base_code')!=base:raise ValueError('Invalid provider response')
    stamp=datetime.fromtimestamp(data['time_last_update_unix'],timezone.utc)
    if stamp>datetime.now(timezone.utc)+timedelta(minutes=10) or stamp<datetime.now(timezone.utc)-timedelta(hours=48):raise ValueError('Provider timestamp unavailable or outdated')
    rates={k:data['rates'][k] for k in CURRENCIES}
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in rates.values()) or rates[base]!=1:raise ValueError('Invalid provider rates')
    return dict(base=base,rates=rates,as_of=stamp.isoformat(),source=SOURCE,source_url='https://www.exchangerate-api.com/docs/free',fetched_at=now())

def rates(db,base):
    current=datetime.now(timezone.utc)
    with db() as c:row=c.execute('SELECT * FROM hub_fx_cache WHERE base=?',(base,)).fetchone()
    cached=json.loads(row['payload']) if row else None
    if cached and current-datetime.fromisoformat(cached['fetched_at'])<timedelta(hours=1) and current-datetime.fromisoformat(cached['as_of'])<timedelta(hours=48):return cached|{'status':'cached'}
    try:
        data=fetch_rates(base)
        with db() as c:c.execute('INSERT OR REPLACE INTO hub_fx_cache VALUES (?,?,?)',(base,json.dumps(data),data['fetched_at']))
        return data|{'status':'live'}
    except Exception:
        if cached and current-datetime.fromisoformat(cached['as_of'])<timedelta(hours=48):return cached|{'status':'stale','warning':'Provider unavailable. Showing a previously retrieved rate; do not rely on it for a transfer.'}
        fail('Exchange rates are unavailable. No estimated or sample rate has been substituted. Please retry.',503)
