"""HTTP photo lifecycle smoke test. Creates then deletes a temporary account."""
from io import BytesIO
import secrets
import sys
import urllib.request
from PIL import Image, ImageDraw
from smoke_wardrobe import call, client
import smoke_wardrobe


def main():
    smoke_wardrobe.base = sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:8000'
    credentials={'username':'photo_smoke_'+secrets.token_hex(6),'password':secrets.token_urlsafe(32)}
    csrf=call('/api/auth/session/')[1]['csrfToken']
    call('/api/auth/register/',credentials,csrf=csrf)
    token=None
    try:
        token=call('/api/auth/token/',credentials)[1]['access']
        image=Image.new('RGB',(256,256),'white')
        ImageDraw.Draw(image).rectangle((64,32,192,224),fill='blue')
        buffer=BytesIO(); image.save(buffer,format='JPEG')
        boundary='looksy'+secrets.token_hex(10)
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="test.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()+buffer.getvalue()+f'\r\n--{boundary}--\r\n'.encode())
        request=urllib.request.Request(smoke_wardrobe.base+'/api/clothing/from-photo/',data=body,headers={'Content-Type':'multipart/form-data; boundary='+boundary,'Authorization':'Bearer '+token})
        import json
        with client.open(request,timeout=120) as response:
            assert response.status==201
            item=json.load(response)
        photo=item['photo']
        assert photo['analysis']['background']=='u2netp', photo['analysis']
        for url in [photo['url'],photo['original_url']]:
            request=urllib.request.Request(smoke_wardrobe.base+url,headers={'Authorization':'Bearer '+token})
            with client.open(request,timeout=15) as response:
                assert response.headers['Cache-Control']=='private, no-store'
                output=Image.open(BytesIO(response.read()))
                assert output.format=='PNG'
                assert not output.getexif()
        assert call(f"/api/clothing/{item['id']}/",method='DELETE',token=token)[0]==204
        print('HTTP photo smoke passed: upload, card, actual u2netp, private original/processed, delete.')
        print('Recognition status:',photo['analysis']['recognition']['status'])
    finally:
        if token is None:
            token=call('/api/auth/token/',credentials)[1]['access']
        assert call('/api/account/',{'password':credentials['password']},method='DELETE',token=token)[0]==204
        print('Temporary account removed.')

if __name__=='__main__':
    main()
