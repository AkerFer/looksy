"""Real HTTP weather/AI check. Outages are reported, never counted as live success.
Optional --require-live fails unless both weather and Ollama return live data.
"""
import json
import secrets
import sys
import urllib.error
import smoke_wardrobe
from smoke_wardrobe import call as base_call

def call(*args, **kwargs):
    return base_call(*args, **kwargs, timeout=90)


def safe_call(*args,**kwargs):
    try:
        return call(*args,**kwargs)
    except urllib.error.HTTPError as exc:
        return exc.code,json.loads(exc.read())


def main():
    smoke_wardrobe.base=sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:8000'
    required='--require-live' in sys.argv
    credentials={'username':'services_'+secrets.token_hex(6),'password':secrets.token_urlsafe(32)}
    csrf=call('/api/auth/session/')[1]['csrfToken']
    call('/api/auth/register/',credentials,csrf=csrf)
    token=None
    try:
        token=call('/api/auth/token/',credentials)[1]['access']
        call('/api/profile/',{'city':'Ташкент','latitude':'41.31108','longitude':'69.24056'},method='PATCH',token=token)
        categories=call('/api/categories/',token=token)[1]['results']
        slots={row['slot']:row['id'] for row in categories}
        for slot in ['top','bottom','shoes','outerwear']:
            call('/api/clothing/',{'name':'Service smoke '+slot,'category':slots[slot],'comfort':4,'warmth':3},token=token)
        weather_status,data=safe_call('/api/weather/forecast/',{'latitude':'41.31108','longitude':'69.24056'},token=token)
        assert weather_status in (200,503)
        print('Live Open-Meteo:', 'OK' if weather_status==200 else 'UNAVAILABLE (503), error handling verified')
        _,result=call('/api/outfits/generate/',{'use_weather':True},token=token)
        assert result['count']>0
        if result['weather_status']=='unavailable':
            assert result['weights']['weather']==0 and result['weather'] is None
        _,stylist=call('/api/stylist/',{'message':'Что надеть?'},token=token)
        assert stylist['source'] in ('rules','ollama')
        print('Live Ollama:', 'OK' if stylist['source']=='ollama' else 'UNAVAILABLE, local rules fallback verified')
        print('HTTP service workflow passed; generation weather status:',result['weather_status'])
        if required:
            assert weather_status==200 and stylist['source']=='ollama','Live services are unavailable.'
    finally:
        if token is None:
            token=call('/api/auth/token/',credentials)[1]['access']
        assert call('/api/account/',{'password':credentials['password']},method='DELETE',token=token)[0]==204
        print('Temporary account removed.')

if __name__=='__main__':
    main()
