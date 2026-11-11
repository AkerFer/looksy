"""Small bounded JSON transport. Keep inherited proxies and TLS verification."""
import json
import requests

class ServiceUnavailable(Exception):
    pass


def json_request(method, url, *, params=None, payload=None, timeout=(3,8), limit=512_000, retries=0):
    for attempt in range(retries+1):
        try:
            with requests.request(method,url,params=params,json=payload,timeout=timeout,allow_redirects=False,stream=True) as response:
                if response.status_code >= 500 and attempt < retries:
                    continue
                if response.status_code != 200:
                    raise ServiceUnavailable('Сервис недоступен.')
                chunks=[]; size=0
                for chunk in response.iter_content(chunk_size=16384):
                    size += len(chunk)
                    if size > limit:
                        raise ServiceUnavailable('Слишком большой ответ сервиса.')
                    chunks.append(chunk)
                result=json.loads(b''.join(chunks))
                if not isinstance(result,dict):
                    raise ServiceUnavailable('Некорректный ответ сервиса.')
                return result
        except (requests.RequestException,ValueError) as exc:
            if attempt == retries:
                raise ServiceUnavailable('Не удалось подключиться к сервису или прочитать ответ.') from None
    raise ServiceUnavailable('Сервис недоступен.')
