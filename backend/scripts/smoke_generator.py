"""HTTP generation test with a temporary real wardrobe; removes account afterwards."""
import secrets
import sys
import smoke_wardrobe
from smoke_wardrobe import call


def main():
    smoke_wardrobe.base = sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:8000'
    credentials={'username':'generate_smoke_'+secrets.token_hex(6),'password':secrets.token_urlsafe(32)}
    csrf=call('/api/auth/session/')[1]['csrfToken']
    call('/api/auth/register/',credentials,csrf=csrf)
    token=None
    try:
        token=call('/api/auth/token/',credentials)[1]['access']
        categories=call('/api/categories/',token=token)[1]['results']
        category_by_slot={item['slot']:item['id'] for item in categories}
        ids=[]
        for slot in ['top','top','bottom','dress','shoes','outerwear']:
            item=call('/api/clothing/',{'name':'Smoke '+slot,'category':category_by_slot[slot],'styles':['casual'],'comfort':4,'warmth':3},token=token)[1]
            ids.append(item['id'])
        status,result=call('/api/outfits/generate/',{'count':3,'required_items':[ids[2]],'excluded_items':[ids[1]],'temperature_c':20},token=token)
        assert status==201
        assert result['count']==2, result
        for outfit in result['results']:
            assert ids[2] in outfit['items'] and ids[1] not in outfit['items']
            assert set(outfit['items']) <= set(ids)
            assert not outfit['generation_is_stale']
            assert 0 <= outfit['generation']['score'] <= 100
        chosen=result['results'][0]
        assert call('/api/saved-outfits/',{'outfit':chosen['id']},token=token)[0]==201
        history=call('/api/outfits/',token=token)[1]
        assert history['count']==2
        call(f"/api/clothing/{ids[2]}/",{'comfort':2},method='PATCH',token=token)
        assert call(f"/api/outfits/{chosen['id']}/",token=token)[1]['generation_is_stale']
        print('HTTP generator passed: real items, constraints, ranking, history, favorites, stale-score detection.')
    finally:
        if token is None:
            token=call('/api/auth/token/',credentials)[1]['access']
        assert call('/api/account/',{'password':credentials['password']},method='DELETE',token=token)[0]==204
        print('Temporary account and wardrobe removed.')

if __name__=='__main__':
    main()
