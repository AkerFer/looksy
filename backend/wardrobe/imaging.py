"""Local image pipeline. No photos are sent to external services."""
from functools import lru_cache
from io import BytesIO
import json
from pathlib import Path
import warnings

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings
from rest_framework.exceptions import ValidationError


def encode(image):
    # A new image strips EXIF, ICC, comments and appended payloads.
    clean = Image.new(image.mode, image.size)
    clean.paste(image)
    buffer = BytesIO()
    clean.save(buffer, format='PNG')
    return buffer.getvalue()


def decode(upload):
    if upload.size > settings.PHOTO_MAX_BYTES:
        raise ValidationError({'image': 'Изображение должно быть не больше 5 МБ.'})
    raw = upload.read(settings.PHOTO_MAX_BYTES + 1)
    if len(raw) > settings.PHOTO_MAX_BYTES:
        raise ValidationError({'image': 'Изображение должно быть не больше 5 МБ.'})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as probe:
                if probe.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValueError('format')
                if getattr(probe, 'n_frames', 1) != 1:
                    raise ValueError('animation')
                if probe.width * probe.height > settings.PHOTO_MAX_PIXELS or min(probe.size) < 32:
                    raise ValueError('dimensions')
                probe.verify()
            with Image.open(BytesIO(raw)) as source:
                source.load()
                image = ImageOps.exif_transpose(source).convert('RGBA')
        return image
    except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError({'image': 'Нужен корректный JPEG, PNG или WebP: один кадр, от 32 px, не больше 16 Мп.'}) from None


@lru_cache(maxsize=2)
def background_session(model_dir):
    from rembg import new_session
    # Must already exist: inference never downloads weights.
    import os
    os.environ['U2NET_HOME'] = model_dir
    import hashlib
    paths = [Path(model_dir) / 'models/u2netp/u2netp.onnx', Path(model_dir) / 'u2netp.onnx']
    weight = next(path for path in paths if path.is_file())
    if hashlib.md5(weight.read_bytes()).hexdigest() != '8e83ca70e441ab06c318d82300c84806':
        raise ValueError('Invalid u2netp checksum')
    return new_session('u2netp', providers=['CPUExecutionProvider'])


def remove_background(image):
    notices = []
    if image.getchannel('A').getextrema()[0] < 255:
        return image, 'existing_alpha', notices
    model_dir = settings.U2NET_HOME
    if any((Path(model_dir) / path).is_file() for path in ['models/u2netp/u2netp.onnx', 'u2netp.onnx']):
        try:
            from rembg import remove
            result = remove(image, session=background_session(model_dir))
            if result.getchannel('A').getbbox():
                return result, 'u2netp', notices
        except Exception:
            notices.append('Модель удаления фона недоступна; применён резервный алгоритм.')
    else:
        notices.append('Модель удаления фона не установлена; применён резервный алгоритм.')
    # GrabCut is a classical segmentation fallback, not clothing recognition.
    rgb = np.array(image.convert('RGB'))
    h, w = rgb.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    try:
        cv2.setRNGSeed(0)
        cv2.grabCut(rgb, mask, (max(1,w//20), max(1,h//20), w-max(2,w//10), h-max(2,h//10)),
                    np.zeros((1,65),np.float64), np.zeros((1,65),np.float64), 3, cv2.GC_INIT_WITH_RECT)
        alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype('uint8')
        ratio = np.count_nonzero(alpha) / alpha.size
        if 0.01 < ratio < 0.95:
            output = image.copy()
            output.putalpha(Image.fromarray(alpha))
            return output, 'grabcut', notices
    except cv2.error:
        pass
    notices.append('Фон не удалось надёжно отделить. Сохранено изображение с фоном.')
    return image, 'unchanged', notices


def center(image, size=1024):
    box = image.getchannel('A').getbbox()
    crop = image.crop(box) if box else image
    ratio = min(size * .88 / crop.width, size * .88 / crop.height)
    crop = crop.resize((max(1,round(crop.width * ratio)), max(1,round(crop.height * ratio))), Image.Resampling.LANCZOS)
    result = Image.new('RGBA', (size,size), (255,255,255,0))
    result.alpha_composite(crop, ((size-crop.width)//2, (size-crop.height)//2))
    return result


def palette(image):
    sample = image.copy()
    sample.thumbnail((128,128))
    values = np.array(sample)
    foreground = values[values[:,:,3] > 200][:,:3]
    if len(foreground) == 0:
        return []
    strip = Image.fromarray(foreground.reshape(1,-1,3)).quantize(colors=3)
    colors = strip.getpalette()
    return [{'hex': '#%02X%02X%02X' % tuple(colors[index*3:index*3+3]), 'share': round(count/len(foreground),3)}
            for count,index in sorted(strip.getcolors(), reverse=True)]


@lru_cache(maxsize=1)
def classifier(model_path, labels_path):
    import onnxruntime as ort
    labels = json.loads(Path(labels_path).read_text())
    if not isinstance(labels, list) or not labels or not all(isinstance(x,str) for x in labels):
        raise ValueError('Invalid labels')
    return ort.InferenceSession(model_path, providers=['CPUExecutionProvider']), labels


def recognize(image):
    # Optional trusted local ONNX classifier, NCHW float32 1x3x224x224, ImageNet normalization.
    model, labels_path = settings.CLOTHING_ONNX_MODEL, settings.CLOTHING_ONNX_LABELS
    unavailable = {'status': 'unavailable', 'category': None, 'season': None,
                   'message': 'Модель распознавания не установлена. Выберите категорию и сезон вручную.'}
    if not model or not labels_path:
        return unavailable
    try:
        session, labels = classifier(model, labels_path)
        rgb = Image.new('RGB', image.size, 'white')
        rgb.paste(image, mask=image.getchannel('A'))
        pixels = np.asarray(ImageOps.fit(rgb,(224,224)), dtype=np.float32) / 255
        pixels = (pixels - np.array([.485,.456,.406],dtype=np.float32)) / np.array([.229,.224,.225],dtype=np.float32)
        inputs = pixels.transpose(2,0,1)[None,...]
        logits = np.asarray(session.run(None, {session.get_inputs()[0].name: inputs})[0]).reshape(-1)
        if len(logits) != len(labels) or not np.isfinite(logits).all():
            raise ValueError('Invalid output')
        probabilities = np.exp(logits - logits.max())
        probabilities /= probabilities.sum()
        best = int(probabilities.argmax())
        confidence = float(probabilities[best])
        return {'status':'suggested' if confidence >= .7 else 'uncertain',
                'category':labels[best] if confidence >= .7 else None,
                'confidence':round(confidence,4), 'season':None,
                'message':'Предположение модели: проверьте вручную. Сезон и материал автоматически не определяются.'}
    except Exception:
        return dict(unavailable, status='error', message='Ошибка локальной модели. Выберите категорию и сезон вручную.')


def process(upload, avatar=False):
    image = decode(upload)
    # Retain the orientation-corrected original pixels, but never the untrusted source bytes/EXIF.
    original = encode(image)
    image.thumbnail((1024,1024), Image.Resampling.LANCZOS)
    if avatar:
        output = center(image,512)
        analysis = {'background':'not_requested','recognition':{'status':'not_requested'},'warnings':[]}
    else:
        output, method, notices = remove_background(image)
        analysis = {'background':method, 'recognition':recognize(output), 'colors':palette(output), 'warnings':notices}
        output = center(output)
    analysis['width'], analysis['height'] = output.size
    analysis['lighting'] = 'preserved'  # No guessed white-balance changes to clothing colors.
    return original, encode(output), analysis
