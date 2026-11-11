"""Exercise a running backend using a temporary real account; remove it afterwards.
Usage: python scripts/smoke_wardrobe.py http://127.0.0.1:8000
"""
import http.cookiejar
import json
import secrets
import sys
import urllib.parse
import urllib.request

base = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8000'
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, data=None, *, method=None, token=None, csrf=None, timeout=15):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if csrf:
        headers['X-CSRFToken'] = csrf
    request = urllib.request.Request(base + path, data=json.dumps(data).encode() if data is not None else None,
                                     headers=headers, method=method)
    with client.open(request, timeout=timeout) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def main():
    credentials = {'username': 'smoke_' + secrets.token_hex(8), 'password': secrets.token_urlsafe(32)}
    csrf = call('/api/auth/session/')[1]['csrfToken']
    token = None
    created = False
    try:
        status, _ = call('/api/auth/register/', dict(credentials, display_name='Smoke'), csrf=csrf)
        assert status == 201
        created = True
        token = call('/api/auth/token/', credentials)[1]['access']
        _, profile = call('/api/profile/', {'city': 'Ташкент', 'cold_sensitivity': 4}, method='PATCH', token=token)
        assert profile['city'] == 'Ташкент'
        _, preferences = call('/api/preferences/', {'styles': ['Casual'], 'comfort_priority': 75}, method='PATCH', token=token)
        assert preferences['comfort_priority'] == 75
        categories = call('/api/categories/', token=token)[1]['results']
        category = categories[0]['id']
        status, item = call('/api/clothing/', {'name': 'Smoke shirt', 'category': category, 'styles': ['Casual']}, token=token)
        assert status == 201
        _, filtered = call('/api/clothing/?' + urllib.parse.urlencode({'search': 'Smoke', 'is_available': 'true'}), token=token)
        assert [row['id'] for row in filtered['results']] == [item['id']]
        url = f"/api/clothing/{item['id']}/"
        assert call(url, {'is_available': False}, method='PATCH', token=token)[1]['is_available'] is False
        assert call('/api/clothing/summary/', token=token)[1]['unavailable'] == 1
        assert call(url, method='DELETE', token=token)[0] == 204
        assert call('/api/clothing/summary/', token=token)[1]['total'] == 0
        print('HTTP wardrobe smoke passed: registration, JWT, profile, preferences, create/search/edit/delete, summary.')
    finally:
        if created:
            if token is None:
                token = call('/api/auth/token/', credentials)[1]['access']
            assert call('/api/account/', {'password': credentials['password']}, method='DELETE', token=token)[0] == 204
            print('Temporary account removed.')


if __name__ == '__main__':
    main()
