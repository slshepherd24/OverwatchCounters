"""OverwatchCounters: static site + cached server-side statistics gateway."""
import json, os, time, threading, urllib.request, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CACHE={}; LOCK=threading.Lock(); TTL=6*3600
HERO_KEYS={''.join(c for c in s.lower() if c.isalnum()) for s in ['D.Va','Doomfist','Junker Queen','Mauga','Orisa','Ramattra','Reinhardt','Roadhog','Sigma','Winston','Wrecking Ball','Zarya','Ashe','Bastion','Cassidy','Echo','Genji','Hanzo','Junkrat','Mei','Pharah','Reaper','Sojourn','Soldier: 76','Sombra','Symmetra','Torbjörn','Tracer','Venture','Widowmaker','Ana','Baptiste','Brigitte','Illari','Juno','Kiriko','Lifeweaver','Lúcio','Mercy','Moira','Zenyatta','Freja','Hazard','Juyang','Wuyang']}

def canon(s): return ''.join(c for c in str(s).lower() if c.isalnum())
def rate(v):
    try:
        n=float(str(v).strip().replace('%',''))
        return n if 0<=n<=100 else None
    except (ValueError,TypeError): return None

def parse_rows(data):
    if isinstance(data,list): rows=data
    elif isinstance(data,dict):
        rows=next((data[k] for k in ('data','heroes','results','rates') if k in data),[])
        if isinstance(rows,dict): rows=list(rows.values())
    else: rows=[]
    out={}
    for r in rows if isinstance(rows,list) else []:
        if not isinstance(r,dict): continue
        hero=r.get('name') or r.get('heroName') or r.get('hero_name') or r.get('hero')
        if isinstance(hero,dict):hero=hero.get('name')
        win=rate(next((r[k] for k in ('winRate','win_rate','winrate') if k in r),None))
        if win is None and isinstance(r.get('win'),dict): win=rate(r['win'].get('rate'))
        if win is None and isinstance(r.get('stats'),dict): win=rate(r['stats'].get('winRate'))
        if canon(hero) in HERO_KEYS and win is not None: out[canon(hero)]={'win':win}
    return out

def fetch_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'OverwatchSwapLab/1.0 (personal stats dashboard)','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=12) as r:
        if int(r.status)!=200: raise ValueError('Non-200 upstream response')
        if int(r.headers.get('Content-Length','0'))>4_000_000:raise ValueError('Response too large')
        return json.loads(r.read(4_000_001))

def retrieve(region,platform,rank,mapname):
    params={'input':platform,'map':'all-maps' if mapname=='Unknown' else '-'.join(mapname.lower().split()),'region':region,'role':'All','rq':'2','tier':rank}
    url='https://overwatch.blizzard.com/en-us/rates/data/?'+urllib.parse.urlencode(params)
    try:
        rates=parse_rows(fetch_json(url))
        if len(rates)>=8:return {'rates':rates,'meta':{'source':'Blizzard','label':f'Official · {rank} · {mapname} · {region}','rank':rank,'map':mapname,'region':region,'platform':platform,'updated':None}}
    except Exception as exc: print('Official feed unavailable:',type(exc).__name__,flush=True)
    if platform=='PC':
        try:
            data=fetch_json('https://cycalo.github.io/ow-stats-data/ow_rates.json')
            roles=((data.get('regions') or {}).get(region) or {}).get('roles') or data.get('roles') or {}
            rows=[r for v in roles.values() if isinstance(v,list) for r in v]
            rates=parse_rows(rows)
            if len(rates)>=8:return {'rates':rates,'meta':{'source':'Community snapshot','label':f'Community snapshot · All ranks · All maps · PC · {region}','rank':'All','map':'All maps','region':region,'platform':'PC','updated':data.get('lastUpdated')}}
        except Exception as exc: print('Backup feed unavailable:',type(exc).__name__,flush=True)
    return {'rates':{},'meta':None,'error':'No compatible statistics feed available. Strategic scoring remains available.'}

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_GET(self):
        u=urllib.parse.urlsplit(self.path)
        if u.path!='/api/stats':return super().do_GET()
        q=urllib.parse.parse_qs(u.query)
        def pick(k,default,valid):
            v=q.get(k,[default])[0];return v if v in valid else default
        region=pick('region','Americas',{'Americas','Europe','Asia'})
        platform=pick('platform','PC',{'PC','Console'})
        rank=pick('rank','Platinum',{'Bronze','Silver','Gold','Platinum','Diamond','Master','Grandmaster','Champion'})
        mapname=q.get('map',['Unknown'])[0][:80]
        if not all(c.isalnum() or c in ' -:’\'' for c in mapname):mapname='Unknown'
        key=(region,platform,rank,mapname);now=time.time()
        with LOCK: cached=CACHE.get(key)
        if cached and now-cached[0]<TTL: data=cached[1]
        else:
            data=retrieve(*key)
            if data.get('meta'):
                with LOCK:CACHE[key]=(now,data)
            elif cached:data=cached[1].copy();data['stale']=True
        body=json.dumps(data).encode()
        self.send_response(200 if data.get('meta') else 503)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)

if __name__=='__main__':
    port=int(os.environ.get('PORT','8000'))
    print(f'OverwatchCounters: http://localhost:{port}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
